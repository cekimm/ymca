#!/usr/bin/env python3
import datetime as dt
import logging
import sys
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration values (placeholder)
BASE = "https://<your-volunteermatters-host>/api/v3"
AUTH = ("<API_KEY>", "<API_SECRET>")
HDRS = {"X-VM-Customer-Code": "<YOUR_CODE>"}

def validate_config():
    """Validate that required configuration is properly set"""
    logger.info("Validating configuration...")
    
    if "<your-volunteermatters-host>" in BASE:
        logger.error("BASE URL not configured - please replace <your-volunteermatters-host> with actual host")
        return False
    
    if "<API_KEY>" in AUTH[0] or "<API_SECRET>" in AUTH[1]:
        logger.error("API credentials not configured - please replace <API_KEY> and <API_SECRET> with actual values")
        return False
    
    if "<YOUR_CODE>" in HDRS.get("X-VM-Customer-Code", ""):
        logger.error("Customer code not configured - please replace <YOUR_CODE> with actual customer code")
        return False
    
    logger.info("Configuration validation passed")
    return True

def validate_date_range(start_date: dt.date, end_date: dt.date) -> bool:
    """Validate the date range is logical"""
    if start_date >= end_date:
        logger.error(f"Invalid date range: start_date ({start_date}) must be before end_date ({end_date})")
        return False
    
    if end_date > dt.date.today():
        logger.warning(f"End date ({end_date}) is in the future")
    
    logger.info(f"Date range validated: {start_date} to {end_date}")
    return True

if __name__ == "__main__":
    logger.info("Testing validation functions...")
    
    # Test configuration validation
    config_valid = validate_config()
    logger.info(f"Configuration validation result: {config_valid}")
    
    # Test date validation
    start_date = dt.date(2025, 1, 1)
    report_month = dt.date(2025, 8, 1)
    next_month = (report_month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    end_date = next_month
    
    date_valid = validate_date_range(start_date, end_date)
    logger.info(f"Date range validation result: {date_valid}")
    
    logger.info("Validation test completed!")