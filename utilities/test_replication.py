#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
from src.validation.quality_control import ValidationFramework

class TestValidationFramework:
    
    def setup_method(self):
        """Setup validation framework for each test"""
        self.validation_framework = ValidationFramework()
    
    def test_validate_peer_group_analysis_within_range(self):
        """Test peer group analysis - within range case - EXACT COPY"""
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
        
        result = self.validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        print(f"Result: {result}")
        print(f"Result keys: {list(result.keys())}")
        
        # Test the assertions
        try:
            assert isinstance(result, dict)
            print("✅ isinstance(result, dict)")
        except AssertionError:
            print("❌ isinstance(result, dict)")
            
        try:
            assert 'status' in result
            print("✅ 'status' in result")
        except AssertionError:
            print("❌ 'status' in result")
            
        try:
            assert 'z_score' in result
            print("✅ 'z_score' in result")
        except AssertionError:
            print("❌ 'z_score' in result")
            
        try:
            assert 'peer_statistics' in result
            print("✅ 'peer_statistics' in result")
        except AssertionError as e:
            print(f"❌ 'peer_statistics' in result: {e}")
            print(f"Available keys: {list(result.keys())}")
            
        # Should be within range
        try:
            assert result['status'] == 'WITHIN_RANGE'
            print("✅ status == 'WITHIN_RANGE'")
        except AssertionError:
            print(f"❌ status == 'WITHIN_RANGE', got {result['status']}")
            
        try:
            assert abs(result['z_score']) <= 2.0
            print("✅ abs(z_score) <= 2.0")
        except AssertionError:
            print(f"❌ abs(z_score) <= 2.0, got {abs(result['z_score'])}")
    
    def test_validate_peer_group_analysis_insufficient_data(self):
        """Test peer group analysis with insufficient peer data"""
        rating_data = {
            'final_score': 88.5,
            'quantitative_score': 35.0
        }

        # Too few peers
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0],
            'quantitative_score': [33.0, 34.0]
        })

        result = self.validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        print(f"Insufficient data result: {result}")

        try:
            assert result['status'] == 'INSUFFICIENT_PEER_DATA'
            print("✅ status == 'INSUFFICIENT_PEER_DATA'")
        except AssertionError:
            print(f"❌ status == 'INSUFFICIENT_PEER_DATA', got {result['status']}")

    def test_validation_thresholds_configuration(self):
        """Test that validation thresholds are properly configured"""
        # Test Bloomberg consistency thresholds
        try:
            assert hasattr(self.validation_framework, '_bloomberg_deviation_thresholds')
            print("✅ has _bloomberg_deviation_thresholds")
        except AssertionError:
            print("❌ missing _bloomberg_deviation_thresholds")
            
        thresholds = self.validation_framework._bloomberg_deviation_thresholds
        try:
            assert 'validated_max' in thresholds
            print("✅ has validated_max")
        except AssertionError:
            print("❌ missing validated_max")
            
        try:
            assert 'review_required_max' in thresholds
            print("✅ has review_required_max")
        except AssertionError:
            print("❌ missing review_required_max")
            
        try:
            assert thresholds['validated_max'] < thresholds['review_required_max']
            print("✅ validated_max < review_required_max")
        except AssertionError:
            print("❌ validated_max >= review_required_max")

        # Test peer group Z-score thresholds
        try:
            assert hasattr(self.validation_framework, '_peer_zscore_thresholds')
            print("✅ has _peer_zscore_thresholds")
        except AssertionError:
            print("❌ missing _peer_zscore_thresholds")

if __name__ == "__main__":
    test_instance = TestValidationFramework()
    test_instance.setup_method()
    
    print("=" * 60)
    print("TEST 1: peer_group_analysis_within_range")
    print("=" * 60)
    test_instance.test_validate_peer_group_analysis_within_range()
    
    print("\n" + "=" * 60)
    print("TEST 2: peer_group_analysis_insufficient_data")
    print("=" * 60)
    test_instance.test_validate_peer_group_analysis_insufficient_data()
    
    print("\n" + "=" * 60)
    print("TEST 3: validation_thresholds_configuration")
    print("=" * 60)
    test_instance.test_validation_thresholds_configuration()