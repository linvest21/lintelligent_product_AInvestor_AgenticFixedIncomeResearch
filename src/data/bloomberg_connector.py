"""
Bloomberg Global Aggregate Data Integration Pipeline
JIRA: AINV-711

Handles connection to Bloomberg API and data extraction for the
LINVEST21 proprietary credit rating framework.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, date, timezone
import time

# Note: blpapi would be imported in production environment
# import blpapi

logger = logging.getLogger(__name__)


class BloombergConnector:
    """
    Bloomberg data connector for Global Aggregate index data
    
    Handles authentication, data requests, and preprocessing
    for the credit rating calculation pipeline.
    """
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8194):
        """
        Initialize Bloomberg connector
        
        Args:
            server_host: Bloomberg Terminal API server host
            server_port: Bloomberg Terminal API server port
        """
        self.server_host = server_host
        self.server_port = server_port
        self.session = None
        self.is_connected = False
        
        # Required Bloomberg fields per specification
        self.required_fields = [
            # Primary Fields
            'Currency',         # Security currency denomination
            'QualityB',        # Bloomberg beginning quality rating
            'OutstandE',       # Outstanding amount end of period
            'Maturity',        # Years to maturity
            'MrktValue',       # Current market value
            
            # Quantitative Risk Fields
            'ISMA_MDur',       # ISMA Modified Duration
            'OAS_bp',          # Option-Adjusted Spread in basis points
            
            # Sector Fields
            'IssrClsL1',       # Issuer Class Level 1
            'IssrClsL2',       # Issuer Class Level 2
            'Sector',          # Bloomberg sector classification
            'Country',         # Country of risk
            
            # Agency Rating Fields
            'QualityE',        # Bloomberg composite rating ending
            
            # Alpha Factor Fields
            'RetTotal',        # Total return
            'RetPrice',        # Price return
            'MrkValBeg',       # Market value beginning
            'RetCurncy',       # Currency return
            'ProductCurrency', # Product currency
            
            # Additional Fields for Validation
            'YldWorstE',       # Yield to worst end
            'DurAdjMod',       # Duration adjusted modified
            'ConvAdj',         # Convexity adjustment
            'Issuer',          # Issuer name for peer analysis
            'Cusip',           # CUSIP identifier
            'ISIN'             # ISIN identifier
        ]
        
        logger.info("Bloomberg connector initialized")
    
    def connect(self) -> bool:
        """
        Establish connection to Bloomberg Terminal API
        
        Returns:
            bool: True if connection successful
        """
        try:
            # In production, this would establish actual Bloomberg connection
            # session_options = blpapi.SessionOptions()
            # session_options.setServerHost(self.server_host)
            # session_options.setServerPort(self.server_port)
            # self.session = blpapi.Session(session_options)
            # 
            # if not self.session.start():
            #     logger.error("Failed to start Bloomberg session")
            #     return False
            # 
            # if not self.session.openService("//blp/refdata"):
            #     logger.error("Failed to open Bloomberg reference data service")
            #     return False
            
            # Mock connection for development
            self.session = "MOCK_SESSION"
            self.is_connected = True
            
            logger.info("Bloomberg connection established")
            return True
            
        except Exception as e:
            logger.error(f"Bloomberg connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from Bloomberg API"""
        if self.session and self.is_connected:
            # In production: self.session.stop()
            self.session = None
            self.is_connected = False
            logger.info("Bloomberg connection closed")
    
    def extract_global_aggregate_data(self, 
                                    universe_filter: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Extract Bloomberg Global Aggregate index data
        
        Args:
            universe_filter: Optional filter criteria for universe selection
            
        Returns:
            DataFrame with filtered Bloomberg data
        """
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Unable to connect to Bloomberg")
        
        logger.info("Extracting Bloomberg Global Aggregate data...")
        
        try:
            # In production, this would make actual Bloomberg API calls
            # For development, return mock data with realistic structure
            mock_data = self._generate_mock_bloomberg_data()
            
            # Apply universe filter
            if universe_filter:
                filtered_data = self._apply_universe_filter(mock_data, universe_filter)
            else:
                # Default filter per specification
                default_filter = {
                    'Currency': ['USD'],
                    'QualityB_exclude': ['NR', 'D', ''],
                    'OutstandE_min': 300000000,  # $300M minimum
                    'Maturity_min': 1.0          # 1 year minimum
                }
                filtered_data = self._apply_universe_filter(mock_data, default_filter)
            
            logger.info(f"Extracted {len(filtered_data)} securities from Bloomberg Global Aggregate")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Bloomberg data extraction failed: {str(e)}")
            raise
    
    def _apply_universe_filter(self, data: pd.DataFrame, 
                             filter_criteria: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply universe filtering logic per specification
        
        Args:
            data: Raw Bloomberg data
            filter_criteria: Filter criteria dictionary
            
        Returns:
            Filtered DataFrame
        """
        filtered_data = data.copy()
        
        # Apply currency filter
        if 'Currency' in filter_criteria:
            currencies = filter_criteria['Currency']
            filtered_data = filtered_data[filtered_data['Currency'].isin(currencies)]
            logger.debug(f"Currency filter applied: {len(filtered_data)} securities remain")
        
        # Exclude certain quality ratings
        if 'QualityB_exclude' in filter_criteria:
            exclude_ratings = filter_criteria['QualityB_exclude']
            filtered_data = filtered_data[~filtered_data['QualityB'].isin(exclude_ratings)]
            logger.debug(f"Quality exclusion filter applied: {len(filtered_data)} securities remain")
        
        # Minimum outstanding amount
        if 'OutstandE_min' in filter_criteria:
            min_outstanding = filter_criteria['OutstandE_min']
            filtered_data = filtered_data[filtered_data['OutstandE'] >= min_outstanding]
            logger.debug(f"Outstanding amount filter applied: {len(filtered_data)} securities remain")
        
        # Minimum maturity
        if 'Maturity_min' in filter_criteria:
            min_maturity = filter_criteria['Maturity_min']
            filtered_data = filtered_data[filtered_data['Maturity'] >= min_maturity]
            logger.debug(f"Maturity filter applied: {len(filtered_data)} securities remain")
        
        # Exclude securities with null market values
        filtered_data = filtered_data[filtered_data['MrktValue'].notna()]
        
        logger.info(f"Universe filtering complete: {len(filtered_data)} eligible securities")
        return filtered_data
    
    def _generate_mock_bloomberg_data(self, num_securities: int = 10000) -> pd.DataFrame:
        """
        Generate mock Bloomberg Global Aggregate data for development
        
        Args:
            num_securities: Number of mock securities to generate
            
        Returns:
            DataFrame with mock Bloomberg data structure
        """
        np.random.seed(42)  # For reproducible mock data
        
        # Generate base security identifiers
        cusips = [f"{np.random.randint(100000000, 999999999):09d}" for _ in range(num_securities)]
        isins = [f"US{cusip}0" for cusip in cusips]
        
        # Generate realistic Bloomberg field data
        data = {
            'Cusip': cusips,
            'ISIN': isins,
            'Currency': np.random.choice(['USD', 'EUR', 'JPY', 'GBP'], num_securities, p=[0.7, 0.15, 0.1, 0.05]),
            'QualityB': np.random.choice(['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'NR'], 
                                       num_securities, p=[0.05, 0.05, 0.1, 0.1, 0.15, 0.15, 0.15, 0.1, 0.05, 0.05, 0.02, 0.02, 0.01]),
            'QualityE': np.random.choice(['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB'], num_securities),
            
            # Outstanding amounts (in USD)
            'OutstandE': np.random.lognormal(mean=20, sigma=1.5, size=num_securities) * 1000000,
            
            # Maturity (years)
            'Maturity': np.random.exponential(scale=5, size=num_securities) + 1,
            
            # Market values
            'MrktValue': np.random.lognormal(mean=15, sigma=1, size=num_securities) * 1000000,
            'MrkValBeg': np.random.lognormal(mean=15, sigma=1, size=num_securities) * 1000000,
            
            # Duration and spread data
            'ISMA_MDur': np.random.gamma(shape=2, scale=3, size=num_securities),
            'OAS_bp': np.random.gamma(shape=2, scale=50, size=num_securities),
            'DurAdjMod': np.random.gamma(shape=2, scale=3, size=num_securities),
            
            # Sector classifications
            'IssrClsL1': np.random.choice(['Government', 'Government-Related', 'Agency', 'Corporate-Utility', 
                                         'Corporate-Industrial', 'Corporate-Financial', 'Securitized'], 
                                        num_securities, p=[0.15, 0.1, 0.1, 0.15, 0.2, 0.2, 0.1]),
            'IssrClsL2': np.random.choice(['Treasury', 'Municipal', 'Corporate', 'MBS', 'ABS'], num_securities),
            'Sector': np.random.choice(['Government', 'Financial', 'Industrial', 'Utility', 'Technology'], num_securities),
            'Country': np.random.choice(['US', 'Germany', 'Japan', 'UK', 'France'], num_securities, p=[0.7, 0.1, 0.1, 0.05, 0.05]),
            
            # Return data
            'RetTotal': np.random.normal(0.02, 0.1, num_securities),
            'RetPrice': np.random.normal(0.01, 0.08, num_securities),
            'RetCurncy': np.random.normal(0, 0.02, num_securities),
            
            # Additional fields
            'YldWorstE': np.random.gamma(shape=2, scale=0.02, size=num_securities),
            'ConvAdj': np.random.gamma(shape=1, scale=10, size=num_securities),
            'Issuer': [f"Issuer_{i//100}" for i in range(num_securities)],
            'ProductCurrency': ['USD'] * num_securities
        }
        
        df = pd.DataFrame(data)
        
        # Introduce some realistic correlations
        # Higher quality ratings -> lower spreads
        quality_map = {'AAA': 0.2, 'AA+': 0.3, 'AA': 0.4, 'AA-': 0.5, 'A+': 0.6, 'A': 0.7, 
                      'A-': 0.8, 'BBB+': 1.0, 'BBB': 1.2, 'BBB-': 1.5, 'BB+': 2.0, 'BB': 2.5, 'NR': 3.0}
        df['OAS_bp'] = df['OAS_bp'] * df['QualityB'].map(quality_map).fillna(1.0)
        
        # Longer duration -> higher spreads (generally)
        df['OAS_bp'] = df['OAS_bp'] + df['ISMA_MDur'] * 5
        
        logger.debug(f"Generated {len(df)} mock Bloomberg securities")
        return df
    
    def get_security_data(self, identifiers: List[str], 
                         identifier_type: str = "CUSIP") -> pd.DataFrame:
        """
        Get data for specific securities
        
        Args:
            identifiers: List of security identifiers
            identifier_type: Type of identifier (CUSIP, ISIN, etc.)
            
        Returns:
            DataFrame with security data
        """
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Unable to connect to Bloomberg")
        
        # In production, this would query specific securities
        # For development, filter mock data
        mock_data = self._generate_mock_bloomberg_data()
        
        if identifier_type.upper() == "CUSIP":
            filtered_data = mock_data[mock_data['Cusip'].isin(identifiers)]
        elif identifier_type.upper() == "ISIN":
            filtered_data = mock_data[mock_data['ISIN'].isin(identifiers)]
        else:
            raise ValueError(f"Unsupported identifier type: {identifier_type}")
        
        logger.info(f"Retrieved data for {len(filtered_data)} securities")
        return filtered_data
    
    def validate_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate Bloomberg data quality per specification thresholds
        
        Args:
            data: Bloomberg data to validate
            
        Returns:
            Validation report dictionary
        """
        total_securities = len(data)
        
        # Check field completeness
        completeness = {}
        for field in self.required_fields:
            if field in data.columns:
                non_null_count = data[field].notna().sum()
                completeness[field] = {
                    'coverage': non_null_count / total_securities,
                    'missing': total_securities - non_null_count
                }
        
        # Calculate overall coverage
        critical_fields = ['Currency', 'QualityB', 'OutstandE', 'Maturity', 'MrktValue', 
                          'ISMA_MDur', 'OAS_bp', 'IssrClsL1']
        critical_coverage = []
        for field in critical_fields:
            if field in completeness:
                critical_coverage.append(completeness[field]['coverage'])
            else:
                # Field not present in data at all = 0% coverage
                critical_coverage.append(0.0)
        
        overall_coverage = np.mean(critical_coverage) if critical_coverage else 0.0
        
        # Check data quality thresholds per specification
        validation_report = {
            'total_securities': total_securities,
            'overall_coverage': float(overall_coverage),
            'meets_minimum_coverage': bool(overall_coverage >= 0.95),  # 95% requirement
            'field_completeness': completeness,
            'data_quality_issues': [],
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Check for data quality issues
        if overall_coverage < 0.95:
            validation_report['data_quality_issues'].append(
                f"Overall coverage {overall_coverage:.1%} below 95% threshold"
            )
        
        # Check for outliers in key numerical fields
        numeric_fields = ['OutstandE', 'ISMA_MDur', 'OAS_bp', 'Maturity']
        for field in numeric_fields:
            if field in data.columns:
                field_data = data[field].dropna()
                if len(field_data) > 0:
                    # Use IQR method for outlier detection
                    q75 = field_data.quantile(0.75)
                    q25 = field_data.quantile(0.25)
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers = ((field_data < lower_bound) | (field_data > upper_bound)).sum()
                    outlier_rate = outliers / len(field_data)
                    
                    if outlier_rate > 0.02:  # More than 2% outliers
                        validation_report['data_quality_issues'].append(
                            f"{field}: {outlier_rate:.1%} outlier rate"
                        )
        
        logger.info(f"Data quality validation complete: {overall_coverage:.1%} coverage")
        return validation_report