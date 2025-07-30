import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PermitSearch:
    def __init__(self, db_path="./chroma_db"):
        """Initialize the permit search system"""
        print("🔧 Loading permit database...")
        
        # Debug: Check if .env file was loaded
        print(f"🔍 Current working directory: {os.getcwd()}")
        print(f"🔍 .env file exists: {os.path.exists('.env')}")
        
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"🔍 API key found: {bool(api_key)}")
        if api_key:
            print(f"🔍 API key starts with: {api_key[:10]}...")
        
        if not api_key:
            raise ValueError(
                "❌ OPENAI_API_KEY environment variable not found!\n"
                "Please check your .env file format. It should contain:\n"
                "OPENAI_API_KEY=your_actual_key_here\n"
                "(No quotes, no spaces around the = sign)"
            )
        
        try:
            # Initialize the vector store (EXACTLY same way you created it)
            self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
            self.vectorstore = Chroma(
                collection_name="permits",  # This was missing!
                embedding_function=self.embeddings,
                persist_directory=db_path
            )
            print("✅ Database loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            raise
    
    def search(self, query, k=5):
        """Search for permits based on natural language query"""
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            
            print(f"\n🔍 Search results for: '{query}'")
            print("=" * 60)
            
            if not results:
                print("❌ No results found. Try different search terms.")
                return results
            
            for i, result in enumerate(results, 1):
                print(f"\n--- Result {i} ---")
                print(f"📄 Description: {result.page_content}")
                print(f"🏠 Record Number: {result.metadata.get('record_number', 'N/A')}")
                print(f"📊 Status: {result.metadata.get('status', 'N/A')}")
                print(f"🏗️  Type: {result.metadata.get('record_type', 'N/A')}")
                print(f"📅 Date Issued: {result.metadata.get('date_issued', 'N/A')}")
                print(f"⏰ Expires: {result.metadata.get('expiration_date', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def test_different_embeddings(self):
        """Test different embedding models to find the right one"""
        print("\n🧪 Testing different embedding models...")
        
        embedding_options = [
            ("OpenAI", OpenAIEmbeddings()),
            ("HuggingFace (default)", HuggingFaceEmbeddings()),
            ("HuggingFace (sentence-transformers)", HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))
        ]
        
        for name, embedding_func in embedding_options:
            try:
                print(f"\n🔍 Testing {name} embeddings...")
                test_vectorstore = Chroma(
                    persist_directory="./chroma_db",
                    embedding_function=embedding_func
                )
                
                # Test with exact content
                results = test_vectorstore.similarity_search("NEW SFT", k=2)
                if results:
                    print(f"✅ {name} embeddings WORK! Found {len(results)} results")
                    print(f"   Sample result: {results[0].page_content[:50]}...")
                    return embedding_func
                else:
                    print(f"❌ {name} embeddings failed")
                    
            except Exception as e:
                print(f"❌ {name} embeddings error: {e}")
        
        return None
    def debug_search(self):
        """Debug function to see what's actually in the database"""
        try:
            # First test different embeddings
            working_embeddings = self.test_different_embeddings()
            
            if working_embeddings:
                print(f"\n🎉 Found working embeddings! Reinitializing vectorstore...")
                self.vectorstore = Chroma(
                    persist_directory="./chroma_db",
                    embedding_function=working_embeddings
                )
                print("✅ Vectorstore reinitialized with correct embeddings!")
                
                # Test the search now
                print("\n🧪 Testing search with correct embeddings:")
                results = self.vectorstore.similarity_search("kitchen renovation", k=3)
                if results:
                    print(f"✅ Search works! Found {len(results)} results for 'kitchen renovation'")
                    for i, result in enumerate(results, 1):
                        print(f"   {i}. {result.page_content[:100]}...")
                else:
                    print("❌ Still no results")
            
            # Get some sample documents directly
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_collection(name="permits")
            
            # Get first 5 documents
            sample_data = collection.get(limit=5)
            
            print("\n🔍 DEBUG: Sample documents in database:")
            print("=" * 60)
            
            for i, (doc, meta) in enumerate(zip(sample_data['documents'], sample_data['metadatas'])):
                print(f"\nDocument {i+1}:")
                print(f"Content: {doc}")
                print(f"Metadata: {meta}")
                
        except Exception as e:
            print(f"❌ Debug error: {e}")

def main():
    """Main function to run example searches"""
    print("🏗️  Building Permit Search System")
    print("=" * 40)
    
    # Initialize search system
    try:
        searcher = PermitSearch()
        # Test a simple search right away
        print("\n🧪 Quick test search:")
        results = searcher.search("kitchen", k=3)
        
        if results:
            print("\n🎉 Search is working! Let's try more examples...")
        else:
            print("\n🔍 Running debug...")
            searcher.debug_search()
            
    except Exception as e:
        print(f"Failed to initialize search system: {e}")
        return
    
    # Example searches to demonstrate functionality
    example_queries = [
        "kitchen renovation projects",
        "new house construction", 
        "HVAC air conditioning work",
        "projects in Wimauma",
        "residential building alterations"
    ]
    
    print(f"\n🚀 Running example searches...")
    print("=" * 40)
    
    # Skip the automated examples for now, let's debug first
    print("Debug complete. Check the output above to see if exact matches work.")
    
    # Optional: Run one test search
    test_query = input("\nEnter a test search query (or press Enter to skip): ").strip()
    if test_query:
        searcher.search(test_query, k=3)

if __name__ == "__main__":
    main()