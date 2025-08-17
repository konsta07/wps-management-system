# models/company.py - С ДОБАВЛЕННЫМ ПОЛЕМ LOGO_URL
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(100))
    contact_person = Column(String(200))
    
    # Техническая информация
    welding_standards = Column(String(200))
    certification_body = Column(String(200))
    
    # ДОБАВЛЕНО: Логотип компании
    logo_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи с другими таблицами
    wps_records = relationship("WPS", back_populates="company", cascade="all, delete-orphan")
    wpqr_records = relationship("WPQR", back_populates="company", cascade="all, delete-orphan")
    welders = relationship("Welder", back_populates="company", cascade="all, delete-orphan")  # ДОБАВЛЕНО