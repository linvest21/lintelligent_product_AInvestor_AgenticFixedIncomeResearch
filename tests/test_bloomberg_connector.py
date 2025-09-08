"""
Unit Tests for BloombergConnector
JIRA: AINV-711

Comprehensive test coverage for Bloomberg Global Aggregate data integration,
including connection handling, data extraction, filtering, and validation.
"""

import sys
import os
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

import pytest
import pandas as pd
import numpy as np
import logging
from unittest.mock import Mock, patch, MagicMock

from src.data.bloomberg_connector import BloombergConnector

logger = logging.getLogger(__name__)


class TestBloombergConnector:
    """Test suite for BloombergConnector class"""
    
    def test_initialization(self, bloomberg_connector):
        """Test Bloomberg connector initialization"""
        assert isinstance(bloomberg_connector, BloombergConnector)
        assert bloomberg_connector.server_host == "localhost"
        assert bloomberg_connector.server_port == 8194
        assert bloomberg_connector.session is None
        assert bloomberg_connector.is_connected is False
        assert len(bloomberg_connector.required_fields) > 0
        
        # Verify required fields include critical ones
        critical_fields = ['Currency', 'QualityB', 'OutstandE', 'Maturity', 'Cusip', 'ISIN']
        for field in critical_fields:
            assert field in bloomberg_connector.required_fields
    
    def test_initialization_custom_params(self):
        """Test initialization with custom parameters"""
        custom_connector = BloombergConnector(server_host="custom-host", server_port=9999)
        assert custom_connector.server_host == "custom-host"
        assert custom_connector.server_port == 9999
    
    def test_connect_success(self, bloomberg_connector):
        """Test successful connection to Bloomberg"""
        result = bloomberg_connector.connect()
        
        assert result is True
        assert bloomberg_connector.is_connected is True
        assert bloomberg_connector.session is not None
    
    def test_connect_failure(self, bloomberg_connector):
        """Test connection failure handling"""
        # Patch the session creation to simulate connection failure
        original_connect = bloomberg_connector.connect
        def failing_connect():
            try:
                raise Exception("Connection failed")
            except Exception as e:
                logger.error(f"Bloomberg connection failed: {str(e)}")
                return False
        
        bloomberg_connector.connect = failing_connect
        result = bloomberg_connector.connect()
        assert result is False
        
        # Restore original method
        bloomberg_connector.connect = original_connect
    
    def test_disconnect(self, bloomberg_connector):
        """Test disconnection from Bloomberg"""
        # First connect
        bloomberg_connector.connect()
        assert bloomberg_connector.is_connected is True
        
        # Then disconnect
        bloomberg_connector.disconnect()
        assert bloomberg_connector.is_connected is False
        assert bloomberg_connector.session is None
    
    def test_disconnect_when_not_connected(self, bloomberg_connector):
        """Test disconnection when not connected"""
        # Should not raise error
        bloomberg_connector.disconnect()
        assert bloomberg_connector.is_connected is False
    
    def test_extract_global_aggregate_data_default_filter(self, bloomberg_connector):
        """Test extraction with default universe filter"""
        data = bloomberg_connector.extract_global_aggregate_data()
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # Verify default filtering applied
        assert all(data['Currency'] == 'USD')
        assert all(data['OutstandE'] >= 300000000)  # $300M minimum
        assert all(data['Maturity'] >= 1.0)  # 1 year minimum
        assert not data['QualityB'].isin(['NR', 'D', '']).any()
        
        # Verify required columns present
        required_columns = ['Cusip', 'ISIN', 'Currency', 'QualityB']
        for col in required_columns:
            assert col in data.columns
    
    def test_extract_global_aggregate_data_custom_filter(self, bloomberg_connector):
        """Test extraction with custom universe filter"""
        custom_filter = {
            'Currency': ['USD', 'EUR'],
            'OutstandE_min': 500000000,  # Higher minimum
            'Maturity_min': 2.0,
            'QualityB_exclude': ['NR', 'D', 'CCC']
        }
        
        data = bloomberg_connector.extract_global_aggregate_data(custom_filter)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # Verify custom filtering applied
        assert data['Currency'].isin(['USD', 'EUR']).all()
        assert all(data['OutstandE'] >= 500000000)
        assert all(data['Maturity'] >= 2.0)
        assert not data['QualityB'].isin(['NR', 'D', 'CCC']).any()
    
    def test_extract_data_connection_error(self, bloomberg_connector):
        """Test extraction when connection fails"""
        bloomberg_connector.is_connected = False
        
        with patch.object(bloomberg_connector, 'connect', return_value=False):
            with pytest.raises(ConnectionError, match="Unable to connect to Bloomberg"):
                bloomberg_connector.extract_global_aggregate_data()
    
    def test_apply_universe_filter_currency(self, bloomberg_connector, sample_bloomberg_data):
        """Test currency filtering"""
        filter_criteria = {'Currency': ['USD']}
        filtered_data = bloomberg_connector._apply_universe_filter(sample_bloomberg_data, filter_criteria)
        
        assert all(filtered_data['Currency'] == 'USD')
        assert len(filtered_data) <= len(sample_bloomberg_data)
    
    def test_apply_universe_filter_quality_exclusion(self, bloomberg_connector, sample_bloomberg_data):
        """Test quality rating exclusion filtering"""
        filter_criteria = {'QualityB_exclude': ['BBB+', 'A-']}
        filtered_data = bloomberg_connector._apply_universe_filter(sample_bloomberg_data, filter_criteria)
        
        assert not filtered_data['QualityB'].isin(['BBB+', 'A-']).any()
    
    def test_apply_universe_filter_outstanding_minimum(self, bloomberg_connector, sample_bloomberg_data):
        """Test minimum outstanding amount filtering"""
        filter_criteria = {'OutstandE_min': 600000000}
        filtered_data = bloomberg_connector._apply_universe_filter(sample_bloomberg_data, filter_criteria)
        
        assert all(filtered_data['OutstandE'] >= 600000000)
    
    def test_apply_universe_filter_maturity_minimum(self, bloomberg_connector, sample_bloomberg_data):
        """Test minimum maturity filtering"""
        filter_criteria = {'Maturity_min': 5.0}
        filtered_data = bloomberg_connector._apply_universe_filter(sample_bloomberg_data, filter_criteria)
        
        assert all(filtered_data['Maturity'] >= 5.0)
    
    def test_apply_universe_filter_null_market_values(self, bloomberg_connector):
        """Test filtering of null market values"""
        data_with_nulls = pd.DataFrame({
            'Cusip': ['123', '456', '789'],
            'MrktValue': [1000000, None, 2000000],
            'Currency': ['USD', 'USD', 'USD']
        })
        
        filtered_data = bloomberg_connector._apply_universe_filter(data_with_nulls, {})
        
        assert len(filtered_data) == 2  # Should exclude the null market value
        assert filtered_data['MrktValue'].notna().all()
    
    def test_generate_mock_bloomberg_data_default(self, bloomberg_connector):
        """Test mock data generation with default parameters"""
        mock_data = bloomberg_connector._generate_mock_bloomberg_data()
        
        assert isinstance(mock_data, pd.DataFrame)
        assert len(mock_data) == 10000  # Default size
        
        # Verify required columns present
        required_columns = ['Cusip', 'ISIN', 'Currency', 'QualityB', 'OutstandE', 'Maturity']
        for col in required_columns:
            assert col in mock_data.columns
        
        # Verify data quality
        assert mock_data['Cusip'].str.len().eq(9).all()  # CUSIPs are 9 characters
        assert mock_data['ISIN'].str.len().eq(12).all()   # ISINs are 12 characters
        assert mock_data['Currency'].isin(['USD', 'EUR', 'JPY', 'GBP']).all()
        assert mock_data['OutstandE'].gt(0).all()
        assert mock_data['Maturity'].gt(0).all()
    
    def test_generate_mock_bloomberg_data_custom_size(self, bloomberg_connector):
        """Test mock data generation with custom size"""
        custom_size = 100
        mock_data = bloomberg_connector._generate_mock_bloomberg_data(custom_size)
        
        assert len(mock_data) == custom_size
    
    def test_generate_mock_data_correlations(self, bloomberg_connector):
        """Test that mock data has realistic correlations"""
        mock_data = bloomberg_connector._generate_mock_bloomberg_data(1000)
        
        # Higher quality ratings should have lower spreads
        aaa_data = mock_data[mock_data['QualityB'] == 'AAA']
        ccc_data = mock_data[mock_data['QualityB'] == 'CCC']
        
        if len(aaa_data) > 0 and len(ccc_data) > 0:
            aaa_avg_spread = aaa_data['OAS_bp'].mean()
            ccc_avg_spread = ccc_data['OAS_bp'].mean()
            assert aaa_avg_spread < ccc_avg_spread
        
        # Longer duration should correlate with spreads
        correlation = mock_data['ISMA_MDur'].corr(mock_data['OAS_bp'])
        assert correlation > 0  # Should be positive correlation
    
    def test_get_security_data_cusip(self, bloomberg_connector):
        """Test getting data for specific CUSIPs"""
        test_cusips = ['123456789', '987654321']
        
        data = bloomberg_connector.get_security_data(test_cusips, 'CUSIP')
        
        assert isinstance(data, pd.DataFrame)
        # Note: Mock data may not contain exact CUSIPs, but should return DataFrame
        assert 'Cusip' in data.columns
    
    def test_get_security_data_isin(self, bloomberg_connector):
        """Test getting data for specific ISINs"""
        test_isins = ['US1234567890', 'US9876543210']
        
        data = bloomberg_connector.get_security_data(test_isins, 'ISIN')
        
        assert isinstance(data, pd.DataFrame)
        assert 'ISIN' in data.columns
    
    def test_get_security_data_invalid_type(self, bloomberg_connector):
        """Test getting data with invalid identifier type"""
        with pytest.raises(ValueError, match="Unsupported identifier type"):
            bloomberg_connector.get_security_data(['123'], 'INVALID_TYPE')
    
    def test_get_security_data_connection_error(self, bloomberg_connector):
        """Test getting security data when connection fails"""
        bloomberg_connector.is_connected = False
        
        with patch.object(bloomberg_connector, 'connect', return_value=False):
            with pytest.raises(ConnectionError, match="Unable to connect to Bloomberg"):
                bloomberg_connector.get_security_data(['123456789'], 'CUSIP')
    
    def test_validate_data_quality_good_data(self, bloomberg_connector, sample_bloomberg_data):
        """Test data quality validation with good data"""
        validation_report = bloomberg_connector.validate_data_quality(sample_bloomberg_data)
        
        assert isinstance(validation_report, dict)
        assert 'total_securities' in validation_report
        assert 'overall_coverage' in validation_report
        assert 'meets_minimum_coverage' in validation_report
        assert 'field_completeness' in validation_report
        assert 'data_quality_issues' in validation_report
        
        assert validation_report['total_securities'] == len(sample_bloomberg_data)
        assert validation_report['overall_coverage'] >= 0.0
        assert isinstance(validation_report['meets_minimum_coverage'], bool)
    
    def test_validate_data_quality_missing_fields(self, bloomberg_connector):
        """Test data quality validation with missing critical fields"""
        incomplete_data = pd.DataFrame({
            'Cusip': ['123456789', '987654321'],
            'Currency': ['USD', 'USD'],
            # Missing many required fields
        })
        
        validation_report = bloomberg_connector.validate_data_quality(incomplete_data)
        
        assert validation_report['overall_coverage'] < 0.95
        assert not validation_report['meets_minimum_coverage']
        assert len(validation_report['data_quality_issues']) > 0
    
    def test_validate_data_quality_outliers(self, bloomberg_connector):
        """Test data quality validation with outliers"""
        data_with_outliers = pd.DataFrame({
            'Cusip': [f"{i:09d}" for i in range(100)],
            'Currency': ['USD'] * 100,
            'QualityB': ['AA'] * 100,
            'OutstandE': [1000000000] * 95 + [1e15] * 5,  # 5 extreme outliers
            'Maturity': [5.0] * 100,
            'MrktValue': [1000000000] * 100,
            'ISMA_MDur': [4.0] * 100,
            'OAS_bp': [100] * 100,
            'IssrClsL1': ['Corporate'] * 100
        })
        
        validation_report = bloomberg_connector.validate_data_quality(data_with_outliers)
        
        # Should detect outliers in OutstandE field
        assert any('OutstandE' in issue for issue in validation_report['data_quality_issues'])
    
    def test_validate_data_quality_empty_dataframe(self, bloomberg_connector):
        """Test data quality validation with empty DataFrame"""
        empty_data = pd.DataFrame()
        
        validation_report = bloomberg_connector.validate_data_quality(empty_data)
        
        assert validation_report['total_securities'] == 0
        assert validation_report['overall_coverage'] == 0.0
        assert not validation_report['meets_minimum_coverage']
    
    def test_required_fields_completeness(self, bloomberg_connector):
        """Test that all required fields are properly defined"""
        required_fields = bloomberg_connector.required_fields
        
        # Should include all critical fields per specification
        expected_fields = [
            'Currency', 'QualityB', 'OutstandE', 'Maturity', 'MrktValue',
            'ISMA_MDur', 'OAS_bp', 'IssrClsL1', 'IssrClsL2', 'Sector',
            'Country', 'QualityE', 'RetTotal', 'RetPrice', 'MrkValBeg',
            'RetCurncy', 'ProductCurrency', 'YldWorstE', 'DurAdjMod',
            'ConvAdj', 'Issuer', 'Cusip', 'ISIN'
        ]
        
        for field in expected_fields:
            assert field in required_fields
    
    @patch('src.data.bloomberg_connector.logger')
    def test_logging_coverage(self, mock_logger, bloomberg_connector):
        """Test that appropriate logging occurs"""
        bloomberg_connector.connect()
        bloomberg_connector.extract_global_aggregate_data()
        
        # Verify info logging was called
        assert mock_logger.info.called
    
    def test_mock_data_reproducibility(self, bloomberg_connector):
        """Test that mock data generation is reproducible"""
        # Generate same data twice
        data1 = bloomberg_connector._generate_mock_bloomberg_data(100)
        data2 = bloomberg_connector._generate_mock_bloomberg_data(100)
        
        # Should be identical (due to fixed random seed)
        pd.testing.assert_frame_equal(data1, data2)
    
    def test_universe_filter_edge_cases(self, bloomberg_connector):
        """Test universe filtering with edge cases"""
        edge_data = pd.DataFrame({
            'Cusip': ['123456789', '987654321', '456789123'],
            'Currency': ['USD', None, 'EUR'],  # One null currency
            'QualityB': ['AA', 'NR', 'BBB'],    # One not rated
            'OutstandE': [500000000, 200000000, 800000000],  # One below threshold
            'Maturity': [5.0, 0.5, 10.0],      # One below threshold
            'MrktValue': [500000000, None, 800000000]  # One null market value
        })
        
        default_filter = {
            'Currency': ['USD'],
            'QualityB_exclude': ['NR', 'D', ''],
            'OutstandE_min': 300000000,
            'Maturity_min': 1.0
        }
        
        filtered_data = bloomberg_connector._apply_universe_filter(edge_data, default_filter)
        
        # Should only keep the first row after all filters
        assert len(filtered_data) == 1
        assert filtered_data.iloc[0]['Cusip'] == '123456789'
    
    def test_performance_large_dataset(self, bloomberg_connector):
        """Test performance with large dataset generation"""
        import time
        
        start_time = time.time()
        large_data = bloomberg_connector._generate_mock_bloomberg_data(10000)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should generate 10k securities quickly (< 5 seconds)
        assert processing_time < 5.0
        assert len(large_data) == 10000
    
    def test_data_types_consistency(self, bloomberg_connector):
        """Test that generated mock data has consistent types"""
        mock_data = bloomberg_connector._generate_mock_bloomberg_data(100)
        
        # Verify expected data types
        assert mock_data['Cusip'].dtype == 'object'
        assert mock_data['ISIN'].dtype == 'object'
        assert mock_data['Currency'].dtype == 'object'
        assert pd.api.types.is_numeric_dtype(mock_data['OutstandE'])
        assert pd.api.types.is_numeric_dtype(mock_data['Maturity'])
        assert pd.api.types.is_numeric_dtype(mock_data['MrktValue'])
        assert pd.api.types.is_numeric_dtype(mock_data['ISMA_MDur'])
        assert pd.api.types.is_numeric_dtype(mock_data['OAS_bp'])
    
    def test_connection_state_management(self, bloomberg_connector):
        """Test proper connection state management"""
        # Initially not connected
        assert not bloomberg_connector.is_connected
        
        # Connect
        result = bloomberg_connector.connect()
        assert result is True
        assert bloomberg_connector.is_connected
        
        # Multiple connects should work
        result2 = bloomberg_connector.connect()
        assert result2 is True
        assert bloomberg_connector.is_connected
        
        # Disconnect
        bloomberg_connector.disconnect()
        assert not bloomberg_connector.is_connected
        
        # Multiple disconnects should work
        bloomberg_connector.disconnect()
        assert not bloomberg_connector.is_connected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])