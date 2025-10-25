#!/usr/bin/env python3
"""
Test script to verify the new MONTHS_AHEAD configuration is working.
"""

import os

from app.config import settings

def test_months_ahead_config():
    """Test the MONTHS_AHEAD configuration."""
    print("Testing MONTHS_AHEAD Configuration")
    print("=" * 40)
    
    print(f"MONTHS_AHEAD setting: {settings.months_ahead}")
    print(f"Environment variable: {os.getenv('MONTHS_AHEAD', 'Not set')}")
    
    # Test validation
    print(f"\nValidation test:")
    print(f"- Value: {settings.months_ahead}")
    print(f"- Type: {type(settings.months_ahead)}")
    print(f"- Valid range: 1-12")
    print(f"- Is valid: {1 <= settings.months_ahead <= 12}")
    
    # Test what this means for scraping
    from datetime import date, timedelta
    today = date.today()
    
    print(f"\nScraping behavior:")
    print(f"- Today: {today}")
    print(f"- Will check {settings.months_ahead} months ahead")
    
    for i in range(settings.months_ahead):
        target_date = today + timedelta(days=30 * i)
        print(f"  Month {i+1}: {target_date.strftime('%B %Y')} (month {target_date.month})")
    
    print(f"\n✓ Configuration loaded successfully!")

if __name__ == "__main__":
    test_months_ahead_config()
