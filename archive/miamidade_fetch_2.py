import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os

# ArcGIS endpoint
BASE_URL = "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/ArcGIS/rest/services/BuildingPermit_gdb/FeatureServer/0/query"

# Where clause: You can customize for date filtering if desired
# For example, only pull permits issued in the last 1 day
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
where = f"IssueDate >= DATE '{yesterday} 00:00:00'"

PARAMS = {
    "where": where,
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
    print(f"🔎 Querying Miami-Dade permits issued since {yesterday}...")
    
    while True:
        PARAMS["resultOffset"] = offset
        response = requests.get(BASE_URL, params=PARAMS)
        data = response.json()

        if "features" not in data or not data["features"]:
            print("✅ Finished fetching all records.")
            break

        batch = [f["attributes"] for f in data["features"]]
        all_records.extend(batch)
        print(f"Fetched {len(batch)} records (offset: {offset})")
        offset += batch_size
        time.sleep(0.2)

    return all_records

def normalize_records(records):
    print("🔧 Normalizing records...")
    df = pd.DataFrame(records)
    
    print("Returned columns:", df.columns.tolist())
    
    # Extract relevant fields
    df = df.rename(columns={
        "PermitNumber": "record_number",
        "FullAddress": "address",
        "WorkDescription": "description",
        "PermitStatus": "status",
        "PermitType": "record_type",
        "ExpirationDate": "expiration_date",
        "ShortNotes": "short_notes"
    })

    df = df[[
        "record_number", "record_type", "address",
        "description", "status", "expiration_date", "short_notes"
    ]].dropna(subset=["record_number", "address", "description"])

    return df

def save_csv(df, filename="miamidade_permits.csv"):
    df.to_csv(filename, index=False)
    print(f"📁 Saved CSV: {filename}")

if __name__ == "__main__":
    raw_records = fetch_all_records()
    df = normalize_records(raw_records)
    save_csv(df)
