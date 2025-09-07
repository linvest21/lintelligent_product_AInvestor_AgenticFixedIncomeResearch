"""
End-to-End Integration Tests for LINVEST21 Credit Rating System
JIRA: AINV-711

Tests the complete rating workflow from Bloomberg data ingestion 
through final rating calculation and validation.
"""

import pytest
import pandas as pd
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework
from src.models.database_models import Base, CreditRating, BloombergData


class TestEndToEndRating:
    """Integration tests for complete rating workflow"""
    
    @pytest.fixture(scope="class")
    def test_database(self):
        """Create in-memory test database"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture(scope="class")
    def test_session(self, test_database):
        """Create database session"""
        Session = sessionmaker(bind=test_database)
        return Session()
    
    @pytest.fixture
    def rating_engine(self):
        """Create rating engine instance"""
        return LINVEST21RatingEngine()
    
    @pytest.fixture
    def bloomberg_connector(self):
        """Create Bloomberg connector instance"""
        return BloombergConnector()
    
    @pytest.fixture
    def validation_framework(self):
        """Create validation framework instance"""
        return ValidationFramework()
    
    def test_complete_rating_workflow(self, rating_engine, bloomberg_connector, validation_framework):
        """Test complete rating workflow from data extraction to validation"""
        # Step 1: Extract mock Bloomberg data
        bloomberg_connector.connect()
        bloomberg_data = bloomberg_connector._generate_mock_bloomberg_data(10)
        
        # Step 2: Apply universe filters
        filtered_data = bloomberg_connector._apply_universe_filter(bloomberg_data, {
            'Currency': ['USD'],
            'QualityB_exclude': ['NR', 'D'],
            'OutstandE_min': 300000000,
            'Maturity_min': 1.0
        })
        
        assert len(filtered_data) > 0
        assert all(filtered_data['Currency'] == 'USD')
        
        # Step 3: Calculate ratings for filtered securities
        rating_results = []
        for _, security in filtered_data.head(3).iterrows():  # Test with 3 securities
            bond_data = security.to_dict()
            rating_result = rating_engine.calculate_rating(bond_data)
            
            if 'error' not in rating_result:
                rating_results.append({
                    'cusip': security['Cusip'],
                    **rating_result
                })
        
        assert len(rating_results) > 0
        
        # Step 4: Validate ratings
        for result in rating_results:
            assert 'final_score' in result
            assert 'linvest21_rating' in result
            assert result['linvest21_rating'].startswith('LIN-')
            assert 0 <= result['final_score'] <= 120  # Reasonable score range
        
        # Step 5: Test validation framework
        if len(rating_results) > 0:
            sample_rating = rating_results[0]
            sample_bloomberg = filtered_data[filtered_data['Cusip'] == sample_rating['cusip']].iloc[0].to_dict()
            
            validation_result = validation_framework.validate_rating(sample_rating, sample_bloomberg)
            
            assert 'overall_status' in validation_result
            assert validation_result['overall_status'] in ['PASSED', 'REVIEW_REQUIRED', 'FAILED']
    
    def test_bloomberg_data_quality_validation(self, bloomberg_connector):
        """Test Bloomberg data quality validation"""
        bloomberg_connector.connect()
        
        # Generate test data
        test_data = bloomberg_connector._generate_mock_bloomberg_data(100)
        
        # Validate data quality
        validation_report = bloomberg_connector.validate_data_quality(test_data)
        
        assert 'total_securities' in validation_report
        assert validation_report['total_securities'] == 100
        assert 'overall_coverage' in validation_report
        assert validation_report['overall_coverage'] >= 0.8  # Should have good coverage
        assert 'field_completeness' in validation_report
        
        # Test data should meet minimum coverage requirements
        if validation_report['overall_coverage'] >= 0.95:
            assert validation_report['meets_minimum_coverage'] is True
    
    def test_rating_calculation_consistency(self, rating_engine):
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
            result = rating_engine.calculate_rating(test_bond.copy())
            results.append(result)
        
        # Verify consistency
        first_result = results[0]
        if 'error' not in first_result:
            for result in results[1:]:
                assert result['final_score'] == first_result['final_score']
                assert result['linvest21_rating'] == first_result['linvest21_rating']
                assert result['quantitative_score'] == first_result['quantitative_score']
    
    def test_rating_component_weights(self, rating_engine):
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
            result = rating_engine.calculate_rating(security)
            
            if 'error' not in result:
                # Verify component weight limits per specification
                assert 0 <= result['quantitative_score'] <= 40  # 40% max
                assert 0 <= result['sector_score'] <= 25       # 25% max  
                assert 0 <= result['agency_score'] <= 35       # 35% max
                assert 0 <= result['alpha_score'] <= 15        # 15% max
                
                # Verify total makes sense
                total_components = (
                    result['quantitative_score'] + 
                    result['sector_score'] + 
                    result['agency_score'] + 
                    result['alpha_score']
                )
                assert abs(result['final_score'] - total_components) < 0.1
    
    def test_database_storage_retrieval(self, test_session, rating_engine):
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
        test_session.add(test_rating)
        test_session.commit()
        
        # Retrieve and verify
        retrieved_rating = test_session.query(CreditRating).filter_by(cusip='123456789').first()
        
        assert retrieved_rating is not None
        assert retrieved_rating.cusip == '123456789'
        assert retrieved_rating.final_score == 92.5
        assert retrieved_rating.linvest21_rating == 'LIN-AA'
        assert retrieved_rating.created_timestamp is not None
        
        # Test to_dict method
        rating_dict = retrieved_rating.to_dict()
        assert isinstance(rating_dict, dict)
        assert 'cusip' in rating_dict
        assert 'components' in rating_dict
        assert 'quantitative_score' in rating_dict['components']
    
    def test_bloomberg_connector_integration(self, bloomberg_connector):
        """Test Bloomberg connector integration functionality"""
        # Test connection
        assert bloomberg_connector.connect() is True
        assert bloomberg_connector.is_connected is True
        
        # Test data extraction
        universe_data = bloomberg_connector.extract_global_aggregate_data()
        
        assert isinstance(universe_data, pd.DataFrame)
        assert len(universe_data) > 0
        
        # Verify required fields are present
        required_fields = ['Cusip', 'Currency', 'QualityB', 'OutstandE', 'Maturity']
        for field in required_fields:
            assert field in universe_data.columns
        
        # Test specific security data retrieval
        sample_cusips = universe_data['Cusip'].head(3).tolist()
        security_data = bloomberg_connector.get_security_data(sample_cusips, 'CUSIP')
        
        # Note: Mock implementation may not return exact matches
        assert isinstance(security_data, pd.DataFrame)
        
        # Test disconnection
        bloomberg_connector.disconnect()
        assert bloomberg_connector.is_connected is False
    
    def test_validation_framework_integration(self, validation_framework):
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
        
        validation_result = validation_framework.validate_rating(sample_rating, sample_bloomberg)
        
        assert isinstance(validation_result, dict)
        assert 'overall_status' in validation_result
        assert 'bloomberg_consistency' in validation_result
        assert 'validation_metrics' in validation_result
        
        # Test Bloomberg consistency
        bloomberg_result = validation_framework.validate_bloomberg_consistency(
            sample_rating['final_score'], 
            sample_bloomberg['QualityB']
        )
        
        assert 'status' in bloomberg_result
        assert 'score_difference' in bloomberg_result
        assert bloomberg_result['status'] in ['VALIDATED', 'REVIEW_REQUIRED', 'MANUAL_OVERRIDE_NEEDED']
    
    def test_error_handling_integration(self, rating_engine):
        """Test error handling across integrated components"""
        # Test with incomplete data
        incomplete_data = {
            'Cusip': '123456789',
            'Currency': 'USD'
            # Missing many required fields
        }
        
        result = rating_engine.calculate_rating(incomplete_data)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        if 'error' in result:
            assert isinstance(result['error'], str)
            assert len(result['error']) > 0
        
        # Test with invalid data types
        invalid_data = {
            'Cusip': 123456789,  # Should be string
            'Currency': 'USD',
            'QualityB': 'AA',
            'OutstandE': 'invalid',  # Should be numeric
            'Maturity': 'five'  # Should be numeric
        }
        
        result = rating_engine.calculate_rating(invalid_data)
        assert isinstance(result, dict)  # Should not crash
    
    def test_performance_integration(self, rating_engine, bloomberg_connector):
        """Test integrated system performance"""
        import time
        
        # Test with moderate dataset
        bloomberg_connector.connect()
        test_data = bloomberg_connector._generate_mock_bloomberg_data(50)
        
        start_time = time.time()
        
        # Process ratings
        successful_ratings = 0
        for _, security in test_data.iterrows():
            bond_data = security.to_dict()
            result = rating_engine.calculate_rating(bond_data)
            
            if 'error' not in result:
                successful_ratings += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 10.0  # Should process 50 securities in under 10 seconds
        assert successful_ratings >= 40  # Should have at least 80% success rate
        
        # Calculate throughput
        throughput = successful_ratings / processing_time
        assert throughput > 5  # Should process at least 5 ratings per second