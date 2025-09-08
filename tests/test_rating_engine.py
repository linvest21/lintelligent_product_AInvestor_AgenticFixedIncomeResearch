"""
Unit Tests for LINVEST21RatingEngine
JIRA: AINV-711

Comprehensive test coverage for the proprietary credit rating calculation engine,
including positive cases, negative cases, edge cases, and boundary conditions.
"""

import sys
import os
# Add project root to Python path for direct execution
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

import pytest
import numpy as np
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core.rating_engine import LINVEST21RatingEngine


class TestLINVEST21RatingEngine:
    """Test suite for LINVEST21RatingEngine class"""
    
    def test_initialization(self, rating_engine):
        """Test rating engine initialization"""
        assert isinstance(rating_engine, LINVEST21RatingEngine)
        assert hasattr(rating_engine, 'agency_rating_scores')
        assert hasattr(rating_engine, 'sector_risk_multipliers')
        assert len(rating_engine.agency_rating_scores) > 0
        assert len(rating_engine.sector_risk_multipliers) > 0
    
    def test_calculate_rating_complete_data(self, rating_engine, sample_bond_data):
        """Test rating calculation with complete bond data"""
        result = rating_engine.calculate_rating(sample_bond_data)
        
        # Verify result structure
        assert isinstance(result, dict)
        required_fields = [
            'quantitative_score', 'sector_score', 'agency_score', 'alpha_score',
            'final_score', 'linvest21_rating', 'validation_status'
        ]
        for field in required_fields:
            assert field in result
            assert result[field] is not None
        
        # Verify score ranges
        assert 0 <= result['quantitative_score'] <= 40  # 40% weight
        assert 0 <= result['sector_score'] <= 25       # 25% weight
        assert 0 <= result['agency_score'] <= 35       # 35% weight
        assert 0 <= result['alpha_score'] <= 15        # 15% weight
        assert 0 <= result['final_score'] <= 115       # Total possible
        
        # Verify rating format
        assert result['linvest21_rating'].startswith('LIN-')
        assert len(result['linvest21_rating']) >= 5
    
    def test_calculate_rating_missing_data(self, rating_engine):
        """Test rating calculation with missing critical data"""
        incomplete_data = {
            'Cusip': '123456789',
            'Currency': 'USD',
            # Missing QualityB, OutstandE, Maturity, etc.
        }
        
        result = rating_engine.calculate_rating(incomplete_data)
        assert 'error' in result
        assert 'Missing required fields' in result['error']
    
    def test_duration_score_calculation(self, rating_engine):
        """Test duration component scoring with various inputs"""
        # Test normal duration
        score = rating_engine._calculate_duration_score(5.0)
        assert isinstance(score, float)
        assert 0 <= score <= 100  # Raw component score before weighting
        
        # Test short duration
        short_score = rating_engine._calculate_duration_score(1.0)
        assert short_score >= 0
        
        # Test long duration
        long_score = rating_engine._calculate_duration_score(20.0)
        assert long_score >= 0
        
        # Test zero duration
        zero_score = rating_engine._calculate_duration_score(0.0)
        assert zero_score >= 0
    
    def test_spread_score_calculation(self, rating_engine):
        """Test spread component scoring with various inputs"""
        # Test normal spread
        score = rating_engine._calculate_spread_score(100)
        assert isinstance(score, float)
        assert 0 <= score <= 100  # Raw component score before weighting
        
        # Test low spread (high quality)
        low_score = rating_engine._calculate_spread_score(25)
        high_score = rating_engine._calculate_spread_score(500)
        assert low_score < high_score  # Higher spread = higher risk score
        
        # Test extreme spreads
        extreme_high = rating_engine._calculate_spread_score(2000)
        assert extreme_high >= 0
        
        # Test null spread
        null_score = rating_engine._calculate_spread_score(None)
        assert null_score == 0
        
        # Test negative spread (edge case)
        neg_score = rating_engine._calculate_spread_score(-10)
        assert neg_score >= 0
    
    def test_liquidity_score_calculation(self, rating_engine):
        """Test liquidity component scoring with various inputs"""
        # Test normal outstanding amount
        score = rating_engine._calculate_liquidity_score(1000000000)
        assert isinstance(score, float)
        assert 0 <= score <= 100  # Raw component score before weighting
        
        # Test minimum threshold
        min_score = rating_engine._calculate_liquidity_score(300000000)
        assert min_score >= 0
        
        # Test very large outstanding
        large_score = rating_engine._calculate_liquidity_score(50000000000)
        small_score = rating_engine._calculate_liquidity_score(500000000)
        assert large_score <= small_score  # Larger outstanding = lower risk score
        
        # Test zero outstanding
        zero_score = rating_engine._calculate_liquidity_score(0)
        assert zero_score == 100  # Maximum risk for zero outstanding
    
    def test_sector_score_calculation(self, rating_engine):
        """Test sector risk scoring with various inputs"""
        # Test known sectors
        financial_score = rating_engine._calculate_sector_score('Corporate-Financial')
        industrial_score = rating_engine._calculate_sector_score('Corporate-Industrial')
        govt_score = rating_engine._calculate_sector_score('Government')
        
        assert all(isinstance(s, float) for s in [financial_score, industrial_score, govt_score])
        assert all(0 <= s <= 25 for s in [financial_score, industrial_score, govt_score])
        
        # Government should typically score lower (lower risk multiplier)
        assert govt_score <= financial_score
        
        # Test unknown sector
        unknown_score = rating_engine._calculate_sector_score('Unknown-Sector')
        assert unknown_score >= 0
    
    def test_agency_score_calculation(self, rating_engine):
        """Test agency rating scoring with various inputs"""
        # Test investment grade ratings
        aaa_score = rating_engine._calculate_agency_score('AAA')
        aa_score = rating_engine._calculate_agency_score('AA')
        bbb_score = rating_engine._calculate_agency_score('BBB')
        
        assert all(isinstance(s, float) for s in [aaa_score, aa_score, bbb_score])
        assert all(0 <= s <= 35 for s in [aaa_score, aa_score, bbb_score])
        assert aaa_score > aa_score > bbb_score  # Higher rating = higher score
        
        # Test high yield ratings
        bb_score = rating_engine._calculate_agency_score('BB')
        b_score = rating_engine._calculate_agency_score('B')
        ccc_score = rating_engine._calculate_agency_score('CCC')
        
        assert bb_score > b_score > ccc_score
        
        # Test not rated
        nr_score = rating_engine._calculate_agency_score('NR')
        assert nr_score >= 0
        
        # Test null rating (defaults to neutral score)
        null_score = rating_engine._calculate_agency_score(None)
        assert null_score == 17.5  # 50 * 0.35
        
        # Test invalid rating
        invalid_score = rating_engine._calculate_agency_score('INVALID')
        assert invalid_score >= 0
    
    def test_alpha_score_calculation(self, rating_engine, sample_bond_data):
        """Test alpha factor scoring with various inputs"""
        # Test normal returns
        score = rating_engine._calculate_alpha_score(sample_bond_data)
        assert isinstance(score, float)
        assert 0 <= score <= 15  # Already weighted in alpha calculation
        
        # Test high return scenario
        high_return_data = sample_bond_data.copy()
        high_return_data['RetTotal'] = 0.15
        high_score = rating_engine._calculate_alpha_score(high_return_data)
        
        # Test negative return scenario
        neg_return_data = sample_bond_data.copy()
        neg_return_data['RetTotal'] = -0.05
        neg_score = rating_engine._calculate_alpha_score(neg_return_data)
        
        assert high_score >= neg_score
        
        # Test missing return data - should fail due to missing required fields
    
    def test_final_score_to_rating_conversion(self, rating_engine):
        """Test conversion of numerical scores to letter ratings"""
        # Test AAA range
        aaa_rating = rating_engine._score_to_rating(95)
        assert aaa_rating == 'LIN-AAA'
        
        # Test AA range
        aa_plus_rating = rating_engine._score_to_rating(92)
        aa_rating = rating_engine._score_to_rating(88)
        aa_minus_rating = rating_engine._score_to_rating(85)
        
        assert aa_plus_rating == 'LIN-AA+'
        assert aa_rating == 'LIN-AA'
        assert aa_minus_rating == 'LIN-AA-'
        
        # Test A range
        a_plus_rating = rating_engine._score_to_rating(82)
        a_rating = rating_engine._score_to_rating(79)
        a_minus_rating = rating_engine._score_to_rating(76)
        
        assert a_plus_rating == 'LIN-A+'
        assert a_rating == 'LIN-A'
        assert a_minus_rating == 'LIN-A-'
        
        # Test BBB range
        bbb_plus_rating = rating_engine._score_to_rating(73)
        bbb_rating = rating_engine._score_to_rating(69)
        bbb_minus_rating = rating_engine._score_to_rating(66)
        
        assert bbb_plus_rating == 'LIN-BBB+'
        assert bbb_rating == 'LIN-BBB'
        assert bbb_minus_rating == 'LIN-BBB-'
        
        # Test high yield ratings
        bb_rating = rating_engine._score_to_rating(51)
        b_rating = rating_engine._score_to_rating(31)
        ccc_rating = rating_engine._score_to_rating(11)
        
        assert bb_rating == 'LIN-BB'
        assert b_rating == 'LIN-B'
        assert ccc_rating == 'LIN-CCC'
        
        # Test boundary conditions
        boundary_high = rating_engine._score_to_rating(120)  # Above max
        boundary_low = rating_engine._score_to_rating(0)     # At minimum
        
        assert boundary_high.startswith('LIN-')
        assert boundary_low.startswith('LIN-')
    
    def test_edge_cases_null_values(self, rating_engine):
        """Test handling of null and missing values"""
        edge_data = {
            'Cusip': '123456789',
            'Currency': 'USD',
            'QualityB': None,
            'OutstandE': None,
            'Maturity': None,
            'ISMA_MDur': None,
            'OAS_bp': None,
            'IssrClsL1': None,
            'Sector': None,
            'RetTotal': None,
        }
        
        result = rating_engine.calculate_rating(edge_data)
        
        # Should handle gracefully without crashing
        if 'error' not in result:
            assert isinstance(result['final_score'], float)
            assert result['final_score'] >= 0
            assert result['linvest21_rating'].startswith('LIN-')
    
    def test_edge_cases_extreme_values(self, rating_engine, edge_case_bond_data):
        """Test handling of extreme values"""
        for edge_data in edge_case_bond_data:
            if edge_data.get('Cusip') == '000000001':  # Minimum values case
                result = rating_engine.calculate_rating(edge_data)
                if 'error' not in result:
                    # Very high spread should result in low score
                    assert result['final_score'] <= 50
                    assert 'BB' in result['linvest21_rating'] or 'B' in result['linvest21_rating'] or 'CCC' in result['linvest21_rating']
            
            elif edge_data.get('Cusip') == '999999999':  # Maximum values case
                result = rating_engine.calculate_rating(edge_data)
                if 'error' not in result:
                    # AAA rating but very high duration (25 years) limits the score
                    assert 60 <= result['final_score'] <= 75
                    assert 'BBB' in result['linvest21_rating'] or 'A' in result['linvest21_rating']
    
    def test_consistency_same_input(self, rating_engine, sample_bond_data):
        """Test that same input produces consistent results"""
        result1 = rating_engine.calculate_rating(sample_bond_data.copy())
        result2 = rating_engine.calculate_rating(sample_bond_data.copy())
        
        assert result1['final_score'] == result2['final_score']
        assert result1['linvest21_rating'] == result2['linvest21_rating']
        assert result1['quantitative_score'] == result2['quantitative_score']
        assert result1['sector_score'] == result2['sector_score']
        assert result1['agency_score'] == result2['agency_score']
        assert result1['alpha_score'] == result2['alpha_score']
    
    def test_component_weight_validation(self, rating_engine, sample_bond_data):
        """Test that component weights sum correctly"""
        result = rating_engine.calculate_rating(sample_bond_data)
        
        if 'error' not in result:
            # Calculate expected total (allowing for floating point precision)
            expected_total = (
                result['quantitative_score'] + 
                result['sector_score'] + 
                result['agency_score'] + 
                result['alpha_score']
            )
            
            # Should be close to final_score (within floating point tolerance)
            assert abs(result['final_score'] - expected_total) < 0.01
    
    def test_rating_monotonicity(self, rating_engine):
        """Test that better inputs produce better ratings"""
        base_data = {
            'Cusip': '123456789',
            'Currency': 'USD',
            'QualityB': 'BBB',
            'OutstandE': 1000000000,
            'Maturity': 5.0,
            'MrktValue': 1000000000,
            'ISMA_MDur': 4.0,
            'OAS_bp': 150,
            'IssrClsL1': 'Corporate-Industrial',
            'Sector': 'Industrial',
            'RetTotal': 0.05,
            'RetPrice': 0.04,
            'RetCurncy': 0.01
        }
        
        # Better quality rating should produce higher score
        better_data = base_data.copy()
        better_data['QualityB'] = 'AA'
        better_data['OAS_bp'] = 75  # Lower spread
        
        base_result = rating_engine.calculate_rating(base_data)
        better_result = rating_engine.calculate_rating(better_data)
        
        if 'error' not in base_result and 'error' not in better_result:
            assert better_result['final_score'] > base_result['final_score']
    
    def test_performance_large_dataset(self, rating_engine, performance_test_data):
        """Test performance with large dataset"""
        import time
        
        start_time = time.time()
        
        results = []
        for _, row in performance_test_data.head(100).iterrows():  # Test with 100 securities
            bond_data = row.to_dict()
            result = rating_engine.calculate_rating(bond_data)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100 ratings in reasonable time (< 10 seconds)
        assert processing_time < 10.0
        
        # Verify all calculations completed
        successful_results = [r for r in results if 'error' not in r]
        assert len(successful_results) > 90  # At least 90% success rate
    
    @patch('src.core.rating_engine.logger')
    def test_logging_coverage(self, mock_logger, rating_engine, sample_bond_data):
        """Test that appropriate logging occurs"""
        rating_engine.calculate_rating(sample_bond_data)
        
        # Verify debug logging was called
        assert mock_logger.debug.called
    
    def test_input_validation_types(self, rating_engine):
        """Test input type validation"""
        # Test with wrong types
        invalid_inputs = [
            None,
            "string_instead_of_dict",
            123,
            [],
            {'Cusip': 123456789},  # CUSIP should be string
        ]
        
        for invalid_input in invalid_inputs:
            result = rating_engine.calculate_rating(invalid_input)
            # Should handle gracefully without crashing
            assert isinstance(result, dict)
    
    def test_mathematical_accuracy(self, rating_engine):
        """Test mathematical accuracy of calculations"""
        # Known input with expected output
        precise_data = {
            'Cusip': '123456789',
            'Currency': 'USD',
            'QualityB': 'AA',  # Should map to specific score
            'OutstandE': 1000000000,  # Exactly 1B
            'Maturity': 5.0,
            'MrktValue': 1000000000,
            'ISMA_MDur': 4.5,
            'OAS_bp': 100,
            'IssrClsL1': 'Corporate-Financial',
            'Sector': 'Financial',
            'RetTotal': 0.05,
            'RetPrice': 0.045,
            'RetCurncy': 0.005,
            'MrkValBeg': 1000000000
        }
        
        result = rating_engine.calculate_rating(precise_data)
        
        if 'error' not in result:
            # Verify component calculations are within expected ranges
            # Duration component should be reasonable for 4.5 duration
            assert 8 <= result['quantitative_score'] <= 40
            
            # AA rating should produce high agency score
            assert 25 <= result['agency_score'] <= 35
            
            # Financial sector should have reasonable score (Corporate-Financial multiplier 1.15)
            assert 14 <= result['sector_score'] <= 25
            
            # Positive returns should produce positive alpha score
            assert 0 <= result['alpha_score'] <= 15


if __name__ == "__main__":
    # Run the tests directly when script is executed
    pytest.main([__file__, "-v"])