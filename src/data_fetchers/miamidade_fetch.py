import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/ArcGIS/rest/services/BuildingPermit_gdb/FeatureServer/0/query"

def fetch_miamidade_permits(days_back=1, max_records=None):
    """
    Fetch Miami-Dade permits from the last N days
    
    Args:
        days_back (int): Number of days back to fetch permits
        max_records (int): Maximum number of records to fetch (None for all)
    
    Returns:
        list: List of permit dictionaries with source_county added
    """
    logger.info(f"Fetching Miami-Dade permits from last {days_back} days")
    
    # Calculate date range
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    where = f"ISSUDATE >= DATE '{start_date} 00:00:00'"
    
    PARAMS = {
        "where": where,
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        "resultOffset": 0,
        "resultRecordCount": 2000
    }
    
    all_records = []
    offset = 0
    batch_size = 2000
    
    logger.info(f"Querying Miami-Dade permits issued since {start_date}")

    while True:
        if max_records and len(all_records) >= max_records:
            logger.info(f"Reached max_records limit of {max_records}")
            break
            
        PARAMS["resultOffset"] = offset
        
        try:
            response = requests.get(BASE_URL, params=PARAMS, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching data: {e}")
            break

        if "features" not in data or not data["features"]:
            logger.info("Finished fetching all records")
            break

        batch = [f["attributes"] for f in data["features"]]
        
        # Add source county to each record
        for record in batch:
            record['source_county'] = 'miami-dade'
        
        all_records.extend(batch)
        logger.info(f"Fetched {len(batch)} records (total: {len(all_records)})")
        
        offset += batch_size
        time.sleep(0.2)  # Rate limiting

    logger.info(f"Total Miami-Dade permits fetched: {len(all_records)}")
    return all_records
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
    print("\nReturned fields:", list(df.columns))

    # Handle DESC1–DESC10 fields if they exist
    description_fields = [f"DESC{i}" for i in range(1, 11)]
    existing_desc_fields = [col for col in description_fields if col in df.columns]

    if existing_desc_fields:
        df["description"] = df[existing_desc_fields].fillna("").astype(str).agg(" | ".join, axis=1).str.strip(" |")
    else:
        df["description"] = ""

    # Handle BPSTATUS mapping
    status_map = {"A": "Active", "E": "Expired", "F": "Finalized"}
    if "BPSTATUS" in df.columns:
        df["status"] = df["BPSTATUS"].map(status_map).fillna("Unknown")
    else:
        df["status"] = "Unknown"

    # Rename fiel

