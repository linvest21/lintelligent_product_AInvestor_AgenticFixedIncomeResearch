#!/usr/bin/env python3
"""
Full validation framework test runner without pytest dependency
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
from datetime import datetime, timezone
from src.validation.quality_control import ValidationFramework
import traceback

def mock_test_runner():
    """Run all validation framework tests without pytest"""
    vf = ValidationFramework()
    
    tests_passed = 0
    tests_total = 0
    failed_tests = []
    
    def run_test(test_name, test_func):
        nonlocal tests_passed, tests_total, failed_tests
        tests_total += 1
        try:
            print(f"\nRunning {test_name}...")
            test_func()
            print(f"✅ {test_name} PASSED")
            tests_passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {str(e)}")
            failed_tests.append((test_name, str(e)))
    
    # Test basic initialization
    def test_initialization():
        assert hasattr(vf, 'spread_thresholds')
        assert hasattr(vf, '_peer_zscore_thresholds')
        assert len(vf.spread_thresholds) > 0
    
    # Test basic rating validation
    def test_basic_rating_validation():
        rating_result = {
            'final_score': 85.0,
            'linvest21_rating': 'LIN-AA-',
            'quantitative_score': 30.0,
            'sector_score': 21.25,
            'agency_score': 29.4,
            'alpha_score': 4.35
        }
        
        bond_data = {
            'QualityB': 'AA-',
            'IssrClsL1': 'Corporate-Financial',
            'OAS_bp': 120,
            'Cusip': 'TEST123'
        }
        
        result = vf.validate_rating(rating_result, bond_data)
        assert isinstance(result, dict)
        assert 'validation_status' in result
    
    # Test Bloomberg consistency validation
    def test_bloomberg_consistency():
        rating_result = {'linvest21_rating': 'LIN-AA', 'final_score': 87.0}
        bond_data = {'QualityB': 'AA'}
        
        result = vf.validate_bloomberg_consistency(rating_result, bond_data)
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'deviation' in result
    
    # Test spread validation with numeric score
    def test_spread_validation_numeric():
        rating_result = {'final_score': 85.0, 'linvest21_rating': 'LIN-AA-'}
        bond_data = {'OAS_bp': 120}
        
        result = vf.validate_spread_correlation(rating_result, bond_data)
        assert isinstance(result, dict)
        assert 'status' in result
    
    # Test spread validation with string rating
    def test_spread_validation_string():
        rating_result = {'linvest21_rating': 'LIN-BBB+', 'final_score': 72.5}
        bond_data = {'OAS_bp': 200}
        
        result = vf.validate_spread_correlation(rating_result, bond_data)
        assert isinstance(result, dict)
        assert 'status' in result
    
    # Test peer group analysis
    def test_peer_group_analysis():
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
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'z_score' in result
        assert 'peer_statistics' in result
        assert 'validation_score' in result
    
    # Test batch validation
    def test_batch_validation():
        ratings_data = pd.DataFrame({
            'cusip': ['A123', 'B456'],
            'final_score': [85.0, 78.0],
            'linvest21_rating': ['LIN-AA-', 'LIN-A'],
            'quantitative_score': [30.0, 28.0],
            'sector_score': [21.0, 19.0],
            'agency_score': [29.0, 26.0],
            'alpha_score': [5.0, 5.0]
        })
        
        bond_data = pd.DataFrame({
            'Cusip': ['A123', 'B456'],
            'QualityB': ['AA-', 'A'],
            'IssrClsL1': ['Corporate-Financial', 'Corporate-Industrial'],
            'OAS_bp': [120, 180]
        })
        
        results = vf.validate_batch_ratings(ratings_data, bond_data)
        assert isinstance(results, pd.DataFrame)
        assert len(results) == 2
        assert 'validation_status' in results.columns
    
    # Test Z-score calculation accuracy
    def test_z_score_accuracy():
        rating_data = {'final_score': 90.0}
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.0]  # mean = 87.6, std ≈ 2.41
        })
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        # Calculate expected Z-score: (90 - 87.6) / 2.41 ≈ 1.0
        expected_z = (90.0 - peer_data['final_score'].mean()) / peer_data['final_score'].std()
        
        assert abs(result['z_score'] - expected_z) < 0.1  # Within tolerance
    
    # Test outlier detection
    def test_outlier_detection():
        rating_data = {
            'final_score': 120.0,  # Much higher than peers
            'quantitative_score': 40.0,
            'sector_score': 25.0
        }
        
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.5],
            'quantitative_score': [33.0, 34.0, 36.0, 37.0, 35.5],
            'sector_score': [19.0, 20.0, 21.0, 22.0, 20.5]
        })
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'OUTLIER'
        assert abs(result['z_score']) > 2.0
    
    # Test insufficient peer data
    def test_insufficient_peer_data():
        rating_data = {
            'final_score': 88.5,
            'quantitative_score': 35.0
        }
        
        # Too few peers
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0],
            'quantitative_score': [33.0, 34.0]
        })
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'INSUFFICIENT_PEER_DATA'
    
    # Test empty peer data
    def test_empty_peer_data():
        rating_data = {
            'final_score': 88.5,
            'quantitative_score': 35.0
        }
        
        peer_data = pd.DataFrame()
        
        result = vf.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'NO_PEER_DATA'
    
    # Test NO_BLOOMBERG_DATA status
    def test_no_bloomberg_data():
        rating_result = {'linvest21_rating': 'LIN-BBB', 'final_score': 68.0}
        bond_data = {}  # No Bloomberg rating data
        
        result = vf.validate_bloomberg_consistency(rating_result, bond_data)
        assert result['status'] == 'NO_BLOOMBERG_DATA'
    
    # Run all tests
    run_test("Initialization", test_initialization)
    run_test("Basic Rating Validation", test_basic_rating_validation)
    run_test("Bloomberg Consistency", test_bloomberg_consistency)
    run_test("Spread Validation Numeric", test_spread_validation_numeric)
    run_test("Spread Validation String", test_spread_validation_string)
    run_test("Peer Group Analysis", test_peer_group_analysis)
    run_test("Batch Validation", test_batch_validation)
    run_test("Z-score Accuracy", test_z_score_accuracy)
    run_test("Outlier Detection", test_outlier_detection)
    run_test("Insufficient Peer Data", test_insufficient_peer_data)
    run_test("Empty Peer Data", test_empty_peer_data)
    run_test("No Bloomberg Data", test_no_bloomberg_data)
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION FRAMEWORK TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {tests_total}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(tests_passed/tests_total*100):.1f}%")
    
    if failed_tests:
        print(f"\nFailed Tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
    else:
        print("\n🎉 ALL TESTS PASSED!")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    mock_test_runner()