#view_db.py

import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="langchain")

print(f"📊 Total documents: {collection.count()}")
print("\n🔍 Sample documents:")

results = collection.get(limit=10)
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    print(f"\n--- Document {i+1} ---")
    print(f"Content: {doc}")
    print(f"Metadata: {meta}")