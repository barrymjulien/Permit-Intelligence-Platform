import requests
import pandas as pd
import time
import os

# --- Hardcoded date for testing ---
query_date = "2025-07-10"
print(f"🔎 Querying Miami-Dade permits issued since {query_date}...")

# ArcGIS endpoint
BASE_URL = "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/ArcGIS/rest/services/BuildingPermit_gdb/FeatureServer/0/query"

PARAMS = {
    "where": f"ISSUDATE >= DATE '{query_date} 00:00:00'",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json",
    "resultOffset": 0,
    "resultRecordCount": 2000
}

def fetch_all_records():
    all_records = []
    offset = 0
    batch_size = 2000
    
    while True:
        PARAMS["resultOffset"] = offset
        response = requests.get(BASE_URL, params=PARAMS)
        data = response.json()

        if "features" not in data or not data["features"]:
            print("✅ Finished fetching all records.")
            break

        batch = [f["attributes"] for f in data["features"]]
        all_records.extend(batch)
        print(f"📦 Fetched {len(batch)} records (offset: {offset})")
        offset += batch_size
        time.sleep(0.2)

    print(f"🧾 Total raw records: {len(all_records)}")
    return all_records

def normalize_records(records):
    print("🔧 Normalizing records...")
    df = pd.DataFrame(records)

    print("\n📋 Returned fields:", list(df.columns))

    if df.empty:
        print("⚠️ DataFrame is empty. Nothing to normalize.")
        return df

    # Combine all DESC fields into one description
    description_fields = [f"DESC{i}" for i in range(1, 11) if f"DESC{i}" in df.columns]
    if description_fields:
        df["description"] = df[description_fields].fillna("").agg(" | ".join, axis=1).str.strip(" |")
    else:
        df["description"] = ""

    # Translate permit status
    if "BPSTATUS" in df.columns:
        status_map = {"A": "Active", "E": "Expired", "F": "Finalized"}
        df["status"] = df["BPSTATUS"].map(status_map).fillna("Unknown")
    else:
        df["status"] = "Unknown"

    df = df.rename(columns={
        "MPRMTNUM": "record_number",
        "TYPE": "record_type",
        "STNDADDR": "address",
        "ISSUDATE": "issue_date",
        "ESTVALUE": "estimated_value",
        "CONTRNAME": "contractor_name",
        "CONTRNUM": "contractor_id",
        "GEOFOLIO": "geo_folio",
        "RESCOMM": "use_type",
        "CLUC": "land_use_code",
        "LGLDESC1": "legal_desc_1",
        "LGLDESC2": "legal_desc_2"
    })

    # Filter out blank records
    required_fields = ["record_number", "address", "description"]
    existing_fields = [f for f in required_fields if f in df.columns]
    df = df.dropna(subset=existing_fields)

    final_fields = [
        "record_number", "record_type", "address", "description", "status", "issue_date",
        "estimated_value", "contractor_name", "contractor_id", "geo_folio",
        "use_type", "land_use_code", "legal_desc_1", "legal_desc_2"
    ]
    available_fields = [f for f in final_fields if f in df.columns]
    df = df[available_fields]

    print(f"✅ Normalized records: {len(df)}")
    return df

def save_csv(df, filename):
    if df.empty:
        print("⚠️ No data to save.")
        return

    df.to_csv(filename, index=False)
    print(f"📁 Saved CSV: {filename}")

if __name__ == "__main__":
    raw_records = fetch_all_records()
    df = normalize_records(raw_records)
    save_csv(df, filename="miamidade_permits_20250710.csv")
