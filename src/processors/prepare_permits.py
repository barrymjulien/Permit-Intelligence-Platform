"""
Permit Data Normalization and Processing
Handles data from multiple counties and normalizes to common schema
"""

import json
import logging
import pandas as pd
import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import re

logger = logging.getLogger(__name__)

@dataclass
class NormalizedPermit:
    """Standardized permit data structure"""
    permit_id: str
    source_county: str
    permit_type: str
    description: str
    address: str
    city: str
    zipcode: str
    coordinates: Optional[Dict[str, float]] = None
    applicant_name: Optional[str] = None
    contractor_name: Optional[str] = None
    permit_value: Optional[float] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: Optional[str] = None
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

class PermitProcessor:
    def __init__(self, enable_geocoding=True):
        # Field mappings for each county
        self.field_mappings = {
            'miami-dade': {
                'permit_id': 'FOLIO',
                'permit_type': 'PERMIT_TYPE',
                'description': 'DESC1',  # Will combine DESC1-DESC10 if available
                'address': 'ADDRESS',
                'city': 'CITY',
                'zipcode': 'ZIP',
                'applicant_name': 'APPLICANT',
                'contractor_name': 'CONTRACTOR',
                'permit_value': 'JOB_VAL',
                'issue_date': 'ISSUDATE',
                'expiration_date': 'EXPRDATE',
                'status': 'STATUS'
            },
            'hillsborough': {
                'permit_id': 'Record Number',
                'permit_type': 'Record Type',
                'description': 'Description',
                'address': 'Address',
                'city': 'City',
                'zipcode': 'Zip',
                'applicant_name': 'Applicant Name',
                'contractor_name': 'Contractor Name',
                'permit_value': 'Estimated Value',
                'issue_date': 'Date',
                'expiration_date': 'Expiration Date',
                'status': 'Status'
            }
        }
        
        # Geocoding setup
        self.enable_geocoding = enable_geocoding
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.cache_file = Path("data/cache/geocode_cache.json")
        self.geocode_cache = self.load_geocoding_cache()
        
        if enable_geocoding and not self.google_api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not found. Geocoding will use cache only.")
    
    def load_geocoding_cache(self) -> Dict[str, Any]:
        """Load existing geocoding cache"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached geocoding results")
                return cache
        except Exception as e:
            logger.warning(f"Error loading geocoding cache: {e}")
        
        return {}
    
    def save_geocoding_cache(self):
        """Save geocoding cache"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.geocode_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving geocoding cache: {e}")
    
    def geocode_address(self, address: str, city: str = "", zipcode: str = "") -> Optional[Dict[str, float]]:
        """Geocode an address using Google Maps API with caching"""
        if not self.enable_geocoding:
            return None
            
        # Create full address for geocoding
        # If address already contains city/zip info, use it as-is, otherwise build it
        if city or zipcode:
            full_address = f"{address}, {city}, FL {zipcode}".strip(", ")
        else:
            # Address might already be complete (e.g., "123 Main St, City FL 12345")
            full_address = address.strip()
        
        # Normalize for cache lookup (title case, clean whitespace)
        normalized_address = self.clean_address_for_cache(full_address)
        
        # Check cache first (try both original and normalized)
        cache_keys = [full_address, normalized_address]
        for cache_key in cache_keys:
            if cache_key in self.geocode_cache:
                cached_result = self.geocode_cache[cache_key]
                if cached_result and len(cached_result) == 2:
                    return {"lat": cached_result[0], "lng": cached_result[1]}
        
        # If no API key, can't geocode new addresses
        if not self.google_api_key:
            return None
            
        try:
            # Rate limiting
            time.sleep(0.1)
            
            # Call Google Maps API
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": full_address,
                "key": self.google_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                coordinates = {"lat": location["lat"], "lng": location["lng"]}
                
                # Cache the result
                self.geocode_cache[full_address] = [location["lat"], location["lng"]]
                self.save_geocoding_cache()
                
                logger.debug(f"Geocoded: {full_address} -> {coordinates}")
                return coordinates
            else:
                # Cache null result to avoid repeated API calls
                self.geocode_cache[full_address] = None
                self.save_geocoding_cache()
                return None
                
        except Exception as e:
            logger.error(f"Geocoding error for '{full_address}': {e}")
            return None
    
    def normalize_permit(self, raw_permit: Dict[str, Any]) -> NormalizedPermit:
        """Normalize a single permit to standard schema"""
        county = raw_permit.get('source_county', 'unknown')
        mapping = self.field_mappings.get(county, {})
        
        # Extract fields using mapping
        normalized_data = {'source_county': county}
        
        for standard_field, source_field in mapping.items():
            value = raw_permit.get(source_field)
            if value is not None:
                normalized_data[standard_field] = value
        
        # Handle Miami-Dade description fields (DESC1-DESC10)
        if county == 'miami-dade':
            desc_parts = []
            for i in range(1, 11):
                desc_field = f'DESC{i}'
                if desc_field in raw_permit and raw_permit[desc_field]:
                    desc_parts.append(str(raw_permit[desc_field]).strip())
            if desc_parts:
                normalized_data['description'] = ' | '.join(desc_parts)
        
        # Clean and convert permit value
        if 'permit_value' in normalized_data:
            try:
                value_str = str(normalized_data['permit_value']).replace('$', '').replace(',', '').strip()
                normalized_data['permit_value'] = float(value_str) if value_str else None
            except (ValueError, TypeError):
                normalized_data['permit_value'] = None
        
        # Clean address
        if 'address' in normalized_data:
            normalized_data['address'] = self.clean_address(normalized_data['address'])
        
        # Handle date normalization - use current date as pull date
        # Since this is historical data being pulled, use current date as issue date
        from datetime import datetime
        normalized_data['issue_date'] = datetime.now().strftime('%m/%d/%Y')
        
        # Geocode the address if enabled
        if self.enable_geocoding and normalized_data.get('address'):
            coordinates = self.geocode_address(
                normalized_data.get('address', ''),
                normalized_data.get('city', ''),
                normalized_data.get('zipcode', '')
            )
            normalized_data['coordinates'] = coordinates
        
        # Ensure required fields have defaults
        required_defaults = {
            'permit_id': 'UNKNOWN',
            'permit_type': 'UNKNOWN',
            'description': '',
            'address': '',
            'city': '',
            'zipcode': ''
        }
        
        for field, default in required_defaults.items():
            if field not in normalized_data or not normalized_data[field]:
                normalized_data[field] = default
        
        return NormalizedPermit(**normalized_data)
    
    def clean_address_for_cache(self, address: str) -> str:
        """Normalize address format for cache lookup"""
        if not address:
            return ""
        
        # Remove extra whitespace
        address = re.sub(r'\s+', ' ', str(address).strip())
        
        # Convert to title case for consistency
        address = address.title()
        
        # Fix common abbreviations that should stay uppercase
        address = re.sub(r'\bFl\b', 'FL', address)
        address = re.sub(r'\bRd\b', 'Rd', address)
        address = re.sub(r'\bSt\b', 'St', address)
        address = re.sub(r'\bAve\b', 'Ave', address)
        address = re.sub(r'\bDr\b', 'Dr', address)
        address = re.sub(r'\bLn\b', 'Ln', address)
        address = re.sub(r'\bCt\b', 'Ct', address)
        address = re.sub(r'\bPl\b', 'Pl', address)
        address = re.sub(r'\bBlvd\b', 'Blvd', address)
        
        return address

    def clean_address(self, address: str) -> str:
        """Clean and standardize address format"""
        if not address:
            return ""
        
        # Remove extra whitespace
        address = re.sub(r'\s+', ' ', str(address).strip())
        
        # Standardize directionals
        directional_map = {
            'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W',
            'NORTHEAST': 'NE', 'NORTHWEST': 'NW', 'SOUTHEAST': 'SE', 'SOUTHWEST': 'SW'
        }
        
        for full, abbrev in directional_map.items():
            address = re.sub(f'\\b{full}\\b', abbrev, address, flags=re.IGNORECASE)
        
        # Standardize street types
        street_types = {
            'STREET': 'ST', 'AVENUE': 'AVE', 'BOULEVARD': 'BLVD', 'DRIVE': 'DR',
            'ROAD': 'RD', 'LANE': 'LN', 'COURT': 'CT', 'PLACE': 'PL'
        }
        
        for full, abbrev in street_types.items():
            address = re.sub(f'\\b{full}\\b', abbrev, address, flags=re.IGNORECASE)
        
        return address.upper()
    
    def process_permits(self, raw_permits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of raw permits and return normalized data"""
        logger.info(f"Processing {len(raw_permits)} permits")
        
        normalized_permits = []
        
        for i, raw_permit in enumerate(raw_permits):
            try:
                normalized = self.normalize_permit(raw_permit)
                normalized_permits.append(asdict(normalized))
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Processed {i + 1}/{len(raw_permits)} permits")
                    
            except Exception as e:
                logger.error(f"Error processing permit {i}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(normalized_permits)} permits")
        return normalized_permits

def normalize_and_geocode_permits(raw_permits: List[Dict[str, Any]], enable_geocoding=True) -> List[Dict[str, Any]]:
    """Main function to normalize permits and optionally geocode them"""
    processor = PermitProcessor(enable_geocoding=enable_geocoding)
    
    # Process permits
    normalized_permits = processor.process_permits(raw_permits)
    
    # Save geocoding cache if we geocoded anything
    if enable_geocoding:
        processor.save_geocoding_cache()
    
    return normalized_permits

if __name__ == "__main__":
    # Test the processor
    sample_permits = [
        {
            "FOLIO": "TEST123",
            "PERMIT_TYPE": "Building",
            "DESC1": "Kitchen renovation",
            "ADDRESS": "123 Main Street",
            "CITY": "Miami", 
            "ZIP": "33101",
            "source_county": "miami-dade"
        }
    ]
    
    result = normalize_and_geocode_permits(sample_permits)
    print(json.dumps(result, indent=2))
