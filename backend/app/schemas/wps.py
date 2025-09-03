from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WPSBase(BaseModel):
    wps_number: str
    revision: str = "0"
    title: Optional[str] = None
    welding_process: str
    
    # Материалы
    base_material_spec: Optional[str] = None
    base_material_grade: Optional[str] = None
    base_material_thickness_min: Optional[float] = None
    base_material_thickness_max: Optional[float] = None
    
    filler_material_spec: Optional[str] = None
    filler_material_classification: Optional[str] = None
    filler_material_diameter: Optional[str] = None
    
    # Параметры сварки
    welding_positions: Optional[str] = None
    joint_type: Optional[str] = None
    joint_preparation: Optional[str] = None
    
    # Электрические параметры
    current_type: Optional[str] = None
    current_range_min: Optional[int] = None
    current_range_max: Optional[int] = None
    voltage_range_min: Optional[float] = None
    voltage_range_max: Optional[float] = None
    travel_speed_min: Optional[float] = None
    travel_speed_max: Optional[float] = None
    
    # Термообработка
    preheat_temp_min: Optional[int] = None
    preheat_temp_max: Optional[int] = None
    interpass_temp_max: Optional[int] = None
    pwht_required: bool = False
    pwht_temperature: Optional[int] = None
    pwht_time: Optional[float] = None
    
    # Защитный газ
    shielding_gas_composition: Optional[str] = None
    gas_flow_rate: Optional[float] = None
    
    # Статус
    status: str = "Draft"
    qualified_by_wpqr: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

class WPSCreate(WPSBase):
    company_id: int

class WPSUpdate(BaseModel):
    wps_number: Optional[str] = None
    revision: Optional[str] = None
    title: Optional[str] = None
    welding_process: Optional[str] = None
    base_material_spec: Optional[str] = None
    base_material_grade: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[str] = None

class WPS(WPSBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True