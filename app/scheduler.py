import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime
from .scraper import fetch_calendar_data
from .database import get_db_session, test_database_connection
from . import crud
from .config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def job_listener(event):
    """Listen to scheduler events for monitoring."""
    if event.exception:
        logger.error(f"Scheduled job failed: {event.exception}")
    else:
        logger.info(f"Scheduled job completed successfully")

def availability_check_job():
    """Main job function with comprehensive error handling."""
    start_time = datetime.utcnow()
    logger.info("[SCHEDULER] Starting availability check...")
    
    try:
        # Test database connection first
        if not test_database_connection():
            logger.error("Database connection test failed - skipping this cycle")
            return
            
        # Process data with database session
        with get_db_session() as db:
            success_count = 0
            error_count = 0

            for hut_id, hut_config in settings.tracked_huts.items():
                # Fetch calendar data for each hut independently.
                data = fetch_calendar_data(hut_config["base_url"])
                if not data:
                    logger.warning(f"No calendar data retrieved for {hut_id} - skipping")
                    continue

                for day, status in data.items():
                    logger.debug(f"[SCHEDULER] {hut_id} data {day} ({day.strftime('%A')}): {status}")
                    if crud.update_or_create_availability(db, hut_id, day, status):
                        success_count += 1
                    else:
                        error_count += 1
                    
            logger.info(f"Processed {success_count} availability records successfully, {error_count} errors")
            
            # Cleanup old data
            crud.cleanup_old_notifications(db)
            crud.cleanup_old_availability(db)
            
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"[SCHEDULER] Availability check completed in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"[SCHEDULER] Job failed with unexpected error: {e}", exc_info=True)
        # Don't re-raise to prevent scheduler from stopping

def start_scheduler():
    """Start the background scheduler with proper configuration."""
    global scheduler
    
    if scheduler and scheduler.running:
        logger.warning("Scheduler is already running")
        return
        
    try:
        # Configure job store and executor
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=2)
        }
        
        # Create scheduler with configuration
        scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone='UTC'
        )
        
        # Add event listener for monitoring
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Add the main job
        scheduler.add_job(
            availability_check_job,
            'interval',
            minutes=settings.check_interval_minutes,
            id='availability_check',
            name='Availability Check Job',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        logger.info(f"[SCHEDULER] Started - runs every {settings.check_interval_minutes} minutes")
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise

def stop_scheduler():
    """Stop the scheduler gracefully."""
    global scheduler
    
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("[SCHEDULER] Stopped gracefully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    else:
        logger.warning("Scheduler is not running")

def get_scheduler_status():
    """Get current scheduler status."""
    if not scheduler:
        return {"status": "not_initialized"}
        
    if not scheduler.running:
        return {"status": "stopped"}
        
    jobs = scheduler.get_jobs()
    return {
        "status": "running",
        "jobs": len(jobs),
        "next_run": jobs[0].next_run_time.isoformat() if jobs else None
    }
