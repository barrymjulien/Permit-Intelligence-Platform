# populate_chroma.py

import os
from dotenv import load_dotenv
import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

load_dotenv()

# Setup embedding model
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Load your CSV
df = pd.read_csv("hillsborough_permits_1.csv")

df = pd.read_csv("hillsborough_permits_1.csv")

print("📊 Columns:", df.columns.tolist())
print("🔎 First row sample:")
print(df.head(1).to_dict(orient="records")[0])


# Drop rows missing required fields
df = df.dropna(subset=["Description", "Address"])

# Convert each row into a LangChain Document
docs = []
skipped = 0
for i, row in df.iterrows():
    content_parts = [str(row.get("Description", "")).strip(), str(row.get("Address", "")).strip()]
    content = " | ".join([part for part in content_parts if part])

    if not content.strip():
        skipped += 1
        continue

    metadata = {
        "record_number": row.get("Record Number"),
        "record_type": row.get("Record Type"),
        "status": row.get("Status"),
        "expiration_date": row.get("Expiration Date"),
        "date_issued": row.get("Date")
    }

    docs.append(Document(page_content=content, metadata=metadata))

print(f"📄 Prepared {len(docs)} documents for ingestion. Skipped {skipped} empty rows.")

# Initialize Chroma DB
vectorstore = Chroma(
    collection_name="permits",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

# Add documents to the vector store
vectorstore.add_documents(docs)
vectorstore.persist()

print(f"✅ Successfully added {len(docs)} documents to Chroma.")
