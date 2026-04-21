from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Hut(Base):
    __tablename__ = "huts"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    booking_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    availabilities = relationship("Availability", back_populates="hut")


class Availability(Base):
    __tablename__ = "hut_availability"
    __table_args__ = (UniqueConstraint("hut_id", "date", name="uq_availability_hut_date"),)

    id = Column(Integer, primary_key=True, index=True)
    hut_id = Column(Integer, ForeignKey("huts.id"), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    status = Column(String, index=True)  # 'free', 'booked'
    last_checked = Column(DateTime, default=datetime.utcnow)

    hut = relationship("Hut", back_populates="availabilities")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
