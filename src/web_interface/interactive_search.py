#interactive_search.py

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

def interactive_search():
    print("🏗️  Building Permit Search System")
    print("=" * 40)
    
    # Initialize search
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=OpenAIEmbeddings()
    )
    
    while True:
        query = input("\n🔍 Enter your search query (or 'quit' to exit): ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        if not query:
            continue
            
        # Perform search
        results = vectorstore.similarity_search(query, k=5)
        
        if not results:
            print("❌ No results found.")
            continue
            
        print(f"\n📋 Found {len(results)} relevant permits:")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.metadata.get('record_type', 'Unknown Type')}")
            print(f"   📄 {result.page_content[:150]}...")
            print(f"   🏠 Record: {result.metadata.get('record_number')}")
            print(f"   📅 Status: {result.metadata.get('status')}")
            print(f"   ⏰ Expires: {result.metadata.get('expiration_date')}")

if __name__ == "__main__":
    interactive_search()