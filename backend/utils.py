from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_to_supabase(data):
    # Specify your Supabase table name
    table_name = "cars"

    # Convert DataFrame to a list of dictionaries (each row becomes a dictionary)
    records = data.to_dict(orient="records")

    # Insert records into the Supabase table
    response = supabase.table(table_name).insert(records).execute()