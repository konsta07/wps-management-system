from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class WPQR(Base):
    __tablename__ = "wpqr_records"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wps_id = Column(Integer, ForeignKey("wps_records.id"), nullable=True)
    
    # Основная информация WPQR
    wpqr_number = Column(String(100), nullable=False, index=True)
    test_date = Column(DateTime(timezone=True))
    welder_name = Column(String(200))
    welder_qualification = Column(String(100))  # Номер аттестации сварщика
    
    # Фактические параметры сварки (при квалификации)
    actual_joint_design = Column(Text)
    actual_base_material = Column(String(200))
    base_metal_thickness = Column(Float)
    actual_filler_material = Column(String(200))
    actual_welding_position = Column(String(50))
    actual_preheat_temp = Column(Integer)  # °C
    actual_interpass_temp = Column(Integer)  # °C
    
    # Электрические параметры (фактические)
    actual_current = Column(Integer)  # Ампер
    actual_voltage = Column(Float)  # Вольт
    actual_travel_speed = Column(Float)  # мм/мин
    actual_heat_input = Column(Float)  # кДж/мм
    
    # Результаты механических испытаний
    # Испытание на растяжение
    tensile_strength = Column(Float)  # МПа
    tensile_location = Column(String(50))  # Weld, HAZ, Base
    tensile_result = Column(String(20))  # Pass/Fail
    
    # Испытание на изгиб
    bend_test_type = Column(String(50))  # Face, Root, Side
    bend_test_angle = Column(Integer)  # градусы
    bend_test_result = Column(String(20))  # Pass/Fail
    bend_test_notes = Column(Text)
    
    # Испытание на ударную вязкость (если требуется)
    impact_test_temp = Column(Integer)  # °C
    impact_energy_weld = Column(Float)  # Джоули
    impact_energy_haz = Column(Float)  # Джоули
    impact_result = Column(String(20))  # Pass/Fail
    
    # Макроструктурный анализ
    macro_examination_result = Column(String(20))  # Pass/Fail
    macro_notes = Column(Text)
    
    # NDT испытания
    ndt_method = Column(String(100))  # RT, UT, PT, MT
    ndt_standard = Column(String(100))  # Стандарт контроля
    ndt_result = Column(String(20))  # Pass/Fail
    ndt_report_number = Column(String(100))
    
    # Заключение
    overall_result = Column(String(20), nullable=False)  # Qualified/Not Qualified
    qualified_thickness_range = Column(String(100))  # Квалифицированный диапазон толщин
    qualified_positions = Column(String(100))  # Квалифицированные положения
    qualified_materials = Column(Text)  # Квалифицированные материалы
    
    # Подписи и утверждения
    tested_by = Column(String(200))
    witnessed_by = Column(String(200))
    approved_by = Column(String(200))
    approved_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    company = relationship("Company", back_populates="wpqr_records")
    qualified_wps = relationship("WPS", back_populates="wpqr_records")