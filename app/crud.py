import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta
from typing import Optional, List
from . import models
from .config import settings
from .notification import send_hut_availability_email

logger = logging.getLogger(__name__)

def validate_status(status: str) -> bool:
    """Validate that status is one of the allowed values."""
    return status in ['free', 'booked']

def log_notification(db: Session, message: str, day: Optional[date] = None) -> bool:
    """Log a notification with proper error handling."""
    try:
        if not message or len(message.strip()) == 0:
            logger.warning("Attempted to log empty notification message")
            return False
        send_hut_availability_email(day)
        notif = models.Notification(date=day, message=message.strip())
        db.add(notif)
        db.commit()
        logger.info(f"[NOTIFY] {message}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to log notification: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error logging notification: {e}")
        db.rollback()
        return False

def cleanup_old_notifications(db: Session, days: int = None) -> int:
    """
    Remove notifications older than the given number of days.
    Returns number of deleted records.
    """
    if days is None:
        days = settings.max_notification_age_days
        
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = db.query(models.Notification).filter(models.Notification.created_at < cutoff).delete()
        db.commit()
        if deleted > 0:
            logger.info(f"[CLEANUP] Removed {deleted} old notifications (>{days} days).")
        return deleted
    except SQLAlchemyError as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        db.rollback()
        return 0
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")
        db.rollback()
        return 0

def cleanup_old_availability(db: Session, days: int = None) -> int:
    """
    Remove availability records older than the given number of days.
    Returns number of deleted records.
    """
    if days is None:
        days = settings.max_availability_age_days
        
    try:
        cutoff = date.today() - timedelta(days=days)
        deleted = db.query(models.Availability).filter(models.Availability.date < cutoff).delete()
        db.commit()
        if deleted > 0:
            logger.info(f"[CLEANUP] Removed {deleted} old availability records (>{days} days).")
        return deleted
    except SQLAlchemyError as e:
        logger.error(f"Failed to cleanup availability: {e}")
        db.rollback()
        return 0
    except Exception as e:
        logger.error(f"Unexpected error during availability cleanup: {e}")
        db.rollback()
        return 0

def get_by_date(db: Session, day: date) -> Optional[models.Availability]:
    """Get availability record by date with error handling."""
    try:
        return db.query(models.Availability).filter(models.Availability.date == day).first()
    except SQLAlchemyError as e:
        logger.error(f"Failed to get availability for {day}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting availability for {day}: {e}")
        return None

def update_or_create_availability(db: Session, day: date, status: str) -> bool:
    """Update or create availability record with validation and error handling."""
    try:
        # Validate inputs
        if not isinstance(day, date):
            logger.error(f"Invalid date type: {type(day)}")
            return False
            
        if not validate_status(status):
            logger.error(f"Invalid status '{status}' for date {day}")
            return False
            
        # Check if date is reasonable (not too far in the past or future)
        today = date.today()
        if day < today - timedelta(days=30):
            logger.warning(f"Date {day} is more than 30 days in the past")
        if day > today + timedelta(days=365):
            logger.warning(f"Date {day} is more than 1 year in the future")
            
        db_item = get_by_date(db, day)
        if db_item:
            if db_item.status != status:
                db_item.status = status
                db_item.last_checked = datetime.utcnow()
                if status == 'free':
                    msg = f"New free slot opened for Opfiger Hut on {day}: Status changed from {db_item.status} → {status}"
                    log_notification(db, msg, day)
                logger.info(f"Updated availability for {day}: {status}")
            else:
                # Update last_checked even if status didn't change
                db_item.last_checked = datetime.utcnow()
        else:
            db_item = models.Availability(date=day, status=status)
            db.add(db_item)
            if status == 'free':
                msg = f"New availability for Opfiger Hut found on {day} Status = ({status})"
                log_notification(db, msg, day)
            logger.info(f"Created new availability for {day}: {status}")

        db.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error updating availability for {day}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating availability for {day}: {e}")
        db.rollback()
        return False

def get_availability_stats(db: Session) -> dict:
    """Get statistics about availability data."""
    try:
        total = db.query(models.Availability).count()
        free = db.query(models.Availability).filter(models.Availability.status == 'free').count()
        booked = db.query(models.Availability).filter(models.Availability.status == 'booked').count()
        
        return {
            'total': total,
            'free': free,
            'booked': booked,
            'last_updated': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get availability stats: {e}")
        return {}
