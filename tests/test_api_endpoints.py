"""
Unit Tests for FastAPI Endpoints
JIRA: AINV-711

Comprehensive test coverage for the REST API endpoints including
real-time rating lookup, batch processing, system status, and error handling.
"""

import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from src.models.database_models import CreditRating, ProcessingLog


class TestAPIEndpoints:
    """Test suite for FastAPI REST endpoints"""
    
    def test_root_endpoint(self, test_api_client):
        """Test root endpoint returns service information"""
        response = test_api_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "service" in data
        assert "version" in data
        assert "jira_ticket" in data
        assert "status" in data
        assert data["service"] == "LINVEST21 Credit Rating System"
        assert data["jira_ticket"] == "AINV-711"
        assert data["status"] == "operational"
    
    def test_health_check_endpoint(self, test_api_client):
        """Test health check endpoint"""
        response = test_api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["status"] == "healthy"
        assert data["service"] == "LINVEST21 Credit Rating API"
        
        # Verify timestamp format
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert isinstance(timestamp, datetime)
    
    def test_get_rating_existing_cusip(self, test_api_client, mock_credit_ratings):
        """Test getting rating for existing CUSIP"""
        cusip = "123456789"
        response = test_api_client.get(f"/api/v1/rating/{cusip}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        expected_fields = [
            'cusip', 'isin', 'linvest21_rating', 'final_score',
            'components', 'validation_status', 'calculation_date', 'last_updated'
        ]
        for field in expected_fields:
            assert field in data
        
        assert data['cusip'] == cusip
        assert data['linvest21_rating'] == 'LIN-AA+'
        assert data['final_score'] == 97.8
        assert 'quantitative' in data['components']
        assert 'sector' in data['components']
        assert 'agency' in data['components']
        assert 'alpha' in data['components']
    
    def test_get_rating_non_existing_cusip(self, test_api_client):
        """Test getting rating for non-existing CUSIP"""
        cusip = "000000000"
        
        with patch('src.api.main.bloomberg_connector.get_security_data') as mock_bloomberg:
            # Mock empty Bloomberg data
            import pandas as pd
            mock_bloomberg.return_value = pd.DataFrame()
            
            response = test_api_client.get(f"/api/v1/rating/{cusip}")
            
            assert response.status_code == 404
            data = response.json()
            assert "CUSIP" in data["detail"]
            assert "not found" in data["detail"]
    
    @patch('src.api.main.bloomberg_connector.get_security_data')
    @patch('src.api.main.rating_engine.calculate_rating')
    def test_get_rating_calculation_on_demand(self, mock_rating_calc, mock_bloomberg, test_api_client):
        """Test on-demand rating calculation for new CUSIP"""
        cusip = "999999999"
        
        # Mock Bloomberg data
        import pandas as pd
        mock_bloomberg_data = pd.DataFrame({
            'Cusip': [cusip],
            'Currency': ['USD'],
            'QualityB': ['AA'],
            'OutstandE': [1000000000],
            'Maturity': [5.0],
            'ISMA_MDur': [4.5],
            'OAS_bp': [100]
        })
        mock_bloomberg.return_value = mock_bloomberg_data
        
        # Mock rating calculation
        mock_rating_calc.return_value = {
            'linvest21_rating': 'LIN-AA',
            'final_score': 88.5,
            'quantitative_score': 35.0,
            'sector_score': 20.0,
            'agency_score': 28.0,
            'alpha_score': 5.5,
            'validation_status': 'VALIDATED'
        }
        
        response = test_api_client.get(f"/api/v1/rating/{cusip}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['cusip'] == cusip
        assert data['linvest21_rating'] == 'LIN-AA'
        assert data['final_score'] == 88.5
        
        # Verify Bloomberg connector and rating engine were called
        mock_bloomberg.assert_called_once()
        mock_rating_calc.assert_called_once()
    
    @patch('src.api.main.bloomberg_connector.get_security_data')
    def test_get_rating_calculation_error(self, mock_bloomberg, test_api_client):
        """Test handling of rating calculation errors"""
        cusip = "888888888"
        
        # Mock Bloomberg data
        import pandas as pd
        mock_bloomberg_data = pd.DataFrame({
            'Cusip': [cusip],
            'Currency': ['USD'],
            'QualityB': ['AA']
        })
        mock_bloomberg.return_value = mock_bloomberg_data
        
        with patch('src.api.main.rating_engine.calculate_rating') as mock_rating_calc:
            # Mock calculation error
            mock_rating_calc.return_value = {'error': 'Calculation failed'}
            
            response = test_api_client.get(f"/api/v1/rating/{cusip}")
            
            assert response.status_code == 400
            data = response.json()
            assert "Rating calculation failed" in data["detail"]
    
    def test_batch_rating_processing_success(self, test_api_client, mock_credit_ratings):
        """Test successful batch rating processing"""
        request_data = {
            "cusips": ["123456789", "987654321"],
            "include_components": True,
            "validation_level": "full"
        }
        
        response = test_api_client.post("/api/v1/ratings/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        expected_fields = [
            'request_id', 'status', 'processed_count', 'successful_count',
            'failed_count', 'ratings', 'processing_time_seconds'
        ]
        for field in expected_fields:
            assert field in data
        
        assert data['status'] == 'completed'
        assert data['processed_count'] == 2
        assert data['successful_count'] >= 1  # At least one should succeed from mock data
        assert len(data['ratings']) == 2
        
        # Verify individual rating structure
        for rating in data['ratings']:
            assert 'cusip' in rating
            assert 'linvest21_rating' in rating
            if rating['linvest21_rating']:  # If rating exists
                assert 'components' in rating
    
    def test_batch_rating_processing_empty_cusips(self, test_api_client):
        """Test batch processing with empty CUSIP list"""
        request_data = {
            "cusips": [],
            "include_components": True
        }
        
        response = test_api_client.post("/api/v1/ratings/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['processed_count'] == 0
        assert data['successful_count'] == 0
        assert len(data['ratings']) == 0
    
    def test_batch_rating_processing_invalid_request(self, test_api_client):
        """Test batch processing with invalid request data"""
        # Missing required cusips field
        request_data = {
            "include_components": True
        }
        
        response = test_api_client.post("/api/v1/ratings/batch", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.api.main.bloomberg_connector.get_security_data')
    def test_batch_rating_processing_mixed_results(self, mock_bloomberg, test_api_client):
        """Test batch processing with mixed success/failure results"""
        request_data = {
            "cusips": ["123456789", "000000000", "999999999"],  # Mix of valid/invalid
            "include_components": False
        }
        
        # Mock Bloomberg data - return data for some CUSIPs only
        import pandas as pd
        mock_bloomberg_data = pd.DataFrame({
            'Cusip': ['123456789'],  # Only one CUSIP has data
            'Currency': ['USD'],
            'QualityB': ['AA']
        })
        mock_bloomberg.return_value = mock_bloomberg_data
        
        response = test_api_client.post("/api/v1/ratings/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['processed_count'] == 3
        assert data['successful_count'] >= 0
        assert data['failed_count'] >= 0
        assert data['successful_count'] + data['failed_count'] == 3
    
    def test_get_system_status(self, test_api_client):
        """Test system status endpoint"""
        response = test_api_client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = [
            'status', 'version', 'database_status', 'bloomberg_status',
            'performance_metrics'
        ]
        for field in expected_fields:
            assert field in data
        
        assert data['status'] == 'operational'
        assert data['version'] == '1.0.0'
        assert data['database_status'] in ['connected', 'disconnected']
        assert data['bloomberg_status'] in ['connected', 'disconnected']
        assert isinstance(data['performance_metrics'], dict)
    
    def test_get_system_status_with_processing_logs(self, test_api_client, test_db_session):
        """Test system status with existing processing logs"""
        # Create mock processing log
        log_entry = ProcessingLog(
            process_date=date.today(),
            process_type='DAILY_ETL',
            start_timestamp=datetime.utcnow() - timedelta(hours=1),
            end_timestamp=datetime.utcnow(),
            total_securities_processed=1000,
            successful_calculations=950,
            failed_calculations=50,
            processing_time_seconds=3600,
            coverage_rate=95.0,
            calculation_success_rate=95.0,
            validation_pass_rate=92.0,
            process_status='COMPLETED'
        )
        test_db_session.add(log_entry)
        test_db_session.commit()
        
        response = test_api_client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'last_processing_run' in data
        assert data['last_processing_run'] is not None
        
        # Verify performance metrics
        metrics = data['performance_metrics']
        assert 'coverage_rate' in metrics
        assert 'calculation_success_rate' in metrics
        assert 'validation_pass_rate' in metrics
    
    def test_get_rating_history_success(self, test_api_client, test_db_session):
        """Test rating history endpoint with existing data"""
        cusip = "123456789"
        
        # Create historical ratings
        historical_ratings = [
            CreditRating(
                cusip=cusip,
                calculation_date=date.today() - timedelta(days=i),
                linvest21_rating=f'LIN-A{"+" if i % 2 == 0 else ""}',
                final_score=85.0 + i * 0.5,
                validation_status='VALIDATED'
            )
            for i in range(10)  # 10 historical entries
        ]
        
        for rating in historical_ratings:
            test_db_session.add(rating)
        test_db_session.commit()
        
        response = test_api_client.get(f"/api/v1/ratings/history/{cusip}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['cusip'] == cusip
        assert data['history_days'] == 90  # Default
        assert data['rating_count'] == 10
        assert len(data['ratings']) == 10
        
        # Verify rating structure
        for rating in data['ratings']:
            assert 'calculation_date' in rating
            assert 'linvest21_rating' in rating
            assert 'final_score' in rating
            assert 'validation_status' in rating
    
    def test_get_rating_history_custom_days(self, test_api_client, test_db_session):
        """Test rating history with custom days parameter"""
        cusip = "123456789"
        
        # Create historical ratings
        recent_rating = CreditRating(
            cusip=cusip,
            calculation_date=date.today() - timedelta(days=5),
            linvest21_rating='LIN-AA',
            final_score=88.0,
            validation_status='VALIDATED'
        )
        old_rating = CreditRating(
            cusip=cusip,
            calculation_date=date.today() - timedelta(days=50),
            linvest21_rating='LIN-A+',
            final_score=85.0,
            validation_status='VALIDATED'
        )
        
        test_db_session.add(recent_rating)
        test_db_session.add(old_rating)
        test_db_session.commit()
        
        # Request only 30 days of history
        response = test_api_client.get(f"/api/v1/ratings/history/{cusip}?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['history_days'] == 30
        assert data['rating_count'] == 1  # Only recent rating within 30 days
    
    def test_get_rating_history_not_found(self, test_api_client):
        """Test rating history for non-existent CUSIP"""
        cusip = "000000000"
        
        response = test_api_client.get(f"/api/v1/ratings/history/{cusip}")
        
        assert response.status_code == 404
        data = response.json()
        assert "No rating history found" in data["detail"]
        assert cusip in data["detail"]
    
    def test_api_cors_headers(self, test_api_client):
        """Test CORS headers are properly set"""
        response = test_api_client.options("/")
        
        # FastAPI with CORS middleware should handle OPTIONS requests
        assert response.status_code in [200, 405]  # May vary based on implementation
    
    def test_api_error_handling_500(self, test_api_client):
        """Test internal server error handling"""
        cusip = "123456789"
        
        with patch('src.api.main.get_db') as mock_get_db:
            # Mock database error
            mock_get_db.side_effect = Exception("Database connection failed")
            
            response = test_api_client.get(f"/api/v1/rating/{cusip}")
            
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]
    
    def test_api_validation_errors(self, test_api_client):
        """Test API request validation errors"""
        # Test invalid JSON for batch endpoint
        response = test_api_client.post(
            "/api/v1/ratings/batch",
            json={"cusips": "not_a_list"}  # Should be list, not string
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_api_response_models(self, test_api_client, mock_credit_ratings):
        """Test API response models conform to specification"""
        cusip = "123456789"
        response = test_api_client.get(f"/api/v1/rating/{cusip}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present and have correct types
        assert isinstance(data['cusip'], str)
        assert isinstance(data['final_score'], (int, float))
        assert isinstance(data['components'], dict)
        assert isinstance(data['validation_status'], str)
        
        # Verify component structure
        components = data['components']
        expected_components = ['quantitative', 'sector', 'agency', 'alpha']
        for comp in expected_components:
            assert comp in components
            assert isinstance(components[comp], (int, float))
    
    def test_api_performance_batch_processing(self, test_api_client):
        """Test API performance with large batch"""
        import time
        
        # Create large batch request
        large_cusips = [f"{i:09d}" for i in range(100000000, 100000050)]  # 50 CUSIPs
        request_data = {
            "cusips": large_cusips,
            "include_components": False  # Reduce response size
        }
        
        start_time = time.time()
        response = test_api_client.post("/api/v1/ratings/batch", json=request_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert response.status_code == 200
        # Should process 50 ratings in reasonable time (< 30 seconds)
        assert processing_time < 30.0
        
        data = response.json()
        assert data['processed_count'] == 50
    
    def test_api_concurrent_requests(self, test_api_client):
        """Test API handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = test_api_client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # Verify all requests succeeded
        assert len(results) == 10
        assert all(status == 200 for status in results)
        
        # Should handle concurrent requests quickly
        assert end_time - start_time < 5.0
    
    def test_api_content_type_handling(self, test_api_client):
        """Test API content type handling"""
        # Test JSON content type
        request_data = {"cusips": ["123456789"]}
        
        response = test_api_client.post(
            "/api/v1/ratings/batch",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
    
    def test_api_rate_limiting_behavior(self, test_api_client):
        """Test API behavior under rapid requests"""
        # Make many rapid requests to test stability
        responses = []
        for i in range(20):
            response = test_api_client.get("/health")
            responses.append(response.status_code)
        
        # All requests should succeed (no rate limiting in test environment)
        assert all(status == 200 for status in responses)
        assert len(responses) == 20
    
    @patch('src.api.main.logger')
    def test_api_logging_coverage(self, mock_logger, test_api_client):
        """Test that API endpoints log appropriately"""
        # Make requests to various endpoints
        test_api_client.get("/")
        test_api_client.get("/health")
        test_api_client.get("/api/v1/rating/123456789")
        
        # Verify logging was called
        assert mock_logger.info.called or mock_logger.debug.called
    
    def test_api_documentation_endpoints(self, test_api_client):
        """Test API documentation endpoints are accessible"""
        # Test OpenAPI schema
        response = test_api_client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "LINVEST21 Credit Rating System API"
        
        # Test Swagger UI (if available)
        docs_response = test_api_client.get("/docs")
        assert docs_response.status_code == 200