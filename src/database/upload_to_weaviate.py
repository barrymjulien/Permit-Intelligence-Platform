import os
import json
import weaviate
from openai import OpenAI
import hashlib
from dotenv import load_dotenv
from tqdm import tqdm

# --- Load Secrets ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# --- OpenAI Setup ---
client_openai = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text, model="text-embedding-3-small"):
    if not text:
        return None
    try:
        response = client_openai.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error for text: {text[:30]}... → {e}")
        return None

# --- Weaviate Client Setup ---
client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(WEAVIATE_API_KEY),
    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
)

# --- Ensure schema exists ---
CLASS_NAME = "Permit"

try:
    client.schema.get(CLASS_NAME)
    print(f"Schema for {CLASS_NAME} already exists.")
except Exception:
    print(f"Creating schema: {CLASS_NAME}")
    client.schema.create_class({
        "class": CLASS_NAME,
        "vectorizer": "none",  # manual embedding
        "properties": [
            {"name": "permit_id", "dataType": ["string"]},
            {"name": "source", "dataType": ["string"]},
            {"name": "description", "dataType": ["text"]},
            # {"name": "status", "dataType": ["string"]},
            {"name": "zip_code", "dataType": ["string"]},
            {"name": "address", "dataType": ["string"]},
            {"name": "date_issued", "dataType": ["string"]},
            {"name": "work_type", "dataType": ["string"]},
            {"name": "lat", "dataType": ["number"]},
            {"name": "lon", "dataType": ["number"]},
        ]
    })

# --- Load Data ---
try:
    with open("cleaned_permits.json", "r") as f:
        permits = json.load(f)
except FileNotFoundError:
    print("Error: 'cleaned_permits.json' not found. Please run 'prepare_permits.py' first.")
    exit()

# --- Upload to Weaviate ---
print(f"Attempting to upload {len(permits)} records to Weaviate...")
with client.batch as batch:
    for item_original in tqdm(permits, desc="Uploading to Weaviate"):
        text = item_original.get("description", "no description")
        vector = get_embedding(text)
        if vector is None:
            print(f"Skipping record due to missing embedding for: {text[:50]}...")
            continue

        # Create a new dictionary to safely prepare data for Weaviate
        item_to_upload = {
            "permit_id": item_original.get("permit_id"),
            "source": item_original.get("source"),
            "description": item_original.get("description"),
            # "status": item_original.get("status"),
            "zip_code": item_original.get("zip_code"),
            "address": item_original.get("address"),
            "date_issued": item_original.get("date_issued"),
            "work_type": item_original.get("work_type"),
        }

        # Only add lat/lon if they are not None
        lat_value = item_original.get("lat")
        lon_value = item_original.get("lon")

        if lat_value is not None:
            item_to_upload["lat"] = lat_value
        if lon_value is not None:
            item_to_upload["lon"] = lon_value

        # Create deterministic UUID from source + permit_id
        uid_base = f"{item_original['source']}_{item_original['permit_id']}"
        uid = hashlib.md5(uid_base.encode()).hexdigest()

        try:
            batch.add_data_object(
                data_object=item_to_upload,
                class_name=CLASS_NAME,
                vector=vector,
                uuid=uid
            )
        except Exception as e:
            print(f"\nUpload failed for UID {uid} (Permit ID: {item_original.get('permit_id')}): {e}. Data object was: {item_to_upload}")

print("Batch upload process initiated. Check Weaviate console for final status.")

if client.is_ready():
    print("Weaviate client is ready.")
else:
    print("Weaviate client is NOT ready. There might be connection issues.")