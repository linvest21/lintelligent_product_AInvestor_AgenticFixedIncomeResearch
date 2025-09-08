"""
End-to-End Integration Tests for LINVEST21 Credit Rating System
JIRA: AINV-711

Tests the complete rating workflow from Bloomberg data ingestion 
through final rating calculation and validation.
"""

import sys
import os
# Add project root to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import unittest
import pandas as pd
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework
from src.models.database_models import Base, CreditRating, BloombergData


class TestEndToEndRating(unittest.TestCase):
    """Integration tests for complete rating workflow"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        # Create in-memory test database
        cls.test_database = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.test_database)
        
        # Create database session
        Session = sessionmaker(bind=cls.test_database)
        cls.test_session = Session()
        
        # Create component instances
        cls.rating_engine = LINVEST21RatingEngine()
        cls.bloomberg_connector = BloombergConnector()
        cls.validation_framework = ValidationFramework()
    
    def test_complete_rating_workflow(self):
        """Test complete rating workflow from data extraction to validation"""
        # Step 1: Extract mock Bloomberg data
        self.bloomberg_connector.connect()
        bloomberg_data = self.bloomberg_connector._generate_mock_bloomberg_data(10)
        
        # Step 2: Apply universe filters
        filtered_data = self.bloomberg_connector._apply_universe_filter(bloomberg_data, {
            'Currency': ['USD'],
            'QualityB_exclude': ['NR', 'D'],
            'OutstandE_min': 300000000,
            'Maturity_min': 1.0
        })
        
        self.assertGreater(len(filtered_data), 0)
        self.assertTrue(all(filtered_data['Currency'] == 'USD'))
        
        # Step 3: Calculate ratings for filtered securities
        rating_results = []
        for _, security in filtered_data.head(3).iterrows():  # Test with 3 securities
            bond_data = security.to_dict()
            rating_result = self.rating_engine.calculate_rating(bond_data)
            
            if 'error' not in rating_result:
                rating_results.append({
                    'cusip': security['Cusip'],
                    **rating_result
                })
        
        self.assertGreater(len(rating_results), 0)
        
        # Step 4: Validate ratings
        for result in rating_results:
            self.assertIn('final_score', result)
            self.assertIn('linvest21_rating', result)
            self.assertTrue(result['linvest21_rating'].startswith('LIN-'))
            self.assertTrue(0 <= result['final_score'] <= 120)  # Reasonable score range
        
        # Step 5: Test validation framework
        if len(rating_results) > 0:
            sample_rating = rating_results[0]
            sample_bloomberg = filtered_data[filtered_data['Cusip'] == sample_rating['cusip']].iloc[0].to_dict()
            
            validation_result = self.validation_framework.validate_rating(sample_rating, sample_bloomberg)
            
            self.assertIn('overall_status', validation_result)
            self.assertIn(validation_result['overall_status'], ['PASSED', 'REVIEW_REQUIRED', 'FAILED'])
    
    def test_bloomberg_data_quality_validation(self):
        """Test Bloomberg data quality validation"""
        self.bloomberg_connector.connect()
        
        # Generate test data
        test_data = self.bloomberg_connector._generate_mock_bloomberg_data(100)
        
        # Validate data quality
        validation_report = self.bloomberg_connector.validate_data_quality(test_data)
        
        self.assertIn('total_securities', validation_report)
        self.assertEqual(validation_report['total_securities'], 100)
        self.assertIn('overall_coverage', validation_report)
        self.assertGreaterEqual(validation_report['overall_coverage'], 0.8)  # Should have good coverage
        self.assertIn('field_completeness', validation_report)
        
        # Test data should meet minimum coverage requirements
        if validation_report['overall_coverage'] >= 0.95:
            self.assertEqual(validation_report['meets_minimum_coverage'], True)
    
    def test_rating_calculation_consistency(self):
        """Test that rating calculations are consistent across multiple runs"""
        # Create consistent test data
        test_bond = {
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
            'RetTotal': 0.05,
            'RetPrice': 0.045,
            'RetCurncy': 0.005,
            'MrkValBeg': 1000000000
        }
        
        # Calculate rating multiple times
        results = []
        for _ in range(5):
            result = self.rating_engine.calculate_rating(test_bond.copy())
            results.append(result)
        
        # Verify consistency
        first_result = results[0]
        if 'error' not in first_result:
            for result in results[1:]:
                self.assertEqual(result['final_score'], first_result['final_score'])
                self.assertEqual(result['linvest21_rating'], first_result['linvest21_rating'])
                self.assertEqual(result['quantitative_score'], first_result['quantitative_score'])
    
    def test_rating_component_weights(self):
        """Test that rating components follow specified weight constraints"""
        test_securities = [
            {
                'Cusip': f'12345678{i}',
                'Currency': 'USD',
                'QualityB': ['AAA', 'AA', 'A', 'BBB'][i % 4],
                'OutstandE': 1000000000,
                'Maturity': 5.0 + i,
                'MrktValue': 1000000000,
                'ISMA_MDur': 4.0 + i * 0.5,
                'OAS_bp': 50 + i * 25,
                'IssrClsL1': 'Corporate-Industrial',
                'Sector': 'Industrial',
                'RetTotal': 0.04 + i * 0.01
            }
            for i in range(4)
        ]
        
        for security in test_securities:
            result = self.rating_engine.calculate_rating(security)
            
            if 'error' not in result:
                # Verify component weight limits per specification
                self.assertTrue(0 <= result['quantitative_score'] <= 40)  # 40% max
                self.assertTrue(0 <= result['sector_score'] <= 25)       # 25% max  
                self.assertTrue(0 <= result['agency_score'] <= 35)       # 35% max
                self.assertTrue(0 <= result['alpha_score'] <= 15)        # 15% max
                
                # Verify total makes sense
                total_components = (
                    result['quantitative_score'] + 
                    result['sector_score'] + 
                    result['agency_score'] + 
                    result['alpha_score']
                )
                self.assertLess(abs(result['final_score'] - total_components), 0.1)
    
    def test_database_storage_retrieval(self):
        """Test complete database storage and retrieval workflow"""
        # Create test rating
        test_rating = CreditRating(
            cusip='123456789',
            isin='US1234567890',
            calculation_date=date.today(),
            issuer='Test Corporation',
            ticker='TEST',
            currency='USD',
            quantitative_score=32.5,
            sector_score=20.0,
            agency_score=28.0,
            alpha_score=12.0,
            final_score=92.5,
            linvest21_rating='LIN-AA',
            validation_status='VALIDATED'
        )
        
        # Store in database
        self.test_session.add(test_rating)
        self.test_session.commit()
        
        # Retrieve and verify
        retrieved_rating = self.test_session.query(CreditRating).filter_by(cusip='123456789').first()
        
        self.assertIsNotNone(retrieved_rating)
        self.assertEqual(retrieved_rating.cusip, '123456789')
        self.assertEqual(retrieved_rating.final_score, 92.5)
        self.assertEqual(retrieved_rating.linvest21_rating, 'LIN-AA')
        self.assertIsNotNone(retrieved_rating.created_timestamp)
        
        # Test to_dict method
        rating_dict = retrieved_rating.to_dict()
        self.assertIsInstance(rating_dict, dict)
        self.assertIn('cusip', rating_dict)
        self.assertIn('components', rating_dict)
        self.assertIn('quantitative_score', rating_dict['components'])
    
    def test_bloomberg_connector_integration(self):
        """Test Bloomberg connector integration functionality"""
        # Test connection
        self.assertTrue(self.bloomberg_connector.connect())
        self.assertTrue(self.bloomberg_connector.is_connected)
        
        # Test data extraction
        universe_data = self.bloomberg_connector.extract_global_aggregate_data()
        
        self.assertIsInstance(universe_data, pd.DataFrame)
        self.assertGreater(len(universe_data), 0)
        
        # Verify required fields are present
        required_fields = ['Cusip', 'Currency', 'QualityB', 'OutstandE', 'Maturity']
        for field in required_fields:
            self.assertIn(field, universe_data.columns)
        
        # Test specific security data retrieval
        sample_cusips = universe_data['Cusip'].head(3).tolist()
        security_data = self.bloomberg_connector.get_security_data(sample_cusips, 'CUSIP')
        
        # Note: Mock implementation may not return exact matches
        self.assertIsInstance(security_data, pd.DataFrame)
        
        # Test disconnection
        self.bloomberg_connector.disconnect()
        self.assertFalse(self.bloomberg_connector.is_connected)
    
    def test_validation_framework_integration(self):
        """Test validation framework integration"""
        # Test sample rating validation
        sample_rating = {
            'cusip': '123456789',
            'final_score': 88.5,
            'linvest21_rating': 'LIN-AA',
            'quantitative_score': 35.0,
            'sector_score': 20.0,
            'agency_score': 28.0,
            'alpha_score': 5.5
        }
        
        sample_bloomberg = {
            'QualityB': 'AA',
            'OAS_bp': 95,
            'IssrClsL1': 'Corporate-Financial',
            'OutstandE': 1000000000,
            'ISMA_MDur': 5.2
        }
        
        validation_result = self.validation_framework.validate_rating(sample_rating, sample_bloomberg)
        
        self.assertIsInstance(validation_result, dict)
        self.assertIn('overall_status', validation_result)
        self.assertIn('validation_checks', validation_result)
        self.assertIn('bloomberg_consistency', validation_result['validation_checks'])
        
        # Test Bloomberg consistency
        bloomberg_result = self.validation_framework.validate_bloomberg_consistency(
            sample_rating['final_score'], 
            sample_bloomberg['QualityB']
        )
        
        self.assertIn('status', bloomberg_result)
        self.assertIn('deviation', bloomberg_result)
        self.assertIn(bloomberg_result['status'], ['VALIDATED', 'REVIEW_REQUIRED', 'MANUAL_OVERRIDE_NEEDED'])
    
    def test_error_handling_integration(self):
        """Test error handling across integrated components"""
        # Test with incomplete data
        incomplete_data = {
            'Cusip': '123456789',
            'Currency': 'USD'
            # Missing many required fields
        }
        
        result = self.rating_engine.calculate_rating(incomplete_data)
        
        # Should handle gracefully
        self.assertIsInstance(result, dict)
        if 'error' in result:
            self.assertIsInstance(result['error'], str)
            self.assertGreater(len(result['error']), 0)
        
        # Test with invalid data types
        invalid_data = {
            'Cusip': 123456789,  # Should be string
            'Currency': 'USD',
            'QualityB': 'AA',
            'OutstandE': 'invalid',  # Should be numeric
            'Maturity': 'five'  # Should be numeric
        }
        
        result = self.rating_engine.calculate_rating(invalid_data)
        self.assertIsInstance(result, dict)  # Should not crash
    
    def test_performance_integration(self):
        """Test integrated system performance"""
        import time
        
        # Test with moderate dataset
        self.bloomberg_connector.connect()
        test_data = self.bloomberg_connector._generate_mock_bloomberg_data(50)
        
        start_time = time.time()
        
        # Process ratings
        successful_ratings = 0
        for _, security in test_data.iterrows():
            bond_data = security.to_dict()
            result = self.rating_engine.calculate_rating(bond_data)
            
            if 'error' not in result:
                successful_ratings += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        self.assertLess(processing_time, 10.0)  # Should process 50 securities in under 10 seconds
        self.assertGreaterEqual(successful_ratings, 40)  # Should have at least 80% success rate
        
        # Calculate throughput
        throughput = successful_ratings / processing_time
        self.assertGreater(throughput, 5)  # Should process at least 5 ratings per second


if __name__ == '__main__':
    unittest.main()