#advanced_search.py

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from datetime import datetime

class AdvancedPermitSearch:
    def __init__(self, db_path="./chroma_db"):
        self.vectorstore = Chroma(
            persist_directory=db_path,
            embedding_function=OpenAIEmbeddings()
        )
    
    def search_with_filters(self, query, status_filter=None, record_type_filter=None, k=10):
        """Search with optional filters"""
        # Get more results initially
        results = self.vectorstore.similarity_search(query, k=k*2)
        
        # Apply filters
        filtered_results = []
        for result in results:
            metadata = result.metadata
            
            # Status filter
            if status_filter and metadata.get('status') != status_filter:
                continue
                
            # Record type filter
            if record_type_filter and record_type_filter.lower() not in metadata.get('record_type', '').lower():
                continue
                
            filtered_results.append(result)
            
            if len(filtered_results) >= k:
                break
        
        return filtered_results
    
    def search_by_location(self, location_query, k=5):
        """Search specifically by location"""
        return self.vectorstore.similarity_search(f"address location {location_query}", k=k)
    
    def get_stats(self):
        """Get database statistics"""
        # This requires direct ChromaDB access
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="permits")
        
        all_data = collection.get()
        total_count = len(all_data['metadatas'])
        
        # Count by status
        status_counts = {}
        type_counts = {}
        
        for meta in all_data['metadatas']:
            status = meta.get('status', 'Unknown')
            record_type = meta.get('record_type', 'Unknown')
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[record_type] = type_counts.get(record_type, 0) + 1
        
        return {
            'total': total_count,
            'by_status': status_counts,
            'by_type': type_counts
        }

# Example usage
if __name__ == "__main__":
    searcher = AdvancedPermitSearch()
    
    # Show database stats
    stats = searcher.get_stats()
    print("📊 Database Statistics:")
    print(f"Total permits: {stats['total']}")
    print(f"By status: {stats['by_status']}")
    print(f"By type: {stats['by_type']}")
    
    # Example searches
    print("\n🔍 Kitchen projects that are 'In Process':")
    results = searcher.search_with_filters("kitchen", status_filter="In Process", k=3)
    for result in results:
        print(f"- {result.page_content[:100]}...")