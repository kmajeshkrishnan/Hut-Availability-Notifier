#!/usr/bin/env python3
"""
Test script to verify the improved scraper is working correctly.
"""

import requests
from datetime import date, datetime

BASE_URL = "http://localhost:8000"

def test_scraper_functionality():
    """Test the improved scraper functionality."""
    print("Testing Improved Scraper Functionality")
    print("=" * 50)
    
    # Test 1: Check if we have data
    print("\n1. Checking for scraped data...")
    response = requests.get(f"{BASE_URL}/availability")
    if response.status_codpe == 200:
        data = response.json()
        print(f"✓ Found {len(data)} availability records")
        
        if data:
            # Show first few records
            print("   Sample records:")
            for record in data[:5]:
                day_name = datetime.strptime(record['date'], '%Y-%m-%d').strftime('%A')
                print(f"   - {record['date']} ({day_name}): {record['status']}")
        else:
            print("   ⚠ No data found - scraper may not be working")
    else:
        print(f"✗ Failed to get availability data: {response.status_code}")
        return False
    
    # Test 2: Check data distribution
    print("\n2. Checking data distribution...")
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        stats = response.json()['availability']
        print(f"✓ Total records: {stats['total']}")
        print(f"✓ Free: {stats['free']}")
        print(f"✓ Booked: {stats['booked']}")
        
        if stats['total'] > 0:
            print("✓ Scraper is finding data")
        else:
            print("⚠ Scraper is not finding any data")
    else:
        print(f"✗ Failed to get stats: {response.status_code}")
        return False
    
    # Test 3: Check if we're getting weekend dates
    print("\n3. Checking for weekend dates...")
    weekend_dates = []
    for record in data:
        day_name = datetime.strptime(record['date'], '%Y-%m-%d').strftime('%A')
        if day_name in ['Friday', 'Saturday']:
            weekend_dates.append((record['date'], day_name, record['status']))
    
    print(f"✓ Found {len(weekend_dates)} weekend dates")
    if weekend_dates:
        print("   Weekend dates found:")
        for date_str, day_name, status in weekend_dates[:10]:  # Show first 10
            print(f"   - {date_str} ({day_name}): {status}")
    else:
        print("⚠ No weekend dates found - this might be expected if all are booked")
    
    # Test 4: Check date range
    print("\n4. Checking date range...")
    if data:
        dates = [datetime.strptime(record['date'], '%Y-%m-%d').date() for record in data]
        min_date = min(dates)
        max_date = max(dates)
        today = date.today()
        
        print(f"✓ Date range: {min_date} to {max_date}")
        print(f"✓ Today: {today}")
        
        if min_date >= today:
            print("✓ All dates are current or future")
        else:
            print("⚠ Some dates are in the past")
            
        if max_date > today:
            print("✓ Scraper is looking ahead")
        else:
            print("⚠ Scraper may not be looking far enough ahead")
    
    # Test 5: Check scheduler status
    print("\n5. Checking scheduler status...")
    response = requests.get(f"{BASE_URL}/scheduler/status")
    if response.status_code == 200:
        scheduler_status = response.json()
        print(f"✓ Scheduler status: {scheduler_status['status']}")
        if 'next_run' in scheduler_status:
            print(f"✓ Next run: {scheduler_status['next_run']}")
    else:
        print(f"✗ Failed to get scheduler status: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("Scraper Test Summary:")
    print(f"- Data found: {len(data) > 0}")
    print(f"- Weekend dates: {len(weekend_dates)}")
    print(f"- Scheduler running: {scheduler_status.get('status') == 'running' if 'scheduler_status' in locals() else 'Unknown'}")
    
    return True

if __name__ == "__main__":
    test_scraper_functionality()
