import os
import re
import json
import time
import pandas as pd
import requests
from tqdm import tqdm
from dotenv import load_dotenv

# --- Load Google API Key from .env or fallback ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Load or initialize local cache ---
CACHE_PATH = "geocode_cache.json"
if os.path.exists(CACHE_PATH):
    with open(CACHE_PATH, "r") as f:
        geocode_cache = json.load(f)
else:
    geocode_cache = {}

def save_cache():
    with open(CACHE_PATH, "w") as f:
        json.dump(geocode_cache, f, indent=2)

# --- Geocode using Google Maps with caching ---
def geocode_google(address):
    if not address:
        return None, None
    if address in geocode_cache:
        return geocode_cache[address]

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}

    try:
        response = requests.get(url, params=params).json()
        if response["status"] == "OK":
            location = response["results"][0]["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]
            geocode_cache[address] = (lat, lon)
            time.sleep(0.02)  # stay under 50/sec
            return lat, lon
    except Exception as e:
        print(f"Geocoding error for {address}: {e}")

    geocode_cache[address] = (None, None)
    return None, None

# --- Normalize work types ---
def normalize_type(raw_type):
    if not isinstance(raw_type, str):
        return "other"
    raw_type = raw_type.lower()
    if "roof" in raw_type:
        return "roof"
    elif "solar" in raw_type:
        return "solar"
    elif "pool" in raw_type:
        return "pool"
    elif "mechanical" in raw_type or "hvac" in raw_type:
        return "hvac"
    elif "new construction" in raw_type:
        return "new_build"
    return "other"

# --- ZIP extraction ---
def extract_zip(address):
    match = re.search(r"\b\d{5}\b", str(address))
    return match.group() if match else None

# --- Main function ---
def prepare_permit_data(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.dropna(subset=["description"])

    # Strip whitespace
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Add zip_code
    df["zip_code"] = df["address"].apply(extract_zip)

    # Geocode with caching
    lats, lons = [], []
    print("🔍 Geocoding addresses...")
    for addr in tqdm(df["address"]):
        lat, lon = geocode_google(addr)
        lats.append(lat)
        lons.append(lon)
    df["lat"] = lats
    df["lon"] = lons

    save_cache()

    # Normalize work type
    df["work_type"] = df["record_type"].apply(normalize_type)

    # Deduplicate
    df = df.drop_duplicates(subset=["record_number"])

    # Prepare final dict list
    results = []
    for _, row in df.iterrows():
        record = {
            "permit_id": str(row["record_number"]),
            "source": "hillsborough",  # or dynamic if needed
            "description": row["description"],
            "status": row.get("status"),
            "zip_code": row.get("zip_code"),
            "address": row.get("address"),
            "date_issued": row.get("expiration_date"),  # or whatever best fits
            "work_type": row.get("work_type"),
            "valuation": None,  # placeholder if not available
            "lat": row.get("lat"),
            "lon": row.get("lon"),
        }
        results.append(record)

    print(f"✅ Prepared {len(results)} permit records.")
    return results

# --- Example ---
if __name__ == "__main__":
    permits = prepare_permit_data("RecordList20250630.csv")
    # Optional: Save to JSON
    with open("cleaned_permits.json", "w") as f:
        json.dump(permits, f, indent=2)
