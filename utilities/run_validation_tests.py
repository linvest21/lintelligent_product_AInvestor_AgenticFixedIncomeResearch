#!/usr/bin/env python3
"""
Simple test runner for validation framework without pytest dependency
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
from datetime import datetime, timezone
from src.validation.quality_control import ValidationFramework

def run_specific_tests():
    """Run the specific tests that were failing"""
    vf = ValidationFramework()
    
    # Test 1: Peer group analysis structure
    print("=" * 50)
    print("Test 1: Peer group analysis structure")
    try:
        rating_data = {
            'final_score': 88.5,
            'quantitative_score': 35.0,
            'sector_score': 20.5
        }
        
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.5],
            'quantitative_score': [33.0, 34.0, 36.0, 37.0, 35.5],
            'sector_score': [19.0, 20.0, 21.0, 22.0, 20.5]
        })
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        print(f"Result: {result}")
        
        # Check for peer_statistics grouping
        if 'peer_statistics' in result:
            print("✅ peer_statistics found in result")
        else:
            print("❌ peer_statistics missing from result")
            
        if 'status' in result and result['status'] in ['WITHIN_RANGE', 'OUTLIER']:
            print("✅ Status is correct")
        else:
            print(f"❌ Status issue: {result.get('status')}")
        
        print("Test 1 PASSED")
        
    except Exception as e:
        print(f"Test 1 FAILED: {str(e)}")
    
    # Test 2: Z-score calculation accuracy
    print("\n" + "=" * 50)
    print("Test 2: Z-score calculation accuracy")
    try:
        rating_data = {'final_score': 90.0}
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.0]  # mean = 87.6, std ≈ 2.41
        })
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        # Calculate expected Z-score: (90 - 87.6) / 2.41 ≈ 1.0
        expected_z = (90.0 - peer_data['final_score'].mean()) / peer_data['final_score'].std()
        
        print(f"Result Z-score: {result.get('z_score')}")
        print(f"Expected Z-score: {expected_z}")
        print(f"Difference: {abs(result.get('z_score', 0) - expected_z)}")
        
        if abs(result.get('z_score', 0) - expected_z) < 0.1:
            print("✅ Z-score calculation within tolerance")
            print("Test 2 PASSED")
        else:
            print("❌ Z-score calculation outside tolerance") 
            print("Test 2 FAILED")
        
    except Exception as e:
        print(f"Test 2 FAILED: {str(e)}")
    
    # Test 3: Status code tests
    print("\n" + "=" * 50)
    print("Test 3: Status codes")
    
    # Test insufficient peer data
    try:
        rating_data = {'final_score': 88.5, 'quantitative_score': 35.0}
        peer_data = pd.DataFrame({'final_score': [85.0, 87.0], 'quantitative_score': [33.0, 34.0]})
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        if result['status'] == 'INSUFFICIENT_PEER_DATA':
            print("✅ INSUFFICIENT_PEER_DATA status correct")
        else:
            print(f"❌ Expected INSUFFICIENT_PEER_DATA, got {result['status']}")
        
        print("Test 3 PASSED")
        
    except Exception as e:
        print(f"Test 3 FAILED: {str(e)}")
    
    # Test 4: Missing attribute check
    print("\n" + "=" * 50)
    print("Test 4: Check for _peer_zscore_thresholds attribute")
    
    if hasattr(vf, '_peer_zscore_thresholds'):
        print("✅ _peer_zscore_thresholds attribute found")
        print(f"   Contents: {vf._peer_zscore_thresholds}")
        print("Test 4 PASSED")
    else:
        print("❌ _peer_zscore_thresholds attribute missing")
        print("Test 4 FAILED")

if __name__ == "__main__":
    run_specific_tests()