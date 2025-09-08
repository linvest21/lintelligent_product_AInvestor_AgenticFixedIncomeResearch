"""
Daily ETL Pipeline for LINVEST21 Credit Rating System
JIRA: AINV-711

Implements the daily rating calculation workflow as specified in the
Confluence technical documentation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone
import logging
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework
from src.models.database_models import (
    CreditRating, BloombergData, ValidationResult, ProcessingLog, RatingHistory, Base
)

logger = logging.getLogger(__name__)


class DailyETLPipeline:
    """
    Daily ETL (Extract, Transform, Load) pipeline
    
    Orchestrates the complete daily rating calculation workflow:
    1. Extract Bloomberg Global Aggregate data
    2. Apply universe filters
    3. Calculate LINVEST21 ratings
    4. Validate & quality control
    5. Store results
    6. Generate alerts for outliers
    """
    
    def __init__(self, database_url: str):
        """
        Initialize daily ETL pipeline
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize components
        self.rating_engine = LINVEST21RatingEngine()
        self.bloomberg_connector = BloombergConnector()
        self.validation_framework = ValidationFramework()
        
        # Performance metrics
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'total_securities_extracted': 0,
            'eligible_securities': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'validation_passes': 0,
            'validation_failures': 0,
            'outliers_detected': 0
        }
        
        # Keep reference to logger for testing
        self.logger = logger
        logger.info("Daily ETL pipeline initialized")
        
    def _get_db_session(self):
        """Get a new database session as a context manager"""
        from contextlib import contextmanager
        
        @contextmanager
        def session_context():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()
        
        return session_context()
        
    async def _generate_alerts(self, validation_results, summary_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate alerts based on validation results and summary statistics"""
        # Convert validation_results to DataFrame if it's a list
        if isinstance(validation_results, list):
            validation_results_df = pd.DataFrame(validation_results)
        else:
            validation_results_df = validation_results
            
        # Generate outlier alerts using the existing method
        outlier_alerts = await self._generate_outlier_alerts(validation_results_df)
        
        # Add summary-based alerts if summary_stats provided
        additional_alerts = []
        if summary_stats:
            # Check coverage rate
            if summary_stats.get('coverage_rate', 1.0) < 0.95:
                additional_alerts.append({
                    'type': 'COVERAGE_LOW',
                    'severity': 'MEDIUM', 
                    'message': f"Coverage rate {summary_stats['coverage_rate']:.1%} below 95% threshold"
                })
            
            # Check success rate
            if summary_stats.get('success_rate', 1.0) < 0.98:
                additional_alerts.append({
                    'type': 'SUCCESS_RATE_LOW',
                    'severity': 'HIGH',
                    'message': f"Success rate below 98% specification threshold"
                })
        
        all_alerts = outlier_alerts + additional_alerts
        
        return {
            'alerts_sent': len(all_alerts),
            'alerts': all_alerts,
            'alert_details': all_alerts,  # Add for test compatibility
            'summary': {
                'total_alerts': len(all_alerts),
                'high_severity': len([a for a in all_alerts if a.get('severity') == 'HIGH']),
                'medium_severity': len([a for a in all_alerts if a.get('severity') == 'MEDIUM'])
            }
        }
        
    async def _calculate_summary_statistics(self, rating_results: List[Dict[str, Any]], 
                                           validation_results: List[Dict[str, Any]],
                                           original_universe_size: int, 
                                           filtered_universe_size: int) -> Dict[str, Any]:
        """Calculate summary statistics for the processing results"""
        total_processed = len(rating_results)
        successful_calculations = len(rating_results)  # All rating_results are successful calculations
        
        # Count validation passes
        validation_pass_count = sum(1 for v in validation_results if v.get('overall_status') == 'PASSED')
        validation_pass_rate = validation_pass_count / len(validation_results) if validation_results else 0.0
        
        # Calculate coverage and universe reduction
        coverage_rate = total_processed / filtered_universe_size if filtered_universe_size > 0 else 0.0
        universe_reduction_rate = filtered_universe_size / original_universe_size if original_universe_size > 0 else 0.0
        
        # Rating distribution
        ratings_distribution = {}
        for result in rating_results:
            rating = result.get('linvest21_rating')
            if rating:
                ratings_distribution[rating] = ratings_distribution.get(rating, 0) + 1
        
        return {
            'total_processed': total_processed,
            'successful_calculations': successful_calculations,
            'validation_pass_count': validation_pass_count,
            'validation_pass_rate': validation_pass_rate,
            'coverage_rate': coverage_rate,
            'universe_reduction_rate': universe_reduction_rate,
            'ratings_distribution': ratings_distribution,
            'original_universe_size': original_universe_size,
            'filtered_universe_size': filtered_universe_size
        }
    
    async def run_daily_process(self, process_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Execute the complete daily rating process
        
        Args:
            process_date: Date for processing (defaults to today)
            
        Returns:
            Processing results summary
        """
        if process_date is None:
            process_date = date.today()
        
        self.metrics['start_time'] = datetime.now(timezone.utc)
        
        logger.info(f"Starting daily rating process for {process_date}")
        
        # Create database session
        db_session = self.SessionLocal()
        
        try:
            # Create processing log entry
            process_log = ProcessingLog(
                process_date=process_date,
                process_type="DAILY_ETL",
                start_timestamp=self.metrics['start_time'],
                process_status="RUNNING"
            )
            db_session.add(process_log)
            db_session.commit()
            
            # Step 1: Extract Bloomberg Data
            logger.info("Step 1: Extracting Bloomberg Global Aggregate data")
            bloomberg_data = await self._extract_bloomberg_data()
            self.metrics['total_securities_extracted'] = len(bloomberg_data)
            
            # Step 2: Apply Universe Filters  
            logger.info("Step 2: Applying universe filters")
            filtered_data = await self._apply_universe_filters(bloomberg_data)
            self.metrics['eligible_securities'] = len(filtered_data)
            
            # Step 3: Calculate Ratings
            logger.info("Step 3: Calculating LINVEST21 ratings")
            rating_results = await self._calculate_ratings(filtered_data)
            
            # Step 4: Validation & Quality Control
            logger.info("Step 4: Running validation and quality control")
            validation_results = await self._validate_ratings(rating_results, filtered_data)
            
            # Step 5: Store Results
            logger.info("Step 5: Storing results to database")
            await self._store_results(rating_results, validation_results, process_date, db_session)
            
            # Step 6: Generate Alerts
            logger.info("Step 6: Generating outlier alerts")
            alerts = await self._generate_outlier_alerts(validation_results)
            
            # Update processing metrics
            self.metrics['end_time'] = datetime.now(timezone.utc)
            processing_time = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()
            
            # Update processing log
            process_log.end_timestamp = self.metrics['end_time']
            process_log.total_securities_processed = self.metrics['eligible_securities']
            process_log.successful_calculations = self.metrics['successful_calculations']
            process_log.failed_calculations = self.metrics['failed_calculations']
            process_log.validation_passes = self.metrics['validation_passes']
            process_log.validation_failures = self.metrics['validation_failures']
            process_log.processing_time_seconds = processing_time
            process_log.coverage_rate = self.metrics['eligible_securities'] / max(self.metrics['total_securities_extracted'], 1)
            process_log.calculation_success_rate = self.metrics['successful_calculations'] / max(self.metrics['eligible_securities'], 1)
            process_log.validation_pass_rate = self.metrics['validation_passes'] / max(self.metrics['successful_calculations'], 1)
            process_log.process_status = "COMPLETED"
            process_log.notes = f"Processed {self.metrics['eligible_securities']} securities, {len(alerts)} outliers detected"
            
            db_session.commit()
            
            # Generate summary
            results_summary = {
                'process_date': process_date.isoformat(),
                'status': 'SUCCESS',
                'process_status': 'COMPLETED',  # Add for test compatibility
                'processing_time_seconds': processing_time,
                'metrics': self.metrics.copy(),
                'alerts': alerts,
                'summary': {
                    'total_extracted': self.metrics['total_securities_extracted'],
                    'eligible_securities': self.metrics['eligible_securities'],
                    'successful_ratings': self.metrics['successful_calculations'],
                    'coverage_rate': process_log.coverage_rate,
                    'success_rate': process_log.calculation_success_rate,
                    'validation_pass_rate': process_log.validation_pass_rate
                }
            }
            
            logger.info(f"Daily process completed successfully in {processing_time:.1f}s")
            logger.info(f"Coverage: {process_log.coverage_rate:.1%}, Success: {process_log.calculation_success_rate:.1%}, Validation: {process_log.validation_pass_rate:.1%}")
            
            return results_summary
            
        except Exception as e:
            # Update processing log with error
            process_log.process_status = "FAILED"
            process_log.error_message = str(e)
            process_log.end_timestamp = datetime.now(timezone.utc)
            db_session.commit()
            
            logger.error(f"Daily process failed: {str(e)}")
            
            return {
                'process_date': process_date.isoformat(),
                'status': 'FAILED',
                'process_status': 'FAILED',  # Add for test compatibility
                'error': str(e),
                'error_message': str(e),  # Add for test compatibility
                'metrics': self.metrics.copy()
            }
            
        finally:
            db_session.close()
    
    async def _extract_bloomberg_data(self) -> pd.DataFrame:
        """
        Step 1: Extract Bloomberg Global Aggregate data
        
        Returns:
            Raw Bloomberg data DataFrame
        """
        try:
            # Connect to Bloomberg if not already connected
            if not self.bloomberg_connector.is_connected:
                self.bloomberg_connector.connect()
            
            # Extract data with default filters
            bloomberg_data = self.bloomberg_connector.extract_global_aggregate_data()
            
            logger.info(f"Extracted {len(bloomberg_data)} securities from Bloomberg Global Aggregate")
            
            # Validate data quality
            data_quality = self.bloomberg_connector.validate_data_quality(bloomberg_data)
            if not data_quality['meets_minimum_coverage']:
                logger.warning(f"Data quality below threshold: {data_quality['overall_coverage']:.1%}")
            
            return bloomberg_data
            
        except Exception as e:
            logger.error(f"Bloomberg data extraction failed: {str(e)}")
            raise
    
    async def _apply_universe_filters(self, bloomberg_data: pd.DataFrame, filters: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Step 2: Apply universe filtering logic per specification
        
        Args:
            bloomberg_data: Raw Bloomberg data
            filters: Optional custom filtering criteria
            
        Returns:
            Filtered DataFrame meeting eligibility criteria
        """
        try:
            initial_count = len(bloomberg_data)
            filtered_data = bloomberg_data.copy()
            
            # Use custom filters if provided, otherwise use defaults
            if filters:
                # Filter 1: Currency filter (can be customized)
                currencies = filters.get('Currency', ['USD'])
                if isinstance(currencies, str):
                    currencies = [currencies]
                filtered_data = filtered_data[filtered_data['Currency'].isin(currencies)]
                logger.debug(f"After currency filter ({currencies}): {len(filtered_data)} securities")
                
                # Filter 3: Outstanding amount (customizable minimum)
                min_outstanding = filters.get('OutstandE_min', 300_000_000)
                filtered_data = filtered_data[filtered_data['OutstandE'] >= min_outstanding]
                logger.debug(f"After outstanding amount filter (>=${min_outstanding:,}): {len(filtered_data)} securities")
                
                # Filter 4: Maturity (customizable minimum) 
                min_maturity = filters.get('Maturity_min', 1.0)
                filtered_data = filtered_data[filtered_data['Maturity'] >= min_maturity]
                logger.debug(f"After maturity filter (>={min_maturity}): {len(filtered_data)} securities")
            else:
                # Default filters
                # Filter 1: USD currency only (Phase 1 requirement)
                filtered_data = filtered_data[filtered_data['Currency'] == 'USD']
                logger.debug(f"After currency filter: {len(filtered_data)} securities")
                
                # Filter 3: Minimum outstanding amount ($300M)
                filtered_data = filtered_data[filtered_data['OutstandE'] >= 300_000_000]
                logger.debug(f"After outstanding amount filter: {len(filtered_data)} securities")
                
                # Filter 4: Minimum maturity (1 year)
                filtered_data = filtered_data[filtered_data['Maturity'] >= 1.0]
                logger.debug(f"After maturity filter: {len(filtered_data)} securities")
            
            # These filters are always applied regardless of custom filters
            # Filter 2: Exclude unrated/defaulted securities
            exclude_ratings = ['NR', 'D', '']
            filtered_data = filtered_data[~filtered_data['QualityB'].isin(exclude_ratings)]
            logger.debug(f"After rating filter: {len(filtered_data)} securities")
            
            # Filter 5: Non-null market values (only if column exists)
            if 'MrktValue' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['MrktValue'].notna()]
                logger.debug(f"After market value filter: {len(filtered_data)} securities")
            else:
                logger.debug("MrktValue column not present, skipping market value filter")
            
            # Calculate filtering statistics
            exclusion_rate = 1 - (len(filtered_data) / initial_count) if initial_count > 0 else 0
            
            logger.info(f"Universe filtering complete: {len(filtered_data)} eligible securities ({exclusion_rate:.1%} excluded)")
            
            # Expected output per specification: ~8,500 eligible USD IG securities
            if len(filtered_data) < 5000:
                logger.warning(f"Low eligible security count: {len(filtered_data)} (expected ~8,500)")
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Universe filtering failed: {str(e)}")
            raise
    
    async def _calculate_ratings(self, filtered_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Step 3: Calculate LINVEST21 ratings for all eligible securities
        
        Args:
            filtered_data: Filtered Bloomberg data
            
        Returns:
            List of rating calculation results
        """
        try:
            rating_results = []
            successful_count = 0
            failed_count = 0
            
            logger.info(f"Calculating ratings for {len(filtered_data)} securities")
            
            # Process securities in batches for memory efficiency
            batch_size = 1000
            total_batches = (len(filtered_data) + batch_size - 1) // batch_size
            
            for batch_num, start_idx in enumerate(range(0, len(filtered_data), batch_size)):
                end_idx = min(start_idx + batch_size, len(filtered_data))
                batch_data = filtered_data.iloc[start_idx:end_idx]
                
                logger.debug(f"Processing batch {batch_num + 1}/{total_batches}")
                
                for idx, bond in batch_data.iterrows():
                    try:
                        # Calculate rating using LINVEST21 engine
                        bond_dict = bond.to_dict()
                        rating_result = self.rating_engine.calculate_rating(bond_dict)
                        
                        # Add metadata
                        rating_result['cusip'] = bond.get('Cusip', f'UNKNOWN_{idx}')
                        rating_result['row_index'] = idx
                        rating_result['bloomberg_data'] = bond_dict
                        
                        rating_results.append(rating_result)
                        
                        if rating_result.get('error') or rating_result.get('validation_status') == 'CALCULATION_FAILED':
                            failed_count += 1
                        else:
                            successful_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Rating calculation failed for row {idx}: {str(e)}")
                        
                        rating_results.append({
                            'cusip': bond.get('Cusip', f'UNKNOWN_{idx}'),
                            'row_index': idx,
                            'error': str(e),
                            'validation_status': 'CALCULATION_FAILED',
                            'final_score': None,
                            'linvest21_rating': None,
                            'bloomberg_data': bond.to_dict()
                        })
                        failed_count += 1
                
                # Progress logging
                if (batch_num + 1) % 5 == 0:
                    logger.info(f"Processed {end_idx} securities ({successful_count} successful, {failed_count} failed)")
            
            self.metrics['successful_calculations'] = successful_count
            self.metrics['failed_calculations'] = failed_count
            
            success_rate = successful_count / len(filtered_data) if len(filtered_data) > 0 else 0
            logger.info(f"Rating calculation complete: {success_rate:.1%} success rate")
            
            # Check against specification requirement (98% success rate)
            if success_rate < 0.98:
                logger.warning(f"Success rate {success_rate:.1%} below 98% specification threshold")
            
            return rating_results
            
        except Exception as e:
            logger.error(f"Rating calculation failed: {str(e)}")
            raise
    
    async def _validate_ratings(self, rating_results: List[Dict[str, Any]], 
                              filtered_data: pd.DataFrame) -> pd.DataFrame:
        """
        Step 4: Validate ratings and run quality control
        
        Args:
            rating_results: List of rating results
            filtered_data: Original Bloomberg data
            
        Returns:
            DataFrame with validation results
        """
        try:
            logger.info(f"Validating {len(rating_results)} ratings")
            
            # Prepare bond data list for validation
            bond_data_list = []
            for result in rating_results:
                bond_data_list.append(result.get('bloomberg_data', {}))
            
            # Convert rating_results to DataFrame if it's a list
            if isinstance(rating_results, list):
                rating_results_df = pd.DataFrame(rating_results)
            else:
                rating_results_df = rating_results
                
            # Run batch validation - handle both list and DataFrame returns
            validation_results = self.validation_framework.batch_validate_ratings(
                rating_results_df, bond_data_list
            )
            
            # Convert to DataFrame if it's a list (for test compatibility)
            if isinstance(validation_results, list):
                validation_results = pd.DataFrame(validation_results)
            
            # Count validation outcomes
            validation_counts = validation_results['overall_status'].value_counts()
            passed_count = validation_counts.get('PASSED', 0)
            failed_count = validation_counts.get('FAILED', 0)
            review_count = validation_counts.get('REVIEW_REQUIRED', 0)
            
            self.metrics['validation_passes'] = passed_count
            self.metrics['validation_failures'] = failed_count + review_count
            
            validation_pass_rate = passed_count / len(validation_results) if len(validation_results) > 0 else 0
            
            logger.info(f"Validation complete: {validation_pass_rate:.1%} pass rate")
            
            # Check against specification requirement (90% pass rate)
            if validation_pass_rate < 0.90:
                logger.warning(f"Validation pass rate {validation_pass_rate:.1%} below 90% specification threshold")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Rating validation failed: {str(e)}")
            raise
    
    async def _store_results(self, rating_results: List[Dict[str, Any]], 
                           validation_results: pd.DataFrame, 
                           process_date: date, db_session) -> Dict[str, Any]:
        """
        Step 5: Store results to database
        
        Args:
            rating_results: Rating calculation results
            validation_results: Validation results
            process_date: Processing date
            db_session: Database session
        """
        try:
            logger.info(f"Storing {len(rating_results)} rating results to database")
            
            # Convert validation_results to DataFrame if it's a list (for compatibility)
            if isinstance(validation_results, list):
                validation_results_df = pd.DataFrame(validation_results)
            else:
                validation_results_df = validation_results
            
            stored_count = 0
            
            for i, rating_result in enumerate(rating_results):
                try:
                    cusip = rating_result.get('cusip')
                    if not cusip or cusip.startswith('UNKNOWN_'):
                        continue
                    
                    # Get corresponding validation result
                    validation_row = validation_results_df.iloc[i] if i < len(validation_results_df) else None
                    
                    # Create CreditRating record
                    credit_rating = CreditRating(
                        cusip=cusip,
                        isin=rating_result.get('bloomberg_data', {}).get('ISIN'),
                        calculation_date=process_date,
                        issuer=rating_result.get('bloomberg_data', {}).get('Issuer'),
                        currency=rating_result.get('bloomberg_data', {}).get('Currency'),
                        
                        # Component scores
                        quantitative_score=rating_result.get('quantitative_score'),
                        duration_component=rating_result.get('components', {}).get('duration'),
                        spread_component=rating_result.get('components', {}).get('spread'),
                        liquidity_component=rating_result.get('components', {}).get('liquidity'),
                        sector_score=rating_result.get('sector_score'),
                        agency_score=rating_result.get('agency_score'),
                        alpha_score=rating_result.get('alpha_score'),
                        
                        # Final rating
                        final_score=rating_result.get('final_score'),
                        linvest21_rating=rating_result.get('linvest21_rating'),
                        
                        # Validation flags
                        validation_status=rating_result.get('validation_status'),
                        bloomberg_deviation=validation_row.get('validation_scores', {}).get('bloomberg_deviation') if validation_row is not None else None,
                        peer_z_score=validation_row.get('validation_scores', {}).get('peer_z_score') if validation_row is not None else None
                    )
                    
                    db_session.add(credit_rating)
                    db_session.flush()  # Flush to get the rating_id
                    stored_count += 1
                    
                    # Store validation result if available
                    if validation_row is not None and validation_row.get('overall_status'):
                        validation_record = ValidationResult(
                            rating_id=credit_rating.rating_id,  # Now available after flush
                            cusip=cusip,
                            calculation_date=process_date,
                            bloomberg_consistency=validation_row.get('validation_checks', {}).get('bloomberg_consistency'),
                            spread_correlation=validation_row.get('validation_checks', {}).get('spread_consistency'),
                            peer_group_analysis=validation_row.get('validation_checks', {}).get('peer_group'),
                            bloomberg_deviation=validation_row.get('validation_scores', {}).get('bloomberg_deviation'),
                            spread_deviation=validation_row.get('validation_scores', {}).get('spread_deviation'),
                            peer_z_score=validation_row.get('validation_scores', {}).get('peer_z_score'),
                            overall_status=validation_row.get('overall_status'),
                            validation_notes='; '.join(validation_row.get('recommendations', []))
                        )
                        
                        db_session.add(validation_record)
                    
                    # Commit in batches for performance
                    if stored_count % 100 == 0:
                        db_session.commit()
                        logger.debug(f"Stored {stored_count} ratings")
                    
                except Exception as e:
                    logger.warning(f"Failed to store result for {rating_result.get('cusip')}: {str(e)}")
                    db_session.rollback()
            
            # Final commit
            db_session.commit()
            
            logger.info(f"Successfully stored {stored_count} rating results")
            
            return {
                'stored_ratings': stored_count,
                'stored_bloomberg_data': len(rating_results),
                'stored_validations': len(validation_results) if not isinstance(validation_results, list) else len(validation_results)
            }
            
        except Exception as e:
            logger.error(f"Database storage failed: {str(e)}")
            db_session.rollback()
            raise
    
    async def _generate_outlier_alerts(self, validation_results: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Step 6: Generate alerts for outliers and validation failures
        
        Args:
            validation_results: Validation results DataFrame
            
        Returns:
            List of alert dictionaries
        """
        try:
            alerts = []
            
            # Generate quality control report
            quality_report = self.validation_framework.generate_quality_report(validation_results)
            
            # Alert for low validation pass rate
            if not quality_report.get('meets_90_percent_threshold', True):
                alerts.append({
                    'type': 'QUALITY_THRESHOLD',
                    'severity': 'HIGH',
                    'message': f"Validation pass rate {quality_report.get('validation_pass_rate', 0):.1%} below 90% threshold",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            # Alert for manual override needed ratings
            manual_override_count = 0
            outlier_count = 0
            
            for _, row in validation_results.iterrows():
                checks = row.get('validation_checks', {})
                if isinstance(checks, dict):
                    if 'MANUAL_OVERRIDE_NEEDED' in checks.values():
                        manual_override_count += 1
                    if 'OUTLIER' in checks.values():
                        outlier_count += 1
            
            if manual_override_count > 0:
                alerts.append({
                    'type': 'MANUAL_OVERRIDE',
                    'severity': 'HIGH',
                    'message': f"{manual_override_count} ratings require manual override",
                    'count': manual_override_count,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            if outlier_count > 0:
                alerts.append({
                    'type': 'PEER_OUTLIERS',
                    'severity': 'MEDIUM',
                    'message': f"{outlier_count} ratings identified as peer group outliers",
                    'count': outlier_count,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                self.metrics['outliers_detected'] = outlier_count
            
            # Alert for processing performance issues
            if self.metrics['end_time'] and self.metrics['start_time']:
                processing_time = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()
                if processing_time > 7200:  # 2 hours per specification
                    alerts.append({
                        'type': 'PERFORMANCE',
                        'severity': 'MEDIUM',
                        'message': f"Processing time {processing_time/3600:.1f} hours exceeds 2-hour target",
                        'processing_time_seconds': processing_time,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            logger.info(f"Generated {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Alert generation failed: {str(e)}")
            return [{
                'type': 'SYSTEM_ERROR',
                'severity': 'HIGH',
                'message': f"Alert generation failed: {str(e)}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }]


async def main():
    """Main entry point for daily ETL pipeline"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Database configuration
    database_url = os.getenv(
        'DATABASE_URL', 
        'postgresql://postgres:password@localhost:5432/linvest21_ratings'
    )
    
    # Create and run pipeline
    pipeline = DailyETLPipeline(database_url)
    
    try:
        results = await pipeline.run_daily_process()
        
        print(f"Daily ETL Pipeline Results:")
        print(f"Status: {results['status']}")
        print(f"Processing Time: {results.get('processing_time_seconds', 0):.1f}s")
        print(f"Summary: {results.get('summary', {})}")
        
        if results.get('alerts'):
            print(f"Alerts Generated: {len(results['alerts'])}")
            for alert in results['alerts']:
                print(f"  - {alert['type']}: {alert['message']}")
        
    except Exception as e:
        logger.error(f"Daily ETL pipeline failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())