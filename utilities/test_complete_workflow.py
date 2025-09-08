#!/usr/bin/env python3
"""
Complete Workflow Test for LINVEST21 Credit Rating System
JIRA: AINV-711

Tests the entire workflow from Bloomberg data ingestion through rating calculation
without requiring external test framework dependencies.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(__file__))

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework


class WorkflowTester:
    """Test runner for complete LINVEST21 workflow"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
    def assert_equal(self, actual, expected, message=""):
        """Assert equality test"""
        if actual == expected:
            self.passed_tests += 1
            return True
        else:
            self.failed_tests += 1
            self.test_results.append(f"FAILED: {message} - Expected {expected}, got {actual}")
            return False
    
    def assert_true(self, condition, message=""):
        """Assert condition is true"""
        if condition:
            self.passed_tests += 1
            return True
        else:
            self.failed_tests += 1
            self.test_results.append(f"FAILED: {message} - Condition was False")
            return False
    
    def assert_in(self, item, container, message=""):
        """Assert item in container"""
        if item in container:
            self.passed_tests += 1
            return True
        else:
            self.failed_tests += 1
            self.test_results.append(f"FAILED: {message} - {item} not in container")
            return False
    
    def run_test(self, test_name, test_func):
        """Run a single test"""
        print(f"\nRunning: {test_name}")
        try:
            test_func()
            print(f"  ✓ {test_name} passed")
        except Exception as e:
            self.failed_tests += 1
            self.test_results.append(f"ERROR in {test_name}: {str(e)}")
            print(f"  ✗ {test_name} failed: {str(e)}")
    
    def test_bloomberg_connector(self):
        """Test Bloomberg connector functionality"""
        connector = BloombergConnector()
        
        # Test connection
        self.assert_true(connector.connect(), "Bloomberg connection should succeed")
        self.assert_true(connector.is_connected, "Connector should be connected")
        
        # Test data generation
        data = connector._generate_mock_bloomberg_data(10)
        self.assert_equal(len(data), 10, "Should generate 10 securities")
        
        # Test required fields
        required_fields = ['Cusip', 'Currency', 'QualityB', 'OutstandE', 'Maturity']
        for field in required_fields:
            self.assert_in(field, data.columns, f"Field {field} should be present")
        
        # Test universe filter
        filtered = connector._apply_universe_filter(data, {
            'Currency': ['USD'],
            'OutstandE_min': 300000000
        })
        self.assert_true(all(filtered['Currency'] == 'USD'), "All currencies should be USD")
        
        # Test disconnection
        connector.disconnect()
        self.assert_equal(connector.is_connected, False, "Connector should be disconnected")
    
    def test_rating_engine(self):
        """Test rating engine calculations"""
        engine = LINVEST21RatingEngine()
        
        # Test with complete bond data
        bond_data = {
            'Cusip': '123456789',
            'Currency': 'USD',
            'QualityB': 'AA',
            'OutstandE': 1000000000,
            'Maturity': 5.0,
            'MrktValue': 1000000000,
            'ISMA_MDur': 4.5,
            'OAS_bp': 100,
            'IssrClsL1': 'Corporate-Financial',
            'Sector': 'Financial',
            'RetTotal': 0.05
        }
        
        result = engine.calculate_rating(bond_data)
        
        # Check result structure
        self.assert_in('final_score', result, "Result should have final_score")
        self.assert_in('linvest21_rating', result, "Result should have linvest21_rating")
        self.assert_in('quantitative_score', result, "Result should have quantitative_score")
        self.assert_in('sector_score', result, "Result should have sector_score")
        self.assert_in('agency_score', result, "Result should have agency_score")
        self.assert_in('alpha_score', result, "Result should have alpha_score")
        
        # Check score ranges
        self.assert_true(0 <= result['final_score'] <= 120, "Final score should be in valid range")
        self.assert_true(result['linvest21_rating'].startswith('LIN-'), "Rating should start with LIN-")
        
        # Test consistency - same input should give same output
        result2 = engine.calculate_rating(bond_data.copy())
        self.assert_equal(result['final_score'], result2['final_score'], "Consistent calculation")
    
    def test_validation_framework(self):
        """Test validation framework"""
        validator = ValidationFramework()
        
        # Test rating validation
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
        
        result = validator.validate_rating(rating_data, bloomberg_data)
        
        # Check validation result structure
        self.assert_in('overall_status', result, "Should have overall_status")
        self.assert_in('validation_checks', result, "Should have validation_checks")
        self.assert_in('bloomberg_consistency', result['validation_checks'], "Should have Bloomberg check")
        
        # Check status values
        valid_statuses = ['PASSED', 'REVIEW_REQUIRED', 'FAILED']
        self.assert_in(result['overall_status'], valid_statuses, "Valid status value")
    
    def test_complete_workflow(self):
        """Test complete end-to-end workflow"""
        # Initialize components
        connector = BloombergConnector()
        engine = LINVEST21RatingEngine()
        validator = ValidationFramework()
        
        # Step 1: Connect and get data
        connector.connect()
        bloomberg_data = connector._generate_mock_bloomberg_data(20)
        
        # Step 2: Apply filters
        filtered_data = connector._apply_universe_filter(bloomberg_data, {
            'Currency': ['USD'],
            'QualityB_exclude': ['NR', 'D'],
            'OutstandE_min': 300000000,
            'Maturity_min': 1.0
        })
        
        self.assert_true(len(filtered_data) > 0, "Should have filtered data")
        
        # Step 3: Calculate ratings for subset
        successful_ratings = 0
        failed_ratings = 0
        
        for idx, row in filtered_data.head(5).iterrows():
            bond_data = row.to_dict()
            rating_result = engine.calculate_rating(bond_data)
            
            if 'error' not in rating_result:
                successful_ratings += 1
                
                # Step 4: Validate rating
                validation_result = validator.validate_rating(rating_result, bond_data)
                self.assert_in('overall_status', validation_result, f"Validation for {bond_data['Cusip']}")
            else:
                failed_ratings += 1
        
        self.assert_true(successful_ratings > 0, "Should have successful ratings")
        
        # Test performance
        start_time = time.time()
        for idx, row in filtered_data.head(10).iterrows():
            engine.calculate_rating(row.to_dict())
        elapsed_time = time.time() - start_time
        
        self.assert_true(elapsed_time < 5.0, f"Should process 10 ratings quickly (took {elapsed_time:.2f}s)")
        
        connector.disconnect()
    
    def test_us_agg_benchmark_workflow(self):
        """Test US AGG benchmark analysis workflow"""
        connector = BloombergConnector()
        engine = LINVEST21RatingEngine()
        
        # Generate US AGG-like data
        connector.connect()
        us_agg_data = connector.extract_global_aggregate_data()
        
        # Apply US AGG filters
        filtered = connector._apply_universe_filter(us_agg_data, {
            'Currency': ['USD'],
            'QualityB_exclude': ['NR', 'D'],
            'OutstandE_min': 300000000,
            'Maturity_min': 1.0
        })
        
        # Calculate ratings for sample
        sample_size = min(20, len(filtered))
        ratings = []
        
        for idx, row in filtered.head(sample_size).iterrows():
            result = engine.calculate_rating(row.to_dict())
            if 'error' not in result:
                ratings.append(result)
        
        self.assert_true(len(ratings) > 0, "Should calculate some ratings")
        
        # Check rating distribution
        rating_counts = {}
        for r in ratings:
            rating = r['linvest21_rating']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        self.assert_true(len(rating_counts) > 0, "Should have rating distribution")
        
        # Verify scores are in expected ranges
        scores = [r['final_score'] for r in ratings]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        self.assert_true(50 <= avg_score <= 90, f"Average score in expected range ({avg_score:.1f})")
        
        connector.disconnect()
    
    def run_all_tests(self):
        """Run all workflow tests"""
        print("\n" + "="*60)
        print("LINVEST21 Complete Workflow Test Suite")
        print("="*60)
        
        # Run test suite
        self.run_test("Bloomberg Connector", self.test_bloomberg_connector)
        self.run_test("Rating Engine", self.test_rating_engine)
        self.run_test("Validation Framework", self.test_validation_framework)
        self.run_test("Complete Workflow", self.test_complete_workflow)
        self.run_test("US AGG Benchmark", self.test_us_agg_benchmark_workflow)
        
        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"✓ Passed: {self.passed_tests}")
        print(f"✗ Failed: {self.failed_tests}")
        print(f"Success Rate: {100 * self.passed_tests / (self.passed_tests + self.failed_tests):.1f}%")
        
        if self.test_results:
            print("\nFailed Test Details:")
            for result in self.test_results:
                print(f"  - {result}")
        
        return self.failed_tests == 0


def main():
    """Main test runner"""
    tester = WorkflowTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()