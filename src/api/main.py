"""
FastAPI Application for LINVEST21 Credit Rating System
JIRA: AINV-711

Provides REST API endpoints for real-time rating lookup and batch processing
as specified in the Confluence technical documentation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.models.database_models import CreditRating, BloombergData, ValidationResult, ProcessingLog, Base
from src.validation.quality_control import ValidationFramework

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql://postgres:password@localhost:5432/linvest21_ratings"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global instances
rating_engine = LINVEST21RatingEngine()
bloomberg_connector = BloombergConnector()
validation_framework = ValidationFramework()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting LINVEST21 Credit Rating System API")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Connect to Bloomberg (in production)
    # bloomberg_connector.connect()
    
    yield
    
    # Cleanup
    bloomberg_connector.disconnect()
    logger.info("LINVEST21 Credit Rating System API shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="LINVEST21 Credit Rating System API",
    description="Proprietary Credit Rating Framework leveraging Bloomberg Global Aggregate data",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for database session
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API Models
class RatingResponse(BaseModel):
    """Response model for rating lookup"""
    cusip: str
    isin: Optional[str] = None
    linvest21_rating: Optional[str] = None
    final_score: Optional[float] = None
    components: Optional[Dict[str, float]] = None
    validation_status: Optional[str] = None
    calculation_date: Optional[str] = None
    last_updated: Optional[str] = None


class BatchRatingRequest(BaseModel):
    """Request model for batch rating processing"""
    cusips: List[str] = Field(..., description="List of CUSIP identifiers")
    include_components: bool = Field(default=True, description="Include component score breakdown")
    validation_level: str = Field(default="full", description="Validation level: basic/full")


class BatchRatingResponse(BaseModel):
    """Response model for batch rating processing"""
    request_id: str
    status: str
    processed_count: int
    successful_count: int
    failed_count: int
    ratings: List[RatingResponse]
    processing_time_seconds: Optional[float] = None


class SystemStatusResponse(BaseModel):
    """System status response model"""
    status: str
    version: str
    database_status: str
    bloomberg_status: str
    last_processing_run: Optional[str] = None
    performance_metrics: Dict[str, Any]


# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with service information"""
    return {
        "service": "LINVEST21 Credit Rating System",
        "version": "1.0.0",
        "jira_ticket": "AINV-711",
        "status": "operational",
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LINVEST21 Credit Rating API"
    }


@app.get("/api/v1/rating/{cusip}", response_model=RatingResponse)
async def get_rating(cusip: str, db: Session = Depends(get_db)):
    """
    Real-time rating lookup for a specific CUSIP
    
    Args:
        cusip: CUSIP identifier
        db: Database session
        
    Returns:
        Rating information with components
    """
    try:
        # Query latest rating from database
        rating = (db.query(CreditRating)
                 .filter(CreditRating.cusip == cusip)
                 .order_by(CreditRating.calculation_date.desc())
                 .first())
        
        if not rating:
            # Try to calculate rating if not found
            try:
                bloomberg_data = bloomberg_connector.get_security_data([cusip], "CUSIP")
                if bloomberg_data.empty:
                    raise HTTPException(status_code=404, detail=f"CUSIP {cusip} not found")
                
                # Calculate rating
                bond_data = bloomberg_data.iloc[0].to_dict()
                rating_result = rating_engine.calculate_rating(bond_data)
                
                if rating_result.get('error'):
                    raise HTTPException(status_code=400, detail=f"Rating calculation failed: {rating_result['error']}")
                
                return RatingResponse(
                    cusip=cusip,
                    linvest21_rating=rating_result['linvest21_rating'],
                    final_score=rating_result['final_score'],
                    components={
                        "quantitative": rating_result['quantitative_score'],
                        "sector": rating_result['sector_score'],
                        "agency": rating_result['agency_score'],
                        "alpha": rating_result['alpha_score']
                    },
                    validation_status=rating_result['validation_status'],
                    calculation_date=datetime.utcnow().date().isoformat(),
                    last_updated=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                logger.error(f"Failed to calculate rating for {cusip}: {str(e)}")
                raise HTTPException(status_code=500, detail="Unable to calculate rating")
        
        # Return stored rating
        return RatingResponse(
            cusip=rating.cusip,
            isin=rating.isin,
            linvest21_rating=rating.linvest21_rating,
            final_score=rating.final_score,
            components={
                "quantitative": rating.quantitative_score,
                "sector": rating.sector_score,
                "agency": rating.agency_score,
                "alpha": rating.alpha_score
            },
            validation_status=rating.validation_status,
            calculation_date=rating.calculation_date.isoformat() if rating.calculation_date else None,
            last_updated=rating.last_updated.isoformat() if rating.last_updated else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rating for {cusip}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/ratings/batch", response_model=BatchRatingResponse)
async def batch_rating_processing(
    request: BatchRatingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Batch rating processing for multiple CUSIPs
    
    Args:
        request: Batch rating request
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Batch processing results
    """
    try:
        request_id = f"batch_{datetime.utcnow().timestamp()}"
        start_time = datetime.utcnow()
        
        logger.info(f"Processing batch request {request_id} for {len(request.cusips)} CUSIPs")
        
        # Get Bloomberg data for all CUSIPs
        bloomberg_data = bloomberg_connector.get_security_data(request.cusips, "CUSIP")
        
        ratings = []
        successful_count = 0
        failed_count = 0
        
        for cusip in request.cusips:
            try:
                # First check database for existing rating
                existing_rating = (db.query(CreditRating)
                                 .filter(CreditRating.cusip == cusip)
                                 .order_by(CreditRating.calculation_date.desc())
                                 .first())
                
                if existing_rating:
                    # Use existing rating
                    rating_response = RatingResponse(
                        cusip=existing_rating.cusip,
                        isin=existing_rating.isin,
                        linvest21_rating=existing_rating.linvest21_rating,
                        final_score=existing_rating.final_score,
                        components={
                            "quantitative": existing_rating.quantitative_score,
                            "sector": existing_rating.sector_score,
                            "agency": existing_rating.agency_score,
                            "alpha": existing_rating.alpha_score
                        } if request.include_components else None,
                        validation_status=existing_rating.validation_status,
                        calculation_date=existing_rating.calculation_date.isoformat() if existing_rating.calculation_date else None,
                        last_updated=existing_rating.last_updated.isoformat() if existing_rating.last_updated else None
                    )
                    ratings.append(rating_response)
                    successful_count += 1
                    
                else:
                    # Calculate new rating
                    cusip_data = bloomberg_data[bloomberg_data['Cusip'] == cusip]
                    if cusip_data.empty:
                        ratings.append(RatingResponse(
                            cusip=cusip,
                            linvest21_rating=None,
                            validation_status="DATA_NOT_FOUND"
                        ))
                        failed_count += 1
                        continue
                    
                    bond_data = cusip_data.iloc[0].to_dict()
                    rating_result = rating_engine.calculate_rating(bond_data)
                    
                    if rating_result.get('error'):
                        ratings.append(RatingResponse(
                            cusip=cusip,
                            linvest21_rating=None,
                            validation_status="CALCULATION_FAILED"
                        ))
                        failed_count += 1
                        continue
                    
                    # Create rating response
                    rating_response = RatingResponse(
                        cusip=cusip,
                        linvest21_rating=rating_result['linvest21_rating'],
                        final_score=rating_result['final_score'],
                        components={
                            "quantitative": rating_result['quantitative_score'],
                            "sector": rating_result['sector_score'], 
                            "agency": rating_result['agency_score'],
                            "alpha": rating_result['alpha_score']
                        } if request.include_components else None,
                        validation_status=rating_result['validation_status'],
                        calculation_date=datetime.utcnow().date().isoformat(),
                        last_updated=datetime.utcnow().isoformat()
                    )
                    ratings.append(rating_response)
                    successful_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to process CUSIP {cusip}: {str(e)}")
                ratings.append(RatingResponse(
                    cusip=cusip,
                    linvest21_rating=None,
                    validation_status="PROCESSING_ERROR"
                ))
                failed_count += 1
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log processing metrics
        background_tasks.add_task(
            log_batch_processing,
            request_id, len(request.cusips), successful_count, failed_count, processing_time
        )
        
        return BatchRatingResponse(
            request_id=request_id,
            status="completed",
            processed_count=len(request.cusips),
            successful_count=successful_count,
            failed_count=failed_count,
            ratings=ratings,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch processing failed")


@app.get("/api/v1/status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_db)):
    """
    Get system status and performance metrics
    
    Args:
        db: Database session
        
    Returns:
        System status information
    """
    try:
        # Check database connectivity
        try:
            db.execute("SELECT 1")
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
        
        # Check Bloomberg connectivity (mock for development)
        bloomberg_status = "connected" if bloomberg_connector.is_connected else "disconnected"
        
        # Get latest processing run
        latest_run = (db.query(ProcessingLog)
                     .order_by(ProcessingLog.start_timestamp.desc())
                     .first())
        
        # Get performance metrics
        try:
            from sqlalchemy import func
            metrics_query = db.query(
                func.avg(ProcessingLog.coverage_rate).label('avg_coverage'),
                func.avg(ProcessingLog.calculation_success_rate).label('avg_success'),
                func.avg(ProcessingLog.validation_pass_rate).label('avg_validation'),
                func.count().label('total_runs')
            ).filter(ProcessingLog.process_date >= datetime.utcnow().date() - timedelta(days=7))
            
            metrics = metrics_query.first()
            
            performance_metrics = {
                "coverage_rate": round(metrics.avg_coverage or 0, 3),
                "calculation_success_rate": round(metrics.avg_success or 0, 3),
                "validation_pass_rate": round(metrics.avg_validation or 0, 3),
                "total_runs_7_days": metrics.total_runs or 0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get performance metrics: {e}")
            performance_metrics = {"error": "metrics_unavailable"}
        
        return SystemStatusResponse(
            status="operational",
            version="1.0.0",
            database_status=db_status,
            bloomberg_status=bloomberg_status,
            last_processing_run=latest_run.start_timestamp.isoformat() if latest_run else None,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to retrieve system status")


@app.get("/api/v1/ratings/history/{cusip}")
async def get_rating_history(
    cusip: str, 
    days: int = Query(default=90, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """
    Get rating history for a specific CUSIP
    
    Args:
        cusip: CUSIP identifier
        days: Number of days of history to retrieve
        db: Database session
        
    Returns:
        Rating history
    """
    try:
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)
        
        ratings = (db.query(CreditRating)
                  .filter(CreditRating.cusip == cusip)
                  .filter(CreditRating.calculation_date >= cutoff_date)
                  .order_by(CreditRating.calculation_date.desc())
                  .all())
        
        if not ratings:
            raise HTTPException(status_code=404, detail=f"No rating history found for CUSIP {cusip}")
        
        history = []
        for rating in ratings:
            history.append({
                "calculation_date": rating.calculation_date.isoformat(),
                "linvest21_rating": rating.linvest21_rating,
                "final_score": rating.final_score,
                "validation_status": rating.validation_status
            })
        
        return {
            "cusip": cusip,
            "history_days": days,
            "rating_count": len(history),
            "ratings": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rating history for {cusip}: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to retrieve rating history")


async def log_batch_processing(request_id: str, total_count: int, successful_count: int, 
                              failed_count: int, processing_time: float):
    """Background task to log batch processing metrics"""
    try:
        db = SessionLocal()
        
        log_entry = ProcessingLog(
            process_date=date.today(),
            process_type="BATCH_API",
            start_timestamp=datetime.utcnow() - timedelta(seconds=processing_time),
            end_timestamp=datetime.utcnow(),
            total_securities_processed=total_count,
            successful_calculations=successful_count,
            failed_calculations=failed_count,
            processing_time_seconds=processing_time,
            calculation_success_rate=successful_count / total_count if total_count > 0 else 0,
            process_status="COMPLETED",
            notes=f"Batch API request {request_id}"
        )
        
        db.add(log_entry)
        db.commit()
        db.close()
        
        logger.info(f"Logged batch processing metrics for request {request_id}")
        
    except Exception as e:
        logger.error(f"Failed to log batch processing metrics: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )