# app/main.py
from fastapi import FastAPI, Query
from typing import List
from app.models import Permit
from app.weaviate_client import client, PERMIT_FIELDS

app = FastAPI(title="Permit Vector API", description="Semantic + structured permit search API", version="0.1")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search/text", response_model=List[Permit])
def semantic_search(q: str = Query(..., description="Query string for semantic search"), k: int = 10):
    query = (
        client.query
        .get("Permit", PERMIT_FIELDS)
        .with_near_text({"concepts": [q]})
        .with_limit(k)
    )
    res = query.do()
    return res.get("data", {}).get("Get", {}).get("Permit", [])

@app.get("/search/filter", response_model=List[Permit])
def filter_by_zip(zip_code: str, limit: int = 10):
    where_filter = {
        "path": ["zip_code"],
        "operator": "Equal",
        "valueText": zip_code
    }
    query = (
        client.query
        .get("Permit", PERMIT_FIELDS)
        .with_where(where_filter)
        .with_limit(limit)
    )
    res = query.do()
    return res.get("data", {}).get("Get", {}).get("Permit", [])
