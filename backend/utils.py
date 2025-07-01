from supabase import create_client, Client
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upload_to_supabase(data, batch_size=100):
    # Specify your Supabase table name
    table_name = "cars"
    try:

        # Convert DataFrame to a list of dictionaries (each row becomes a dictionary)
        records = data.to_dict(orient="records")

        # Insert in batches ot avoid timeout and large payload issues
        total_inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                logger.info(f"Inserting batch {i//batch_size + 1} ({len(batch)} records)")

                # Insert records into the Supabase table
                response = supabase.table(table_name).insert(records).execute()

                if response.data:
                    batch_count = len(response.data)
                    total_inserted += batch_count
                    logger.info(f"Successfully inserted {batch_count} records in batch {i//batch_size + 1}")
                else:
                    logger.warning(f"Batch {i//batch_size + 1} returned no data")
            except Exception as batch_error:
                logger.warning(f"Error inserting batch {i//batch_size + 1}: {batch_error}")
                continue

        logger.info(f"Upload completed. Total records isnerted: {total_inserted}/{len(records)}")
        return total_inserted
    except Exception as e:
        logger.error(f"Error uploading to Supabase: {e}")
        raise