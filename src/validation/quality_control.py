"""
Validation and Quality Control Framework
JIRA: AINV-711

Implements the comprehensive validation framework specified in the Confluence document
for quality control and rating validation.
"""

import statistics
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationFramework:
    """
    Comprehensive validation and quality control framework
    
    Implements all validation checkpoints specified in Step 7 of the
    Confluence specification:
    - Bloomberg baseline validation
    - Spread consistency checks
    - Peer group analysis
    """
    
    def __init__(self):
        """Initialize validation framework"""
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
        
        logger.info("Validation framework initialized")
    
    def validate_rating(self, rating_result: Dict[str, Any], 
                       bond_data: Dict[str, Any], 
                       peer_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Comprehensive rating validation
        
        Args:
            rating_result: Calculated rating result from LINVEST21RatingEngine
            bond_data: Original Bloomberg bond data
            peer_data: Optional peer group data for comparison
            
        Returns:
            Validation result dictionary
        """
        try:
            validation_result = {
                'cusip': bond_data.get('Cusip', 'UNKNOWN'),
                'validation_timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'PASSED',
                'validation_checks': {},
                'validation_scores': {},
                'recommendations': []
            }
            
            lin_score = rating_result.get('final_score')
            if lin_score is None:
                validation_result['overall_status'] = 'FAILED'
                validation_result['validation_checks']['score_available'] = 'FAILED'
                return validation_result
            
            # 7.1 Bloomberg Baseline Validation
            bloomberg_validation = self.validate_bloomberg_consistency(
                lin_score, bond_data.get('QualityB', '')
            )
            validation_result['validation_checks']['bloomberg_consistency'] = bloomberg_validation['status']
            validation_result['validation_scores']['bloomberg_deviation'] = bloomberg_validation['deviation']
            
            # 7.2 Spread Consistency Check
            spread_validation = self.validate_spread_correlation(
                lin_score, bond_data.get('OAS_bp', 0)
            )
            validation_result['validation_checks']['spread_consistency'] = spread_validation['status']
            validation_result['validation_scores']['spread_deviation'] = spread_validation['deviation']
            
            # 7.3 Peer Group Analysis (if peer data available)
            if peer_data:
                peer_validation = self.validate_peer_group(
                    lin_score, bond_data.get('Issuer', ''), 
                    bond_data.get('IssrClsL1', ''), peer_data
                )
                validation_result['validation_checks']['peer_group'] = peer_validation['status']
                validation_result['validation_scores']['peer_z_score'] = peer_validation['z_score']
            else:
                validation_result['validation_checks']['peer_group'] = 'SKIPPED'
                validation_result['validation_scores']['peer_z_score'] = None
            
            # Determine overall status
            failed_checks = [k for k, v in validation_result['validation_checks'].items() 
                           if v in ['FAILED', 'MANUAL_OVERRIDE_NEEDED', 'OUTLIER']]
            
            review_checks = [k for k, v in validation_result['validation_checks'].items() 
                           if v in ['REVIEW_REQUIRED', 'FLAG_FOR_REVIEW']]
            
            if failed_checks:
                validation_result['overall_status'] = 'FAILED'
                validation_result['recommendations'].append(
                    f"Manual review required for failed checks: {', '.join(failed_checks)}"
                )
            elif review_checks:
                validation_result['overall_status'] = 'REVIEW_REQUIRED'
                validation_result['recommendations'].append(
                    f"Review recommended for: {', '.join(review_checks)}"
                )
            
            logger.debug(f"Validation completed for {bond_data.get('Cusip')}: {validation_result['overall_status']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                'cusip': bond_data.get('Cusip', 'UNKNOWN'),
                'validation_timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'FAILED',
                'error': str(e),
                'validation_checks': {},
                'validation_scores': {},
                'recommendations': ['System error during validation - manual review required']
            }
    
    def validate_bloomberg_consistency(self, lin_score: float, bloomberg_quality: str) -> Dict[str, Any]:
        """
        7.1 Bloomberg Baseline Validation
        
        Validates LINVEST21 score against Bloomberg agency rating baseline
        per specification methodology.
        
        Args:
            lin_score: LINVEST21 calculated score
            bloomberg_quality: Bloomberg composite rating
            
        Returns:
            Validation result with status and deviation
        """
        try:
            bloomberg_numeric = self.agency_rating_scores.get(bloomberg_quality, 50)
            score_difference = abs(lin_score - bloomberg_numeric)
            
            if score_difference <= 15:
                status = "VALIDATED"
            elif score_difference <= 25:
                status = "REVIEW_REQUIRED"
            else:
                status = "MANUAL_OVERRIDE_NEEDED"
            
            return {
                'status': status,
                'deviation': score_difference,
                'bloomberg_numeric_score': bloomberg_numeric,
                'linvest21_score': lin_score,
                'bloomberg_rating': bloomberg_quality
            }
            
        except Exception as e:
            logger.error(f"Bloomberg validation failed: {str(e)}")
            return {
                'status': 'FAILED',
                'deviation': None,
                'error': str(e)
            }
    
    def validate_spread_correlation(self, lin_score: float, oas_spread: float) -> Dict[str, Any]:
        """
        7.2 Spread Consistency Check
        
        Validates that higher LINVEST21 scores correlate with lower spreads
        as expected from credit risk theory.
        
        Args:
            lin_score: LINVEST21 calculated score
            oas_spread: Option-Adjusted Spread in basis points
            
        Returns:
            Validation result with status and deviation
        """
        try:
            # Expected spread based on linear relationship: higher scores -> lower spreads
            expected_spread = 500 - (lin_score * 4)  # Rough linear relationship
            spread_deviation = abs(oas_spread - expected_spread)
            
            status = "PASS" if spread_deviation < 200 else "FLAG_FOR_REVIEW"
            
            return {
                'status': status,
                'deviation': spread_deviation,
                'expected_spread': expected_spread,
                'actual_spread': oas_spread,
                'correlation_check': 'PASS' if lin_score > 50 and oas_spread < 300 else 'REVIEW'
            }
            
        except Exception as e:
            logger.error(f"Spread validation failed: {str(e)}")
            return {
                'status': 'FAILED',
                'deviation': None,
                'error': str(e)
            }
    
    def validate_peer_group(self, lin_score: float, issuer: str, sector: str, 
                          peer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        7.3 Peer Group Analysis
        
        Compares LINVEST21 score against peer group to identify outliers
        and ensure consistency within similar credit profiles.
        
        Args:
            lin_score: LINVEST21 calculated score
            issuer: Issuer name for peer matching
            sector: Sector for peer matching
            peer_data: List of peer rating data
            
        Returns:
            Validation result with z-score and status
        """
        try:
            peer_scores = self._get_peer_scores(issuer, sector, peer_data)
            
            if len(peer_scores) < 2:
                return {
                    'status': 'INSUFFICIENT_PEERS',
                    'z_score': None,
                    'peer_count': len(peer_scores),
                    'note': 'Not enough peer data for comparison'
                }
            
            peer_mean = statistics.mean(peer_scores)
            peer_std = statistics.stdev(peer_scores) if len(peer_scores) > 1 else 0
            
            if peer_std == 0:
                z_score = 0
            else:
                z_score = abs(lin_score - peer_mean) / peer_std
            
            status = "OUTLIER" if z_score > 2.0 else "WITHIN_RANGE"
            
            return {
                'status': status,
                'z_score': z_score,
                'peer_count': len(peer_scores),
                'peer_mean': peer_mean,
                'peer_std': peer_std,
                'linvest21_score': lin_score,
                'outlier_threshold': 2.0
            }
            
        except Exception as e:
            logger.error(f"Peer group validation failed: {str(e)}")
            return {
                'status': 'FAILED',
                'z_score': None,
                'error': str(e)
            }
    
    def _get_peer_scores(self, issuer: str, sector: str, 
                        peer_data: List[Dict[str, Any]]) -> List[float]:
        """
        Extract peer scores for comparison
        
        Args:
            issuer: Issuer name
            sector: Sector classification
            peer_data: List of peer data dictionaries
            
        Returns:
            List of peer scores for comparison
        """
        peer_scores = []
        
        for peer in peer_data:
            # Match by issuer first (strongest peer relationship)
            if peer.get('Issuer') == issuer and peer.get('final_score') is not None:
                peer_scores.append(peer['final_score'])
            # Then match by sector
            elif peer.get('IssrClsL1') == sector and peer.get('final_score') is not None:
                peer_scores.append(peer['final_score'])
        
        return peer_scores
    
    def batch_validate_ratings(self, rating_results: List[Dict[str, Any]], 
                              bond_data_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Validate multiple ratings in batch
        
        Args:
            rating_results: List of LINVEST21 rating results
            bond_data_list: List of corresponding Bloomberg bond data
            
        Returns:
            DataFrame with validation results
        """
        validation_results = []
        
        # Create peer dataset for peer group validation
        peer_data = []
        for i, result in enumerate(rating_results):
            if result.get('final_score') is not None:
                peer_data.append({
                    **bond_data_list[i],
                    'final_score': result['final_score']
                })
        
        for i, (rating_result, bond_data) in enumerate(zip(rating_results, bond_data_list)):
            try:
                validation_result = self.validate_rating(rating_result, bond_data, peer_data)
                validation_results.append(validation_result)
                
            except Exception as e:
                logger.error(f"Batch validation failed for item {i}: {str(e)}")
                validation_results.append({
                    'cusip': bond_data.get('Cusip', f'UNKNOWN_{i}'),
                    'overall_status': 'FAILED',
                    'error': str(e)
                })
        
        logger.info(f"Batch validation completed for {len(validation_results)} ratings")
        return pd.DataFrame(validation_results)
    
    def generate_quality_report(self, validation_results: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive quality control report
        
        Args:
            validation_results: DataFrame with validation results
            
        Returns:
            Quality report dictionary
        """
        try:
            total_ratings = len(validation_results)
            
            if total_ratings == 0:
                return {
                    'total_ratings': 0,
                    'error': 'No validation results provided'
                }
            
            # Status distribution
            status_counts = validation_results['overall_status'].value_counts()
            
            # Validation check performance
            check_performance = {}
            if 'validation_checks' in validation_results.columns:
                for check_type in ['bloomberg_consistency', 'spread_consistency', 'peer_group']:
                    check_values = []
                    for checks in validation_results['validation_checks'].dropna():
                        if isinstance(checks, dict) and check_type in checks:
                            check_values.append(checks[check_type])
                    
                    if check_values:
                        check_counts = pd.Series(check_values).value_counts()
                        check_performance[check_type] = check_counts.to_dict()
            
            # Score deviations analysis
            deviation_stats = {}
            if 'validation_scores' in validation_results.columns:
                for score_type in ['bloomberg_deviation', 'spread_deviation', 'peer_z_score']:
                    deviations = []
                    for scores in validation_results['validation_scores'].dropna():
                        if isinstance(scores, dict) and score_type in scores and scores[score_type] is not None:
                            deviations.append(scores[score_type])
                    
                    if deviations:
                        deviation_stats[score_type] = {
                            'mean': np.mean(deviations),
                            'median': np.median(deviations),
                            'std': np.std(deviations),
                            'min': np.min(deviations),
                            'max': np.max(deviations),
                            'count': len(deviations)
                        }
            
            # Quality thresholds per specification
            passed_count = status_counts.get('PASSED', 0)
            validation_pass_rate = passed_count / total_ratings
            
            quality_report = {
                'report_timestamp': datetime.utcnow().isoformat(),
                'total_ratings': total_ratings,
                'status_distribution': status_counts.to_dict(),
                'validation_pass_rate': validation_pass_rate,
                'meets_90_percent_threshold': validation_pass_rate >= 0.90,  # Per specification
                'check_performance': check_performance,
                'deviation_statistics': deviation_stats,
                'quality_flags': [],
                'recommendations': []
            }
            
            # Add quality flags and recommendations
            if validation_pass_rate < 0.90:
                quality_report['quality_flags'].append(
                    f"Validation pass rate {validation_pass_rate:.1%} below 90% threshold"
                )
                quality_report['recommendations'].append(
                    "Review model calibration and validation thresholds"
                )
            
            # Check for high deviation rates
            if 'bloomberg_deviation' in deviation_stats:
                avg_deviation = deviation_stats['bloomberg_deviation']['mean']
                if avg_deviation > 20:
                    quality_report['quality_flags'].append(
                        f"High average Bloomberg deviation: {avg_deviation:.1f} points"
                    )
                    quality_report['recommendations'].append(
                        "Review agency rating synthesis methodology"
                    )
            
            logger.info(f"Quality report generated: {validation_pass_rate:.1%} pass rate")
            return quality_report
            
        except Exception as e:
            logger.error(f"Quality report generation failed: {str(e)}")
            return {
                'error': str(e),
                'report_timestamp': datetime.utcnow().isoformat()
            }
    
    def validate_data_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data completeness against specification requirements
        
        Args:
            data: Bloomberg data to validate
            
        Returns:
            Data completeness validation report
        """
        required_fields = [
            'Currency', 'QualityB', 'OutstandE', 'Maturity', 'MrktValue',
            'ISMA_MDur', 'OAS_bp', 'IssrClsL1', 'RetTotal', 'MrkValBeg', 'RetCurncy'
        ]
        
        total_records = len(data)
        completeness_report = {
            'total_records': total_records,
            'field_completeness': {},
            'overall_completeness': 0,
            'meets_95_percent_threshold': False,
            'validation_timestamp': datetime.utcnow().isoformat()
        }
        
        if total_records == 0:
            return completeness_report
        
        field_completeness = []
        for field in required_fields:
            if field in data.columns:
                non_null_count = data[field].notna().sum()
                completeness_pct = non_null_count / total_records
                completeness_report['field_completeness'][field] = {
                    'completeness': completeness_pct,
                    'missing_count': total_records - non_null_count
                }
                field_completeness.append(completeness_pct)
            else:
                completeness_report['field_completeness'][field] = {
                    'completeness': 0.0,
                    'missing_count': total_records,
                    'note': 'Field not present in data'
                }
                field_completeness.append(0.0)
        
        overall_completeness = np.mean(field_completeness)
        completeness_report['overall_completeness'] = overall_completeness
        completeness_report['meets_95_percent_threshold'] = overall_completeness >= 0.95
        
        logger.info(f"Data completeness validation: {overall_completeness:.1%}")
        return completeness_report