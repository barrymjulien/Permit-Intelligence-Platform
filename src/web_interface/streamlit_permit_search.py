#streamlit_permit_search.py

import streamlit as st
import os
from dotenv import load_dotenv
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Building Permit Search",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_vectorstore():
    """Load the Chroma vectorstore - cached for performance"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            st.error("❌ OPENAI_API_KEY not found in environment variables!")
            st.stop()
        
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        vectorstore = Chroma(
            collection_name="permits",
            embedding_function=embeddings,
            persist_directory="../../data/chroma_db"
        )
        return vectorstore
    except Exception as e:
        st.error(f"❌ Error loading database: {e}")
        st.stop()

@st.cache_data
def get_database_stats():
    """Get database statistics - cached for performance"""
    try:
        client = chromadb.PersistentClient(path="../../data/chroma_db")
        collection = client.get_collection(name="permits")
        
        all_data = collection.get()
        total_count = len(all_data['metadatas'])
        
        # Count by status and type
        status_counts = {}
        type_counts = {}
        location_counts = {}
        
        for meta in all_data['metadatas']:
            status = meta.get('status', 'Unknown')
            record_type = meta.get('record_type', 'Unknown')
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[record_type] = type_counts.get(record_type, 0) + 1
        
        # Get location info from documents
        for doc in all_data['documents']:
            if '|' in doc:
                location_part = doc.split('|')[1].strip()
                if 'FL' in location_part:
                    city = location_part.split(',')[1].strip().replace(' FL', '').strip()
                    location_counts[city] = location_counts.get(city, 0) + 1
        
        return {
            'total': total_count,
            'by_status': status_counts,
            'by_type': type_counts,
            'by_location': location_counts
        }
    except Exception as e:
        st.error(f"Error getting stats: {e}")
        return None

def main():
    st.title("🏗️ Building Permit Search System")
    st.markdown("*Search through Hillsborough County building permits using natural language*")
    
    # Load the vectorstore
    vectorstore = load_vectorstore()
    
    # Sidebar with stats and filters
    with st.sidebar:
        st.header("📊 Database Overview")
        
        stats = get_database_stats()
        if stats:
            st.metric("Total Permits", stats['total'])
            
            # Status breakdown
            st.subheader("📋 By Status")
            for status, count in stats['by_status'].items():
                st.write(f"• **{status}**: {count}")
            
            # Location breakdown
            st.subheader("📍 By Location")
            for location, count in sorted(stats['by_location'].items(), key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"• **{location}**: {count}")
            
            # Type breakdown (top 5)
            st.subheader("🏗️ Top Permit Types")
            for ptype, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"• **{ptype[:30]}...**: {count}" if len(ptype) > 30 else f"• **{ptype}**: {count}")
        
        st.markdown("---")
        st.subheader("💡 Search Tips")
        st.markdown("""
        Try searching for:
        - **"kitchen renovation"**
        - **"new construction"**
        - **"HVAC work"**
        - **"screen enclosure"**
        - **"projects in Wimauma"**
        - **Or any building-related terms!**
        """)
    
    # Main search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "🔍 Enter your search query:",
            placeholder="e.g., kitchen renovations, new construction, HVAC work, projects in Wimauma...",
            help="Use natural language to describe what you're looking for"
        )
    
    with col2:
        num_results = st.selectbox("Results to show:", [5, 10, 15, 20], index=0)
    
    # Advanced filters
    with st.expander("🔧 Advanced Filters (Optional)"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status:",
                ["All"] + list(stats['by_status'].keys()) if stats else ["All"],
                index=0
            )
        
        with col2:
            # Extract unique cities for location filter
            cities = ["All"] + list(stats['by_location'].keys()) if stats else ["All"]
            location_filter = st.selectbox(
                "Filter by City:",
                cities,
                index=0
            )
        
        with col3:
            permit_types = ["All"] + list(stats['by_type'].keys()) if stats else ["All"]
            type_filter = st.selectbox(
                "Filter by Type:",
                permit_types,
                index=0
            )
    
    # Search button and results
    if st.button("🔍 Search", type="primary") or query:
        if query.strip():
            with st.spinner("Searching permits..."):
                try:
                    # Perform search
                    results = vectorstore.similarity_search(query, k=num_results*2)  # Get extra for filtering
                    
                    # Apply filters
                    filtered_results = []
                    for result in results:
                        metadata = result.metadata
                        
                        # Status filter
                        if status_filter != "All" and metadata.get('status') != status_filter:
                            continue
                        
                        # Location filter
                        if location_filter != "All":
                            if '|' in result.page_content:
                                location_part = result.page_content.split('|')[1]
                                if location_filter not in location_part:
                                    continue
                            else:
                                continue
                        
                        # Type filter
                        if type_filter != "All" and metadata.get('record_type') != type_filter:
                            continue
                        
                        filtered_results.append(result)
                        
                        if len(filtered_results) >= num_results:
                            break
                    
                    # Display results
                    if filtered_results:
                        st.success(f"✅ Found {len(filtered_results)} relevant permits")
                        
                        # Option to export results
                        if st.button("📥 Export Results to CSV"):
                            export_data = []
                            for result in filtered_results:
                                export_data.append({
                                    'Description': result.page_content,
                                    'Record Number': result.metadata.get('record_number', ''),
                                    'Status': result.metadata.get('status', ''),
                                    'Type': result.metadata.get('record_type', ''),
                                    'Date Issued': result.metadata.get('date_issued', ''),
                                    'Expiration': result.metadata.get('expiration_date', '')
                                })
                            
                            df = pd.DataFrame(export_data)
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name=f"permit_search_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                mime="text/csv"
                            )
                        
                        st.markdown("---")
                        
                        # Display each result
                        for i, result in enumerate(filtered_results, 1):
                            with st.expander(f"📋 Result {i}: {result.metadata.get('record_type', 'Unknown Type')}", expanded=i<=3):
                                # Parse description and address
                                if '|' in result.page_content:
                                    description, address = result.page_content.split('|', 1)
                                    st.markdown(f"**📝 Description:** {description.strip()}")
                                    st.markdown(f"**📍 Address:** {address.strip()}")
                                else:
                                    st.markdown(f"**📝 Description:** {result.page_content}")
                                
                                # Metadata in columns
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(f"**🆔 Record:** {result.metadata.get('record_number', 'N/A')}")
                                    st.markdown(f"**📊 Status:** {result.metadata.get('status', 'N/A')}")
                                with col2:
                                    st.markdown(f"**📅 Date Issued:** {result.metadata.get('date_issued', 'N/A')}")
                                    st.markdown(f"**⏰ Expires:** {result.metadata.get('expiration_date', 'N/A')}")
                                with col3:
                                    record_type = result.metadata.get('record_type', 'N/A')
                                    if len(record_type) > 30:
                                        st.markdown(f"**🏗️ Type:** {record_type[:30]}...")
                                        st.caption(f"Full type: {record_type}")
                                    else:
                                        st.markdown(f"**🏗️ Type:** {record_type}")
                    
                    else:
                        st.warning("❌ No results found matching your criteria. Try:")
                        st.markdown("""
                        - Different search terms
                        - Removing some filters
                        - Checking spelling
                        - Using broader terms (e.g., "kitchen" instead of "kitchen renovation")
                        """)
                        
                except Exception as e:
                    st.error(f"❌ Search error: {e}")
        else:
            st.info("👆 Enter a search query above to get started!")
    
    # Footer
    st.markdown("---")
    st.markdown("*Built with Streamlit • Powered by ChromaDB & OpenAI Embeddings*")

if __name__ == "__main__":
    main()