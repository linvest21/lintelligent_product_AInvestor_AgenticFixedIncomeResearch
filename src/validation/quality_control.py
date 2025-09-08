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
from datetime import datetime, timezone
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
            'Caa3': 5, 'CCC-': 5,
            # Add missing ratings that tests expect
            'CC': 2, 'C': 1, 'D': 0, 'NR': 50
        }
        
        # Add spread thresholds that tests expect
        self.spread_thresholds = {
            'LIN-AAA': {'min': 10, 'max': 50},
            'LIN-AA+': {'min': 25, 'max': 75},
            'LIN-AA': {'min': 40, 'max': 100},
            'LIN-AA-': {'min': 55, 'max': 125},
            'LIN-A+': {'min': 70, 'max': 150},
            'LIN-A': {'min': 85, 'max': 175},
            'LIN-A-': {'min': 100, 'max': 200},
            'LIN-BBB+': {'min': 125, 'max': 250},
            'LIN-BBB': {'min': 150, 'max': 300},
            'LIN-BBB-': {'min': 175, 'max': 350},
            'LIN-BB+': {'min': 200, 'max': 400},
            'LIN-BB': {'min': 250, 'max': 500},
            'LIN-BB-': {'min': 300, 'max': 600},
            'LIN-B+': {'min': 400, 'max': 700},
            'LIN-B': {'min': 500, 'max': 800},
            'LIN-B-': {'min': 600, 'max': 900},
            'LIN-CCC+': {'min': 700, 'max': 1000},
            'LIN-CCC': {'min': 800, 'max': 1200},
            'LIN-CCC-': {'min': 900, 'max': 1500}
        }
        
        # Add Bloomberg deviation thresholds
        self._bloomberg_deviation_thresholds = {
            'validated_max': 15,
            'review_required_max': 25,
            'manual_override_threshold': 999
        }
        
        # Add peer group Z-score thresholds for statistical analysis
        self._peer_zscore_thresholds = {
            'excellent': 1.0,
            'good': 1.5,
            'acceptable': 2.0,
            'poor': 2.5,
            'outlier': 3.0,
            'outlier_threshold': 2.0  # Add for test compatibility
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
                'validation_timestamp': datetime.now(timezone.utc).isoformat(),
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
            bloomberg_validation = self.validate_bloomberg_consistency(rating_result, bond_data)
            validation_result['validation_checks']['bloomberg_consistency'] = bloomberg_validation['status']
            validation_result['validation_scores']['bloomberg_deviation'] = bloomberg_validation['deviation']
            # Add for test compatibility - expose at top level
            validation_result['bloomberg_consistency'] = bloomberg_validation
            # Add validation score
            validation_result['bloomberg_consistency']['validation_score'] = self._calculate_validation_score(bloomberg_validation)
            
            # 7.2 Spread Consistency Check
            spread_validation = self.validate_spread_correlation(rating_result, bond_data)
            validation_result['validation_checks']['spread_consistency'] = spread_validation['status']
            validation_result['validation_scores']['spread_deviation'] = spread_validation['deviation']
            # Add for test compatibility - expose at top level
            validation_result['spread_correlation'] = spread_validation
            # Add validation score  
            validation_result['spread_correlation']['validation_score'] = self._calculate_validation_score(spread_validation)
            
            # 7.3 Peer Group Analysis (if peer data available)
            if peer_data:
                peer_validation = self.validate_peer_group(
                    lin_score, bond_data.get('Issuer', ''), 
                    bond_data.get('IssrClsL1', ''), peer_data
                )
                validation_result['validation_checks']['peer_group'] = peer_validation['status']
                validation_result['validation_scores']['peer_z_score'] = peer_validation['z_score']
                # Add for test compatibility - expose at top level
                validation_result['peer_group_analysis'] = peer_validation
            else:
                validation_result['validation_checks']['peer_group'] = 'SKIPPED'
                validation_result['validation_scores']['peer_z_score'] = None
                # Add for test compatibility - expose at top level even when skipped
                validation_result['peer_group_analysis'] = {
                    'status': 'SKIPPED',
                    'z_score': None,
                    'reason': 'No peer data provided'
                }
            
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
            
            # Add validation_metrics for test compatibility
            validation_result['validation_metrics'] = {
                'bloomberg_deviation': validation_result['validation_scores'].get('bloomberg_deviation'),
                'spread_deviation': validation_result['validation_scores'].get('spread_deviation'),
                'peer_z_score': validation_result['validation_scores'].get('peer_z_score')
            }
            
            # Calculate and add overall validation_score
            validation_result['validation_score'] = self._calculate_validation_score({
                'bloomberg_consistency': validation_result['validation_checks']['bloomberg_consistency'],
                'spread_correlation': validation_result['validation_checks']['spread_consistency'],
                'peer_group_analysis': validation_result['validation_checks']['peer_group']
            })
            
            logger.debug(f"Validation completed for {bond_data.get('Cusip')}: {validation_result['overall_status']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                'cusip': bond_data.get('Cusip', 'UNKNOWN'),
                'validation_timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': 'FAILED',
                'error': str(e),
                'validation_checks': {},
                'validation_scores': {},
                'recommendations': ['System error during validation - manual review required']
            }
    
    def validate_bloomberg_consistency(self, rating_result: Dict[str, Any], bond_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        7.1 Bloomberg Baseline Validation
        
        Validates LINVEST21 score against Bloomberg agency rating baseline
        per specification methodology.
        
        Args:
            rating_result: LINVEST21 rating result dictionary
            bond_data: Bloomberg bond data dictionary
            
        Returns:
            Validation result with status and deviation
        """
        try:
            # Extract values from the input dictionaries
            if isinstance(rating_result, dict):
                lin_score = rating_result.get('final_score')
            else:
                lin_score = rating_result  # Backward compatibility
                
            if isinstance(bond_data, dict):
                bloomberg_quality = bond_data.get('QualityB')
            else:
                bloomberg_quality = bond_data  # Backward compatibility
            
            # Handle null/None bloomberg_quality case first
            if bloomberg_quality is None:
                return {
                    'status': 'NO_BLOOMBERG_RATING',
                    'deviation': None,
                    'score_difference': None,
                    'error': 'No Bloomberg rating provided'
                }
            
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
                'score_difference': score_difference,  # Add for test compatibility
                'bloomberg_numeric_score': bloomberg_numeric,
                'linvest21_score': lin_score,
                'bloomberg_rating': bloomberg_quality
            }
            
        except Exception as e:
            logger.error(f"Bloomberg validation failed: {str(e)}")
            # Extract values from inputs for error handling
            if isinstance(bond_data, dict):
                bloomberg_quality = bond_data.get('QualityB')
            else:
                bloomberg_quality = bond_data
            # Handle null/None bloomberg_quality case
            if bloomberg_quality is None:
                return {
                    'status': 'NO_BLOOMBERG_RATING',
                    'deviation': None,
                    'score_difference': None,
                    'error': 'No Bloomberg rating provided'
                }
            return {
                'status': 'FAILED',
                'deviation': None,
                'score_difference': None,
                'error': str(e)
            }
    
    def validate_spread_correlation(self, rating_result: Dict[str, Any], bond_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        7.2 Spread Consistency Check
        
        Validates that higher LINVEST21 scores correlate with lower spreads
        as expected from credit risk theory.
        
        Args:
            rating_result: LINVEST21 rating result dictionary
            bond_data: Bloomberg bond data dictionary
            
        Returns:
            Validation result with status and deviation
        """
        try:
            # Extract values from input dictionaries
            if isinstance(rating_result, dict):
                lin_rating_or_score = rating_result.get('final_score') or rating_result.get('linvest21_rating')
            else:
                lin_rating_or_score = rating_result  # Backward compatibility
                
            if isinstance(bond_data, dict):
                oas_spread = bond_data.get('OAS_bp')
            else:
                oas_spread = bond_data  # Backward compatibility
            
            # Handle null spread case
            if oas_spread is None:
                return {
                    'status': 'NO_SPREAD_DATA',
                    'deviation': None,
                    'expected_spread_range': None,
                    'actual_spread': None,
                    'error': 'No spread data provided'
                }
            
            # Convert string rating to numeric if needed
            if isinstance(lin_rating_or_score, str):
                # Use spread thresholds for string ratings
                if lin_rating_or_score in self.spread_thresholds:
                    threshold = self.spread_thresholds[lin_rating_or_score]
                    expected_min = threshold['min']
                    expected_max = threshold['max']
                    
                    if expected_min <= oas_spread <= expected_max:
                        status = 'PASS'
                    else:
                        status = 'FLAG_FOR_REVIEW'
                    
                    return {
                        'status': status,
                        'deviation': min(abs(oas_spread - expected_min), abs(oas_spread - expected_max)) if status == 'FLAG_FOR_REVIEW' else 0,
                        'expected_spread_range': {'min': expected_min, 'max': expected_max},
                        'actual_spread': oas_spread,
                        'lin_rating': lin_rating_or_score
                    }
                else:
                    return {
                        'status': 'FAILED',
                        'deviation': None,
                        'error': f'Unknown rating: {lin_rating_or_score}'
                    }
            else:
                # Handle numeric score
                lin_score = float(lin_rating_or_score)
                # Expected spread based on linear relationship: higher scores -> lower spreads
                expected_spread = 500 - (lin_score * 4)  # Rough linear relationship
                spread_deviation = abs(oas_spread - expected_spread)
                
                status = "PASS" if spread_deviation < 200 else "FLAG_FOR_REVIEW"
                
                return {
                    'status': status,
                    'deviation': spread_deviation,
                    'expected_spread': expected_spread,
                    'expected_spread_range': {'min': max(0, expected_spread - 100), 'max': expected_spread + 100},
                    'actual_spread': oas_spread,
                    'correlation_check': 'PASS' if lin_score > 50 and oas_spread < 300 else 'REVIEW'
                }
            
        except Exception as e:
            logger.error(f"Spread validation failed: {str(e)}")
            return {
                'status': 'FAILED',
                'deviation': None,
                'expected_spread_range': None,
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
            
            # Convert to pandas Series for consistent calculation
            peer_series = pd.Series(peer_scores)
            peer_mean = peer_series.mean()
            peer_std = peer_series.std()  # pandas uses ddof=1 by default
            
            if peer_std == 0 or pd.isna(peer_std) or len(peer_scores) < 2:
                z_score = 0.0
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
                'report_timestamp': datetime.now(timezone.utc).isoformat(),
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
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
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
    
    # Add missing methods expected by tests
    
    def validate_peer_group_analysis(self, rating_data: Dict[str, Any], peer_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate peer group analysis for a single rating
        
        Args:
            rating_data: Rating data dictionary 
            peer_data: DataFrame with peer group data
            
        Returns:
            Peer group validation result
        """
        if peer_data is None or len(peer_data) == 0:
            result = {
                'status': 'NO_PEER_DATA',
                'z_score': None,
                'peer_count': 0
            }
            result['validation_score'] = self._calculate_validation_score(result)
            return result
        
        if len(peer_data) < 5:  # Minimum peer count for statistical significance
            result = {
                'status': 'INSUFFICIENT_PEER_DATA',
                'z_score': None,
                'peer_count': len(peer_data),
                'message': 'Insufficient peer data for analysis'
            }
            result['validation_score'] = self._calculate_validation_score(result)
            return result
        
        rating_score = rating_data.get('final_score')
        if rating_score is None:
            result = {
                'status': 'NO_SCORE',
                'z_score': None,
                'error': 'No final_score in rating data'
            }
            result['validation_score'] = self._calculate_validation_score(result)
            return result
        
        peer_scores = peer_data['final_score'].dropna().tolist()
        if len(peer_scores) < 5:
            result = {
                'status': 'INSUFFICIENT_PEER_DATA',
                'z_score': None,
                'peer_count': len(peer_scores)
            }
            result['validation_score'] = self._calculate_validation_score(result)
            return result
        
        try:
            # Convert to pandas Series for consistent calculation with test expectations
            peer_series = pd.Series(peer_scores)
            peer_mean = peer_series.mean()
            peer_std = peer_series.std()  # pandas uses ddof=1 by default, same as in tests
            
            if peer_std == 0 or pd.isna(peer_std):
                z_score = 0.0
            else:
                z_score = abs(rating_score - peer_mean) / peer_std
            
            if z_score > 2.0:
                status = 'OUTLIER'
            else:
                status = 'WITHIN_RANGE'
            
            result = {
                'status': status,
                'z_score': z_score,
                'peer_count': len(peer_scores),
                'peer_mean': peer_mean,
                'peer_std': peer_std,
                # Add peer_statistics grouping for test compatibility
                'peer_statistics': {
                    'count': len(peer_scores),
                    'mean': peer_mean,
                    'std': peer_std,
                    'min': min(peer_scores),
                    'max': max(peer_scores)
                }
            }
            
            # Add validation score
            result['validation_score'] = self._calculate_validation_score(result)
            
            return result
            
        except Exception as e:
            result = {
                'status': 'FAILED',
                'z_score': None,
                'error': str(e)
            }
            result['validation_score'] = self._calculate_validation_score(result)
            return result
    
    def _get_peer_group(self, all_ratings: pd.DataFrame, target_security: Dict[str, Any]) -> pd.DataFrame:
        """
        Get peer group for a target security
        
        Args:
            all_ratings: DataFrame with all ratings
            target_security: Target security data
            
        Returns:
            DataFrame with peer group data
        """
        peers = all_ratings.copy()
        
        # Filter by sector if available
        if 'sector' in target_security and 'sector' in peers.columns:
            peers = peers[peers['sector'] == target_security['sector']]
        
        # Filter by issuer class if available
        if 'issuer_class_l1' in target_security and 'issuer_class_l1' in peers.columns:
            peers = peers[peers['issuer_class_l1'] == target_security['issuer_class_l1']]
        
        # Filter by rating range (within 20 points) if final_score available
        if 'final_score' in target_security and 'final_score' in peers.columns:
            target_score = target_security['final_score']
            peers = peers[
                (peers['final_score'] >= target_score - 20) & 
                (peers['final_score'] <= target_score + 20)
            ]
        
        return peers
    
    def _calculate_validation_score(self, validation_results: Dict[str, Any]) -> float:
        """
        Calculate overall validation score based on individual validation results
        
        Args:
            validation_results: Dictionary with validation check results
            
        Returns:
            Overall validation score (0-100)
        """
        weights = {
            'bloomberg_consistency': 0.4,
            'spread_correlation': 0.35, 
            'peer_group_analysis': 0.25
        }
        
        scores = {
            'VALIDATED': 100, 'PASS': 100, 'WITHIN_RANGE': 100,
            'REVIEW_REQUIRED': 70, 'FLAG_FOR_REVIEW': 70,
            'MANUAL_OVERRIDE_NEEDED': 20, 'OUTLIER': 20,  # More strict for failures
            'FAILED': 0, 'NO_BLOOMBERG_RATING': 30, 'NO_SPREAD_DATA': 30,
            'INSUFFICIENT_DATA': 40, 'INSUFFICIENT_PEER_DATA': 40, 'NO_PEER_DATA': 70
        }
        
        weighted_score = 0
        total_weight = 0
        
        for check_name, weight in weights.items():
            if check_name in validation_results:
                check_result = validation_results[check_name]
                if isinstance(check_result, dict):
                    status = check_result.get('status', 'FAILED')
                else:
                    status = check_result
                
                check_score = scores.get(status, 0)
                weighted_score += check_score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0
        
        return weighted_score / total_weight
    
    def validate_batch_ratings(self, ratings_data, bloomberg_data) -> List[Dict[str, Any]]:
        """
        Validate batch of ratings 
        
        Args:
            ratings_data: List of rating dictionaries or DataFrame
            bloomberg_data: Bloomberg data DataFrame
            
        Returns:
            List of validation results
        """
        # Convert to list if DataFrame
        if isinstance(ratings_data, pd.DataFrame):
            ratings_list = ratings_data.to_dict('records')
        else:
            ratings_list = ratings_data
        
        # Convert bloomberg_data to list of dicts for easier access
        if isinstance(bloomberg_data, pd.DataFrame):
            bloomberg_list = bloomberg_data.to_dict('records')
        else:
            bloomberg_list = bloomberg_data
        
        results = []
        
        for i, rating_data in enumerate(ratings_list):
            try:
                # Get corresponding Bloomberg data
                cusip = rating_data.get('cusip')
                bloomberg_record = {}
                
                # Check if Bloomberg data is completely missing
                if len(bloomberg_list) == 0:
                    results.append({
                        'cusip': cusip or f'UNKNOWN_{i}',
                        'overall_status': 'NO_BLOOMBERG_DATA',
                        'error': 'No Bloomberg data available',
                        'validation_checks': {},
                        'validation_scores': {},
                        'validation_score': 0,
                        'recommendations': ['Bloomberg data required for validation']
                    })
                    continue
                
                # Find matching Bloomberg record by CUSIP
                if cusip and len(bloomberg_list) > 0:
                    for bb_record in bloomberg_list:
                        if bb_record.get('Cusip') == cusip:
                            bloomberg_record = bb_record
                            break
                    
                    # If no match found, use by index if available
                    if not bloomberg_record and i < len(bloomberg_list):
                        bloomberg_record = bloomberg_list[i]
                
                # Validate the rating
                validation_result = self.validate_rating(rating_data, bloomberg_record)
                results.append(validation_result)
                
            except Exception as e:
                results.append({
                    'cusip': rating_data.get('cusip', f'UNKNOWN_{i}'),
                    'overall_status': 'FAILED',
                    'error': str(e),
                    'validation_checks': {},
                    'validation_scores': {},
                    'recommendations': ['Validation failed due to system error']
                })
        
        return results