# models/welder.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Welder(Base):
    __tablename__ = "welders"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Основная информация
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    middle_name = Column(String(100), nullable=True)  # Отчество
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    employee_number = Column(String(50), nullable=True)  # Табельный номер
    
    # Статус сварщика
    status = Column(String(20), default="Active")  # Active, Inactive, Suspended
    hire_date = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    company = relationship("Company", back_populates="welders")
    certificates = relationship("WelderCertificate", back_populates="welder", cascade="all, delete-orphan")

class WelderCertificate(Base):
    __tablename__ = "welder_certificates"
    
    id = Column(Integer, primary_key=True, index=True)
    welder_id = Column(Integer, ForeignKey("welders.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Информация о сертификате
    certificate_number = Column(String(100), nullable=False, index=True)
    certification_body = Column(String(200), nullable=False)  # НАКС, AWS, etc.
    
    # Группа сварки и метод
    welding_group = Column(String(50), nullable=False)  # Группа (А, Б, В, Г и т.д.)
    welding_method = Column(String(100), nullable=False)  # РД, АД, ПП, etc.
    welding_process = Column(String(50), nullable=False)  # SMAW, GMAW, GTAW, etc.
    
    # Материалы и толщины
    base_material = Column(String(200), nullable=True)  # Основной материал
    thickness_range = Column(String(100), nullable=True)  # Диапазон толщин
    welding_positions = Column(String(100), nullable=True)  # Положения сварки
    
    # Даты
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    next_test_date = Column(Date, nullable=True)  # Дата следующего переосвидетельствования
    
    # Файлы
    certificate_file_url = Column(String(500), nullable=True)  # Скан сертификата
    
    # Статус
    status = Column(String(20), default="Valid")  # Valid, Expired, Suspended, Renewed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    welder = relationship("Welder", back_populates="certificates")
    company = relationship("Company")