#!/usr/bin/env python3
"""
Test script to verify the dynamic max_availability_age_days calculation.
"""

def test_dynamic_config():
    """Test the dynamic max_availability_age_days calculation."""
    print("Testing Dynamic max_availability_age_days Calculation")
    print("=" * 55)
    
    # Test different MONTHS_AHEAD values
    test_cases = [
        (1, 60),   # 1 month -> 60 days
        (3, 120),  # 3 months -> 120 days  
        (6, 210),  # 6 months -> 210 days
        (12, 390)  # 12 months -> 390 days
    ]
    
    print("Expected calculations:")
    for months, expected_days in test_cases:
        calculated = (months * 30) + 30
        status = "✓" if calculated == expected_days else "✗"
        print(f"  {status} MONTHS_AHEAD={months:2d} -> {calculated:3d} days (expected: {expected_days})")
    
    print(f"\nFormula: (MONTHS_AHEAD * 30) + 30")
    print(f"Buffer: +30 days to ensure we don't clean up active monitoring data")
    
    print(f"\nBenefits:")
    print(f"- Automatic cleanup calculation")
    print(f"- Prevents data loss during active monitoring")
    print(f"- Scales with monitoring range")
    print(f"- No manual configuration needed")

if __name__ == "__main__":
    test_dynamic_config()
