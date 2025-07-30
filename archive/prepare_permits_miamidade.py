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
        response = requests.get(BASE_URL, params=_
