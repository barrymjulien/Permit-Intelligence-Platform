"""
ChromaDB Upload Script
Uploads processed permits to ChromaDB vector database
"""

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

load_dotenv()
logger = logging.getLogger(__name__)

def upload_permits_to_chroma(permits: List[Dict[str, Any]], 
                           collection_name: str = "permits",
                           persist_directory: str = "./data/chroma_db") -> Dict[str, Any]:
    """
    Upload processed permits to ChromaDB
    
    Args:
        permits: List of normalized permit dictionaries
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory to persist the database
    
    Returns:
        Dictionary with upload results
    """
    logger.info(f"Uploading {len(permits)} permits to ChromaDB")
    
    # Verify OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    try:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        # Convert permits to LangChain Documents
        documents = []
        skipped = 0
        
        for permit in permits:
            try:
                # Create content for embedding
                content_parts = []
                
                # Add key searchable fields
                if permit.get('description'):
                    content_parts.append(str(permit['description']).strip())
                
                if permit.get('address'):
                    content_parts.append(str(permit['address']).strip())
                
                # Include permit type in searchable content but not in the main display
                if permit.get('permit_type'):
                    content_parts.append(str(permit['permit_type']).strip())
                
                # Combine content - only description and address for display split
                # The permit type will be in metadata for proper display
                if permit.get('description') and permit.get('address'):
                    content = f"{permit['description'].strip()} | {permit['address'].strip()}"
                elif permit.get('description'):
                    content = permit['description'].strip()
                elif permit.get('address'):
                    content = permit['address'].strip()
                else:
                    content = " ".join([part for part in content_parts if part])
                
                if not content.strip():
                    skipped += 1
                    continue
                
                # Create metadata (matching expected field names for Streamlit app)
                metadata = {
                    'permit_id': permit.get('permit_id', 'UNKNOWN'),
                    'record_number': permit.get('permit_id', 'UNKNOWN'),  # Streamlit expects this field name
                    'source_county': permit.get('source_county', 'unknown'),
                    'permit_type': permit.get('permit_type', ''),
                    'record_type': permit.get('permit_type', ''),  # Streamlit expects this field name
                    'address': permit.get('address', ''),
                    'city': permit.get('city', ''),
                    'zipcode': permit.get('zipcode', ''),
                    'status': permit.get('status', ''),
                    'issue_date': permit.get('issue_date', ''),
                    'date_issued': permit.get('issue_date', ''),  # Streamlit expects this field name
                    'expiration_date': permit.get('expiration_date', ''),
                    'last_updated': permit.get('last_updated', '')
                }
                
                # Add optional fields if present
                if permit.get('applicant_name'):
                    metadata['applicant_name'] = permit['applicant_name']
                if permit.get('contractor_name'):
                    metadata['contractor_name'] = permit['contractor_name']
                if permit.get('permit_value'):
                    metadata['permit_value'] = str(permit['permit_value'])
                
                documents.append(Document(page_content=content, metadata=metadata))
                
            except Exception as e:
                logger.error(f"Error processing permit {permit.get('permit_id', 'UNKNOWN')}: {e}")
                skipped += 1
                continue
        
        logger.info(f"Prepared {len(documents)} documents for ChromaDB. Skipped {skipped} invalid permits.")
        
        if not documents:
            return {"status": "error", "message": "No valid documents to upload"}
        
        # Initialize or load existing ChromaDB
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory
        )
        
        # Add documents to the vectorstore
        logger.info("Adding documents to ChromaDB...")
        vectorstore.add_documents(documents)
        
        # Get collection stats
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_collection(collection_name)
        total_count = collection.count()
        
        result = {
            "status": "success",
            "uploaded": len(documents),
            "skipped": skipped,
            "total_in_db": total_count,
            "collection_name": collection_name
        }
        
        logger.info(f"Successfully uploaded {len(documents)} permits. Total in DB: {total_count}")
        return result
        
    except Exception as e:
        logger.error(f"Error uploading to ChromaDB: {e}")
        return {"status": "error", "message": str(e)}

def get_collection_stats(collection_name: str = "permits", 
                        persist_directory: str = "./data/chroma_db") -> Dict[str, Any]:
    """Get statistics about the ChromaDB collection"""
    try:
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_collection(collection_name)
        
        return {
            "collection_name": collection_name,
            "total_documents": collection.count(),
            "persist_directory": persist_directory
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Test with sample data
    sample_permits = [
        {
            "permit_id": "TEST123",
            "source_county": "test",
            "permit_type": "Building",
            "description": "Kitchen renovation with new appliances",
            "address": "123 Main St",
            "city": "Tampa",
            "zipcode": "33601",
            "status": "Issued",
            "last_updated": "2025-07-30T10:00:00"
        }
    ]
    
    # Upload test data
    result = upload_permits_to_chroma(sample_permits)
    print(f"Upload result: {result}")
    
    # Get stats
    stats = get_collection_stats()
    print(f"Collection stats: {stats}")
