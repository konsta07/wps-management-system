# models/user.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    full_name = Column(String(200))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# УБРАНО ВСЁ ЛИШНЕЕ:
# - code (это поле компании)
# - address (это поле компании) 
# - phone (это поле компании)
# - contact_person (это поле компании)
# - welding_standards (это поле компании)
# - certification_body (это поле компании)
# - wps_records, wpqr_records (связи компании)