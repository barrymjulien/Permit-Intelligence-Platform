#!/usr/bin/env python3
"""
GitHub Actions Data Persistence Helper
Manages data artifacts between workflow runs
"""

import json
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class GitHubDataManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.artifacts_dir = Path("artifacts")
        
    def prepare_for_run(self):
        """Prepare directories and restore data if available"""
        # Create necessary directories
        dirs_to_create = [
            "data/raw",
            "data/processed", 
            "data/cache",
            "data/chroma_db",
            "logs"
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
        # If we have existing artifacts, restore them
        if self.artifacts_dir.exists():
            self._restore_artifacts()
            
    def _restore_artifacts(self):
        """Restore data from previous runs"""
        logger.info("Restoring data from previous runs...")
        
        # Restore cache
        cache_file = self.artifacts_dir / "cache" / "geocode_cache.json"
        if cache_file.exists():
            shutil.copy2(cache_file, "data/cache/geocode_cache.json")
            logger.info("Restored geocoding cache")
            
        # Restore ChromaDB if it exists
        chroma_source = self.artifacts_dir / "chroma_db"
        if chroma_source.exists():
            shutil.copytree(chroma_source, "data/chroma_db", dirs_exist_ok=True)
            logger.info("Restored ChromaDB data")
            
    def save_run_metadata(self, pipeline_result):
        """Save metadata about this run"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "permits_fetched": pipeline_result.get("permits_fetched", 0),
            "permits_processed": pipeline_result.get("permits_processed", 0),
            "permits_uploaded": pipeline_result.get("permits_uploaded", 0),
            "duration_seconds": pipeline_result.get("duration_seconds", 0),
            "status": pipeline_result.get("status", "unknown")
        }
        
        metadata_file = Path("data/run_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Saved run metadata: {metadata}")

if __name__ == "__main__":
    # This can be called from the workflow to prepare data
    import sys
    
    manager = GitHubDataManager()
    
    if len(sys.argv) > 1 and sys.argv[1] == "prepare":
        manager.prepare_for_run()
        print("✅ Data preparation complete")
    else:
        print("Usage: python github_data_manager.py prepare")
