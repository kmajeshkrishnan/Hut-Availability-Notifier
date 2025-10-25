import logging
from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from datetime import date, datetime
from .database import Base, engine, get_db_session, test_database_connection
from .scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from . import models, crud
from .config import settings, setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Opfinger Availability Monitor",
    description="A monitoring service for Opfinger Hütte availability",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def get_db():
    """Dependency for database sessions."""
    with get_db_session() as db:
        yield db

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        logger.info("Starting Opfinger Availability Monitor...")
        
        # Test database connection
        if not test_database_connection():
            logger.error("Database connection failed during startup")
            raise Exception("Database connection failed")
            
        # Start scheduler
        start_scheduler()
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    try:
        logger.info("Shutting down application...")
        stop_scheduler()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

@app.get("/", tags=["Health"])
def root():
    """Root endpoint with basic status."""
    return {
        "status": "Opfinger availability monitor running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Test database connection
        db_healthy = test_database_connection()
        
        # Get scheduler status
        scheduler_status = get_scheduler_status()
        
        # Overall health
        healthy = db_healthy and scheduler_status.get("status") == "running"
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "scheduler": scheduler_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/stats", tags=["Monitoring"])
def get_stats(db: Session = Depends(get_db)):
    """Get application statistics."""
    try:
        stats = crud.get_availability_stats(db)
        scheduler_status = get_scheduler_status()
        
        return {
            "availability": stats,
            "scheduler": scheduler_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

@app.get("/availability", tags=["Data"])
def get_availability(
    status: Optional[str] = Query(None, description="Filter by status: free/booked"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get availability data with optional filtering."""
    try:
        # Validate status parameter
        if status and status.lower() not in ['free', 'booked']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be one of: free, booked"
            )
            
        query = db.query(models.Availability)
        if status:
            query = query.filter(models.Availability.status == status.lower())
            
        data = query.order_by(models.Availability.date.asc()).limit(limit).all()
        
        return [
            {
                "date": a.date.isoformat(),
                "status": a.status,
                "last_checked": a.last_checked.isoformat() if a.last_checked else None
            }
            for a in data
        ]
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/notifications", tags=["Data"])
def get_notifications(
    limit: int = Query(
        settings.default_notifications_limit,
        ge=1,
        le=settings.max_notifications_limit,
        description="Maximum number of recent notifications to return"
    ),
    db: Session = Depends(get_db)
):
    """Get recent notification logs."""
    try:
        notifs = db.query(models.Notification)\
            .order_by(models.Notification.created_at.desc())\
            .limit(limit)\
            .all()
            
        return [
            {
                "date": n.date.isoformat() if n.date else None,
                "message": n.message,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ]
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/scheduler/status", tags=["Monitoring"])
def get_scheduler_status_endpoint():
    """Get current scheduler status."""
    try:
        return get_scheduler_status()
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduler status"
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
