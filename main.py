"""
Building Permit Intelligence Platform - Main Orchestrator
Coordinates the complete data pipeline from fetching to vector storage
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import pipeline components
from data_fetchers.miamidade_fetch import fetch_miamidade_permits
from data_fetchers.hillsborough_permits import fetch_hillsborough_permits_sync
from processors.prepare_permits import normalize_and_geocode_permits
from database.upload_to_chroma import upload_permits_to_chroma

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
    
    def fetch_permits(self, days_back=1, max_records_per_county=None):
        """Fetch permits from all configured counties"""
        logger.info(f"Fetching permits from the last {days_back} days")
        all_permits = []
        
        # Miami-Dade
        try:
            logger.info("Fetching Miami-Dade permits...")
            miami_permits = fetch_miamidade_permits(days_back=days_back, max_records=max_records_per_county)
            logger.info(f"Fetched {len(miami_permits)} Miami-Dade permits")
            all_permits.extend(miami_permits)
        except Exception as e:
            logger.error(f"Error fetching Miami-Dade permits: {e}")
        
        # Hillsborough  
        try:
            logger.info("Fetching Hillsborough permits...")
            hills_permits = fetch_hillsborough_permits_sync(days_back=days_back, max_records=max_records_per_county)
            logger.info(f"Fetched {len(hills_permits)} Hillsborough permits")
            all_permits.extend(hills_permits)
        except Exception as e:
            logger.error(f"Error fetching Hillsborough permits: {e}")
        
        # Save raw data
        if all_permits:
            raw_file = self.raw_dir / f"permits_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(raw_file, 'w') as f:
                json.dump(all_permits, f, indent=2, default=str)
            logger.info(f"Saved raw data to {raw_file}")
        
        logger.info(f"Total permits fetched: {len(all_permits)}")
        return all_permits
    
    def process_permits(self, raw_permits):
        """Normalize and process permits"""
        if not raw_permits:
            logger.warning("No permits to process")
            return []
        
        logger.info(f"Processing {len(raw_permits)} permits...")
        
        try:
            processed_permits = normalize_and_geocode_permits(raw_permits)
            
            # Save processed data
            processed_file = self.processed_dir / f"permits_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(processed_file, 'w') as f:
                json.dump(processed_permits, f, indent=2, default=str)
            logger.info(f"Saved processed data to {processed_file}")
            
            return processed_permits
            
        except Exception as e:
            logger.error(f"Error processing permits: {e}")
            raise
    
    def upload_to_database(self, processed_permits):
        """Upload processed permits to ChromaDB"""
        if not processed_permits:
            logger.warning("No permits to upload")
            return {"status": "no_data"}
        
        logger.info(f"Uploading {len(processed_permits)} permits to ChromaDB...")
        
        try:
            result = upload_permits_to_chroma(processed_permits)
            logger.info(f"Upload complete: {result}")
            return result
        except Exception as e:
            logger.error(f"Error uploading to database: {e}")
            raise
    
    def run_pipeline(self, days_back=1, max_records_per_county=None):
        """Execute the complete data pipeline"""
        start_time = datetime.now()
        logger.info(f"Starting permit pipeline at {start_time}")
        
        try:
            # Step 1: Fetch permits
            raw_permits = self.fetch_permits(days_back=days_back, max_records_per_county=max_records_per_county)
            
            if not raw_permits:
                return {"status": "no_data", "message": "No permits fetched"}
            
            # Step 2: Process permits
            processed_permits = self.process_permits(raw_permits)
            
            if not processed_permits:
                return {"status": "processing_failed", "message": "No permits processed successfully"}
            
            # Step 3: Upload to database
            upload_result = self.upload_to_database(processed_permits)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            result = {
                "status": "success",
                "permits_fetched": len(raw_permits),
                "permits_processed": len(processed_permits),
                "permits_uploaded": upload_result.get('uploaded', 0),
                "duration_seconds": duration.total_seconds(),
                "timestamp": end_time.isoformat(),
                "upload_details": upload_result
            }
            
            logger.info(f"Pipeline completed successfully: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Pipeline failed: {e}"
            logger.error(error_msg)
            return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import argparse
    
    # Initialize data manager for GitHub Actions if needed
    if os.getenv('GITHUB_ACTIONS'):
        sys.path.append(str(Path(__file__).parent / "scripts"))
        try:
            from github_data_manager import GitHubDataManager
            data_manager = GitHubDataManager()
            data_manager.prepare_for_run()
            logger.info("GitHub Actions data preparation complete")
        except ImportError:
            logger.warning("GitHub data manager not available")
    
    parser = argparse.ArgumentParser(description="Building Permit Intelligence Pipeline")
    parser.add_argument("--days", type=int, default=1, help="Number of days back to fetch permits")
    parser.add_argument("--max-records", type=int, help="Maximum records per county (for testing)")
    
    args = parser.parse_args()
    
    pipeline = PermitPipeline()
    result = pipeline.run_pipeline(days_back=args.days, max_records_per_county=args.max_records)
    
    # Save metadata for GitHub Actions
    if os.getenv('GITHUB_ACTIONS'):
        try:
            data_manager.save_run_metadata(result)
        except:
            pass  # Don't fail if metadata save fails
    
    print(f"\nPipeline Result:")
    print(json.dumps(result, indent=2))
