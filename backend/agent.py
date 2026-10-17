"""LangChain conversational car advisor with game-like progressive narrowing.

Uses ChatOpenAI when OPENAI_API_KEY is set; otherwise a deterministic
rule-based advisor that still drives the same tools and stages (demo mode).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from catalog import get_car, list_cars
from dealers import (
    default_group_id,
    load_group,
    public_group_config,
    resolve_group,
)
from ev_tradeoffs import DEFAULT_ASSUMPTIONS, advise_ev_vs_gas, fuel_category, summarize_tradeoffs
from recommendation_engine import (
    PreferenceState,
    STAGE_PROMPTS,
    apply_choice,
    next_stage_payload,
    rank_cars,
)
from roi_calculator import calculate_ev_roi, roi_from_cars

# Optional LangChain imports — kept soft so the app boots without the package
# during partial installs; requirements.txt pins the real deps.
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError:  # pragma: no cover
    LANGCHAIN_AVAILABLE = False
    tool = None  # type: ignore


SESSIONS: dict[str, dict[str, Any]] = {}


SYSTEM_PROMPT = """You are DriveQuest — a veteran car salesperson who does NOT care about commission,
closing a deal, or steering someone into a higher trim. Your only success metric is whether
this buyer ends up in the car that best fits THEIR life: budget, reliability, value, and
day-to-day needs.

Persona:
- Warm, plain-spoken, and honest. You know the lot and the tradeoffs, but you never upsell.
- If a cheaper / used / smaller car is the better fit, say so clearly.
- If something is a bad idea for them (wrong body style, shaky reliability, EV without home charging), say that too.
- Ask one clarifying question when something important is missing (commute, parking, winters, passengers).
- No jargon unless you immediately translate it. Prefer “running costs” over “TCO”, “break-even” over “ROI” unless they used that word first.

How you help (progressive quest):
1) Budget  2) Body style  3) What matters most  4) New vs used  5) Compare options  6) Best match
Guide them one step at a time. Celebrate progress lightly — this should feel like narrowing choices, not filling a form.

Metrics you may cite (from tools / hex chart): value, budget fit, reliability, efficiency, safety, practicality.
EV vs gas: charging, energy cost, maintenance, incentives, range/cold weather, resale. Use explain_ev_tradeoffs
and calculate_ev_roi when relevant — never invent break-even numbers or inventory.

Style:
- 2–4 short sentences, then a clear next action (“Tap a budget” / “Want me to show the best match?”).
- Be encouraging without pressure. Never invent prices, scores, or cars — trust tool output.
"""


def _system_prompt_for(group: dict[str, Any], location_id: str | None = None) -> str:
    name = group.get("name") or "this dealership group"
    note = group.get("persona_note") or f"You only recommend cars currently in the {name} inventory."
    loc_note = ""
    if location_id:
        for loc in group.get("locations") or []:
            if loc["id"] == location_id:
                loc_note = (
                    f" This embed is scoped to the {loc.get('name') or location_id} rooftop — "
                    "prefer vehicles at this location, and say so when a better group-wide fit exists elsewhere."
                )
                break
    return (
        SYSTEM_PROMPT
        + f"\n\nDealer group context: You are embedded for {name}. "
        + f"{note}{loc_note} Inventory is limited to this group's stock — never invent vehicles."
    )


def _session(
    session_id: str | None,
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    sid = session_id or str(uuid.uuid4())
    gid = group_id or dealer_id
    if sid not in SESSIONS:
        resolved = gid or default_group_id()
        SESSIONS[sid] = {
            "group_id": resolved,
            "dealer_id": resolved,
            "location_id": location_id,
            "prefs": PreferenceState().to_dict(),
            "messages": [],
            "last_contenders": [],
            "last_roi": None,
        }
    else:
        existing_gid = SESSIONS[sid].get("group_id") or SESSIONS[sid].get("dealer_id")
        if gid and existing_gid != gid:
            raise ValueError("session belongs to a different dealer group")
        if location_id is not None and SESSIONS[sid].get("location_id") not in (None, location_id):
            # Allow first pin; reject silent rooftop switches
            if SESSIONS[sid].get("location_id") and SESSIONS[sid].get("location_id") != location_id:
                raise ValueError("session belongs to a different location")
        if location_id and not SESSIONS[sid].get("location_id"):
            SESSIONS[sid]["location_id"] = location_id
    return sid, SESSIONS[sid]


def _group_id(state: dict[str, Any]) -> str:
    return state.get("group_id") or state.get("dealer_id") or default_group_id()


def _dealer_id(state: dict[str, Any]) -> str:
    return _group_id(state)


def _location_id(state: dict[str, Any]) -> str | None:
    return state.get("location_id")


def _cars(state: dict[str, Any]) -> list[dict[str, Any]]:
    return list_cars(_group_id(state), _location_id(state))


def _find_car(state: dict[str, Any], car_id: str) -> dict[str, Any] | None:
    return get_car(car_id, _group_id(state), _location_id(state))


def _pick_ev_gas_pair(state: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    cars = _cars(state)
    ev = next((c for c in cars if fuel_category(c) == "electric"), None)
    if not ev:
        ev = next((c for c in cars if fuel_category(c) == "hybrid"), None)
    gas = next((c for c in cars if fuel_category(c) == "gas"), None)
    if not gas:
        gas = next((c for c in cars if c["id"] != (ev or {}).get("id")), None)
    return ev, gas


def _prefs(state: dict[str, Any]) -> PreferenceState:
    return PreferenceState.from_dict(state["prefs"])


def _save_prefs(state: dict[str, Any], prefs: PreferenceState) -> None:
    state["prefs"] = prefs.to_dict()


def build_tools(state: dict[str, Any]):
    """LangChain tools closed over the current session state."""

    @tool
    def update_preferences(
        budget: float | None = None,
        body_type: str | None = None,
        condition: str | None = None,
        priority: str | None = None,
        fuel_type: str | None = None,
        prefer_ev: bool | None = None,
        miles_per_year: int | None = None,
        eliminate_id: str | None = None,
        shortlist_id: str | None = None,
        stage: str | None = None,
    ) -> str:
        """Update the user's car-shopping preferences and optional game stage."""
        prefs = _prefs(state)
        if budget is not None:
            prefs.budget = float(budget)
            if prefs.stage == "budget":
                prefs.stage = "body"
        if body_type:
            prefs.body_types = ["any"] if body_type == "any" else [body_type.lower()]
            if prefs.stage == "body":
                prefs.stage = "priority"
        if condition:
            prefs.condition = condition.lower()
            if prefs.stage == "condition":
                prefs.stage = "compare"
        if priority:
            prefs.priority = priority.lower()
            if prefs.stage == "priority":
                prefs.stage = "condition"
        if fuel_type:
            prefs.fuel_types = [fuel_type.lower()]
        if prefer_ev is not None:
            prefs.prefer_ev = prefer_ev
        if miles_per_year is not None:
            prefs.miles_per_year = int(miles_per_year)
        if eliminate_id and eliminate_id not in prefs.eliminated_ids:
            prefs.eliminated_ids.append(eliminate_id)
        if shortlist_id and shortlist_id not in prefs.shortlist_ids:
            prefs.shortlist_ids.append(shortlist_id)
        if stage:
            prefs.stage = stage
        _save_prefs(state, prefs)
        return json.dumps({"ok": True, "prefs": prefs.to_dict()})

    @tool
    def rank_contenders(limit: int = 4) -> str:
        """Rank remaining cars with hexagonal metrics given current preferences."""
        prefs = _prefs(state)
        ranked = rank_cars(_cars(state), prefs, limit=limit)
        state["last_contenders"] = ranked
        slim = [
            {
                "id": c["id"],
                "label": f"{c['year']} {c['make']} {c['model']}",
                "price": c["price"],
                "overall": c["overall"],
                "metrics": c["metrics"],
                "summary": c.get("summary"),
            }
            for c in ranked
        ]
        return json.dumps(
            {
                "count": len(slim),
                "cars": slim,
                "group_id": _group_id(state),
                "dealer_id": _group_id(state),
                "location_id": _location_id(state),
            }
        )

    @tool
    def get_best_pick() -> str:
        """Return the single best remaining pick and advance to decide stage."""
        prefs = _prefs(state)
        ranked = rank_cars(_cars(state), prefs, limit=1)
        prefs.stage = "decide"
        _save_prefs(state, prefs)
        state["last_contenders"] = ranked
        if not ranked:
            return json.dumps({"error": "No cars match current filters. Try widening budget or body type."})
        best = ranked[0]
        return json.dumps(
            {
                "best": {
                    "id": best["id"],
                    "label": f"{best['year']} {best['make']} {best['model']}",
                    "price": best["price"],
                    "overall": best["overall"],
                    "metrics": best["metrics"],
                    "hex_labels": best["hex_labels"],
                    "hex_values": best["hex_values"],
                    "summary": best.get("summary"),
                }
            }
        )

    @tool
    def reset_quest() -> str:
        """Reset the recommendation quest to the beginning."""
        state["prefs"] = PreferenceState().to_dict()
        state["last_contenders"] = []
        return json.dumps({"ok": True, "prefs": state["prefs"]})

    @tool
    def explain_ev_tradeoffs(topics: str | None = None, context: str | None = None) -> str:
        """Explain EV vs gas tradeoffs. topics is a comma list of:
        charging, fuel_cost, maintenance, incentives, range_cold, resale.
        Omit topics for all. Optional context is free text about the user's situation."""
        topic_list = None
        if topics:
            topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        payload = summarize_tradeoffs(topic_list)
        prefs = _prefs(state)
        advice = advise_ev_vs_gas(prefs.to_dict(), context)
        state["last_roi"] = None
        return json.dumps({"advice": advice, **payload})

    @tool
    def calculate_ev_roi(
        ev_price: float | None = None,
        gas_price: float | None = None,
        incentive: float | None = None,
        miles_per_year: float | None = None,
        gas_mpg: float | None = None,
        gas_price_per_gallon: float | None = None,
        ev_kwh_per_100mi: float | None = None,
        electricity_rate_per_kwh: float | None = None,
        annual_maintenance_delta: float | None = None,
        home_charger_cost: float | None = None,
        ev_car_id: str | None = None,
        gas_car_id: str | None = None,
    ) -> str:
        """Estimate years/months to break even buying an EV vs a comparable gas car.
        Pass either explicit prices or catalog car ids (ev_car_id / gas_car_id)."""
        prefs = _prefs(state)
        miles = miles_per_year or prefs.miles_per_year or DEFAULT_ASSUMPTIONS["miles_per_year"]
        if prefs.miles_per_year is None and miles_per_year:
            prefs.miles_per_year = int(miles_per_year)
            _save_prefs(state, prefs)

        if ev_car_id and gas_car_id:
            ev_car = _find_car(state, ev_car_id)
            gas_car = _find_car(state, gas_car_id)
            if not ev_car or not gas_car:
                return json.dumps({"error": "Unknown car id for this dealer's inventory."})
            result = roi_from_cars(
                ev_car,
                gas_car,
                incentive=incentive,
                miles_per_year=miles,
                gas_price_per_gallon=gas_price_per_gallon,
                electricity_rate_per_kwh=electricity_rate_per_kwh,
                home_charger_cost=home_charger_cost,
            )
        else:
            if ev_price is None or gas_price is None:
                ev_car, gas_car = _pick_ev_gas_pair(state)
                if not ev_car or not gas_car:
                    return json.dumps({"error": "This lot needs both an EV/hybrid and a gas car for ROI."})
                result = roi_from_cars(
                    ev_car,
                    gas_car,
                    incentive=incentive if incentive is not None else 0.0,
                    miles_per_year=miles,
                    gas_price_per_gallon=gas_price_per_gallon,
                    electricity_rate_per_kwh=electricity_rate_per_kwh,
                    home_charger_cost=home_charger_cost,
                )
            else:
                result = calculate_ev_roi(
                    float(ev_price),
                    float(gas_price),
                    incentive=float(incentive or 0),
                    home_charger_cost=home_charger_cost,
                    miles_per_year=miles,
                    gas_mpg=gas_mpg,
                    gas_price_per_gallon=gas_price_per_gallon,
                    ev_kwh_per_100mi=ev_kwh_per_100mi,
                    electricity_rate_per_kwh=electricity_rate_per_kwh,
                    annual_maintenance_delta=annual_maintenance_delta,
                )
        state["last_roi"] = result
        return json.dumps(result)

    return [
        update_preferences,
        rank_contenders,
        get_best_pick,
        reset_quest,
        explain_ev_tradeoffs,
        calculate_ev_roi,
    ]


def _openai_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and LANGCHAIN_AVAILABLE


def _run_langchain_turn(state: dict[str, Any], user_message: str) -> str:
    tools = build_tools(state)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.4)
    llm_with_tools = llm.bind_tools(tools)
    group_cfg = load_group(_group_id(state))
    history = [SystemMessage(content=_system_prompt_for(group_cfg, _location_id(state)))]
    for msg in state["messages"][-12:]:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))
    history.append(HumanMessage(content=user_message))

    tool_map = {t.name: t for t in tools}
    ai = llm_with_tools.invoke(history)
    # Tool-calling loop (bounded)
    for _ in range(4):
        if not getattr(ai, "tool_calls", None):
            break
        history.append(ai)
        for call in ai.tool_calls:
            fn = tool_map[call["name"]]
            result = fn.invoke(call["args"])
            from langchain_core.messages import ToolMessage

            history.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        ai = llm_with_tools.invoke(history)

    return (ai.content or "").strip() or "Here's where we stand — check the hex chart and pick a move."


def _parse_budget(text: str) -> float | None:
    cleaned = text.lower().replace(",", "")
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(k|thousand)?", cleaned)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2) or (n <= 100 and "budget" in cleaned):
        if n <= 200:  # treat small numbers as thousands
            n *= 1000
    if 3000 <= n <= 200000:
        return n
    return None


def _narrate_stage(prefs: PreferenceState, state: dict[str, Any]) -> str:
    """Produce the next game prompt from current prefs (used after UI chips)."""
    cars = _cars(state)
    if prefs.stage == "budget" and prefs.budget is None:
        return (
            "I’m here to find the car that actually fits you — not to sell you anything. "
            "First: what’s the most you’re comfortable spending? Tap a choice or type an amount."
        )
    if prefs.stage == "body":
        return (
            f"Got it — we’ll stay near ${prefs.budget:,.0f}. "
            "What body style fits your day-to-day: sedan, SUV, hatchback, truck, wagon, or no preference?"
        )
    if prefs.stage == "priority":
        return (
            "What should we protect most: reliability, best deal, low running costs, "
            "space & usefulness, or safety?"
        )
    if prefs.stage == "condition":
        return (
            f"We’ll weight {prefs.priority.replace('_', ' ')} a bit higher. "
            "Do you want new, used, or either?"
        )
    if prefs.stage in ("compare", "decide"):
        ranked = rank_cars(cars, prefs, limit=4)
        state["last_contenders"] = ranked
        if not ranked:
            return (
                "Nothing left under those filters. Let’s loosen budget or body style — "
                "or tap Start over."
            )
        if prefs.stage == "decide":
            best = ranked[0]
            m = best["metrics"]
            return (
                f"Honest best match for you: **{best['year']} {best['make']} {best['model']}** "
                f"at ${best['price']:,.0f} (score {best['overall']}/10). "
                f"Strengths — reliability {m['reliability']}, budget fit {m['budget_fit']}, "
                f"value {m['value']}, efficiency {m['efficiency']}. "
                f"{best.get('summary', '')} Check the chart on the right, or start over anytime."
            )
        lines = [
            f"Here are {len(ranked)} solid options. Keep ones you like, pass on the rest:"
        ]
        for i, c in enumerate(ranked, 1):
            lines.append(
                f"{i}. {c['year']} {c['make']} {c['model']} — ${c['price']:,.0f} "
                f"(score {c['overall']}; reliability {c['metrics']['reliability']}, "
                f"value {c['metrics']['value']})"
            )
        lines.append("Or tap “show my best match” when you’re ready.")
        return "\n".join(lines)
    return STAGE_PROMPTS.get(prefs.stage, STAGE_PROMPTS["budget"])["prompt"]


def _run_demo_turn(state: dict[str, Any], user_message: str) -> str:
    """Deterministic progressive advisor when no LLM key is configured."""
    prefs = _prefs(state)
    text = user_message.strip().lower()
    cars = _cars(state)

    # UI chip path — preferences already applied in apply_ui_choice
    if text.startswith("[choice:"):
        _save_prefs(state, prefs)
        return _narrate_stage(prefs, state)

    if any(w in text for w in ("reset", "start over", "restart")):
        state["prefs"] = PreferenceState().to_dict()
        state["last_contenders"] = []
        state["last_roi"] = None
        return (
            "Fresh start. Still no sales pitch — just the best fit for you. "
            "What’s your max budget? Tap a choice or type a number."
        )

    # Group inventory paste (CSV / comma-delimited lot update)
    if _looks_like_inventory_paste(user_message):
        from inventory_ingest import apply_paste_inventory

        result = apply_paste_inventory(
            _group_id(state),
            user_message,
            default_location=_location_id(state),
            replace_location=_location_id(state),
        )
        return _format_ingest_reply(result)

    # EV vs gas advice + ROI (can interrupt the quest flow)
    miles_match = re.search(r"(\d[\d,]*)\s*(?:miles|/yr|per year|a year)", text)
    if miles_match:
        prefs.miles_per_year = int(miles_match.group(1).replace(",", ""))

    if any(w in text for w in ("electric", " ev", "ev ", "ev?", "tesla", "plug-in", "charging")):
        prefs.prefer_ev = True
    if any(w in text for w in ("gas car", "gasoline", "petrol", "prefer gas", "stick with gas")):
        prefs.prefer_ev = False

    wants_roi = any(
        w in text
        for w in (
            "roi",
            "break even",
            "breakeven",
            "break-even",
            "payback",
            "worth it",
            "savings",
            "calculator",
        )
    )
    wants_tradeoffs = any(
        w in text
        for w in (
            "ev vs",
            "electric vs",
            "vs gas",
            "versus gas",
            "tradeoff",
            "trade-off",
            "charging",
            "incentive",
            "tax credit",
            "cold weather",
            "range anxiety",
        )
    )

    if wants_roi or (wants_tradeoffs and "roi" in text):
        incentive = DEFAULT_ASSUMPTIONS["federal_ev_credit"] if "credit" in text or "incentive" in text else 0.0
        ev_car, gas_car = _pick_ev_gas_pair(state)
        if "bolt" in text:
            ev_car = _find_car(state, "chevrolet-bolt-2022") or ev_car
        if "civic" in text:
            gas_car = _find_car(state, "honda-civic-2023") or gas_car
        if "corolla" in text:
            gas_car = _find_car(state, "toyota-corolla-2023") or gas_car
        if not ev_car or not gas_car:
            return (
                "I need both an EV/hybrid and a gas car on this lot to run break-even. "
                "Upload or paste this week’s inventory, or ask about tradeoffs instead."
            )
        result = roi_from_cars(
            ev_car,
            gas_car,
            incentive=incentive,
            miles_per_year=prefs.miles_per_year or DEFAULT_ASSUMPTIONS["miles_per_year"],
        )
        state["last_roi"] = result
        _save_prefs(state, prefs)
        yrs = result["years_to_roi"]
        payback = f"{yrs:.1f} years" if yrs is not None else "never (at these inputs)"
        return (
            f"Straight numbers — **{result['ev_car']['label']}** vs **{result['gas_car']['label']}**.\n"
            f"Extra you pay upfront (after incentives/charger): ${result['upfront_premium']:,.0f}.\n"
            f"You save about ${result['annual_total_savings']:,.0f}/year on energy + upkeep.\n"
            f"Break-even: **{payback}**.\n"
            f"{result['verdict']}\n"
            "Tweak the calculator below, or ask me about charging, winters, or incentives."
        )

    if wants_tradeoffs or (
        prefs.prefer_ev is True
        and any(w in text for w in ("why", "should i", "explain", "tell me", "pros", "cons"))
    ):
        advice = advise_ev_vs_gas(prefs.to_dict(), text)
        topics = summarize_tradeoffs(
            ["charging", "fuel_cost", "maintenance", "incentives", "range_cold", "resale"]
        )
        _save_prefs(state, prefs)
        lines = [advice, "", "Key tradeoffs:"]
        for t in topics["topics"][:4]:
            lines.append(f"- **{t['title']}**: {t['tip']}")
        lines.append("Want a break-even estimate? Ask me, or use the calculator below.")
        return "\n".join(lines)

    # Free-text preference sniffing
    budget = _parse_budget(text)
    if budget and (prefs.budget is None or "budget" in text or prefs.stage == "budget"):
        prefs.budget = budget
        if prefs.stage == "budget":
            prefs.stage = "body"

    body_map = {
        "sedan": "sedan",
        "suv": "suv",
        "crossover": "suv",
        "hatch": "hatchback",
        "hatchback": "hatchback",
        "truck": "truck",
        "wagon": "wagon",
        "surprise": "any",
        "any": "any",
    }
    for key, val in body_map.items():
        if key in text and prefs.stage in ("body", "budget", "priority"):
            prefs.body_types = ["any"] if val == "any" else [val]
            if prefs.stage == "body":
                prefs.stage = "priority"
            break

    for pri in ("reliability", "value", "efficiency", "practicality", "safety"):
        if pri in text:
            prefs.priority = pri
            if prefs.stage == "priority":
                prefs.stage = "condition"
            break

    if "new" in text and "used" not in text:
        prefs.condition = "new"
        if prefs.stage == "condition":
            prefs.stage = "compare"
    elif "used" in text:
        prefs.condition = "used"
        if prefs.stage == "condition":
            prefs.stage = "compare"
    elif "either" in text:
        prefs.condition = "either"
        if prefs.stage == "condition":
            prefs.stage = "compare"

    # Auto-advance empty stages with gentle nudges
    if prefs.stage == "budget" and prefs.budget is None:
        _save_prefs(state, prefs)
        return (
            "I’m here to find the car that fits you — not to push a sale. "
            "What’s your max budget? Tap a choice or say something like \"$25k\"."
        )

    if prefs.stage == "body" and not prefs.body_types:
        _save_prefs(state, prefs)
        return (
            f"Budget near ${prefs.budget:,.0f} — good. "
            "Sedan, SUV, hatchback, truck, wagon, or no preference?"
        )

    if prefs.stage == "priority" and not prefs.priority:
        _save_prefs(state, prefs)
        return (
            "What matters most: reliability, best deal, low running costs, "
            "space & usefulness, or safety?"
        )

    if prefs.stage == "condition" and not prefs.condition:
        _save_prefs(state, prefs)
        return f"We’ll protect {prefs.priority.replace('_', ' ')}. New, used, or either?"

    if prefs.stage in ("compare", "decide") or (
        prefs.budget and prefs.body_types and prefs.priority and prefs.condition
    ):
        if prefs.stage == "condition":
            prefs.stage = "compare"
        ranked = rank_cars(cars, prefs, limit=4)
        state["last_contenders"] = ranked
        _save_prefs(state, prefs)
        if not ranked:
            return (
                "Nothing fits those filters. Raise the budget, widen the body style, "
                "or say “start over”."
            )
        if "best" in text or "pick" in text or "recommend" in text or prefs.stage == "decide":
            best = ranked[0]
            prefs.stage = "decide"
            _save_prefs(state, prefs)
            m = best["metrics"]
            return (
                f"Honest best match: **{best['year']} {best['make']} {best['model']}** "
                f"at ${best['price']:,.0f} (score {best['overall']}/10). "
                f"Reliability {m['reliability']}, budget fit {m['budget_fit']}, "
                f"value {m['value']}, efficiency {m['efficiency']}. "
                f"{best.get('summary', '')} See the chart on the right — or start over."
            )
        lines = [
            f"Here are {len(ranked)} strong options. Keep favorites or pass:"
        ]
        for i, c in enumerate(ranked, 1):
            lines.append(
                f"{i}. {c['year']} {c['make']} {c['model']} — ${c['price']:,.0f} "
                f"(score {c['overall']}; reliability {c['metrics']['reliability']}, "
                f"value {c['metrics']['value']})"
            )
        lines.append("Or ask me to show your best match.")
        return "\n".join(lines)

    _save_prefs(state, prefs)
    stage_meta = STAGE_PROMPTS.get(prefs.stage, STAGE_PROMPTS["budget"])
    return stage_meta["prompt"]


def chat(
    message: str,
    session_id: str | None = None,
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> dict[str, Any]:
    sid, state = _session(
        session_id,
        group_id=group_id or dealer_id,
        location_id=location_id,
    )
    state["messages"].append({"role": "user", "content": message})

    if _openai_ready():
        reply = _run_langchain_turn(state, message)
        mode = "langchain"
    else:
        reply = _run_demo_turn(state, message)
        mode = "demo"

    state["messages"].append({"role": "assistant", "content": reply})
    prefs = _prefs(state)
    group = public_group_config(_group_id(state), _location_id(state))
    contenders = state.get("last_contenders") or rank_cars(_cars(state), prefs, limit=4)
    if prefs.budget and prefs.stage in ("compare", "decide", "condition"):
        contenders = rank_cars(_cars(state), prefs, limit=4)
        state["last_contenders"] = contenders

    stage_payload = next_stage_payload(prefs, contenders)
    return {
        "session_id": sid,
        "group": group,
        "dealer": group,  # alias
        "reply": reply,
        "mode": mode,
        "langchain_available": LANGCHAIN_AVAILABLE,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "prefs": prefs.to_dict(),
        "stage": stage_payload,
        "contenders": contenders,
        "hex_axes": list(contenders[0]["hex_labels"]) if contenders else list(STAGE_PROMPTS),
        "roi": state.get("last_roi"),
        "ev_assumptions": DEFAULT_ASSUMPTIONS,
        "inventory_count": len(_cars(state)),
        "location_id": _location_id(state),
    }


def apply_ui_choice(
    session_id: str | None,
    stage: str,
    value: Any,
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> dict[str, Any]:
    sid, state = _session(
        session_id,
        group_id=group_id or dealer_id,
        location_id=location_id,
    )
    prefs = _prefs(state)
    if stage == "compare" and str(value) == "done":
        prefs.stage = "decide"
        _save_prefs(state, prefs)
        return chat(
            "What's the best pick?",
            sid,
            group_id=_group_id(state),
            location_id=_location_id(state),
        )
    prefs = apply_choice(prefs, stage, value)
    _save_prefs(state, prefs)

    label = str(value)
    return chat(
        f"[choice:{stage}={label}]",
        sid,
        group_id=_group_id(state),
        location_id=_location_id(state),
    )


def new_session(
    group_id: str | None = None,
    location_id: str | None = None,
    *,
    dealer_id: str | None = None,
) -> dict[str, Any]:
    gid = resolve_group(group_id=group_id or dealer_id)
    sid, state = _session(None, group_id=gid, location_id=location_id)
    prefs = PreferenceState()
    stage = next_stage_payload(prefs)
    group = public_group_config(gid, location_id)
    count = len(_cars(state))
    scope = (
        f"at {group['name']}"
        if location_id
        else f"across the {group.get('group_name') or group['name']} group"
    )
    return {
        "session_id": sid,
        "group": group,
        "dealer": group,
        "reply": (
            f"Welcome to {group['name']} — I’m your DriveQuest advisor. "
            "Think of me as a salesperson who isn’t paid to close: I only care about "
            f"the best car for *you* {scope} "
            f"({count} vehicles loaded). "
            "Start with your budget below, or ask anytime whether an EV is worth it."
        ),
        "mode": "langchain" if _openai_ready() else "demo",
        "langchain_available": LANGCHAIN_AVAILABLE,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "prefs": prefs.to_dict(),
        "stage": stage,
        "contenders": [],
        "roi": None,
        "ev_assumptions": DEFAULT_ASSUMPTIONS,
        "inventory_count": count,
        "location_id": location_id,
    }


def _looks_like_inventory_paste(message: str) -> bool:
    lower = message.lower()
    if "stock" in lower and ("make" in lower or "year" in lower) and ("," in message or "\t" in message):
        return True
    lines = [ln for ln in message.strip().splitlines() if ln.strip()]
    if len(lines) >= 2 and ("," in lines[0] or "\t" in lines[0]):
        header = lines[0].lower()
        return any(k in header for k in ("stock", "vin", "make", "model", "price", "year"))
    return False


def _format_ingest_reply(result: dict[str, Any]) -> str:
    ok = result.get("accepted", 0)
    bad = result.get("errors") or []
    period = result.get("period_label") or "current period"
    loc = result.get("location_id")
    scope = f" (location `{loc}`)" if loc else " (group-wide)"
    lines = [
        f"Updated inventory for **{period}**{scope}: **{ok}** vehicle(s) loaded.",
    ]
    if result.get("sample"):
        lines.append("Sample rows I understood:")
        for row in result["sample"][:3]:
            loc_tag = f" · {row['location_id']}" if row.get("location_id") else ""
            lines.append(
                f"- {row.get('year')} {row.get('make')} {row.get('model')} · ${row.get('price'):,}{loc_tag}"
            )
    if bad:
        lines.append(f"Flagged **{len(bad)}** bad row(s):")
        for err in bad[:5]:
            lines.append(f"- Row {err.get('row')}: {err.get('message')}")
        if len(bad) > 5:
            lines.append(f"- …and {len(bad) - 5} more")
    lines.append("Recommendations, quest, chat, and ROI now use this latest loaded inventory.")
    return "\n".join(lines)
