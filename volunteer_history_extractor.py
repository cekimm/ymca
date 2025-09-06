import datetime as dt
import requests
import pandas as pd

import logging
import sys
import time
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volunteer_extractor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from requests.auth import HTTPBasicAuth

BASE = "https://api.volunteermatters.io/api/v2"   # from Swagger "Servers"
AUTH = HTTPBasicAuth("62lJN9CLNQbuVag36vFSmDg", "oRBbayCJRE2fdJyqKfs9Axw")
HDRS = {
    "X-VM-Customer-Code": "cincinnatiymca",
    "Accept": "application/json",
}

def validate_config():
    """Validate that required configuration is properly set"""
    logger.info("Validating configuration...")
    
    if "<your-volunteermatters-host>" in BASE:
        logger.error("BASE URL not configured - please replace <your-volunteermatters-host> with actual host")
        sys.exit(1)
    
    # Check if AUTH is properly configured (HTTPBasicAuth object)
    if not hasattr(AUTH, 'username') or not hasattr(AUTH, 'password'):
        logger.error("AUTH not properly configured - should be HTTPBasicAuth object")
        sys.exit(1)
    
    if "<API_KEY>" in AUTH.username or "<API_SECRET>" in AUTH.password:
        logger.error("API credentials not configured - please replace <API_KEY> and <API_SECRET> with actual values")
        sys.exit(1)
    
    if "<YOUR_CODE>" in HDRS.get("X-VM-Customer-Code", ""):
        logger.error("Customer code not configured - please replace <YOUR_CODE> with actual customer code")
        sys.exit(1)
    
    logger.info("Configuration validation passed")

def make_api_request(url: str, headers: Dict, auth: HTTPBasicAuth, params: Dict, max_retries: int = 3) -> Dict[str, Any]:
    """Make API request with retry logic and proper error handling"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Making API request (attempt {attempt + 1}/{max_retries}): {url}")
            logger.debug(f"Parameters: {params}")
            
            response = requests.get(url, headers=headers, auth=auth, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"API response status: {response.status_code}")
            logger.debug(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            return data
            
        except requests.exceptions.Timeout as e:
            logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
            
        except ValueError as e:
            logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

def validate_date_range(start_date: dt.date, end_date: dt.date) -> None:
    """Validate the date range is logical"""
    if start_date >= end_date:
        logger.error(f"Invalid date range: start_date ({start_date}) must be before end_date ({end_date})")
        sys.exit(1)
    
    if end_date > dt.date.today():
        logger.warning(f"End date ({end_date}) is in the future")
    
    logger.info(f"Date range validated: {start_date} to {end_date}")

def extract_items_from_response(data: Dict[str, Any]) -> List[Dict]:
    """Extract items from API response with validation"""
    # Try different possible field names for items
    items = data.get("items") or data.get("results") or data.get("data")
    
    if items is None:
        logger.warning("No items found in response. Checking if response is a list...")
        if isinstance(data, list):
            items = data
        else:
            logger.error(f"Could not find items in response. Available keys: {list(data.keys()) if isinstance(data, dict) else 'Response is not a dict'}")
            return []
    
    if not isinstance(items, list):
        logger.error(f"Items is not a list, got: {type(items)}")
        return []
    
    logger.info(f"Found {len(items)} items in response")
    return items

def main():
    """Main execution function with comprehensive error handling"""
    try:
        logger.info("Starting volunteer history extraction...")
        
        # Validate configuration
        validate_config()
        
        # ---- date window: Jan 1, 2025 -> first day of month being reported ----
        report_month = dt.date(2025, 8, 1)   # example: August report
        start_date   = dt.date(2025, 1, 1)
        # endDate must be the **first day of the next month**
        next_month = (report_month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        end_date = next_month  # e.g., 2025-09-01
        
        # Validate date range
        validate_date_range(start_date, end_date)
        
        params = {
            "startDate": start_date.isoformat(),
            "endDate":   end_date.isoformat(),
            "page": 1,
            "pageSize": 1000
        }
        
        logger.info(f"Starting data extraction with parameters: {params}")
        
        rows = []
        page_count = 0
        
        while True:
            page_count += 1
            logger.info(f"Fetching page {page_count}...")
            
            try:
                data = make_api_request(f"{BASE}/volunteerHistory", HDRS, AUTH, params)
                items = extract_items_from_response(data)
                
                if not items:
                    logger.info("No more items found, stopping pagination")
                    break
                
                rows.extend(items)
                logger.info(f"Added {len(items)} items from page {page_count}. Total items: {len(rows)}")
                
                # pagination handling: adapt to your API (examples below)
                if data.get("hasNextPage"):
                    params["page"] += 1
                    logger.debug("Found hasNextPage=True, incrementing page")
                elif data.get("nextPage"):
                    params["page"] = data["nextPage"]
                    logger.debug(f"Found nextPage={data['nextPage']}")
                else:
                    logger.info("No more pages indicated, stopping pagination")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing page {page_count}: {e}")
                raise
        
        if not rows:
            logger.warning("No data retrieved! Check your API configuration and date range.")
            sys.exit(1)
        
        logger.info(f"Total rows retrieved: {len(rows)}")
        
        # Create DataFrame with error handling
        try:
            df = pd.DataFrame(rows)
            logger.info(f"DataFrame created with shape: {df.shape}")
            if not df.empty:
                logger.info(f"DataFrame columns: {list(df.columns)}")
                logger.debug(f"Sample data (first 3 rows):\n{df.head(3).to_string()}")
        except Exception as e:
            logger.error(f"Error creating DataFrame: {e}")
            raise
        
        # Optional: select/rename the columns you need
        # df = df[["volunteerName","project","hours","startDate","endDate", ...]]
        
        # Save to Excel for your dashboard pipeline
        out = f"VolunteerHistory_{start_date:%Y-%m}_to_{(end_date - dt.timedelta(days=1)):%Y-%m}.xlsx"
        
        try:
            df.to_excel(out, index=False)
            logger.info(f"Successfully saved: {out} | rows: {len(df)}")
            print(f"Saved: {out}  |  rows: {len(df)}")
        except Exception as e:
            logger.error(f"Error saving to Excel: {e}")
            # Fallback to CSV
            csv_out = out.replace('.xlsx', '.csv')
            df.to_csv(csv_out, index=False)
            logger.info(f"Saved as CSV instead: {csv_out}")
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
    
# ---- Date window: Jan 1, 2025 -> first day of the month AFTER report month ----
report_month = dt.date(2025, 8, 1)   # Example: August 2025
start_date   = dt.date(2025, 1, 1)
end_date     = (report_month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

params = {
    "startDate": start_date.isoformat(),
    "endDate":   end_date.isoformat(),
    "page": 1,
    "pageSize": 1000
}

rows = []
while True:
    url = f"{BASE}/volunteerHistory"
    r = requests.get(url, headers=HDRS, auth=AUTH, params=params, timeout=60)
    print(f"Requesting: {r.url}")
    print("Status:", r.status_code)
    if not r.ok:
        raise SystemExit(f"❌ {r.status_code} {r.reason}: {r.text}")

    data = r.json()
    items = data.get("items") or data.get("results") or data
    if not items:
        break
    rows.extend(items)

    if data.get("hasNextPage"):
        params["page"] += 1
    elif data.get("nextPage"):
        params["page"] = data["nextPage"]
    else:
        break

# ---- Save to Excel ----
df = pd.DataFrame(rows)
out = f"VolunteerHistory_{start_date:%Y-%m}_to_{(end_date - dt.timedelta(days=1)):%Y-%m}.xlsx"
df.to_excel(out, index=False)
print(f"✅ Saved: {out} | rows: {len(df)}")