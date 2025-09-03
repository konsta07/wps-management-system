from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class WPS(Base):
    __tablename__ = "wps_records"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Основная информация WPS
    wps_number = Column(String(100), nullable=False, index=True)
    revision = Column(String(10), default="0")
    title = Column(String(200))
    welding_process = Column(String(100), nullable=False)  # GMAW, SMAW, GTAW, etc.
    
    # Материалы
    base_material_spec = Column(String(200))  # Спецификация основного материала
    base_material_grade = Column(String(100))  # Марка стали
    base_material_thickness_min = Column(Float)  # мм
    base_material_thickness_max = Column(Float)  # мм
    
    filler_material_spec = Column(String(200))  # Спецификация присадочного материала  
    filler_material_classification = Column(String(100))  # Классификация по AWS/ISO
    filler_material_diameter = Column(String(50))  # Диаметр проволоки/электрода
    
    # Параметры сварки
    welding_positions = Column(String(50))  # PA, PB, PC, PD, PE, PF, PG
    joint_type = Column(String(50))  # BW (butt weld), FW (fillet weld)
    joint_preparation = Column(Text)  # Описание разделки кромок
    
    # Электрические параметры
    current_type = Column(String(20))  # AC, DC+, DC-
    current_range_min = Column(Integer)  # Ампер
    current_range_max = Column(Integer)  # Ампер
    voltage_range_min = Column(Float)  # Вольт
    voltage_range_max = Column(Float)  # Вольт
    travel_speed_min = Column(Float)  # мм/мин
    travel_speed_max = Column(Float)  # мм/мин
    
    # Термообработка
    preheat_temp_min = Column(Integer)  # °C
    preheat_temp_max = Column(Integer)  # °C
    interpass_temp_max = Column(Integer)  # °C
    pwht_required = Column(Boolean, default=False)  # Post Weld Heat Treatment
    pwht_temperature = Column(Integer)  # °C
    pwht_time = Column(Float)  # часы
    
    # Защитный газ (для GMAW, GTAW)
    shielding_gas_composition = Column(String(200))
    gas_flow_rate = Column(Float)  # л/мин
    
    # Статус и даты
    status = Column(String(50), default="Draft")  # Draft, Active, Superseded, Obsolete
    qualified_by_wpqr = Column(String(200))  # Номера квалифицирующих WPQR
    approved_by = Column(String(200))
    approved_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    company = relationship("Company", back_populates="wps_records")
    wpqr_records = relationship("WPQR", back_populates="qualified_wps")