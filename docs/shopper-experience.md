# Shopper experience (POC)

What a buyer sees when DriveQuest is embedded on a dealer site (or opened from the local landing page).

## Entry points

- Group-wide: `/embed/northstar-motors` — all rooftops in the group.
- One store: `/embed/northstar-motors/downtown` — that location’s lot only.
- Landing cards on `/` open the same UIs.

Branding (name, tagline, colors) comes from the group; location embeds may show the rooftop name/tagline.

## The quest (progressive narrowing)

Chips + free-text chat walk six stages:

| Step | Intent |
|------|--------|
| 1 Budget | Max spend |
| 2 Type | Body style (sedan, SUV, …) |
| 3 Priority | What matters most (feeds hex emphasis) |
| 4 New/used | Condition preference |
| 5 Compare | Shortlist on the hex radar |
| 6 Best match | Top pick + honest summary |

You can skip around via chat (“under 25k”, “need a hybrid”, “reset”). Progress is light — game-like, not a form gauntlet.

**Demo badge:** without OpenAI, UI shows “Demo advisor”; with a key, “Live advisor”. Behavior of stages/scoring stays aligned.

## Chat persona

DriveQuest is framed as a veteran salesperson who **doesn’t care about commission**:

- Prefer the cheaper / used / smaller car when it’s the better fit.
- Say no to bad fits (wrong body, shaky reliability, EV without a charging story).
- Only recommend cars on **this** inventory — never invent stock.
- Short replies + a clear next action.

## Hex radar

Six axes for contenders: **Value, Budget fit, Reliability, Efficiency, Safety, Practicality**.

- Built from inventory fields (price, market value, MPG, ratings, seats, etc.).
- Gallery + legend sit beside the chart.
- Scores are **POC heuristics**, not third-party certifications.

## EV vs gas + ROI

- **Ask EV vs gas** (quick prompt) or type naturally about charging, incentives, cold weather, resale.
- **ROI panel:** pick a sample EV/hybrid vs gas pair from *this* lot (or enter custom prices), set miles/year, fuel/electricity rates, incentive, charger cost → **years to break even** + yearly savings breakdown.
- Numbers use transparent default assumptions; change the knobs for the demo story.

## Inventory scope (what shoppers never see)

- Another dealer group’s cars.
- Cars removed by the latest ingest (live `inventory.json` only).
- Other rooftops when the embed is location-scoped (untagged “group shared” rows may still appear — POC behavior).

## Reset

**Start over** clears the session preferences and starts a fresh quest on the same group/location.

## Limitations visible in demos

- Photos may be shared sample images if `photo_url` wasn’t provided.
- Reliability / safety defaults fill in when the spreadsheet omitted them.
- Sessions die if the server restarts (in-memory).

More gaps: [poc-limitations.md](./poc-limitations.md).
