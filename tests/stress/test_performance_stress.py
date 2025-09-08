"""
Stress Tests for LINVEST21 Credit Rating System
JIRA: AINV-711

Performance and load testing to validate system behavior under stress conditions.
Tests throughput, memory usage, concurrent processing, and system limits.
"""

import sys
import os
# Add project root to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import pytest
import pandas as pd
import numpy as np
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
import psutil
from unittest.mock import patch

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector


class TestPerformanceStress:
    """Stress tests for system performance and scalability"""
    
    @pytest.fixture
    def rating_engine(self):
        """Create rating engine for stress testing"""
        return LINVEST21RatingEngine()
    
    @pytest.fixture
    def bloomberg_connector(self):
        """Create Bloomberg connector for stress testing"""
        return BloombergConnector()
    
    @pytest.fixture
    def large_dataset(self):
        """Generate large dataset for stress testing"""
        np.random.seed(42)  # For reproducible results
        n = 10000
        
        cusips = [f"{i:09d}" for i in range(100000000, 100000000 + n)]
        
        return pd.DataFrame({
            'Cusip': cusips,
            'Currency': np.random.choice(['USD'], n),
            'QualityB': np.random.choice(['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-'], n),
            'OutstandE': np.random.lognormal(20, 1, n) * 1000000,
            'Maturity': np.random.exponential(5, n) + 1,
            'MrktValue': np.random.lognormal(18, 1, n) * 1000000,
            'MrkValBeg': np.random.lognormal(18, 1, n) * 1000000,
            'ISMA_MDur': np.random.gamma(2, 3, n),
            'OAS_bp': np.random.gamma(2, 50, n),
            'DurAdjMod': np.random.gamma(2, 3, n),
            'IssrClsL1': np.random.choice(['Corporate-Financial', 'Corporate-Industrial', 'Corporate-Utility'], n),
            'Sector': np.random.choice(['Financial', 'Industrial', 'Utility'], n),
            'Country': ['US'] * n,
            'Issuer': [f"Company_{i//100}" for i in range(n)],
            'RetTotal': np.random.normal(0.05, 0.1, n),
            'RetPrice': np.random.normal(0.04, 0.08, n),
            'RetCurncy': np.random.normal(0.01, 0.02, n),
            'ProductCurrency': ['USD'] * n,
            'YldWorstE': np.random.gamma(2, 0.02, n)
        })
    
    def test_high_throughput_rating_calculation(self, rating_engine, large_dataset):
        """Test system throughput with high volume rating calculations"""
        # Test with 1000 securities
        test_data = large_dataset.head(1000)
        
        start_time = time.time()
        successful_calculations = 0
        failed_calculations = 0
        
        for _, security in test_data.iterrows():
            bond_data = security.to_dict()
            result = rating_engine.calculate_rating(bond_data)
            
            if 'error' in result:
                failed_calculations += 1
            else:
                successful_calculations += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance requirements
        throughput = successful_calculations / total_time
        success_rate = successful_calculations / len(test_data)
        
        # Assertions per specification requirements
        assert total_time < 300  # Should complete 1000 ratings in under 5 minutes
        assert throughput >= 5   # Should process at least 5 ratings per second
        assert success_rate >= 0.95  # Should have 95%+ success rate
        
        print(f"Processed {successful_calculations} ratings in {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} ratings/second")
        print(f"Success rate: {success_rate:.1%}")
    
    def test_memory_efficiency_large_dataset(self, rating_engine, large_dataset):
        """Test memory usage with large dataset processing"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process 500 securities and monitor memory
        test_data = large_dataset.head(500)
        processed_count = 0
        
        for _, security in test_data.iterrows():
            bond_data = security.to_dict()
            result = rating_engine.calculate_rating(bond_data)
            
            if 'error' not in result:
                processed_count += 1
            
            # Check memory every 100 calculations
            if processed_count % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory should not grow excessively
                assert memory_increase < 200  # Should not use more than 200MB additional
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        # Final memory check
        assert total_memory_increase < 300  # Should not increase by more than 300MB
        
        print(f"Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB")
        print(f"Memory increase: {total_memory_increase:.1f}MB")
    
    def test_concurrent_rating_calculations(self, rating_engine, large_dataset):
        """Test system behavior with concurrent rating calculations"""
        test_data = large_dataset.head(200)
        
        def calculate_batch(batch_data):
            """Calculate ratings for a batch of securities"""
            results = []
            for _, security in batch_data.iterrows():
                bond_data = security.to_dict()
                result = rating_engine.calculate_rating(bond_data)
                results.append(result)
            return results
        
        # Split data into batches for concurrent processing
        batch_size = 50
        batches = [test_data.iloc[i:i+batch_size] for i in range(0, len(test_data), batch_size)]
        
        start_time = time.time()
        
        # Process batches concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_batch = {executor.submit(calculate_batch, batch): batch for batch in batches}
            
            total_successful = 0
            total_failed = 0
            
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                
                for result in batch_results:
                    if 'error' in result:
                        total_failed += 1
                    else:
                        total_successful += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        throughput = total_successful / total_time
        success_rate = total_successful / len(test_data)
        
        assert total_time < 60   # Should complete in under 1 minute with concurrency
        assert throughput >= 10  # Should achieve higher throughput with concurrency
        assert success_rate >= 0.95
        
        print(f"Concurrent processing: {total_successful} ratings in {total_time:.2f}s")
        print(f"Concurrent throughput: {throughput:.2f} ratings/second")
    
    def test_bloomberg_data_extraction_stress(self, bloomberg_connector):
        """Test Bloomberg data extraction under stress"""
        bloomberg_connector.connect()
        
        start_time = time.time()
        
        # Extract large dataset multiple times to stress the connector
        extraction_count = 5
        total_securities = 0
        
        for i in range(extraction_count):
            data = bloomberg_connector._generate_mock_bloomberg_data(2000)
            total_securities += len(data)
            
            # Validate data quality for each extraction
            validation_report = bloomberg_connector.validate_data_quality(data)
            assert validation_report['total_securities'] == 2000
            assert validation_report['overall_coverage'] >= 0.90
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance requirements
        securities_per_second = total_securities / total_time
        
        assert total_time < 30  # Should complete 5 extractions in under 30 seconds
        assert securities_per_second >= 1000  # Should generate at least 1000 securities/second
        
        print(f"Generated {total_securities} securities in {total_time:.2f}s")
        print(f"Generation rate: {securities_per_second:.0f} securities/second")
    
    def test_rating_calculation_edge_cases_stress(self, rating_engine):
        """Test rating calculation with extreme and edge case data"""
        # Generate edge case scenarios
        edge_cases = []
        
        # Minimum values
        for i in range(100):
            edge_cases.append({
                'Cusip': f'MIN{i:06d}',
                'Currency': 'USD',
                'QualityB': 'CCC',
                'OutstandE': 300000000,  # Minimum threshold
                'Maturity': 1.0,         # Minimum threshold
                'MrktValue': 300000000,
                'MrkValBeg': 300000000,
                'ISMA_MDur': 0.1,
                'OAS_bp': 2000,          # Very high spread
                'IssrClsL1': 'Corporate-Industrial',
                'Sector': 'Industrial',
                'RetTotal': -0.50,       # Very negative return
                'RetCurncy': 0.01
            })
        
        # Maximum values
        for i in range(100):
            edge_cases.append({
                'Cusip': f'MAX{i:06d}',
                'Currency': 'USD', 
                'QualityB': 'AAA',
                'OutstandE': 50000000000,  # Very large
                'Maturity': 30.0,          # Long maturity
                'MrktValue': 50000000000,
                'MrkValBeg': 50000000000,
                'ISMA_MDur': 25.0,         # High duration
                'OAS_bp': 5,               # Very low spread
                'IssrClsL1': 'Government',
                'Sector': 'Government',
                'RetTotal': 0.30,          # Very high return
                'RetCurncy': -0.01
            })
        
        # Null/missing values
        for i in range(100):
            edge_cases.append({
                'Cusip': f'NUL{i:06d}',
                'Currency': 'USD',
                'QualityB': None,
                'OutstandE': None,
                'Maturity': 5.0,
                'MrktValue': 1000000000,
                'ISMA_MDur': None,
                'OAS_bp': None,
                'IssrClsL1': None,
                'Sector': None,
                'RetTotal': None
            })
        
        start_time = time.time()
        successful_calculations = 0
        failed_calculations = 0
        
        for edge_case in edge_cases:
            result = rating_engine.calculate_rating(edge_case)
            
            if 'error' in result:
                failed_calculations += 1
            else:
                successful_calculations += 1
                
                # Verify result validity for successful calculations
                assert isinstance(result['final_score'], (int, float))
                assert result['final_score'] >= 0
                assert result['linvest21_rating'].startswith('LIN-')
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Edge case handling requirements
        total_cases = len(edge_cases)
        success_rate = successful_calculations / total_cases
        
        assert total_time < 60    # Should handle edge cases quickly
        assert success_rate >= 0.66  # Should handle at least 66% of edge cases (200/300)
        
        print(f"Edge case testing: {successful_calculations}/{total_cases} successful")
        print(f"Edge case success rate: {success_rate:.1%}")
    
    def test_system_stability_long_running(self, rating_engine, bloomberg_connector):
        """Test system stability over extended operation"""
        bloomberg_connector.connect()
        
        start_time = time.time()
        target_runtime = 120  # Run for 2 minutes
        
        total_processed = 0
        total_successful = 0
        batch_count = 0
        
        while (time.time() - start_time) < target_runtime:
            # Generate small batch
            batch_data = bloomberg_connector._generate_mock_bloomberg_data(10)
            
            batch_successful = 0
            for _, security in batch_data.iterrows():
                bond_data = security.to_dict()
                result = rating_engine.calculate_rating(bond_data)
                
                total_processed += 1
                if 'error' not in result:
                    total_successful += 1
                    batch_successful += 1
            
            batch_count += 1
            
            # Monitor system health every 20 batches
            if batch_count % 20 == 0:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                # System should remain stable
                assert memory_mb < 1000  # Should not exceed 1GB memory usage
                
                current_time = time.time() - start_time
                throughput = total_processed / current_time
                
                print(f"Time: {current_time:.0f}s, Processed: {total_processed}, Throughput: {throughput:.1f}/s")
        
        total_time = time.time() - start_time
        overall_throughput = total_processed / total_time
        success_rate = total_successful / total_processed
        
        # Long-running stability requirements
        assert total_processed >= 1000  # Should process significant volume
        assert overall_throughput >= 8   # Should maintain good throughput
        assert success_rate >= 0.95     # Should maintain high success rate
        
        print(f"Long-running test: {total_processed} processed over {total_time:.1f}s")
        print(f"Average throughput: {overall_throughput:.2f} ratings/second")
        print(f"Overall success rate: {success_rate:.1%}")
    
    def test_bloomberg_connector_stress(self, bloomberg_connector):
        """Test Bloomberg connector under stress conditions"""
        bloomberg_connector.connect()
        
        # Test rapid consecutive data requests
        start_time = time.time()
        
        for i in range(50):  # 50 rapid requests
            data = bloomberg_connector._generate_mock_bloomberg_data(100)
            
            # Apply filters to stress the filtering logic
            filtered_data = bloomberg_connector._apply_universe_filter(data, {
                'Currency': ['USD'],
                'QualityB_exclude': ['NR', 'D'],
                'OutstandE_min': 500000000,
                'Maturity_min': 2.0
            })
            
            assert isinstance(filtered_data, pd.DataFrame)
            assert len(filtered_data) <= len(data)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle rapid requests efficiently
        assert total_time < 30  # Should complete 50 requests in under 30 seconds
        
        # Test connection stability
        assert bloomberg_connector.is_connected is True
        
        bloomberg_connector.disconnect()
        assert bloomberg_connector.is_connected is False
    
    def test_memory_leak_detection(self, rating_engine):
        """Test for memory leaks in rating calculations"""
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # Perform many rating calculations in batches
        for batch in range(10):
            batch_data = []
            
            # Create batch data
            for i in range(100):
                batch_data.append({
                    'Cusip': f'LEAK{batch:02d}{i:03d}',
                    'Currency': 'USD',
                    'QualityB': 'A',
                    'OutstandE': 1000000000,
                    'Maturity': 5.0,
                    'MrktValue': 1000000000,
                    'ISMA_MDur': 4.0,
                    'OAS_bp': 100,
                    'IssrClsL1': 'Corporate-Industrial',
                    'Sector': 'Industrial',
                    'RetTotal': 0.05
                })
            
            # Process batch
            for bond_data in batch_data:
                result = rating_engine.calculate_rating(bond_data)
                # Immediately discard result to test for leaks
                result = None
            
            # Clear batch data
            batch_data = None
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - baseline_memory
            
            # Memory should not continuously grow
            assert memory_increase < 100  # Should not increase by more than 100MB
        
        # Final memory check after all batches
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - baseline_memory
        
        # Total increase should be reasonable
        assert total_increase < 150  # Should not increase by more than 150MB total
        
        print(f"Memory leak test: {baseline_memory:.1f}MB → {final_memory:.1f}MB")
        print(f"Total memory increase: {total_increase:.1f}MB")
    
    def test_error_recovery_stress(self, rating_engine):
        """Test system recovery from error conditions"""
        error_count = 0
        success_count = 0
        recovery_count = 0
        
        # Mix of valid and invalid data to stress error handling
        test_cases = []
        
        # Valid cases
        for i in range(50):
            test_cases.append({
                'Cusip': f'VALID{i:03d}',
                'Currency': 'USD',
                'QualityB': 'A',
                'OutstandE': 1000000000,
                'Maturity': 5.0,
                'MrktValue': 1000000000,
                'MrkValBeg': 1000000000,
                'ISMA_MDur': 4.0,
                'OAS_bp': 100,
                'IssrClsL1': 'Corporate-Industrial',
                'Sector': 'Industrial',
                'RetTotal': 0.05,
                'RetCurncy': 0.001
            })
        
        # Invalid cases
        for i in range(50):
            test_cases.append({
                'Cusip': f'INVALID{i:03d}',
                'Currency': None,  # Invalid
                'QualityB': 'INVALID_RATING',
                'OutstandE': 'not_a_number',  # Invalid
                'Maturity': None,
                'MrktValue': -1000000000  # Invalid negative value
            })
        
        # Randomize order to stress error recovery
        import random
        random.shuffle(test_cases)
        
        consecutive_errors = 0
        max_consecutive_errors = 0
        
        for i, test_case in enumerate(test_cases):
            result = rating_engine.calculate_rating(test_case)
            
            if 'error' in result:
                error_count += 1
                consecutive_errors += 1
                max_consecutive_errors = max(max_consecutive_errors, consecutive_errors)
            else:
                success_count += 1
                if consecutive_errors > 0:
                    recovery_count += 1
                consecutive_errors = 0
        
        # Error recovery requirements
        total_cases = len(test_cases)
        error_rate = error_count / total_cases
        success_rate = success_count / total_cases
        
        assert success_rate >= 0.45  # Should handle at least 45% successfully (50/100)
        assert max_consecutive_errors < 20  # Should not have long error streaks
        assert recovery_count > 0  # Should demonstrate recovery capability
        
        print(f"Error recovery test: {success_count}/{total_cases} successful")
        print(f"Error rate: {error_rate:.1%}, Recovery events: {recovery_count}")
        print(f"Max consecutive errors: {max_consecutive_errors}")