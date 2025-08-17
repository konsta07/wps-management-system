# schemas/company.py - С ДОБАВЛЕНИЕМ LOGO_URL
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    code: str
    address: str
    phone: str
    email: str
    contact_person: Optional[str] = None
    welding_standards: Optional[str] = None
    certification_body: Optional[str] = None
    logo_url: Optional[str] = None  # ДОБАВЛЕНО

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    welding_standards: Optional[str] = None
    certification_body: Optional[str] = None
    logo_url: Optional[str] = None  # ДОБАВЛЕНО

class Company(CompanyBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True