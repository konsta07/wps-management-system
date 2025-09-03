from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import validator

@validator('overall_result')
def validate_overall_result(cls, v):
    if v not in ['Qualified', 'Not Qualified']:
        raise ValueError('Must be Qualified or Not Qualified')
    return v
class WPQRBase(BaseModel):
    wpqr_number: str
    test_date: Optional[datetime] = None
    welder_name: Optional[str] = None
    welder_qualification: Optional[str] = None
    
    # Фактические параметры
    actual_joint_design: Optional[str] = None
    actual_base_material: Optional[str] = None
    actual_filler_material: Optional[str] = None
    actual_welding_position: Optional[str] = None
    actual_preheat_temp: Optional[int] = None
    actual_interpass_temp: Optional[int] = None
    
    actual_current: Optional[int] = None
    actual_voltage: Optional[float] = None
    actual_travel_speed: Optional[float] = None
    actual_heat_input: Optional[float] = None
    
    # Результаты испытаний
    tensile_strength: Optional[float] = None
    tensile_location: Optional[str] = None
    tensile_result: Optional[str] = None
    
    bend_test_type: Optional[str] = None
    bend_test_angle: Optional[int] = None
    bend_test_result: Optional[str] = None
    bend_test_notes: Optional[str] = None
    
    impact_test_temp: Optional[int] = None
    impact_energy_weld: Optional[float] = None
    impact_energy_haz: Optional[float] = None
    impact_result: Optional[str] = None
    
    macro_examination_result: Optional[str] = None
    macro_notes: Optional[str] = None
    
    ndt_method: Optional[str] = None
    ndt_standard: Optional[str] = None
    ndt_result: Optional[str] = None
    ndt_report_number: Optional[str] = None
    
    # Заключение
    overall_result: str
    qualified_thickness_range: Optional[str] = None
    qualified_positions: Optional[str] = None
    qualified_materials: Optional[str] = None
    
    tested_by: Optional[str] = None
    witnessed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

class WPQRCreate(WPQRBase):
    company_id: int
    wps_id: Optional[int] = None

class WPQRUpdate(BaseModel):
    wpqr_number: Optional[str] = None
    test_date: Optional[datetime] = None
    welder_name: Optional[str] = None
    welder_qualification: Optional[str] = None
    
    # Результаты испытаний
    tensile_strength: Optional[float] = None
    tensile_result: Optional[str] = None
    bend_test_result: Optional[str] = None
    impact_result: Optional[str] = None
    macro_examination_result: Optional[str] = None
    ndt_result: Optional[str] = None
    
    # Заключение
    overall_result: Optional[str] = None
    qualified_thickness_range: Optional[str] = None
    qualified_positions: Optional[str] = None
    
    # Утверждение
    tested_by: Optional[str] = None
    witnessed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

class WPQR(WPQRBase):
    id: int
    company_id: int
    wps_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True