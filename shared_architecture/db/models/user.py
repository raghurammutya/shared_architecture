from sqlalchemy import Column, Integer, String, ForeignKey,Enum
from sqlalchemy.orm import relationship
from app.models.group import Group
from shared_architecture.db import Base
from shared_architecture.models.enums import UserRole


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    phone_number = Column(String, unique=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    group = relationship("Group", back_populates="members")
    role = Column(Enum(UserRole), default=UserRole.USER)
    trading_accounts = relationship("TradingAccount", back_populates="user")
