from sqlalchemy import Column, Integer, String, Date, DateTime
from datetime import datetime
from .database import Base

class AvailabilityOpfinger(Base):
    __tablename__ = "availability_opfinger"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    status = Column(String, index=True)  # 'free', 'booked'
    last_checked = Column(DateTime, default=datetime.utcnow)


class AvailabilityStGeorgs(Base):
    __tablename__ = "availability_st_georgs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    status = Column(String, index=True)  # 'free', 'booked'
    last_checked = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
