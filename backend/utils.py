from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_to_supabase(data):
    for row in data:
        response = supabase.table("cars").insert(row).execute()
        if response.status_code != 201:
            print(f"Insert error: {response.data}")
