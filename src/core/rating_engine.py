"""
LINVEST21 Proprietary Credit Rating Engine
JIRA: AINV-711

Implementation of the proprietary credit rating framework that leverages Bloomberg
Global Aggregate index data to create LINVEST21 credit ratings.

Methodology combines:
- Traditional agency ratings (35% weight)
- Quantitative market signals (40% weight) 
- Sector risk assessments (25% weight)
- Proprietary alpha factors (15% weight)
"""

import math
from typing import Dict, Any, Optional
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LINVEST21RatingEngine:
    """
    Core calculation engine for LINVEST21 proprietary credit ratings
    
    Processes Bloomberg Global Aggregate data to generate ratings on the
    LIN-AAA through LIN-CCC scale using multi-component methodology.
    """
    
    def __init__(self):
        """Initialize the rating engine with sector risk multipliers"""
        self.sector_risk_multipliers = {
            'Government': 0.50,
            'Government-Related': 0.65,
            'Agency': 0.70,
            'Corporate-Utility': 0.85,
            'Corporate-Industrial': 1.00,
            'Corporate-Financial': 1.15,
            'Securitized': 0.90
        }
        
        # Agency rating numeric mapping
        self.agency_rating_scores = {
            'Aaa': 95, 'AAA': 95,
            'Aa1': 90, 'AA+': 90,
            'Aa2': 87, 'AA': 87,
            'Aa3': 84, 'AA-': 84,
            'A1': 81, 'A+': 81,
            'A2': 78, 'A': 78,
            'A3': 75, 'A-': 75,
            'Baa1': 72, 'BBB+': 72,
            'Baa2': 68, 'BBB': 68,
            'Baa3': 65, 'BBB-': 65,
            'Ba1': 55, 'BB+': 55,
            'Ba2': 50, 'BB': 50,
            'Ba3': 45, 'BB-': 45,
            'B1': 35, 'B+': 35,
            'B2': 30, 'B': 30,
            'B3': 25, 'B-': 25,
            'Caa1': 15, 'CCC+': 15,
            'Caa2': 10, 'CCC': 10,
            'Caa3': 5, 'CCC-': 5
        }
        
        logger.info("LINVEST21 Rating Engine initialized")
    
    def calculate_rating(self, bond_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate LINVEST21 rating for a single bond
        
        Args:
            bond_data: Bloomberg bond data record containing required fields
            
        Returns:
            dict: Rating components and final score with validation status
        """
        try:
            # Validate required fields
            required_fields = [
                'ISMA_MDur', 'OAS_bp', 'OutstandE', 'IssrClsL1', 
                'QualityB', 'RetTotal', 'MrktValue', 'MrkValBeg', 'RetCurncy'
            ]
            
            missing_fields = [field for field in required_fields if field not in bond_data or bond_data[field] is None]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Step 2: Quantitative Score (40% Total Weight)
            duration_score = self._calculate_duration_score(bond_data['ISMA_MDur'])
            spread_score = self._calculate_spread_score(bond_data['OAS_bp'])
            liquidity_score = self._calculate_liquidity_score(bond_data['OutstandE'])
            
            quantitative_score = (
                duration_score * 0.15 +
                spread_score * 0.15 + 
                liquidity_score * 0.10
            )
            
            # Step 3: Sector Score (25% Total Weight)
            sector_score = self._calculate_sector_score(bond_data['IssrClsL1'])
            
            # Step 4: Agency Score (35% Total Weight)
            agency_score = self._calculate_agency_score(bond_data['QualityB'])
            
            # Step 5: Alpha Score (15% Total Weight)
            alpha_score = self._calculate_alpha_score(bond_data)
            
            # Final Aggregation
            final_score = quantitative_score + sector_score + agency_score + alpha_score
            final_score = max(0, min(100, final_score))
            
            # Convert to LINVEST21 rating
            linvest21_rating = self._score_to_rating(final_score)
            
            result = {
                'final_score': round(final_score, 2),
                'linvest21_rating': linvest21_rating,
                'quantitative_score': round(quantitative_score, 2),
                'sector_score': round(sector_score, 2),
                'agency_score': round(agency_score, 2),
                'alpha_score': round(alpha_score, 2),
                'components': {
                    'duration': round(duration_score, 2),
                    'spread': round(spread_score, 2),
                    'liquidity': round(liquidity_score, 2),
                    'momentum': round(self._calculate_momentum_score(bond_data['RetTotal']), 2),
                    'stability': round(self._calculate_stability_score(bond_data), 2),
                    'currency': round(self._calculate_currency_score(bond_data['RetCurncy']), 2)
                },
                'validation_status': 'CALCULATED',
                'calculation_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.debug(f"Rating calculated successfully: {linvest21_rating} (Score: {final_score})")
            return result
            
        except Exception as e:
            logger.error(f"Rating calculation failed: {str(e)}")
            return {
                'final_score': None,
                'linvest21_rating': None,
                'error': str(e),
                'validation_status': 'FAILED',
                'calculation_timestamp': datetime.utcnow().isoformat()
            }
    
    def _calculate_duration_score(self, isma_mdur: float) -> float:
        """
        Calculate duration risk score (15% weight)
        
        Args:
            isma_mdur: ISMA Modified Duration
            
        Returns:
            Duration risk score (0-100)
        """
        duration_risk_score = min(isma_mdur / 10.0, 1.0) * 100
        
        # Risk interpretation:
        # 0-2 years: Low risk (20-40 points)
        # 2-5 years: Moderate risk (40-60 points) 
        # 5-10 years: High risk (60-100 points)
        # 10+ years: Maximum risk (100 points)
        
        return duration_risk_score
    
    def _calculate_spread_score(self, oas_bp: float) -> float:
        """
        Calculate credit spread risk score (15% weight)
        
        Args:
            oas_bp: Option-Adjusted Spread in basis points
            
        Returns:
            Spread risk score (0-100)
        """
        spread_risk_score = min(oas_bp / 500.0, 1.0) * 100
        
        # Risk interpretation:
        # 0-50bp: Minimal spread risk (10-20 points)
        # 50-150bp: Moderate spread risk (20-40 points)
        # 150-300bp: Elevated spread risk (40-70 points)
        # 300-500bp: High spread risk (70-100 points)
        # 500bp+: Maximum spread risk (100 points)
        
        return spread_risk_score
    
    def _calculate_liquidity_score(self, outstand_e: float) -> float:
        """
        Calculate liquidity risk score (10% weight)
        
        Args:
            outstand_e: Outstanding amount end of period
            
        Returns:
            Liquidity risk score (0-100)
        """
        if outstand_e <= 0:
            return 100  # Maximum risk for zero/negative outstanding
            
        liquidity_risk_score = 100 - min(math.log10(outstand_e / 1000000) * 20, 80)
        
        # Risk interpretation:
        # $10B+: Excellent liquidity (20 points)
        # $1-10B: Good liquidity (40 points)
        # $500M-1B: Moderate liquidity (60 points)
        # $300-500M: Lower liquidity (80 points)
        
        return max(0, liquidity_risk_score)
    
    def _calculate_sector_score(self, issuer_class_l1: str) -> float:
        """
        Calculate sector risk score (25% weight)
        
        Args:
            issuer_class_l1: Issuer Class Level 1 from Bloomberg
            
        Returns:
            Sector risk score
        """
        base_score = 50  # Neutral baseline
        multiplier = self.sector_risk_multipliers.get(issuer_class_l1, 1.00)
        sector_score = base_score * multiplier * 0.25
        
        return sector_score
    
    def _calculate_agency_score(self, quality_b: str) -> float:
        """
        Calculate agency rating synthesis score (35% weight)
        
        Args:
            quality_b: Bloomberg composite rating beginning
            
        Returns:
            Agency score
        """
        numeric_score = self.agency_rating_scores.get(quality_b, 50)  # Default to neutral
        agency_score = numeric_score * 0.35
        
        return agency_score
    
    def _calculate_alpha_score(self, bond_data: Dict[str, Any]) -> float:
        """
        Calculate proprietary alpha factors score (15% weight)
        
        Args:
            bond_data: Bond data containing alpha factor fields
            
        Returns:
            Alpha score
        """
        # Component 5A: Price Momentum Score (5% Weight)
        momentum_score = self._calculate_momentum_score(bond_data['RetTotal'])
        
        # Component 5B: Market Value Stability (5% Weight)  
        stability_score = self._calculate_stability_score(bond_data)
        
        # Component 5C: Currency Risk Factor (5% Weight)
        currency_score = self._calculate_currency_score(bond_data['RetCurncy'])
        
        alpha_score = (momentum_score + stability_score + currency_score) * 0.05
        
        return alpha_score
    
    def _calculate_momentum_score(self, ret_total: float) -> float:
        """Calculate price momentum score"""
        momentum_score = 50 + (ret_total * 10)
        
        # Momentum bands:
        # Positive momentum (+5% returns): 100 points
        # Neutral (0% returns): 50 points
        # Negative momentum (-5% returns): 0 points
        
        return max(0, min(100, momentum_score))
    
    def _calculate_stability_score(self, bond_data: Dict[str, Any]) -> float:
        """Calculate market value stability score"""
        mrkt_value = bond_data['MrktValue']
        mrk_val_beg = bond_data['MrkValBeg']
        
        if mrk_val_beg == 0 or mrk_val_beg is None:
            return 50  # Neutral if no beginning value
            
        mv_change_pct = abs((mrkt_value - mrk_val_beg) / mrk_val_beg * 100)
        stability_score = 100 - min(mv_change_pct, 100)
        
        # Stability interpretation:
        # 0-2% change: High stability (96-100 points)
        # 2-5% change: Moderate stability (90-96 points)
        # 5-10% change: Lower stability (80-90 points)
        # 10%+ change: Volatile (0-80 points)
        
        return stability_score
    
    def _calculate_currency_score(self, ret_currency: float) -> float:
        """Calculate currency risk factor score"""
        currency_risk_score = 50 - abs(ret_currency * 20)
        currency_risk_score = max(0, min(100, currency_risk_score))
        
        # For USD base currency securities, RetCurncy should be minimal
        # Higher absolute currency returns indicate FX volatility risk
        
        return currency_risk_score
    
    def _score_to_rating(self, score: float) -> str:
        """
        Convert numeric score to LINVEST21 rating
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            LINVEST21 rating string
        """
        if score >= 95:
            return 'LIN-AAA'
        elif score >= 90:
            return 'LIN-AA+'
        elif score >= 87:
            return 'LIN-AA'
        elif score >= 84:
            return 'LIN-AA-'
        elif score >= 81:
            return 'LIN-A+'
        elif score >= 78:
            return 'LIN-A'
        elif score >= 75:
            return 'LIN-A-'
        elif score >= 72:
            return 'LIN-BBB+'
        elif score >= 68:
            return 'LIN-BBB'
        elif score >= 65:
            return 'LIN-BBB-'
        elif score >= 55:
            return 'LIN-BB+'
        elif score >= 50:
            return 'LIN-BB'
        elif score >= 45:
            return 'LIN-BB-'
        elif score >= 35:
            return 'LIN-B+'
        elif score >= 30:
            return 'LIN-B'
        elif score >= 25:
            return 'LIN-B-'
        elif score >= 15:
            return 'LIN-CCC+'
        elif score >= 10:
            return 'LIN-CCC'
        else:
            return 'LIN-CCC-'
    
    def batch_calculate_ratings(self, bond_data_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ratings for multiple bonds
        
        Args:
            bond_data_df: DataFrame with Bloomberg bond data
            
        Returns:
            DataFrame with calculated ratings and components
        """
        results = []
        
        for idx, bond in bond_data_df.iterrows():
            result = self.calculate_rating(bond.to_dict())
            result['cusip'] = bond.get('Cusip', f'UNKNOWN_{idx}')
            result['row_index'] = idx
            results.append(result)
        
        logger.info(f"Batch calculated ratings for {len(results)} securities")
        return pd.DataFrame(results)