#!/usr/bin/env python3
"""
Simple test script to validate the application improvements.
Run this after starting the application to verify everything works.
"""

import requests

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, expected_status=200):
    """Test an endpoint and return the response."""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"✓ {endpoint}: {response.status_code}")
        if response.status_code == expected_status:
            return response.json()
        else:
            print(f"  Error: Expected {expected_status}, got {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"✗ {endpoint}: Connection failed - {e}")
        return None

def main():
    """Run basic tests on the application."""
    print("Testing Opfinger Availability Monitor API")
    print("=" * 50)
    
    # Test basic endpoints
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/stats", "Statistics"),
        ("/scheduler/status", "Scheduler status"),
        ("/availability", "Availability data"),
        ("/notifications", "Notifications"),
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        print(f"\nTesting {description}...")
        result = test_endpoint(endpoint)
        if result:
            results[endpoint] = result
    
    # Test with parameters
    print(f"\nTesting availability with status filter...")
    test_endpoint("/availability?status=free")
    
    print(f"\nTesting notifications with limit...")
    test_endpoint("/notifications?limit=5")
    
    # Display some results
    print(f"\n" + "=" * 50)
    print("Test Results Summary:")
    
    if "/health" in results:
        health = results["/health"]
        print(f"Application Status: {health.get('status', 'unknown')}")
        print(f"Database: {health.get('database', 'unknown')}")
        print(f"Scheduler: {health.get('scheduler', {}).get('status', 'unknown')}")
    
    if "/stats" in results:
        stats = results["/stats"]
        availability = stats.get('availability', {})
        print(f"Total Records: {availability.get('total', 0)}")
        print(f"Free: {availability.get('free', 0)}")
        print(f"Booked: {availability.get('booked', 0)}")
    
    print(f"\nAPI Documentation available at: {BASE_URL}/docs")
    print("Test completed!")

if __name__ == "__main__":
    main()
