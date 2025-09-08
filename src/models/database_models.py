"""
Database Models for LINVEST21 Credit Rating System
JIRA: AINV-711

SQLAlchemy models implementing the database schema from the Confluence specification.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class CreditRating(Base):
    """
    Main table for storing LINVEST21 credit ratings
    
    Implements the database schema specified in the Confluence document
    with all required fields for rating storage and validation.
    """
    __tablename__ = 'linvest21_credit_ratings'
    
    # Primary key
    rating_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Security identifiers
    cusip = Column(String(9), nullable=False)
    isin = Column(String(12), nullable=True)
    calculation_date = Column(Date, nullable=False)
    
    # Security information
    issuer = Column(String(100), nullable=True)
    ticker = Column(String(20), nullable=True)
    currency = Column(String(3), nullable=True)
    
    # Component scores (DECIMAL(5,2) equivalent)
    quantitative_score = Column(Float, nullable=True)
    duration_component = Column(Float, nullable=True)
    spread_component = Column(Float, nullable=True)
    liquidity_component = Column(Float, nullable=True)
    
    sector_score = Column(Float, nullable=True)
    agency_score = Column(Float, nullable=True)
    alpha_score = Column(Float, nullable=True)
    
    # Final rating
    final_score = Column(Float, nullable=True)
    linvest21_rating = Column(String(10), nullable=True)
    
    # Validation flags
    validation_status = Column(String(20), nullable=True)
    bloomberg_deviation = Column(Float, nullable=True)
    peer_z_score = Column(Float, nullable=True)
    
    # Audit trail
    created_timestamp = Column(DateTime, default=func.current_timestamp())
    last_updated = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<CreditRating(cusip='{self.cusip}', rating='{self.linvest21_rating}', score={self.final_score})>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'rating_id': self.rating_id,
            'cusip': self.cusip,
            'isin': self.isin,
            'calculation_date': self.calculation_date.isoformat() if self.calculation_date else None,
            'issuer': self.issuer,
            'ticker': self.ticker,
            'currency': self.currency,
            'final_score': self.final_score,
            'linvest21_rating': self.linvest21_rating,
            'components': {
                'quantitative_score': self.quantitative_score,
                'duration_component': self.duration_component,
                'spread_component': self.spread_component,
                'liquidity_component': self.liquidity_component,
                'sector_score': self.sector_score,
                'agency_score': self.agency_score,
                'alpha_score': self.alpha_score
            },
            'validation_status': self.validation_status,
            'bloomberg_deviation': self.bloomberg_deviation,
            'peer_z_score': self.peer_z_score,
            'created_timestamp': self.created_timestamp.isoformat() if self.created_timestamp else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class BloombergData(Base):
    """
    Table for storing raw Bloomberg data
    
    Caches Bloomberg Global Aggregate data to reduce API calls
    and maintain historical records for backtesting.
    """
    __tablename__ = 'bloomberg_data'
    
    # Primary key
    data_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Security identifiers
    cusip = Column(String(9), nullable=False)
    isin = Column(String(12), nullable=True)
    data_date = Column(Date, nullable=False)
    
    # Primary fields
    currency = Column(String(3), nullable=True)
    quality_b = Column(String(10), nullable=True)  # Bloomberg beginning quality rating
    quality_e = Column(String(10), nullable=True)  # Bloomberg ending quality rating
    outstand_e = Column(Float, nullable=True)      # Outstanding amount end
    maturity = Column(Float, nullable=True)        # Years to maturity
    mrkt_value = Column(Float, nullable=True)      # Current market value
    mrk_val_beg = Column(Float, nullable=True)     # Market value beginning
    
    # Quantitative risk fields
    isma_mdur = Column(Float, nullable=True)       # ISMA Modified Duration
    oas_bp = Column(Float, nullable=True)          # Option-Adjusted Spread (bp)
    dur_adj_mod = Column(Float, nullable=True)     # Duration adjusted modified
    conv_adj = Column(Float, nullable=True)        # Convexity adjustment
    
    # Sector fields
    issuer_cls_l1 = Column(String(50), nullable=True)  # Issuer Class Level 1
    issuer_cls_l2 = Column(String(50), nullable=True)  # Issuer Class Level 2
    sector = Column(String(50), nullable=True)         # Bloomberg sector
    country = Column(String(10), nullable=True)       # Country of risk
    issuer = Column(String(100), nullable=True)       # Issuer name
    
    # Return fields
    ret_total = Column(Float, nullable=True)       # Total return
    ret_price = Column(Float, nullable=True)       # Price return
    ret_currency = Column(Float, nullable=True)    # Currency return
    product_currency = Column(String(3), nullable=True)  # Product currency
    
    # Validation fields
    yld_worst_e = Column(Float, nullable=True)     # Yield to worst end
    
    # Audit fields
    created_timestamp = Column(DateTime, default=func.current_timestamp())
    last_updated = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<BloombergData(cusip='{self.cusip}', date='{self.data_date}', quality='{self.quality_b}')>"


class ValidationResult(Base):
    """
    Table for storing validation results and quality control metrics
    
    Tracks the validation status of each rating calculation
    and stores detailed validation metrics for monitoring.
    """
    __tablename__ = 'validation_results'
    
    # Primary key
    validation_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key reference
    rating_id = Column(Integer, nullable=False)  # References credit_ratings.rating_id
    cusip = Column(String(9), nullable=False)
    calculation_date = Column(Date, nullable=False)
    
    # Validation checks
    bloomberg_consistency = Column(String(20), nullable=True)    # VALIDATED/REVIEW_REQUIRED/MANUAL_OVERRIDE_NEEDED
    spread_correlation = Column(String(20), nullable=True)       # PASS/FLAG_FOR_REVIEW
    peer_group_analysis = Column(String(20), nullable=True)      # WITHIN_RANGE/OUTLIER
    
    # Validation metrics
    bloomberg_deviation = Column(Float, nullable=True)           # Absolute score difference from Bloomberg
    spread_deviation = Column(Float, nullable=True)             # Deviation from expected spread
    peer_z_score = Column(Float, nullable=True)                 # Z-score vs peer group
    
    # Overall validation status
    overall_status = Column(String(20), nullable=False)         # PASSED/FAILED/REVIEW_REQUIRED
    validation_notes = Column(Text, nullable=True)              # Additional validation notes
    
    # Audit fields
    validation_timestamp = Column(DateTime, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<ValidationResult(cusip='{self.cusip}', status='{self.overall_status}')>"


class ProcessingLog(Base):
    """
    Table for tracking daily processing runs and system metrics
    
    Maintains audit trail of ETL processing and system performance
    metrics as required by the governance framework.
    """
    __tablename__ = 'processing_log'
    
    # Primary key
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Processing run information
    process_date = Column(Date, nullable=False)
    process_type = Column(String(20), nullable=False)           # DAILY_ETL/BATCH_CALC/MANUAL
    start_timestamp = Column(DateTime, nullable=False)
    end_timestamp = Column(DateTime, nullable=True)
    
    # Processing metrics
    total_securities_processed = Column(Integer, nullable=True)
    successful_calculations = Column(Integer, nullable=True)
    failed_calculations = Column(Integer, nullable=True)
    validation_passes = Column(Integer, nullable=True)
    validation_failures = Column(Integer, nullable=True)
    
    # Performance metrics
    processing_time_seconds = Column(Float, nullable=True)
    coverage_rate = Column(Float, nullable=True)               # Percentage of eligible universe processed
    calculation_success_rate = Column(Float, nullable=True)    # Percentage of successful calculations
    validation_pass_rate = Column(Float, nullable=True)        # Percentage passing validation
    
    # Status and notes
    process_status = Column(String(20), nullable=False)        # RUNNING/COMPLETED/FAILED
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ProcessingLog(date='{self.process_date}', status='{self.process_status}')>"


class RatingHistory(Base):
    """
    Table for maintaining rating history and changes over time
    
    Tracks rating changes for backtesting and performance analysis
    as required by the model risk management framework.
    """
    __tablename__ = 'rating_history'
    
    # Primary key
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Security and rating information
    cusip = Column(String(9), nullable=False)
    effective_date = Column(Date, nullable=False)
    previous_rating = Column(String(10), nullable=True)
    new_rating = Column(String(10), nullable=False)
    previous_score = Column(Float, nullable=True)
    new_score = Column(Float, nullable=False)
    
    # Change analysis
    rating_change_direction = Column(String(10), nullable=True)  # UPGRADE/DOWNGRADE/UNCHANGED
    score_change = Column(Float, nullable=True)                 # New score - Previous score
    change_reason = Column(String(100), nullable=True)          # PRIMARY_COMPONENT_DRIVER
    
    # Audit fields
    created_timestamp = Column(DateTime, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<RatingHistory(cusip='{self.cusip}', change='{self.rating_change_direction}')>"


# Create indexes as specified in the Confluence document
Index('idx_cusip_date', CreditRating.cusip, CreditRating.calculation_date)
Index('idx_rating_date', CreditRating.linvest21_rating, CreditRating.calculation_date)
Index('idx_bloomberg_cusip_date', BloombergData.cusip, BloombergData.data_date)
Index('idx_validation_rating_id', ValidationResult.rating_id)
Index('idx_processing_date', ProcessingLog.process_date)
Index('idx_history_cusip_date', RatingHistory.cusip, RatingHistory.effective_date)


class DatabaseManager:
    """
    Database management utilities for the credit rating system
    
    Provides helper methods for common database operations
    and maintains connection management.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database manager
        
        Args:
            database_url: SQLAlchemy database connection URL
        """
        self.database_url = database_url
        self.engine = None
        self.session = None
        logger.info("Database manager initialized")
    
    def create_tables(self, engine):
        """
        Create all database tables
        
        Args:
            engine: SQLAlchemy engine instance
        """
        try:
            Base.metadata.create_all(engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def get_latest_rating(self, cusip: str) -> Optional[CreditRating]:
        """
        Get the most recent rating for a CUSIP
        
        Args:
            cusip: Security CUSIP identifier
            
        Returns:
            Latest CreditRating record or None
        """
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        return (self.session.query(CreditRating)
                .filter(CreditRating.cusip == cusip)
                .order_by(CreditRating.calculation_date.desc())
                .first())
    
    def get_ratings_by_date(self, calculation_date: date) -> list:
        """
        Get all ratings for a specific calculation date
        
        Args:
            calculation_date: Date to query
            
        Returns:
            List of CreditRating records
        """
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        return (self.session.query(CreditRating)
                .filter(CreditRating.calculation_date == calculation_date)
                .all())
    
    def get_processing_metrics(self, days: int = 30) -> dict:
        """
        Get processing performance metrics for recent period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        # Calculate recent performance metrics
        from sqlalchemy import func
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=days)
        
        metrics = (self.session.query(
            func.avg(ProcessingLog.coverage_rate).label('avg_coverage'),
            func.avg(ProcessingLog.calculation_success_rate).label('avg_success_rate'),
            func.avg(ProcessingLog.validation_pass_rate).label('avg_validation_rate'),
            func.avg(ProcessingLog.processing_time_seconds).label('avg_processing_time')
        ).filter(ProcessingLog.process_date >= cutoff_date).first())
        
        return {
            'average_coverage_rate': metrics.avg_coverage if metrics else 0,
            'average_success_rate': metrics.avg_success_rate if metrics else 0,
            'average_validation_rate': metrics.avg_validation_rate if metrics else 0,
            'average_processing_time': metrics.avg_processing_time if metrics else 0,
            'analysis_period_days': days
        }