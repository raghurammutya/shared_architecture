from sqlalchemy import Column, Integer, String, DateTime, Text
from shared_architecture.db.base import Base
from shared_architecture.utils.datetime_utils import utc_now 
import datetime

class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=utc_now())
