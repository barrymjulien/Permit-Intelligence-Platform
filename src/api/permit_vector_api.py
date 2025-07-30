# main.py
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(WEAVIATE_API_KEY),
    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
)

app = FastAPI(title="Permit Vector API", description="Semantic + structured permit search API", version="0.1")

class Permit(BaseModel):
    permit_id: str
    source: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None
    work_type: Optional[str] = None
    date_issued: Optional[str] = None
    short_notes: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search/text", response_model=List[Permit])
def semantic_search(q: str = Query(..., description="Query string for semantic search"),
                    k: int = 10):
    query = (
        client.query
        .get("Permit", ["permit_id", "source", "address", "zip_code", "lat", "lon", "description", "status", "work_type", "date_issued", "short_notes"])
        .with_near_text({"concepts": [q]})
        .with_limit(k)
    )
    res = query.do()
    return [r["data"]["Get"]["Permit"] for r in [res]][0]

@app.get("/search/filter", response_model=List[Permit])
def filter_by_zip(zip_code: str, limit: int = 10):
    where_filter = {
        "path": ["zip_code"],
        "operator": "Equal",
        "valueText": zip_code
    }
    query = (
        client.query
        .get("Permit", ["permit_id", "source", "address", "zip_code", "lat", "lon", "description", "status", "work_type", "date_issued", "short_notes"])
        .with_where(where_filter)
        .with_limit(limit)
    )
    res = query.do()
    return [r["data"]["Get"]["Permit"] for r in [res]][0]
