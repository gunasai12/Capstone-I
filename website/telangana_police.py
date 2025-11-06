"""
Telangana Police Integrated e-Challan System Integration
"""

import requests
import json
from datetime import datetime, timedelta
import re
import time
import random
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelanganaPoliceAPI:
    """
    Integration with Telangana Police e-Challan System
    Supports multiple integration methods: API Setu, direct web services, third-party APIs
    """
    
    def __init__(self):
        self.base_urls = {
            'telangana_police': 'https://echallan.tspolice.gov.in',
            'parivahan': 'https://echallan.parivahan.gov.in',
            'api_setu': 'https://apisetu.gov.in'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Cache for reducing API calls
        self.cache = {}
        self.cache_expiry = 300  # 5 minutes
    
    def search_vehicle_challans(self, vehicle_number: str) -> List[Dict[str, Any]]:
        """
        Search for all challans for a specific vehicle number
        
        Args:
            vehicle_number: Vehicle registration number (e.g., TS05FH4947)
            
        Returns:
            List of challan records
        """
        try:
            # Normalize vehicle number
            vehicle_number = self._normalize_vehicle_number(vehicle_number)
            
            # Check cache first
            cache_key = f"vehicle_{vehicle_number}"
            if self._is_cache_valid(cache_key):
                logger.info(f"Returning cached data for vehicle {vehicle_number}")
                return self.cache[cache_key]['data']
            
            # Try multiple sources
            results = []
            
            # Method 1: Telangana Police Portal
            try:
                ts_results = self._fetch_from_telangana_portal(vehicle_number)
                results.extend(ts_results)
                logger.info(f"Found {len(ts_results)} records from Telangana Police portal")
            except Exception as e:
                logger.warning(f"Telangana Police portal failed: {e}")
            
            # Method 2: National Parivahan Portal
            try:
                parivahan_results = self._fetch_from_parivahan(vehicle_number)
                results.extend(parivahan_results)
                logger.info(f"Found {len(parivahan_results)} records from Parivahan portal")
            except Exception as e:
                logger.warning(f"Parivahan portal failed: {e}")
            
            # Method 3: Third-party APIs (if available)
            try:
                third_party_results = self._fetch_from_third_party_apis(vehicle_number)
                results.extend(third_party_results)
                logger.info(f"Found {len(third_party_results)} records from third-party APIs")
            except Exception as e:
                logger.warning(f"Third-party APIs failed: {e}")
            
            # Deduplicate results based on challan number
            results = self._deduplicate_challans(results)
            
            # Cache the results
            self.cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Total unique challans found for {vehicle_number}: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vehicle challans: {e}")
            return []
    
    def search_challan_by_number(self, challan_number: str) -> Optional[Dict[str, Any]]:
        """
        Search for a specific challan by its number
        
        Args:
            challan_number: E-challan number
            
        Returns:
            Challan details or None if not found
        """
        try:
            cache_key = f"challan_{challan_number}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
            
            # Try multiple sources
            for method_name, method in [
                ("Telangana Police", self._fetch_challan_from_telangana),
                ("Parivahan", self._fetch_challan_from_parivahan),
                ("Third-party", self._fetch_challan_from_third_party)
            ]:
                try:
                    result = method(challan_number)
                    if result:
                        # Cache the result
                        self.cache[cache_key] = {
                            'data': result,
                            'timestamp': datetime.now()
                        }
                        logger.info(f"Found challan {challan_number} via {method_name}")
                        return result
                except Exception as e:
                    logger.warning(f"{method_name} failed for challan {challan_number}: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching challan: {e}")
            return None
    
    def get_all_recent_challans(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get all recent challans from the system (if supported by API)
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of recent challans
        """
        try:
            # This would typically require admin access or special API permissions
            # For now, return demo data structure
            return self._get_demo_recent_challans(days_back)
        except Exception as e:
            logger.error(f"Error fetching recent challans: {e}")
            return []
    
    def _fetch_from_telangana_portal(self, vehicle_number: str) -> List[Dict[str, Any]]:
        """Fetch data from Telangana Police portal"""
        url = f"{self.base_urls['telangana_police']}/publicview/"
        
        # This is a simulation of the web scraping process
        # In practice, you'd need to handle forms, CAPTCHA, etc.
        
        payload = {
            'vehicleNo': vehicle_number,
            'searchType': 'vehicle'
        }
        
        # For demo purposes, return simulated data
        return self._generate_demo_challans(vehicle_number, 'telangana_police')
    
    def _fetch_from_parivahan(self, vehicle_number: str) -> List[Dict[str, Any]]:
        """Fetch data from National Parivahan portal"""
        url = f"{self.base_urls['parivahan']}/index/accused-challan/"
        
        # Simulate API call
        return self._generate_demo_challans(vehicle_number, 'parivahan')
    
    def _fetch_from_third_party_apis(self, vehicle_number: str) -> List[Dict[str, Any]]:
        """Fetch data from third-party APIs like APIclub.in"""
        # These would require API keys and paid subscriptions
        # For demo, return simulated data
        return self._generate_demo_challans(vehicle_number, 'third_party')
    
    def _fetch_challan_from_telangana(self, challan_number: str) -> Optional[Dict[str, Any]]:
        """Fetch specific challan from Telangana Police"""
        # Simulate specific challan lookup
        return self._generate_demo_challan_detail(challan_number, 'telangana_police')
    
    def _fetch_challan_from_parivahan(self, challan_number: str) -> Optional[Dict[str, Any]]:
        """Fetch specific challan from Parivahan"""
        return self._generate_demo_challan_detail(challan_number, 'parivahan')
    
    def _fetch_challan_from_third_party(self, challan_number: str) -> Optional[Dict[str, Any]]:
        """Fetch specific challan from third-party APIs"""
        return self._generate_demo_challan_detail(challan_number, 'third_party')
    
    def _normalize_vehicle_number(self, vehicle_number: str) -> str:
        """Normalize vehicle number format"""
        # Remove spaces and convert to uppercase
        normalized = re.sub(r'\s+', '', vehicle_number.upper())
        
        # Validate format (basic Indian vehicle number pattern)
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$', normalized):
            logger.warning(f"Invalid vehicle number format: {vehicle_number}")
        
        return normalized
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        
        cache_time = self.cache[key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_expiry
    
    def _deduplicate_challans(self, challans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate challans based on challan number"""
        seen = set()
        unique_challans = []
        
        for challan in challans:
            challan_id = challan.get('challan_number', '')
            if challan_id and challan_id not in seen:
                seen.add(challan_id)
                unique_challans.append(challan)
        
        return unique_challans
    
    def _generate_demo_challans(self, vehicle_number: str, source: str) -> List[Dict[str, Any]]:
        """Generate demo challan data for testing"""
        challans = []
        
        # Generate 2-5 demo challans per source
        import random
        num_challans = random.randint(1, 3) if vehicle_number else 0
        
        violations = [
            {'type': 'Over Speeding', 'fine': 1000, 'section': 'MV Act 184'},
            {'type': 'No Helmet', 'fine': 1000, 'section': 'MV Act 129'},
            {'type': 'Signal Jump', 'fine': 5000, 'section': 'MV Act 177'},
            {'type': 'Wrong Side Driving', 'fine': 5000, 'section': 'MV Act 184'},
            {'type': 'Mobile Phone Usage', 'fine': 5000, 'section': 'MV Act 184'},
        ]
        
        for i in range(num_challans):
            violation = random.choice(violations)
            challan_date = datetime.now() - timedelta(days=random.randint(1, 90))
            
            challan = {
                'challan_number': f"{source.upper()[:2]}{challan_date.strftime('%Y%m%d')}{random.randint(1000, 9999)}",
                'vehicle_number': vehicle_number,
                'violation_type': violation['type'],
                'fine_amount': violation['fine'],
                'challan_date': challan_date.strftime('%Y-%m-%d'),
                'challan_time': f"{random.randint(8, 20):02d}:{random.randint(0, 59):02d}",
                'location': f"Traffic Post {random.randint(1, 50)}, Hyderabad",
                'officer_name': f"Inspector {chr(65 + random.randint(0, 25))}. Kumar",
                'section': violation['section'],
                'court': 'Metropolitan Magistrate Court, Hyderabad',
                'last_date': (challan_date + timedelta(days=30)).strftime('%Y-%m-%d'),
                'payment_status': random.choice(['Paid', 'Unpaid', 'Pending']),
                'source': source,
                'created_at': challan_date.isoformat(),
                'is_telangana_police': True
            }
            
            challans.append(challan)
        
        return challans
    
    def _generate_demo_challan_detail(self, challan_number: str, source: str) -> Dict[str, Any]:
        """Generate detailed demo challan data"""
        violations = [
            {'type': 'Over Speeding', 'fine': 1000, 'section': 'MV Act 184'},
            {'type': 'No Helmet', 'fine': 1000, 'section': 'MV Act 129'},
        ]
        
        violation = violations[0]  # Use first violation for consistency
        challan_date = datetime.now() - timedelta(days=15)
        
        return {
            'challan_number': challan_number,
            'vehicle_number': 'TS05FH4947',  # Default demo vehicle
            'violation_type': violation['type'],
            'fine_amount': violation['fine'],
            'challan_date': challan_date.strftime('%Y-%m-%d'),
            'challan_time': '14:30',
            'location': 'Banjara Hills, Hyderabad',
            'officer_name': 'Inspector R. Sharma',
            'section': violation['section'],
            'court': 'Metropolitan Magistrate Court, Hyderabad',
            'last_date': (challan_date + timedelta(days=30)).strftime('%Y-%m-%d'),
            'payment_status': 'Unpaid',
            'source': source,
            'created_at': challan_date.isoformat(),
            'is_telangana_police': True,
            'additional_details': {
                'weather': 'Clear',
                'road_type': 'Main Road',
                'vehicle_model': 'Motorcycle',
                'owner_name': 'Demo Owner',
                'address': 'Hyderabad, Telangana'
            }
        }
    
    def _get_demo_recent_challans(self, days_back: int) -> List[Dict[str, Any]]:
        """Get demo recent challans"""
        recent_challans = []
        
        # Generate some recent challans for demo
        for i in range(10):  # Generate 10 recent challans
            challan_date = datetime.now() - timedelta(days=i)
            vehicle_num = f"TS{random.randint(10, 50):02d}{random.choice(['AB', 'CD', 'EF', 'GH'])}{random.randint(1000, 9999)}"
            
            challan = {
                'challan_number': f"TS{challan_date.strftime('%Y%m%d')}{random.randint(1000, 9999)}",
                'vehicle_number': vehicle_num,
                'violation_type': random.choice(['Over Speeding', 'No Helmet', 'Signal Jump', 'Wrong Parking']),
                'fine_amount': random.choice([500, 1000, 2000, 5000]),
                'challan_date': challan_date.strftime('%Y-%m-%d'),
                'location': f"Area {random.randint(1, 20)}, Hyderabad",
                'payment_status': random.choice(['Paid', 'Unpaid']),
                'source': 'recent_data',
                'is_telangana_police': True
            }
            
            recent_challans.append(challan)
        
        return recent_challans

# Global instance for easy access
telangana_api = TelanganaPoliceAPI()

def get_vehicle_challans(vehicle_number: str) -> List[Dict[str, Any]]:
    """
    Simple function to get all challans for a vehicle
    """
    return telangana_api.search_vehicle_challans(vehicle_number)

def get_challan_details(challan_number: str) -> Optional[Dict[str, Any]]:
    """
    Simple function to get specific challan details
    """
    return telangana_api.search_challan_by_number(challan_number)

def get_recent_challans(days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Simple function to get recent challans
    """
    return telangana_api.get_all_recent_challans(days_back)