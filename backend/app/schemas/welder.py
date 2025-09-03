# schemas/welder.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# Схемы для сертификатов
class WelderCertificateBase(BaseModel):
    certificate_number: str
    certification_body: str
    welding_group: str
    welding_method: str
    welding_process: str
    base_material: Optional[str] = None
    thickness_range: Optional[str] = None
    welding_positions: Optional[str] = None
    issue_date: date
    expiry_date: date
    next_test_date: Optional[date] = None
    status: Optional[str] = "Valid"

class WelderCertificateCreate(WelderCertificateBase):
    welder_id: int
    company_id: int

class WelderCertificateUpdate(BaseModel):
    certificate_number: Optional[str] = None
    certification_body: Optional[str] = None
    welding_group: Optional[str] = None
    welding_method: Optional[str] = None
    welding_process: Optional[str] = None
    base_material: Optional[str] = None
    thickness_range: Optional[str] = None
    welding_positions: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    next_test_date: Optional[date] = None
    status: Optional[str] = None
    certificate_file_url: Optional[str] = None

class WelderCertificate(WelderCertificateBase):
    id: int
    welder_id: int
    company_id: int
    certificate_file_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Схемы для сварщиков
class WelderBase(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_number: Optional[str] = None
    status: Optional[str] = "Active"
    hire_date: Optional[date] = None

class WelderCreate(WelderBase):
    company_id: int

class WelderUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_number: Optional[str] = None
    status: Optional[str] = None
    hire_date: Optional[date] = None

class Welder(WelderBase):
    id: int
    company_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    certificates: List[WelderCertificate] = []

    class Config:
        from_attributes = True

# Схема для уведомлений об истекающих сертификатах
class ExpiringCertificate(BaseModel):
    certificate_id: int
    welder_name: str
    certificate_number: str
    welding_group: str
    welding_method: str
    expiry_date: date
    days_until_expiry: int
    urgency_level: str  # "warning" (60+ days), "urgent" (30-60 days), "critical" (<30 days)

class ExpiringCertificatesResponse(BaseModel):
    company_id: int
    company_name: str
    total_expiring: int
    critical: List[ExpiringCertificate] = []
    urgent: List[ExpiringCertificate] = []
    warning: List[ExpiringCertificate] = []