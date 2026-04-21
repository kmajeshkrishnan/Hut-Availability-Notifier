import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta
from typing import Optional, Type
from . import models
from .config import settings
from .notification import send_hut_availability_email

logger = logging.getLogger(__name__)

AVAILABILITY_MODELS = {
    "opfinger": models.AvailabilityOpfinger,
    "st_georgs": models.AvailabilityStGeorgs,
}


def get_availability_model(hut_id: str) -> Type[models.AvailabilityOpfinger]:
    """Resolve hut id to the matching availability table model."""
    model = AVAILABILITY_MODELS.get(hut_id)
    if not model:
        raise ValueError(f"Unsupported hut_id: {hut_id}")
    return model

def validate_status(status: str) -> bool:
    """Validate that status is one of the allowed values."""
    return status in ['free', 'booked']

def log_notification(db: Session, message: str, hut_id: str, day: Optional[date] = None) -> bool:
    """Log a notification with proper error handling."""
    try:
        if not message or len(message.strip()) == 0:
            logger.warning("Attempted to log empty notification message")
            return False
        send_hut_availability_email(day, hut_id)
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
        deleted = 0
        for hut_id, availability_model in AVAILABILITY_MODELS.items():
            hut_deleted = db.query(availability_model).filter(availability_model.date < cutoff).delete()
            deleted += hut_deleted
            if hut_deleted > 0:
                logger.info(f"[CLEANUP] Removed {hut_deleted} old records from {hut_id}.")
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

def get_by_date(db: Session, day: date, hut_id: str):
    """Get availability record by date with error handling."""
    try:
        availability_model = get_availability_model(hut_id)
        return db.query(availability_model).filter(availability_model.date == day).first()
    except SQLAlchemyError as e:
        logger.error(f"Failed to get availability for {hut_id} on {day}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting availability for {hut_id} on {day}: {e}")
        return None

def update_or_create_availability(db: Session, hut_id: str, day: date, status: str) -> bool:
    """Update or create availability record with validation and error handling."""
    try:
        availability_model = get_availability_model(hut_id)
        hut_name = settings.tracked_huts[hut_id]["name"]

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
            
        db_item = get_by_date(db, day, hut_id)
        if db_item:
            if db_item.status != status:
                previous_status = db_item.status
                db_item.status = status
                db_item.last_checked = datetime.utcnow()
                if status == 'free':
                    msg = f"New free slot opened for {hut_name} on {day}: Status changed from {previous_status} -> {status}"
                    log_notification(db, msg, hut_id, day)
                logger.info(f"Updated availability for {hut_id} on {day}: {status}")
            else:
                # Update last_checked even if status didn't change
                db_item.last_checked = datetime.utcnow()
        else:
            db_item = availability_model(date=day, status=status)
            db.add(db_item)
            if status == 'free':
                msg = f"New availability for {hut_name} found on {day} status=({status})"
                log_notification(db, msg, hut_id, day)
            logger.info(f"Created new availability for {hut_id} on {day}: {status}")

        db.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error updating availability for {hut_id} on {day}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating availability for {hut_id} on {day}: {e}")
        db.rollback()
        return False

def get_availability_stats(db: Session) -> dict:
    """Get statistics about availability data."""
    try:
        by_hut = {}
        total = 0
        free = 0
        booked = 0

        for hut_id, availability_model in AVAILABILITY_MODELS.items():
            hut_total = db.query(availability_model).count()
            hut_free = db.query(availability_model).filter(availability_model.status == 'free').count()
            hut_booked = db.query(availability_model).filter(availability_model.status == 'booked').count()
            by_hut[hut_id] = {
                "total": hut_total,
                "free": hut_free,
                "booked": hut_booked,
            }
            total += hut_total
            free += hut_free
            booked += hut_booked

        return {
            'total': total,
            'free': free,
            'booked': booked,
            'by_hut': by_hut,
            'last_updated': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get availability stats: {e}")
        return {}
