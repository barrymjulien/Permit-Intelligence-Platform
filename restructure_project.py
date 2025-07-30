#!/usr/bin/env python3
"""
Project Restructure Script
Organizes the Building Permits project into proper directory structure
"""

import os
import shutil
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_directory_structure():
    """Create the new directory structure"""
    directories = [
        "src",
        "src/data_fetchers",
        "src/processors", 
        "src/database",
        "src/web_interface",
        "src/api",
        "data",
        "data/raw",
        "data/processed",
        "data/cache",
        "config",
        "logs",
        "scripts",
        "tests",
        "archive"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

def move_file_safely(source, destination):
    """Move a file safely, creating destination directory if needed"""
    source_path = Path(source)
    dest_path = Path(destination)
    
    if not source_path.exists():
        logger.warning(f"Source file does not exist: {source}")
        return False
    
    # Create destination directory if it doesn't exist
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if dest_path.exists():
            logger.warning(f"Destination already exists, skipping: {dest_path}")
            return False
        
        shutil.move(str(source_path), str(dest_path))
        logger.info(f"Moved: {source} → {destination}")
        return True
    except Exception as e:
        logger.error(f"Error moving {source} to {destination}: {e}")
        return False

def restructure_project():
    """Reorganize the project files"""
    logger.info("Starting project restructure...")
    
    # Create directory structure
    create_directory_structure()
    
    # File movements based on current structure
    file_moves = {
        # Core data fetchers (keep latest versions)
        "miamidade_fetch.py": "src/data_fetchers/miamidade_fetch.py",
        "permits_scraper4.py": "src/data_fetchers/hillsborough_permits.py",  # Latest version
        
        # Processors
        "prepare_permits.py": "src/processors/prepare_permits.py",
        "chroma_client.py": "src/processors/chroma_client.py",
        
        # Database operations
        "populate_chroma.py": "src/database/populate_chroma.py",
        "upload_to_weaviate.py": "src/database/upload_to_weaviate.py",
        "weaviate_client.py": "src/database/weaviate_client.py",
        "view_db.py": "src/database/view_db.py",
        
        # Web interface
        "streamlit_permit_search.py": "src/web_interface/streamlit_permit_search.py",
        "interactive_search.py": "src/web_interface/interactive_search.py",
        "advanced_search.py": "src/web_interface/advanced_search.py",
        "search_permits.py": "src/web_interface/search_permits.py",
        
        # API (convert current main.py to FastAPI)
        "main.py": "src/api/fastapi_main.py",
        "permitVectorAPI": "src/api/permit_vector_api.py",
        
        # Data files
        "miamidade_permits.csv": "data/raw/miamidade_permits.csv",
        "cleaned_permits.json": "data/processed/cleaned_permits.json",
        "geocode_cache.json": "data/cache/geocode_cache.json",
        
        # Utility scripts
        "list.py": "scripts/list.py",
        
        # Configuration
        "dependices.txt": "config/dependencies.txt",
        "Dockerfile.dockerfile": "config/Dockerfile",
        ".env": ".env",  # Keep in root
    }
    
    # Archive old versions
    archive_files = {
        "miamidade_fetch_2.py": "archive/miamidade_fetch_2.py",
        "miamidade_fetch_debug.py": "archive/miamidade_fetch_debug.py",
        "permits_scraper.py": "archive/permits_scraper.py",
        "permits_scraper2.py": "archive/permits_scraper2.py",
        "permits_scraper3.py": "archive/permits_scraper3.py",
        "prepare_permits_hills.py": "archive/prepare_permits_hills.py",
        "prepare_permits_miamidade.py": "archive/prepare_permits_miamidade.py",
    }
    
    # Move permit downloads
    permit_downloads_moves = {
        "permit_downloads/RecordList20250630.csv": "data/raw/hillsborough_permits_20250630.csv"
    }
    
    # Execute file moves
    logger.info("Moving main files...")
    for source, dest in file_moves.items():
        move_file_safely(source, dest)
    
    logger.info("Moving archive files...")
    for source, dest in archive_files.items():
        move_file_safely(source, dest)
    
    logger.info("Moving permit downloads...")
    for source, dest in permit_downloads_moves.items():
        move_file_safely(source, dest)
    
    # Move chroma_db directory
    if Path("chroma_db").exists():
        if not Path("data/chroma_db").exists():
            shutil.move("chroma_db", "data/chroma_db")
            logger.info("Moved: chroma_db → data/chroma_db")
        else:
            logger.warning("data/chroma_db already exists, skipping chroma_db move")
    
    # Move __pycache__ to archive
    if Path("__pycache__").exists():
        if not Path("archive/__pycache__").exists():
            shutil.move("__pycache__", "archive/__pycache__")
            logger.info("Moved: __pycache__ → archive/__pycache__")
    
    # Clean up empty permit_downloads directory
    if Path("permit_downloads").exists() and not any(Path("permit_downloads").iterdir()):
        Path("permit_downloads").rmdir()
        logger.info("Removed empty directory: permit_downloads")

def create_new_main_orchestrator():
    """Create the new main.py orchestrator"""
    main_content = '''"""
Building Permit Intelligence Platform - Main Orchestrator
Coordinates the complete data pipeline from fetching to vector storage
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import pipeline components
from data_fetchers.miamidade_fetch import fetch_miamidade_permits
from data_fetchers.hillsborough_permits import fetch_hillsborough_permits  
from processors.prepare_permits import normalize_and_geocode_permits
from database.populate_chroma import upload_permits_to_chroma

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PermitPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Ensure directories exist
        for dir_path in [self.raw_dir, self.processed_dir, Path("logs")]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def run_pipeline(self):
        """Run the complete data pipeline"""
        logger.info("Starting Building Permit Intelligence Pipeline...")
        
        try:
            # TODO: Implement full pipeline
            # 1. Fetch permits from all counties
            # 2. Normalize and geocode data
            # 3. Upload to ChromaDB
            # 4. Generate reports
            
            logger.info("Pipeline completed successfully")
            return {"status": "success", "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    pipeline = PermitPipeline()
    result = asyncio.run(pipeline.run_pipeline())
    print(f"Pipeline result: {result}")
'''
    
    with open("main.py", "w") as f:
        f.write(main_content)
    logger.info("Created new main.py orchestrator")

def create_config_files():
    """Create initial configuration files"""
    
    # Pipeline configuration
    pipeline_config = '''{
  "counties": ["miami-dade", "hillsborough"],
  "batch_size": 100,
  "max_daily_permits": 1000,
  "geocoding": {
    "enabled": true,
    "batch_size": 25,
    "cache_file": "data/cache/geocode_cache.json",
    "rate_limit_delay": 0.1
  },
  "chroma": {
    "collection_name": "permits",
    "persist_directory": "./data/chroma_db",
    "embedding_model": "text-embedding-3-small"
  },
  "field_mappings": {
    "miami-dade": {
      "permit_id": "permit_number",
      "permit_type": "permit_type",
      "description": "description",
      "address": "address",
      "city": "city",
      "zipcode": "zip_code"
    },
    "hillsborough": {
      "permit_id": "record_number",
      "permit_type": "record_type",
      "description": "description",
      "address": "address",
      "city": "city",
      "zipcode": "zip_code"
    }
  }
}'''
    
    with open("config/pipeline_config.json", "w") as f:
        f.write(pipeline_config)
    logger.info("Created config/pipeline_config.json")
    
    # README for new structure
    readme_content = '''# Building Permit Intelligence Platform

## Project Structure
```
├── src/                    # Source code
│   ├── data_fetchers/      # County data fetching scripts
│   ├── processors/         # Data normalization and processing
│   ├── database/           # Database operations (ChromaDB, Weaviate)
│   ├── web_interface/      # Streamlit and web UI components
│   └── api/                # FastAPI endpoints
├── data/                   # Data storage
│   ├── raw/                # Raw permit data from counties
│   ├── processed/          # Cleaned and normalized data
│   ├── cache/              # Geocoding and other caches
│   └── chroma_db/          # ChromaDB vector database
├── config/                 # Configuration files
├── logs/                   # Application logs
├── scripts/                # Utility scripts
├── tests/                  # Test files
├── archive/                # Old/deprecated files
└── main.py                 # Main pipeline orchestrator
```

## Quick Start
1. Install dependencies: `pip install -r config/dependencies.txt`
2. Set up environment variables in `.env`
3. Run pipeline: `python main.py`
4. Launch web interface: `streamlit run src/web_interface/streamlit_permit_search.py`

## Components
- **Data Fetchers**: Scripts to fetch permit data from Miami-Dade and Hillsborough counties
- **Processors**: Normalize data schemas and geocode addresses
- **Database**: ChromaDB vector storage for semantic search
- **Web Interface**: Streamlit app for searching and analyzing permits
- **API**: FastAPI endpoints for programmatic access
'''
    
    with open("README.md", "w") as f:
        f.write(readme_content)
    logger.info("Created README.md")

def main():
    """Main restructure function"""
    try:
        logger.info("=== Building Permit Project Restructure ===")
        
        # Restructure files
        restructure_project()
        
        # Create new main orchestrator
        create_new_main_orchestrator()
        
        # Create configuration files
        create_config_files()
        
        logger.info("=== Restructure Complete ===")
        logger.info("New project structure created successfully!")
        logger.info("Next steps:")
        logger.info("1. Review the new file organization")
        logger.info("2. Update import paths in moved files")
        logger.info("3. Test the new structure")
        logger.info("4. Run: python main.py")
        
    except Exception as e:
        logger.error(f"Restructure failed: {e}")
        raise

if __name__ == "__main__":
    main()
