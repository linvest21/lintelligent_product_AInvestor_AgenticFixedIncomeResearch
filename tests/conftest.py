"""
Test Configuration for LINVEST21 Credit Rating System
JIRA: AINV-711

Provides pytest fixtures and configuration for comprehensive testing.
"""

import sys
import os
# Add project root to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework
from src.models.database_models import Base, CreditRating, BloombergData, ValidationResult, ProcessingLog
from src.etl.daily_pipeline import DailyETLPipeline
from src.api.main import app, get_db


@pytest.fixture(scope="session")
def test_database_engine():
    """Create test database engine with in-memory SQLite"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_db_session(test_database_engine):
    """Create test database session with rollback after each test"""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_database_engine)
    session = TestSessionLocal()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def test_api_client(test_db_session):
    """Create FastAPI test client with test database"""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def rating_engine():
    """Create LINVEST21RatingEngine instance"""
    return LINVEST21RatingEngine()


@pytest.fixture
def bloomberg_connector():
    """Create BloombergConnector instance"""
    return BloombergConnector()


@pytest.fixture
def validation_framework():
    """Create ValidationFramework instance"""
    return ValidationFramework()


@pytest.fixture
def daily_pipeline(test_db_session):
    """Create DailyETLPipeline instance with test database"""
    engine = test_db_session.get_bind()
    # Extract the database URL from the engine
    database_url = str(engine.url)
    pipeline = DailyETLPipeline(database_url)
    # Ensure the tables exist on the pipeline's engine too
    Base.metadata.create_all(pipeline.engine)
    return pipeline


@pytest.fixture
def sample_bloomberg_data():
    """Generate sample Bloomberg data for testing"""
    return pd.DataFrame({
        'Cusip': ['123456789', '987654321', '456789123'],
        'ISIN': ['US1234567890', 'US9876543210', 'US4567891230'],
        'Currency': ['USD', 'USD', 'USD'],
        'QualityB': ['AA', 'BBB+', 'A-'],
        'QualityE': ['AA-', 'BBB', 'A-'],
        'OutstandE': [500000000, 1000000000, 750000000],
        'Maturity': [5.5, 10.2, 3.1],
        'MrktValue': [505000000, 1020000000, 740000000],
        'MrkValBeg': [500000000, 1000000000, 750000000],
        'ISMA_MDur': [4.2, 8.5, 2.8],
        'OAS_bp': [85, 150, 110],
        'DurAdjMod': [4.1, 8.3, 2.7],
        'ConvAdj': [12.5, 45.2, 8.3],
        'IssrClsL1': ['Corporate-Financial', 'Corporate-Industrial', 'Corporate-Utility'],
        'IssrClsL2': ['Corporate', 'Corporate', 'Corporate'],
        'Sector': ['Financial', 'Industrial', 'Utility'],
        'Country': ['US', 'US', 'US'],
        'Issuer': ['Bank Corp', 'Manufacturing Inc', 'Power Company'],
        'RetTotal': [0.045, 0.032, 0.038],
        'RetPrice': [0.040, 0.028, 0.035],
        'RetCurncy': [0.005, 0.004, 0.003],
        'ProductCurrency': ['USD', 'USD', 'USD'],
        'YldWorstE': [0.042, 0.055, 0.048]
    })


@pytest.fixture
def sample_bond_data():
    """Generate sample individual bond data for rating calculation"""
    return {
        'Cusip': '123456789',
        'ISIN': 'US1234567890',
        'Currency': 'USD',
        'QualityB': 'AA',
        'QualityE': 'AA-',
        'OutstandE': 500000000,
        'Maturity': 5.5,
        'MrktValue': 505000000,
        'MrkValBeg': 500000000,
        'ISMA_MDur': 4.2,
        'OAS_bp': 85,
        'DurAdjMod': 4.1,
        'ConvAdj': 12.5,
        'IssrClsL1': 'Corporate-Financial',
        'IssrClsL2': 'Corporate',
        'Sector': 'Financial',
        'Country': 'US',
        'Issuer': 'Bank Corp',
        'RetTotal': 0.045,
        'RetPrice': 0.040,
        'RetCurncy': 0.005,
        'ProductCurrency': 'USD',
        'YldWorstE': 0.042
    }


@pytest.fixture
def sample_rating_calculations():
    """Generate expected rating calculations for validation"""
    return {
        'quantitative_score': 32.5,
        'sector_score': 22.0,
        'agency_score': 30.5,
        'alpha_score': 12.8,
        'final_score': 97.8,
        'linvest21_rating': 'LIN-AA+',
        'validation_status': 'VALIDATED'
    }


@pytest.fixture
def mock_credit_ratings(test_db_session):
    """Create mock credit ratings in test database"""
    ratings = [
        CreditRating(
            cusip='123456789',
            isin='US1234567890',
            calculation_date=date.today(),
            issuer='Bank Corp',
            ticker='BANK',
            currency='USD',
            quantitative_score=32.5,
            duration_component=12.0,
            spread_component=15.0,
            liquidity_component=5.5,
            sector_score=22.0,
            agency_score=30.5,
            alpha_score=12.8,
            final_score=97.8,
            linvest21_rating='LIN-AA+',
            validation_status='VALIDATED',
            bloomberg_deviation=8.5,
            peer_z_score=0.25
        ),
        CreditRating(
            cusip='987654321',
            isin='US9876543210',
            calculation_date=date.today(),
            issuer='Manufacturing Inc',
            ticker='MANU',
            currency='USD',
            quantitative_score=28.0,
            duration_component=10.5,
            spread_component=12.5,
            liquidity_component=5.0,
            sector_score=18.5,
            agency_score=25.0,
            alpha_score=10.2,
            final_score=81.7,
            linvest21_rating='LIN-A+',
            validation_status='VALIDATED',
            bloomberg_deviation=12.3,
            peer_z_score=-0.15
        )
    ]
    
    for rating in ratings:
        test_db_session.add(rating)
    test_db_session.commit()
    
    return ratings


@pytest.fixture
def edge_case_bond_data():
    """Generate edge case bond data for boundary testing"""
    return [
        # Minimum values
        {
            'Cusip': '000000001',
            'Currency': 'USD',
            'QualityB': 'CCC',
            'OutstandE': 300000000,  # Minimum threshold
            'Maturity': 1.0,  # Minimum threshold
            'MrktValue': 300000000,
            'MrkValBeg': 300000000,
            'ISMA_MDur': 0.5,
            'OAS_bp': 2000,  # Very high spread
            'IssrClsL1': 'Corporate-Industrial',
            'Sector': 'Industrial',
            'RetTotal': -0.50,  # Negative return
            'RetCurncy': 0.01,
        },
        # Maximum values  
        {
            'Cusip': '999999999',
            'Currency': 'USD',
            'QualityB': 'AAA',
            'OutstandE': 50000000000,  # Very large
            'Maturity': 30.0,  # Long maturity
            'MrktValue': 50000000000,
            'MrkValBeg': 50000000000,
            'ISMA_MDur': 25.0,  # High duration
            'OAS_bp': 10,  # Very low spread
            'IssrClsL1': 'Government',
            'Sector': 'Government',
            'RetTotal': 0.20,  # High return
            'RetCurncy': -0.02,
        },
        # Null/Missing values
        {
            'Cusip': '555555555',
            'Currency': 'USD',
            'QualityB': None,
            'OutstandE': None,
            'Maturity': 5.0,
            'MrktValue': 1000000000,
            'ISMA_MDur': None,
            'OAS_bp': None,
            'IssrClsL1': None,
            'Sector': 'Unknown',
            'RetTotal': None,
        }
    ]


@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing"""
    np.random.seed(42)
    n = 1000
    
    cusips = [f"{i:09d}" for i in range(100000000, 100000000 + n)]
    
    return pd.DataFrame({
        'Cusip': cusips,
        'Currency': np.random.choice(['USD'], n),
        'QualityB': np.random.choice(['AAA', 'AA', 'A', 'BBB', 'BB'], n),
        'OutstandE': np.random.lognormal(20, 1, n) * 1000000,
        'Maturity': np.random.exponential(5, n) + 1,
        'MrktValue': np.random.lognormal(18, 1, n) * 1000000,
        'MrkValBeg': np.random.lognormal(18, 1, n) * 1000000,
        'ISMA_MDur': np.random.gamma(2, 3, n),
        'OAS_bp': np.random.gamma(2, 50, n),
        'IssrClsL1': np.random.choice(['Corporate-Financial', 'Corporate-Industrial'], n),
        'Sector': np.random.choice(['Financial', 'Industrial'], n),
        'RetTotal': np.random.normal(0.05, 0.1, n),
        'RetCurncy': np.random.normal(0, 0.02, n)
    })