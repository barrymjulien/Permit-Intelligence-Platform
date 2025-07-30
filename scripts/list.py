import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

# List all collections first
collections = client.list_collections()
print(f"📊 Available collections: {[c.name for c in collections]}")

if collections:
    # Get the first collection (or specify the correct name)
    collection = collections[0]  # or client.get_collection(name="actual_name")
    print(f"\n🔍 Collection '{collection.name}' has {collection.count()} documents")
    
    # View sample documents
    results = collection.get(limit=5)
    for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
        print(f"\n--- Document {i+1} ---")
        print(f"Content: {doc[:200]}...")
        print(f"Metadata: {meta}")
else:
    print("❌ No collections found in the database")