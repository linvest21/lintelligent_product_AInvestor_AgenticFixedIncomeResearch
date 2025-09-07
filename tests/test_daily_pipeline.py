"""
Unit Tests for Daily ETL Pipeline
JIRA: AINV-711

Comprehensive test coverage for the daily ETL pipeline including
data extraction, filtering, calculation, validation, and storage processes.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio

from src.etl.daily_pipeline import DailyETLPipeline
from src.models.database_models import CreditRating, BloombergData, ProcessingLog


class TestDailyETLPipeline:
    """Test suite for DailyETLPipeline class"""
    
    def test_initialization(self, test_database_engine):
        """Test daily pipeline initialization"""
        pipeline = DailyETLPipeline(test_database_engine)
        
        assert pipeline.engine == test_database_engine
        assert hasattr(pipeline, 'bloomberg_connector')
        assert hasattr(pipeline, 'rating_engine')
        assert hasattr(pipeline, 'validation_framework')
        assert pipeline.batch_size == 1000  # Default batch size
    
    def test_initialization_custom_params(self, test_database_engine):
        """Test initialization with custom parameters"""
        pipeline = DailyETLPipeline(test_database_engine, batch_size=500)
        assert pipeline.batch_size == 500
    
    @pytest.mark.asyncio
    async def test_run_daily_process_complete_success(self, daily_pipeline, sample_bloomberg_data):
        """Test complete daily process execution with success"""
        process_date = date.today()
        
        with patch.object(daily_pipeline, '_extract_bloomberg_data', new_callable=AsyncMock) as mock_extract, \
             patch.object(daily_pipeline, '_apply_universe_filters', new_callable=AsyncMock) as mock_filter, \
             patch.object(daily_pipeline, '_calculate_ratings', new_callable=AsyncMock) as mock_calc, \
             patch.object(daily_pipeline, '_validate_ratings', new_callable=AsyncMock) as mock_validate, \
             patch.object(daily_pipeline, '_store_results', new_callable=AsyncMock) as mock_store, \
             patch.object(daily_pipeline, '_generate_alerts', new_callable=AsyncMock) as mock_alerts:
            
            # Mock return values
            mock_extract.return_value = sample_bloomberg_data
            mock_filter.return_value = sample_bloomberg_data.head(2)  # Filtered data
            
            mock_calc_results = [
                {
                    'cusip': '123456789',
                    'final_score': 88.5,
                    'linvest21_rating': 'LIN-AA',
                    'quantitative_score': 35.0,
                    'sector_score': 20.0,
                    'agency_score': 28.0,
                    'alpha_score': 5.5
                }
            ]
            mock_calc.return_value = mock_calc_results
            
            mock_validation_results = [
                {
                    'cusip': '123456789',
                    'overall_status': 'PASSED',
                    'validation_score': 95.0
                }
            ]
            mock_validate.return_value = mock_validation_results
            
            mock_store.return_value = {'stored_ratings': 1, 'stored_bloomberg_data': 2}
            mock_alerts.return_value = {'alerts_sent': 0}
            
            # Run the process
            result = await daily_pipeline.run_daily_process(process_date)
            
            # Verify result structure
            assert isinstance(result, dict)
            assert 'process_status' in result
            assert 'summary' in result
            assert result['process_status'] == 'COMPLETED'
            
            # Verify all steps were called
            mock_extract.assert_called_once()
            mock_filter.assert_called_once()
            mock_calc.assert_called_once()
            mock_validate.assert_called_once()
            mock_store.assert_called_once()
            mock_alerts.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_daily_process_with_failures(self, daily_pipeline):
        """Test daily process with some failures"""
        process_date = date.today()
        
        with patch.object(daily_pipeline, '_extract_bloomberg_data', new_callable=AsyncMock) as mock_extract:
            # Mock extraction failure
            mock_extract.side_effect = Exception("Bloomberg connection failed")
            
            result = await daily_pipeline.run_daily_process(process_date)
            
            assert result['process_status'] == 'FAILED'
            assert 'error_message' in result
            assert "Bloomberg connection failed" in result['error_message']
    
    @pytest.mark.asyncio
    async def test_extract_bloomberg_data_success(self, daily_pipeline, sample_bloomberg_data):
        """Test Bloomberg data extraction"""
        with patch.object(daily_pipeline.bloomberg_connector, 'extract_global_aggregate_data') as mock_extract:
            mock_extract.return_value = sample_bloomberg_data
            
            result = await daily_pipeline._extract_bloomberg_data()
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(sample_bloomberg_data)
            assert all(col in result.columns for col in ['Cusip', 'Currency', 'QualityB'])
            mock_extract.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_bloomberg_data_connection_error(self, daily_pipeline):
        """Test Bloomberg data extraction with connection error"""
        with patch.object(daily_pipeline.bloomberg_connector, 'extract_global_aggregate_data') as mock_extract:
            mock_extract.side_effect = ConnectionError("Unable to connect to Bloomberg")
            
            with pytest.raises(Exception, match="Bloomberg data extraction failed"):
                await daily_pipeline._extract_bloomberg_data()
    
    @pytest.mark.asyncio
    async def test_apply_universe_filters_default(self, daily_pipeline, sample_bloomberg_data):
        """Test universe filtering with default criteria"""
        result = await daily_pipeline._apply_universe_filters(sample_bloomberg_data)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) <= len(sample_bloomberg_data)
        
        # Verify filtering criteria applied
        assert all(result['Currency'] == 'USD')
        assert all(result['OutstandE'] >= 300000000)
        assert all(result['Maturity'] >= 1.0)
        assert not result['QualityB'].isin(['NR', 'D', '']).any()
    
    @pytest.mark.asyncio
    async def test_apply_universe_filters_custom(self, daily_pipeline, sample_bloomberg_data):
        """Test universe filtering with custom criteria"""
        custom_filters = {
            'Currency': ['USD', 'EUR'],
            'OutstandE_min': 500000000,
            'Maturity_min': 3.0
        }
        
        result = await daily_pipeline._apply_universe_filters(sample_bloomberg_data, custom_filters)
        
        assert isinstance(result, pd.DataFrame)
        # Should be more restrictive than default
        assert all(result['OutstandE'] >= 500000000)
        assert all(result['Maturity'] >= 3.0)
    
    @pytest.mark.asyncio
    async def test_apply_universe_filters_empty_result(self, daily_pipeline):
        """Test universe filtering that results in empty dataset"""
        # Create data that will be filtered out
        restrictive_data = pd.DataFrame({
            'Cusip': ['123456789'],
            'Currency': ['EUR'],  # Will be filtered out if looking for USD only
            'QualityB': ['NR'],   # Will be filtered out
            'OutstandE': [100000000],  # Below minimum
            'Maturity': [0.5]     # Below minimum
        })
        
        result = await daily_pipeline._apply_universe_filters(restrictive_data)
        
        # Should result in empty DataFrame
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_ratings_success(self, daily_pipeline, sample_bloomberg_data):
        """Test rating calculations with successful data"""
        with patch.object(daily_pipeline.rating_engine, 'calculate_rating') as mock_calc:
            mock_calc.return_value = {
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.5,
                'validation_status': 'CALCULATED'
            }
            
            filtered_data = sample_bloomberg_data.head(2)  # Small sample for testing
            result = await daily_pipeline._calculate_ratings(filtered_data)
            
            assert isinstance(result, list)
            assert len(result) == len(filtered_data)
            
            # Verify each result has required fields
            for rating_result in result:
                assert 'cusip' in rating_result
                assert 'final_score' in rating_result
                assert 'linvest21_rating' in rating_result
            
            # Verify rating engine was called for each security
            assert mock_calc.call_count == len(filtered_data)
    
    @pytest.mark.asyncio
    async def test_calculate_ratings_with_errors(self, daily_pipeline, sample_bloomberg_data):
        """Test rating calculations with some errors"""
        call_count = 0
        
        def mock_calc_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail the second calculation
                return {'error': 'Calculation failed for this security'}
            return {
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.5
            }
        
        with patch.object(daily_pipeline.rating_engine, 'calculate_rating') as mock_calc:
            mock_calc.side_effect = mock_calc_side_effect
            
            filtered_data = sample_bloomberg_data.head(3)
            result = await daily_pipeline._calculate_ratings(filtered_data)
            
            assert isinstance(result, list)
            assert len(result) == 2  # Should only return successful calculations
            
            # Verify only successful calculations are included
            for rating_result in result:
                assert 'error' not in rating_result
                assert rating_result['final_score'] == 88.5
    
    @pytest.mark.asyncio
    async def test_calculate_ratings_batch_processing(self, daily_pipeline, performance_test_data):
        """Test rating calculations with batch processing"""
        with patch.object(daily_pipeline.rating_engine, 'calculate_rating') as mock_calc:
            mock_calc.return_value = {
                'final_score': 85.0,
                'linvest21_rating': 'LIN-A',
                'quantitative_score': 32.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.0
            }
            
            # Use large dataset to test batching
            large_data = performance_test_data.head(100)
            result = await daily_pipeline._calculate_ratings(large_data)
            
            assert len(result) == 100
            assert mock_calc.call_count == 100
    
    @pytest.mark.asyncio
    async def test_validate_ratings_success(self, daily_pipeline):
        """Test rating validation with successful validations"""
        rating_results = [
            {
                'cusip': '123456789',
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.5
            }
        ]
        
        bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789'],
            'QualityB': ['AA'],
            'OAS_bp': [85],
            'IssrClsL1': ['Corporate-Financial']
        })
        
        with patch.object(daily_pipeline.validation_framework, 'validate_batch_ratings') as mock_validate:
            mock_validate.return_value = [
                {
                    'cusip': '123456789',
                    'overall_status': 'PASSED',
                    'validation_score': 95.0,
                    'bloomberg_consistency': {'status': 'VALIDATED'},
                    'spread_correlation': {'status': 'PASS'},
                    'peer_group_analysis': {'status': 'WITHIN_RANGE'}
                }
            ]
            
            result = await daily_pipeline._validate_ratings(rating_results, bloomberg_data)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['overall_status'] == 'PASSED'
            assert result[0]['validation_score'] == 95.0
            
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_ratings_with_failures(self, daily_pipeline):
        """Test rating validation with some failures"""
        rating_results = [
            {
                'cusip': '123456789',
                'final_score': 120.0,  # Unrealistic high score
                'linvest21_rating': 'LIN-AAA',
                'quantitative_score': 40.0,
                'sector_score': 25.0,
                'agency_score': 35.0,
                'alpha_score': 20.0  # Over limit
            }
        ]
        
        bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789'],
            'QualityB': ['BBB'],  # Much lower than LINVEST21 rating
            'OAS_bp': [300],      # High spread inconsistent with rating
            'IssrClsL1': ['Corporate-Industrial']
        })
        
        with patch.object(daily_pipeline.validation_framework, 'validate_batch_ratings') as mock_validate:
            mock_validate.return_value = [
                {
                    'cusip': '123456789',
                    'overall_status': 'REVIEW_REQUIRED',
                    'validation_score': 45.0,
                    'bloomberg_consistency': {'status': 'MANUAL_OVERRIDE_NEEDED'},
                    'spread_correlation': {'status': 'FLAG_FOR_REVIEW'},
                    'peer_group_analysis': {'status': 'OUTLIER'}
                }
            ]
            
            result = await daily_pipeline._validate_ratings(rating_results, bloomberg_data)
            
            assert result[0]['overall_status'] == 'REVIEW_REQUIRED'
            assert result[0]['validation_score'] == 45.0
    
    @pytest.mark.asyncio
    async def test_store_results_success(self, daily_pipeline, test_db_session):
        """Test storing results to database"""
        rating_results = [
            {
                'cusip': '123456789',
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.5,
                'validation_status': 'VALIDATED'
            }
        ]
        
        bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789'],
            'Currency': ['USD'],
            'QualityB': ['AA'],
            'OutstandE': [1000000000],
            'Maturity': [5.0]
        })
        
        validation_results = [
            {
                'cusip': '123456789',
                'overall_status': 'PASSED',
                'validation_score': 95.0
            }
        ]
        
        process_date = date.today()
        
        # Mock the database session
        with patch.object(daily_pipeline, '_get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session
            
            result = await daily_pipeline._store_results(
                rating_results, bloomberg_data, validation_results, process_date
            )
            
            assert isinstance(result, dict)
            assert 'stored_ratings' in result
            assert 'stored_bloomberg_data' in result
            assert 'stored_validations' in result
            
            # Verify data was stored
            stored_rating = test_db_session.query(CreditRating).filter_by(cusip='123456789').first()
            assert stored_rating is not None
            assert stored_rating.final_score == 88.5
            assert stored_rating.linvest21_rating == 'LIN-AA'
    
    @pytest.mark.asyncio
    async def test_store_results_duplicate_handling(self, daily_pipeline, test_db_session):
        """Test handling of duplicate ratings for same CUSIP and date"""
        # Create existing rating
        existing_rating = CreditRating(
            cusip='123456789',
            calculation_date=date.today(),
            final_score=85.0,
            linvest21_rating='LIN-A+'
        )
        test_db_session.add(existing_rating)
        test_db_session.commit()
        
        # Try to store updated rating
        rating_results = [
            {
                'cusip': '123456789',
                'final_score': 88.5,
                'linvest21_rating': 'LIN-AA',
                'quantitative_score': 35.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.5
            }
        ]
        
        bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789'],
            'Currency': ['USD'],
            'QualityB': ['AA']
        })
        
        with patch.object(daily_pipeline, '_get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session
            
            result = await daily_pipeline._store_results(
                rating_results, bloomberg_data, [], date.today()
            )
            
            # Should handle duplicates gracefully
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_generate_alerts_no_issues(self, daily_pipeline):
        """Test alert generation with no issues"""
        validation_results = [
            {
                'cusip': '123456789',
                'overall_status': 'PASSED',
                'validation_score': 95.0
            }
        ]
        
        summary_stats = {
            'total_processed': 100,
            'successful_calculations': 98,
            'validation_pass_rate': 0.95,
            'coverage_rate': 0.99
        }
        
        result = await daily_pipeline._generate_alerts(validation_results, summary_stats)
        
        assert isinstance(result, dict)
        assert 'alerts_sent' in result
        assert result['alerts_sent'] == 0  # No alerts needed for good performance
    
    @pytest.mark.asyncio
    async def test_generate_alerts_with_issues(self, daily_pipeline):
        """Test alert generation with performance issues"""
        validation_results = [
            {
                'cusip': '123456789',
                'overall_status': 'REVIEW_REQUIRED',
                'validation_score': 45.0
            },
            {
                'cusip': '987654321',
                'overall_status': 'FAILED',
                'validation_score': 25.0
            }
        ]
        
        summary_stats = {
            'total_processed': 100,
            'successful_calculations': 70,  # Low success rate
            'validation_pass_rate': 0.60,  # Below threshold
            'coverage_rate': 0.85          # Below threshold
        }
        
        result = await daily_pipeline._generate_alerts(validation_results, summary_stats)
        
        assert isinstance(result, dict)
        assert 'alerts_sent' in result
        assert result['alerts_sent'] > 0  # Should send alerts for issues
        assert 'alert_details' in result
    
    @pytest.mark.asyncio
    async def test_calculate_summary_statistics(self, daily_pipeline):
        """Test calculation of summary statistics"""
        rating_results = [
            {'cusip': '123', 'final_score': 88.5},
            {'cusip': '456', 'final_score': 75.0},
            {'cusip': '789', 'final_score': 92.0}
        ]
        
        validation_results = [
            {'cusip': '123', 'overall_status': 'PASSED'},
            {'cusip': '456', 'overall_status': 'REVIEW_REQUIRED'},
            {'cusip': '789', 'overall_status': 'PASSED'}
        ]
        
        original_universe_size = 1000
        filtered_universe_size = 500
        
        stats = await daily_pipeline._calculate_summary_statistics(
            rating_results, validation_results, original_universe_size, filtered_universe_size
        )
        
        assert isinstance(stats, dict)
        assert stats['total_processed'] == 3
        assert stats['successful_calculations'] == 3
        assert stats['validation_pass_count'] == 2
        assert stats['validation_pass_rate'] == 2/3
        assert stats['coverage_rate'] == 3/500  # processed / filtered universe
        assert stats['universe_reduction_rate'] == 500/1000  # filtered / original
    
    def test_get_db_session(self, daily_pipeline):
        """Test database session creation"""
        session_context = daily_pipeline._get_db_session()
        
        # Should return a context manager
        assert hasattr(session_context, '__enter__')
        assert hasattr(session_context, '__exit__')
        
        # Test context manager usage
        with session_context as session:
            assert session is not None
            # Session should be usable for queries
            result = session.execute("SELECT 1")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_performance_large_dataset(self, daily_pipeline, performance_test_data):
        """Test pipeline performance with large dataset"""
        import time
        
        # Mock all external dependencies for pure performance testing
        with patch.object(daily_pipeline.bloomberg_connector, 'extract_global_aggregate_data') as mock_extract, \
             patch.object(daily_pipeline.rating_engine, 'calculate_rating') as mock_calc, \
             patch.object(daily_pipeline.validation_framework, 'validate_batch_ratings') as mock_validate, \
             patch.object(daily_pipeline, '_store_results', new_callable=AsyncMock) as mock_store:
            
            # Setup mocks
            mock_extract.return_value = performance_test_data
            mock_calc.return_value = {
                'final_score': 85.0,
                'linvest21_rating': 'LIN-A',
                'quantitative_score': 32.0,
                'sector_score': 20.0,
                'agency_score': 28.0,
                'alpha_score': 5.0
            }
            mock_validate.return_value = [
                {'cusip': cusip, 'overall_status': 'PASSED', 'validation_score': 90.0}
                for cusip in performance_test_data['Cusip']
            ]
            mock_store.return_value = {'stored_ratings': len(performance_test_data)}
            
            start_time = time.time()
            result = await daily_pipeline.run_daily_process()
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Should process large dataset in reasonable time (< 10 seconds)
            assert processing_time < 10.0
            assert result['process_status'] == 'COMPLETED'
    
    @patch('src.etl.daily_pipeline.logger')
    def test_logging_coverage(self, mock_logger, daily_pipeline):
        """Test that appropriate logging occurs"""
        # Test sync logging by calling a method that logs
        session = daily_pipeline._get_db_session()
        assert session is not None
        
        # Verify logger was used (methods may call logger during initialization)
        # This is more of a smoke test to ensure logger is accessible
        assert hasattr(daily_pipeline, 'logger') or mock_logger.info.called or mock_logger.debug.called
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, daily_pipeline):
        """Test error handling and recovery mechanisms"""
        with patch.object(daily_pipeline.bloomberg_connector, 'extract_global_aggregate_data') as mock_extract:
            # First call fails, second succeeds (simulating retry logic)
            mock_extract.side_effect = [
                Exception("Temporary connection error"),
                pd.DataFrame({'Cusip': ['123456789'], 'Currency': ['USD'], 'QualityB': ['AA']})
            ]
            
            # If pipeline implements retry logic, it should recover
            # If not, it should fail gracefully
            result = await daily_pipeline.run_daily_process()
            
            # Either succeeds after retry or fails gracefully
            assert result['process_status'] in ['COMPLETED', 'FAILED']
            assert 'error_message' in result or 'summary' in result
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_batch_processing(self, daily_pipeline, performance_test_data):
        """Test memory efficiency with batch processing"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch.object(daily_pipeline.bloomberg_connector, 'extract_global_aggregate_data') as mock_extract, \
             patch.object(daily_pipeline.rating_engine, 'calculate_rating') as mock_calc, \
             patch.object(daily_pipeline, '_store_results', new_callable=AsyncMock) as mock_store:
            
            # Use large dataset
            large_data = performance_test_data
            mock_extract.return_value = large_data
            mock_calc.return_value = {'final_score': 85.0, 'linvest21_rating': 'LIN-A'}
            mock_store.return_value = {'stored_ratings': len(large_data)}
            
            await daily_pipeline.run_daily_process()
            
            # Check memory usage hasn't grown excessively
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (< 100MB for test dataset)
            assert memory_increase < 100