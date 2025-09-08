#!/usr/bin/env python3
"""
Unit Tests for ValidationFramework
JIRA: AINV-711

Comprehensive test coverage for the quality control and validation system,
including Bloomberg consistency, spread correlation, and peer group analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, date

from src.validation.quality_control import ValidationFramework


class TestValidationFramework:
    """Test suite for ValidationFramework class"""
    
    def test_initialization(self, validation_framework):
        """Test validation framework initialization"""
        assert isinstance(validation_framework, ValidationFramework)
        assert hasattr(validation_framework, 'agency_rating_scores')
        assert hasattr(validation_framework, 'spread_thresholds')
        assert len(validation_framework.agency_rating_scores) > 0
        assert len(validation_framework.spread_thresholds) > 0
    
    def test_validate_rating_complete_success(self, validation_framework):
        """Test complete rating validation with passing data"""
        rating_data = {
            'cusip': '123456789',
            'final_score': 88.5,
            'quantitative_score': 35.0,
            'sector_score': 20.5,
            'agency_score': 28.0,
            'alpha_score': 5.0,
            'linvest21_rating': 'LIN-AA-'
        }
        
        bloomberg_data = {
            'QualityB': 'AA',
            'OAS_bp': 95,
            'IssrClsL1': 'Corporate-Financial',
            'OutstandE': 1000000000,
            'ISMA_MDur': 5.2
        }
        
        result = validation_framework.validate_rating(rating_data, bloomberg_data)
        
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'bloomberg_consistency' in result
        assert 'spread_correlation' in result
        assert 'peer_group_analysis' in result
        assert 'validation_metrics' in result
        
        # Should pass validation with good data
        assert result['overall_status'] in ['PASSED', 'REVIEW_REQUIRED']
    
    def test_validate_bloomberg_consistency_validated(self, validation_framework):
        """Test Bloomberg consistency validation - validated case"""
        lin_score = 88.5
        bloomberg_quality = 'AA'
        
        result = validation_framework.validate_bloomberg_consistency(lin_score, bloomberg_quality)
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'score_difference' in result
        assert 'bloomberg_numeric_score' in result
        
        # Score difference should be small for AA rating
        assert result['score_difference'] <= 25
        assert result['status'] in ['VALIDATED', 'REVIEW_REQUIRED']
    
    def test_validate_bloomberg_consistency_override_needed(self, validation_framework):
        """Test Bloomberg consistency validation - manual override needed"""
        lin_score = 95.0  # Very high LINVEST21 score
        bloomberg_quality = 'BBB'  # Much lower Bloomberg rating
        
        result = validation_framework.validate_bloomberg_consistency(lin_score, bloomberg_quality)
        
        assert result['status'] == 'MANUAL_OVERRIDE_NEEDED'
        assert result['score_difference'] > 25
    
    def test_validate_bloomberg_consistency_null_rating(self, validation_framework):
        """Test Bloomberg consistency with null Bloomberg rating"""
        lin_score = 88.5
        bloomberg_quality = None
        
        result = validation_framework.validate_bloomberg_consistency(lin_score, bloomberg_quality)
        
        assert result['status'] == 'NO_BLOOMBERG_RATING'
        assert result['score_difference'] is None
    
    def test_validate_bloomberg_consistency_invalid_rating(self, validation_framework):
        """Test Bloomberg consistency with invalid Bloomberg rating"""
        lin_score = 88.5
        bloomberg_quality = 'INVALID_RATING'
        
        result = validation_framework.validate_bloomberg_consistency(lin_score, bloomberg_quality)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert 'status' in result
    
    def test_validate_spread_correlation_pass(self, validation_framework):
        """Test spread correlation validation - pass case"""
        linvest21_rating = 'LIN-AA'
        actual_spread = 85
        
        result = validation_framework.validate_spread_correlation(linvest21_rating, actual_spread)
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'expected_spread_range' in result
        assert 'actual_spread' in result
        assert 'deviation' in result
        
        # Should pass for reasonable spread
        assert result['status'] in ['PASS', 'FLAG_FOR_REVIEW']
    
    def test_validate_spread_correlation_flag_review(self, validation_framework):
        """Test spread correlation validation - flag for review"""
        linvest21_rating = 'LIN-AA'
        actual_spread = 200  # Very high spread for AA rating
        
        result = validation_framework.validate_spread_correlation(linvest21_rating, actual_spread)
        
        assert result['status'] == 'FLAG_FOR_REVIEW'
        assert result['deviation'] > 0
    
    def test_validate_spread_correlation_null_spread(self, validation_framework):
        """Test spread correlation with null spread"""
        linvest21_rating = 'LIN-AA'
        actual_spread = None
        
        result = validation_framework.validate_spread_correlation(linvest21_rating, actual_spread)
        
        assert result['status'] == 'NO_SPREAD_DATA'
        assert result['actual_spread'] is None
    
    def test_validate_spread_correlation_invalid_rating(self, validation_framework):
        """Test spread correlation with invalid rating"""
        linvest21_rating = 'INVALID-RATING'
        actual_spread = 100
        
        result = validation_framework.validate_spread_correlation(linvest21_rating, actual_spread)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert 'status' in result
    
    def test_validate_peer_group_analysis_within_range(self, validation_framework):
        """Test peer group analysis - within range case"""
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
        
        result = validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'z_score' in result
        assert 'peer_statistics' in result
        
        # Should be within range
        assert result['status'] == 'WITHIN_RANGE'
        assert abs(result['z_score']) <= 2.0
    
    def test_validate_peer_group_analysis_outlier(self, validation_framework):
        """Test peer group analysis - outlier case"""
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
        
        result = validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'OUTLIER'
        assert abs(result['z_score']) > 2.0
    
    def test_validate_peer_group_analysis_insufficient_data(self, validation_framework):
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
        
        result = validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'INSUFFICIENT_PEER_DATA'
    
    def test_validate_peer_group_analysis_empty_peers(self, validation_framework):
        """Test peer group analysis with empty peer data"""
        rating_data = {
            'final_score': 88.5,
            'quantitative_score': 35.0
        }
        
        peer_data = pd.DataFrame()
        
        result = validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        assert result['status'] == 'NO_PEER_DATA'
    
    def test_get_peer_group_sector_filter(self, validation_framework):
        """Test peer group retrieval with sector filtering"""
        all_ratings = pd.DataFrame({
            'cusip': ['123', '456', '789', '012', '345'],
            'sector': ['Financial', 'Financial', 'Industrial', 'Financial', 'Utility'],
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.5],
            'issuer_class_l1': ['Corporate'] * 5
        })
        
        target_security = {
            'sector': 'Financial',
            'issuer_class_l1': 'Corporate'
        }
        
        peers = validation_framework._get_peer_group(all_ratings, target_security)
        
        # Should only return Financial sector peers
        assert len(peers) == 3  # Excluding self, 3 Financial peers
        assert all(peers['sector'] == 'Financial')
    
    def test_get_peer_group_rating_range_filter(self, validation_framework):
        """Test peer group retrieval with rating range filtering"""
        all_ratings = pd.DataFrame({
            'cusip': ['123', '456', '789', '012', '345'],
            'final_score': [50.0, 85.0, 87.0, 89.0, 120.0],  # Wide range
            'sector': ['Financial'] * 5,
            'issuer_class_l1': ['Corporate'] * 5
        })
        
        target_security = {
            'final_score': 87.0,
            'sector': 'Financial',
            'issuer_class_l1': 'Corporate'
        }
        
        peers = validation_framework._get_peer_group(all_ratings, target_security)
        
        # Should filter out extreme scores
        assert all(peers['final_score'] >= 70.0)  # Above minimum
        assert all(peers['final_score'] <= 100.0)  # Below maximum
    
    def test_calculate_validation_score_all_pass(self, validation_framework):
        """Test validation score calculation when all checks pass"""
        validation_results = {
            'bloomberg_consistency': {'status': 'VALIDATED'},
            'spread_correlation': {'status': 'PASS'},
            'peer_group_analysis': {'status': 'WITHIN_RANGE'}
        }
        
        score = validation_framework._calculate_validation_score(validation_results)
        
        assert isinstance(score, float)
        assert score == 100.0  # Perfect score
    
    def test_calculate_validation_score_mixed_results(self, validation_framework):
        """Test validation score calculation with mixed results"""
        validation_results = {
            'bloomberg_consistency': {'status': 'REVIEW_REQUIRED'},
            'spread_correlation': {'status': 'PASS'},
            'peer_group_analysis': {'status': 'OUTLIER'}
        }
        
        score = validation_framework._calculate_validation_score(validation_results)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score < 100  # Should be penalized for issues
    
    def test_calculate_validation_score_all_fail(self, validation_framework):
        """Test validation score calculation when all checks fail"""
        validation_results = {
            'bloomberg_consistency': {'status': 'MANUAL_OVERRIDE_NEEDED'},
            'spread_correlation': {'status': 'FLAG_FOR_REVIEW'},
            'peer_group_analysis': {'status': 'OUTLIER'}
        }
        
        score = validation_framework._calculate_validation_score(validation_results)
        
        assert isinstance(score, float)
        assert score < 50  # Low score for multiple failures
    
    def test_validate_batch_ratings(self, validation_framework):
        """Test batch validation of multiple ratings"""
        ratings_data = [
            {
                'cusip': '123456789',
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.5,
                'agency_score': 28.0,
                'alpha_score': 5.0
            },
            {
                'cusip': '987654321',
                'final_score': 75.0,
                'linvest21_rating': 'LIN-A-',
                'quantitative_score': 30.0,
                'sector_score': 18.0,
                'agency_score': 22.0,
                'alpha_score': 5.0
            }
        ]
        
        bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789', '987654321'],
            'QualityB': ['AA', 'A'],
            'OAS_bp': [85, 120],
            'IssrClsL1': ['Corporate-Financial', 'Corporate-Industrial'],
            'OutstandE': [1000000000, 800000000],
            'ISMA_MDur': [5.2, 4.8]
        })
        
        results = validation_framework.validate_batch_ratings(ratings_data, bloomberg_data)
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        for result in results:
            assert 'cusip' in result
            assert 'overall_status' in result
            assert 'validation_score' in result
    
    def test_validate_batch_ratings_missing_bloomberg_data(self, validation_framework):
        """Test batch validation with missing Bloomberg data"""
        ratings_data = [
            {
                'cusip': '123456789',
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA'
            }
        ]
        
        # Empty Bloomberg data
        bloomberg_data = pd.DataFrame()
        
        results = validation_framework.validate_batch_ratings(ratings_data, bloomberg_data)
        
        assert len(results) == 1
        assert results[0]['overall_status'] == 'NO_BLOOMBERG_DATA'
    
    def test_agency_rating_scores_completeness(self, validation_framework):
        """Test that all expected agency ratings are mapped"""
        expected_ratings = [
            'AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-',
            'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-',
            'B+', 'B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D', 'NR'
        ]
        
        for rating in expected_ratings:
            assert rating in validation_framework.agency_rating_scores
            assert isinstance(validation_framework.agency_rating_scores[rating], (int, float))
    
    def test_spread_thresholds_completeness(self, validation_framework):
        """Test that spread thresholds are properly defined"""
        expected_ratings = ['LIN-AAA', 'LIN-AA', 'LIN-A', 'LIN-BBB', 'LIN-BB', 'LIN-B', 'LIN-CCC']
        
        for rating in expected_ratings:
            assert rating in validation_framework.spread_thresholds
            threshold = validation_framework.spread_thresholds[rating]
            assert 'min' in threshold
            assert 'max' in threshold
            assert threshold['min'] <= threshold['max']
    
    def test_edge_cases_null_inputs(self, validation_framework):
        """Test handling of null and missing inputs"""
        # Test with minimal data
        rating_data = {
            'cusip': '123456789',
            'final_score': None,
            'linvest21_rating': None
        }
        
        bloomberg_data = {}
        
        result = validation_framework.validate_rating(rating_data, bloomberg_data)
        
        # Should handle gracefully without crashing
        assert isinstance(result, dict)
        assert 'overall_status' in result
    
    def test_performance_large_batch(self, validation_framework, performance_test_data):
        """Test validation performance with large batch"""
        import time
        
        # Create ratings data from performance test data
        ratings_data = []
        for i, row in performance_test_data.head(100).iterrows():
            ratings_data.append({
                'cusip': row['Cusip'],
                'final_score': 85.0 + np.random.normal(0, 5),
                'linvest21_rating': 'LIN-A',
                'quantitative_score': 32.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.0
            })
        
        start_time = time.time()
        results = validation_framework.validate_batch_ratings(ratings_data, performance_test_data.head(100))
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process 100 validations quickly (< 5 seconds)
        assert processing_time < 5.0
        assert len(results) == 100
    
    @patch('src.validation.quality_control.logger')
    def test_logging_coverage(self, mock_logger, validation_framework):
        """Test that appropriate logging occurs"""
        rating_data = {
            'cusip': '123456789',
            'final_score': 88.5,
            'linvest21_rating': 'LIN-AA'
        }
        
        bloomberg_data = {
            'QualityB': 'AA',
            'OAS_bp': 85
        }
        
        validation_framework.validate_rating(rating_data, bloomberg_data)
        
        # Verify logging was called
        assert mock_logger.debug.called or mock_logger.info.called
    
    def test_validation_thresholds_configuration(self, validation_framework):
        """Test that validation thresholds are properly configured"""
        # Test Bloomberg consistency thresholds
        assert hasattr(validation_framework, '_bloomberg_deviation_thresholds')
        thresholds = validation_framework._bloomberg_deviation_thresholds
        assert 'validated_max' in thresholds
        assert 'review_required_max' in thresholds
        assert thresholds['validated_max'] < thresholds['review_required_max']
        
        # Test peer group Z-score thresholds
        assert hasattr(validation_framework, '_peer_zscore_thresholds')
        z_thresholds = validation_framework._peer_zscore_thresholds
        assert 'outlier_threshold' in z_thresholds
        assert z_thresholds['outlier_threshold'] > 0
    
    def test_mathematical_accuracy_validation_score(self, validation_framework):
        """Test mathematical accuracy of validation score calculations"""
        # Test perfect validation
        perfect_results = {
            'bloomberg_consistency': {'status': 'VALIDATED'},
            'spread_correlation': {'status': 'PASS'},
            'peer_group_analysis': {'status': 'WITHIN_RANGE'}
        }
        
        perfect_score = validation_framework._calculate_validation_score(perfect_results)
        assert perfect_score == 100.0
        
        # Test single failure
        single_fail_results = {
            'bloomberg_consistency': {'status': 'MANUAL_OVERRIDE_NEEDED'},  # Major penalty
            'spread_correlation': {'status': 'PASS'},
            'peer_group_analysis': {'status': 'WITHIN_RANGE'}
        }
        
        single_fail_score = validation_framework._calculate_validation_score(single_fail_results)
        assert single_fail_score < perfect_score
        assert single_fail_score >= 0
    
    def test_z_score_calculation_accuracy(self, validation_framework):
        """Test accuracy of Z-score calculations"""
        # Known data with expected Z-score
        rating_data = {'final_score': 90.0}
        peer_data = pd.DataFrame({
            'final_score': [85.0, 87.0, 89.0, 91.0, 86.0]  # mean = 87.6, std ≈ 2.41
        })
        
        result = validation_framework.validate_peer_group_analysis(rating_data, peer_data)
        
        # Calculate expected Z-score: (90 - 87.6) / 2.41 ≈ 1.0
        expected_z = (90.0 - peer_data['final_score'].mean()) / peer_data['final_score'].std()
        
        assert abs(result['z_score'] - expected_z) < 0.1  # Within tolerance
    
    def test_boundary_conditions_spread_validation(self, validation_framework):
        """Test boundary conditions for spread validation"""
        # Test exactly at threshold boundaries
        test_cases = [
            ('LIN-AAA', 25),    # Should be at boundary
            ('LIN-CCC', 800),   # Should be at boundary
            ('LIN-AA', 0),      # Edge case: zero spread
            ('LIN-BBB', 10000), # Edge case: very high spread
        ]
        
        for rating, spread in test_cases:
            result = validation_framework.validate_spread_correlation(rating, spread)
            
            # Should handle all cases without error
            assert isinstance(result, dict)
            assert 'status' in result
            assert result['status'] in ['PASS', 'FLAG_FOR_REVIEW']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])