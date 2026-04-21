import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta
from typing import Optional
from . import models
from .config import settings
from .notification import send_hut_availability_email

logger = logging.getLogger(__name__)

def validate_status(status: str) -> bool:
    """Validate that status is one of the allowed values."""
    return status in ["free", "booked"]


def sync_huts_from_config(db: Session) -> None:
    """Create/update hut master data from configuration."""
    for slug, hut_config in settings.tracked_huts.items():
        hut = db.query(models.Hut).filter(models.Hut.slug == slug).first()
        if hut:
            hut.name = hut_config["name"]
            hut.location = hut_config["location"]
            hut.booking_url = hut_config["base_url"]
            hut.is_active = True
            hut.updated_at = datetime.utcnow()
        else:
            db.add(
                models.Hut(
                    slug=slug,
                    name=hut_config["name"],
                    location=hut_config["location"],
                    booking_url=hut_config["base_url"],
                    is_active=True,
                )
            )

    configured_slugs = set(settings.tracked_huts.keys())
    stale_huts = db.query(models.Hut).filter(~models.Hut.slug.in_(configured_slugs)).all()
    for hut in stale_huts:
        hut.is_active = False
        hut.updated_at = datetime.utcnow()

    db.commit()


def get_hut_by_slug(db: Session, hut_slug: str) -> Optional[models.Hut]:
    """Return hut metadata by slug."""
    return db.query(models.Hut).filter(models.Hut.slug == hut_slug).first()


def log_notification(db: Session, message: str, hut_slug: str, day: Optional[date] = None) -> bool:
    """Log a notification with proper error handling."""
    try:
        if not message or len(message.strip()) == 0:
            logger.warning("Attempted to log empty notification message")
            return False
        send_hut_availability_email(day, hut_slug)
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

def get_by_hut_and_date(db: Session, hut: models.Hut, day: date) -> Optional[models.Availability]:
    """Get availability record by date with error handling."""
    try:
        return (
            db.query(models.Availability)
            .filter(models.Availability.hut_id == hut.id, models.Availability.date == day)
            .first()
        )
    except SQLAlchemyError as e:
        logger.error(f"Failed to get availability for {hut.slug} on {day}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting availability for {hut.slug} on {day}: {e}")
        return None


def update_or_create_availability(db: Session, hut_slug: str, day: date, status: str) -> bool:
    """Update or create availability record with validation and error handling."""
    try:
        hut = get_hut_by_slug(db, hut_slug)
        if not hut:
            logger.error(f"Hut with slug '{hut_slug}' does not exist in database.")
            return False
        hut_name = hut.name

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
            
        db_item = get_by_hut_and_date(db, hut, day)
        if db_item:
            if db_item.status != status:
                previous_status = db_item.status
                db_item.status = status
                db_item.last_checked = datetime.utcnow()
                if status == "free":
                    msg = f"New free slot opened for {hut_name} on {day}: Status changed from {previous_status} -> {status}"
                    log_notification(db, msg, hut_slug, day)
                logger.info(f"Updated availability for {hut_slug} on {day}: {status}")
            else:
                # Update last_checked even if status didn't change
                db_item.last_checked = datetime.utcnow()
        else:
            db_item = models.Availability(hut_id=hut.id, date=day, status=status)
            db.add(db_item)
            if status == "free":
                msg = f"New availability for {hut_name} found on {day} status=({status})"
                log_notification(db, msg, hut_slug, day)
            logger.info(f"Created new availability for {hut_slug} on {day}: {status}")

        db.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error updating availability for {hut_slug} on {day}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating availability for {hut_slug} on {day}: {e}")
        db.rollback()
        return False

def get_availability_stats(db: Session) -> dict:
    """Get statistics about availability data."""
    try:
        by_hut = {}
        huts = db.query(models.Hut).all()
        total = db.query(models.Availability).count()
        free = db.query(models.Availability).filter(models.Availability.status == "free").count()
        booked = db.query(models.Availability).filter(models.Availability.status == "booked").count()

        for hut in huts:
            hut_total = db.query(models.Availability).filter(models.Availability.hut_id == hut.id).count()
            hut_free = (
                db.query(models.Availability)
                .filter(models.Availability.hut_id == hut.id, models.Availability.status == "free")
                .count()
            )
            hut_booked = (
                db.query(models.Availability)
                .filter(models.Availability.hut_id == hut.id, models.Availability.status == "booked")
                .count()
            )
            by_hut[hut.slug] = {
                "name": hut.name,
                "total": hut_total,
                "free": hut_free,
                "booked": hut_booked,
            }

        return {
            "total": total,
            "free": free,
            "booked": booked,
            "by_hut": by_hut,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get availability stats: {e}")
        return {}
