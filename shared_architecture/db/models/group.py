from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from shared_architecture.db.base import Base

class Group(Base):
    __tablename__ = "groups" # type: ignore
    __table_args__ = {'schema': 'tradingdb'}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("tradingdb.users.id"))
    members = relationship("User", back_populates="group", foreign_keys="User.group_id")