# backend/app/main.py - Исправленная версия
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import uvicorn
import os
import uuid
from pathlib import Path
import shutil
from datetime import date, timedelta

from .database import get_db, create_tables
from .models import Company as CompanyModel, WPS as WPSModel, WPQR as WPQRModel
from .models.welder import Welder as WelderModel, WelderCertificate as WelderCertificateModel
from .schemas import (
    Company, CompanyCreate, CompanyUpdate,
    WPS, WPSCreate, WPSUpdate,
    WPQR, WPQRCreate, WPQRUpdate
)
from .schemas.welder import (
    Welder, WelderCreate, WelderUpdate,
    WelderCertificate, WelderCertificateCreate, WelderCertificateUpdate,
    ExpiringCertificatesResponse, ExpiringCertificate
)
# ✅ СОЗДАЕМ APP СНАЧАЛА
app = FastAPI(
    title="WPS Management System",
    description="Система управления технологическими картами сварки (WPS) и протоколами квалификации (WPQR)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ✅ CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
STATIC_DIR = Path("static")
LOGOS_DIR = STATIC_DIR / "logos"
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ ПОДКЛЮЧЕНИЕ PDF РОУТЕРА ПОСЛЕ СОЗДАНИЯ APP
try:
    from .services.pdf_generator import pdf_router
    app.include_router(pdf_router)
    print("✅ PDF router подключен успешно")
except ImportError as e:
    print(f"⚠️ PDF router не подключен: {e}")
except Exception as e:
    print(f"⚠️ Ошибка подключения PDF router: {e}")

# Создание таблиц при запуске
@app.on_event("startup")
async def startup_event():
    """Инициализация базы данных при запуске приложения"""
    try:
        create_tables()
        print("✅ База данных инициализирована")
        print("🚀 Сервер запущен: http://localhost:8000")
        print("📚 API документация: http://localhost:8000/docs")
    except Exception as e:
        print(f"⚠️ Ошибка создания таблиц: {e}")

# =====================================
# БАЗОВЫЕ ENDPOINTS
# =====================================

@app.get("/")
async def root():
    return {
        "message": "WPS Management System API", 
        "version": "1.0.0",
        "docs": "/docs",
        "status": "Full CRUD operations available for Companies, WPS, and WPQR",
        "available_endpoints": {
            "companies": {
                "list": "GET /companies",
                "create": "POST /companies", 
                "get": "GET /companies/{id}",
                "update": "PUT /companies/{id}",
                "delete": "DELETE /companies/{id}",
                "search": "GET /companies/search/{term}",
                "filter": "GET /companies/filter",
                "create_sample": "POST /companies/create-sample"
            },
            "wps": {
                "list": "GET /wps",
                "create": "POST /wps",
                "get": "GET /wps/{id}",
                "update": "PUT /wps/{id}",
                "delete": "DELETE /wps/{id}",
                "by_company": "GET /wps/by-company/{company_id}",
                "search": "GET /wps/search/{term}",
                "create_sample": "POST /wps/create-sample"
            },
            "wpqr": {
                "list": "GET /wpqr",
                "create": "POST /wpqr",
                "get": "GET /wpqr/{id}",
                "update": "PUT /wpqr/{id}",
                "delete": "DELETE /wpqr/{id}",
                "by_company": "GET /wpqr/by-company/{company_id}",
                "by_wps": "GET /wpqr/by-wps/{wps_id}",
                "search": "GET /wpqr/search/{term}",
                "create_sample": "POST /wpqr/create-sample"
            },
            "welders": {
                "list": "GET /welders",
                "create": "POST /welders",
                "get": "GET /welders/{id}",
                "update": "PUT /welders/{id}",
                "delete": "DELETE /welders/{id}",
                "by_company": "GET /welders/by-company/{company_id}",
                "create_sample": "POST /welders/create-sample"
            },
            "certificates": {
                "list": "GET /certificates",
                "create": "POST /certificates",
                "get": "GET /certificates/{id}",
                "update": "PUT /certificates/{id}",
                "delete": "DELETE /certificates/{id}",
                "upload_file": "POST /certificates/{id}/upload-file",
                "expiring": "GET /companies/{id}/expiring-certificates"
            },
            "pdf": {
                "wps_pdf": "GET /api/pdf/wps/{wps_id}",
                "wpqr_pdf_advanced": "GET /api/pdf/wpqr/{wpqr_id}",
                "wpqr_pdf_simple": "GET /api/pdf/wpqr/{wpqr_id}?simple=true"
            },
            "system": {
                "health": "GET /health",
                "test_db": "GET /test-db"
            }
        }
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {"status": "healthy", "database": "connected", "test_query": result}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

@app.get("/test-db")
async def test_database():
    """Тестирование создания базы данных"""
    try:
        from .database import engine
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            
        return {
            "status": "success",
            "database_file": "wps_system.db",
            "tables_created": tables,
            "tables_count": len(tables)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image_file(file: UploadFile) -> None:
    """Валидация загружаемого файла изображения"""
    # Проверяем расширение файла
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Проверяем MIME тип
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть изображением"
        )

def save_logo_file(file: UploadFile, company_id: int) -> str:
    """Сохранение файла логотипа и возврат URL"""
    # Генерируем уникальное имя файла
    file_ext = Path(file.filename).suffix.lower()
    filename = f"company_{company_id}_{uuid.uuid4()}{file_ext}"
    file_path = LOGOS_DIR / filename
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сохранения файла: {str(e)}"
        )
    
    # Возвращаем URL для доступа к файлу
    return f"/static/logos/{filename}"

def delete_old_logo(logo_url: str) -> None:
    """Удаление старого файла логотипа"""
    if logo_url and logo_url.startswith("/static/logos/"):
        old_file_path = Path("static") / logo_url.replace("/static/", "")
        if old_file_path.exists():
            try:
                old_file_path.unlink()
            except Exception as e:
                print(f"⚠️ Не удалось удалить старый логотип {old_file_path}: {e}")

@app.post("/companies/{company_id}/upload-logo")
async def upload_company_logo(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка логотипа для компании"""
    
    # Проверяем, что компания существует
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Валидируем файл
    validate_image_file(file)
    
    # Проверяем размер файла
    file.file.seek(0, 2)  # Переходим в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Удаляем старый логотип, если есть
    if company.logo_url:
        delete_old_logo(company.logo_url)
    
    # Сохраняем новый файл
    logo_url = save_logo_file(file, company_id)
    
    # Обновляем запись в базе данных
    company.logo_url = logo_url
    db.commit()
    db.refresh(company)
    
    return {
        "message": "Логотип загружен успешно",
        "logo_url": logo_url,
        "filename": file.filename,
        "file_size": file_size,
        "company": {
            "id": company.id,
            "name": company.name,
            "logo_url": company.logo_url
        }
    }

@app.delete("/companies/{company_id}/delete-logo")
def delete_company_logo(company_id: int, db: Session = Depends(get_db)):
    """Удаление логотипа компании"""
    
    # Проверяем, что компания существует
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not company.logo_url:
        raise HTTPException(status_code=404, detail="У компании нет логотипа")
    
    # Удаляем файл
    delete_old_logo(company.logo_url)
    
    # Обновляем запись в базе данных
    old_logo_url = company.logo_url
    company.logo_url = None
    db.commit()
    
    return {
        "message": "Логотип удален успешно",
        "deleted_logo_url": old_logo_url,
        "company": {
            "id": company.id,
            "name": company.name,
            "logo_url": company.logo_url
        }
    }

@app.get("/companies/{company_id}/logo")
def get_company_logo_info(company_id: int, db: Session = Depends(get_db)):
    """Получение информации о логотипе компании"""
    
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not company.logo_url:
        return {
            "has_logo": False,
            "logo_url": None,
            "company_name": company.name
        }
    
    # Проверяем, существует ли файл
    logo_path = Path("static") / company.logo_url.replace("/static/", "")
    file_exists = logo_path.exists()
    
    return {
        "has_logo": True,
        "logo_url": company.logo_url,
        "file_exists": file_exists,
        "company_name": company.name,
        "file_path": str(logo_path) if file_exists else None
    }
# =====================================
# COMPANIES CRUD ENDPOINTS
# =====================================

@app.get("/companies", response_model=List[Company])
def get_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получить список всех компаний с пагинацией"""
    companies = db.query(CompanyModel).offset(skip).limit(limit).all()
    return companies

@app.get("/companies/{company_id}", response_model=Company)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Получить компанию по ID"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.post("/companies", response_model=Company, status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Создать новую компанию"""
    existing_company = db.query(CompanyModel).filter(CompanyModel.code == company.code).first()
    if existing_company:
        raise HTTPException(
            status_code=400, 
            detail=f"Company with code '{company.code}' already exists"
        )
    
    db_company = CompanyModel(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

@app.put("/companies/{company_id}", response_model=Company)
def update_company(company_id: int, company_update: CompanyUpdate, db: Session = Depends(get_db)):
    """Обновить компанию"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = company_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    return company

@app.delete("/companies/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """Удалить компанию"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    
    db.delete(company)
    db.commit()
    return {"message": f"Company '{company.name}' deleted successfully", "deleted_id": company_id}

@app.get("/companies/search/{search_term}")
def search_companies(search_term: str, db: Session = Depends(get_db)):
    """Поиск компаний по названию или коду (регистронезависимый)"""
    companies = db.query(CompanyModel).filter(
        CompanyModel.name.ilike(f"%{search_term}%") | 
        CompanyModel.code.ilike(f"%{search_term}%")
    ).all()
    
    return {
        "search_term": search_term,
        "search_mode": "case_insensitive",
        "found_count": len(companies),
        "companies": [
            {
                "id": c.id, 
                "name": c.name, 
                "code": c.code, 
                "email": c.email
            } for c in companies
        ]
    }

@app.get("/companies/filter")
def filter_companies(
    name: str = None, 
    code: str = None, 
    db: Session = Depends(get_db)
):
    """Фильтрация компаний по различным критериям"""
    query = db.query(CompanyModel)
    
    filters_applied = []
    
    if name:
        query = query.filter(CompanyModel.name.ilike(f"%{name}%"))
        filters_applied.append(f"name contains '{name}'")
        
    if code:
        query = query.filter(CompanyModel.code.ilike(f"%{code}%"))
        filters_applied.append(f"code contains '{code}'")
    
    companies = query.all()
    
    return {
        "filters_applied": filters_applied,
        "found_count": len(companies),
        "companies": [
            {
                "id": c.id,
                "name": c.name, 
                "code": c.code,
                "certification_body": c.certification_body
            } for c in companies
        ]
    }

# =====================================
# WPS CRUD ENDPOINTS  
# =====================================

@app.get("/wps", response_model=List[WPS])
def get_wps_list(
    company_id: int = None, 
    status: str = None,
    welding_process: str = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Получить список WPS с фильтрацией"""
    query = db.query(WPSModel)
    
    if company_id:
        query = query.filter(WPSModel.company_id == company_id)
    if status:
        query = query.filter(WPSModel.status.ilike(f"%{status}%"))
    if welding_process:
        query = query.filter(WPSModel.welding_process.ilike(f"%{welding_process}%"))
    
    wps_list = query.offset(skip).limit(limit).all()
    return wps_list

@app.get("/wps/{wps_id}", response_model=WPS)
def get_wps(wps_id: int, db: Session = Depends(get_db)):
    """Получить WPS по ID"""
    wps = db.query(WPSModel).filter(WPSModel.id == wps_id).first()
    if wps is None:
        raise HTTPException(status_code=404, detail="WPS not found")
    return wps

@app.post("/wps", response_model=WPS, status_code=status.HTTP_201_CREATED)
def create_wps(wps: WPSCreate, db: Session = Depends(get_db)):
    """Создать новый WPS"""
    company = db.query(CompanyModel).filter(CompanyModel.id == wps.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    existing_wps = db.query(WPSModel).filter(
        WPSModel.company_id == wps.company_id,
        WPSModel.wps_number == wps.wps_number
    ).first()
    if existing_wps:
        raise HTTPException(
            status_code=400, 
            detail=f"WPS number '{wps.wps_number}' already exists for company '{company.name}'"
        )
    
    db_wps = WPSModel(**wps.dict())
    db.add(db_wps)
    db.commit()
    db.refresh(db_wps)
    return db_wps

@app.put("/wps/{wps_id}", response_model=WPS)
def update_wps(wps_id: int, wps_update: WPSUpdate, db: Session = Depends(get_db)):
    """Обновить WPS"""
    wps = db.query(WPSModel).filter(WPSModel.id == wps_id).first()
    if wps is None:
        raise HTTPException(status_code=404, detail="WPS not found")
    
    update_data = wps_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(wps, field, value)
    
    db.commit()
    db.refresh(wps)
    return wps

@app.delete("/wps/{wps_id}")
def delete_wps(wps_id: int, db: Session = Depends(get_db)):
    """Удалить WPS"""
    wps = db.query(WPSModel).filter(WPSModel.id == wps_id).first()
    if wps is None:
        raise HTTPException(status_code=404, detail="WPS not found")
    
    wps_number = wps.wps_number
    db.delete(wps)
    db.commit()
    return {"message": f"WPS '{wps_number}' deleted successfully", "deleted_id": wps_id}

@app.get("/wps/by-company/{company_id}")
def get_wps_by_company(company_id: int, db: Session = Depends(get_db)):
    """Получить все WPS конкретной компании"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    wps_list = db.query(WPSModel).filter(WPSModel.company_id == company_id).all()
    
    return {
        "company": {"id": company.id, "name": company.name, "code": company.code},
        "wps_count": len(wps_list),
        "wps_list": [
            {
                "id": w.id,
                "wps_number": w.wps_number,
                "title": w.title,
                "welding_process": w.welding_process,
                "status": w.status,
                "revision": w.revision
            } for w in wps_list
        ]
    }

@app.get("/wps/search/{search_term}")
def search_wps(search_term: str, db: Session = Depends(get_db)):
    """Поиск WPS по номеру, названию или процессу сварки"""
    wps_list = db.query(WPSModel).filter(
        WPSModel.wps_number.ilike(f"%{search_term}%") |
        WPSModel.title.ilike(f"%{search_term}%") |
        WPSModel.welding_process.ilike(f"%{search_term}%") |
        WPSModel.base_material_spec.ilike(f"%{search_term}%")
    ).all()
    
    return {
        "search_term": search_term,
        "found_count": len(wps_list),
        "wps_list": [
            {
                "id": w.id,
                "wps_number": w.wps_number,
                "title": w.title,
                "welding_process": w.welding_process,
                "base_material": w.base_material_spec,
                "status": w.status,
                "company_id": w.company_id
            } for w in wps_list
        ]
    }

# =====================================
# WPQR CRUD ENDPOINTS
# =====================================

@app.get("/wpqr", response_model=List[WPQR])
def get_wpqr_list(
    company_id: int = None, 
    wps_id: int = None,
    overall_result: str = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Получить список WPQR с фильтрацией"""
    query = db.query(WPQRModel)
    
    if company_id:
        query = query.filter(WPQRModel.company_id == company_id)
    if wps_id:
        query = query.filter(WPQRModel.wps_id == wps_id)
    if overall_result:
        query = query.filter(WPQRModel.overall_result.ilike(f"%{overall_result}%"))
    
    wpqr_list = query.offset(skip).limit(limit).all()
    return wpqr_list

@app.get("/wpqr/{wpqr_id}", response_model=WPQR)
def get_wpqr(wpqr_id: int, db: Session = Depends(get_db)):
    """Получить WPQR по ID"""
    wpqr = db.query(WPQRModel).filter(WPQRModel.id == wpqr_id).first()
    if wpqr is None:
        raise HTTPException(status_code=404, detail="WPQR not found")
    return wpqr

@app.post("/wpqr", response_model=WPQR, status_code=status.HTTP_201_CREATED)
def create_wpqr(wpqr: WPQRCreate, db: Session = Depends(get_db)):
    """Создать новый WPQR"""
    company = db.query(CompanyModel).filter(CompanyModel.id == wpqr.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if wpqr.wps_id:
        wps = db.query(WPSModel).filter(WPSModel.id == wpqr.wps_id).first()
        if not wps:
            raise HTTPException(status_code=404, detail="WPS not found")
    
    existing_wpqr = db.query(WPQRModel).filter(
        WPQRModel.company_id == wpqr.company_id,
        WPQRModel.wpqr_number == wpqr.wpqr_number
    ).first()
    if existing_wpqr:
        raise HTTPException(
            status_code=400, 
            detail=f"WPQR number '{wpqr.wpqr_number}' already exists for company '{company.name}'"
        )
    
    db_wpqr = WPQRModel(**wpqr.dict())
    db.add(db_wpqr)
    db.commit()
    db.refresh(db_wpqr)
    return db_wpqr

@app.put("/wpqr/{wpqr_id}", response_model=WPQR)
def update_wpqr(wpqr_id: int, wpqr_update: WPQRUpdate, db: Session = Depends(get_db)):
    """Обновить WPQR"""
    wpqr = db.query(WPQRModel).filter(WPQRModel.id == wpqr_id).first()
    if wpqr is None:
        raise HTTPException(status_code=404, detail="WPQR not found")
    
    update_data = wpqr_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(wpqr, field, value)
    
    db.commit()
    db.refresh(wpqr)
    return wpqr

@app.delete("/wpqr/{wpqr_id}")
def delete_wpqr(wpqr_id: int, db: Session = Depends(get_db)):
    """Удалить WPQR"""
    wpqr = db.query(WPQRModel).filter(WPQRModel.id == wpqr_id).first()
    if wpqr is None:
        raise HTTPException(status_code=404, detail="WPQR not found")
    
    wpqr_number = wpqr.wpqr_number
    db.delete(wpqr)
    db.commit()
    return {"message": f"WPQR '{wpqr_number}' deleted successfully", "deleted_id": wpqr_id}

@app.get("/wpqr/by-company/{company_id}")
def get_wpqr_by_company(company_id: int, db: Session = Depends(get_db)):
    """Получить все WPQR конкретной компании"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    wpqr_list = db.query(WPQRModel).filter(WPQRModel.company_id == company_id).all()
    
    return {
        "company": {"id": company.id, "name": company.name, "code": company.code},
        "wpqr_count": len(wpqr_list),
        "wpqr_list": [
            {
                "id": w.id,
                "wpqr_number": w.wpqr_number,
                "welder_name": w.welder_name,
                "overall_result": w.overall_result,
                "test_date": w.test_date,
                "wps_id": w.wps_id
            } for w in wpqr_list
        ]
    }

@app.get("/wpqr/by-wps/{wps_id}")
def get_wpqr_by_wps(wps_id: int, db: Session = Depends(get_db)):
    """Получить все WPQR для конкретного WPS"""
    wps = db.query(WPSModel).filter(WPSModel.id == wps_id).first()
    if not wps:
        raise HTTPException(status_code=404, detail="WPS not found")
    
    wpqr_list = db.query(WPQRModel).filter(WPQRModel.wps_id == wps_id).all()
    
    return {
        "wps": {"id": wps.id, "wps_number": wps.wps_number, "title": wps.title},
        "wpqr_count": len(wpqr_list),
        "wpqr_list": [
            {
                "id": w.id,
                "wpqr_number": w.wpqr_number,
                "welder_name": w.welder_name,
                "overall_result": w.overall_result,
                "test_date": w.test_date
            } for w in wpqr_list
        ]
    }

@app.get("/wpqr/search/{search_term}")
def search_wpqr(search_term: str, db: Session = Depends(get_db)):
    """Поиск WPQR по номеру, сварщику или результату"""
    wpqr_list = db.query(WPQRModel).filter(
        WPQRModel.wpqr_number.ilike(f"%{search_term}%") |
        WPQRModel.welder_name.ilike(f"%{search_term}%") |
        WPQRModel.overall_result.ilike(f"%{search_term}%")
    ).all()
    
    return {
        "search_term": search_term,
        "found_count": len(wpqr_list),
        "wpqr_list": [
            {
                "id": w.id,
                "wpqr_number": w.wpqr_number,
                "welder_name": w.welder_name,
                "overall_result": w.overall_result,
                "company_id": w.company_id,
                "wps_id": w.wps_id
            } for w in wpqr_list
        ]
    }

# =====================================
# SAMPLE DATA CREATION ENDPOINTS
# =====================================

@app.post("/companies/create-sample")
def create_sample_companies(db: Session = Depends(get_db)):
    """Создать несколько образцов компаний для тестирования"""
    sample_companies = [
        {
            "name": "ОАО Северсталь",
            "code": "SEVERSTAL001",
            "address": "г. Череповец, ул. Мира, 30",
            "phone": "+7 (8202) 59-59-59",
            "email": "info@severstal.com",
            "certification_body": "НАКС"
        },
        {
            "name": "ПАО Газпром",
            "code": "GAZPROM001", 
            "address": "г. Москва, ул. Намёткина, 16",
            "phone": "+7 (495) 719-30-01",
            "email": "gazprom@gazprom.ru",
            "certification_body": "НАКС, Lloyd's Register"
        },
        {
            "name": "ООО Сварочные технологии",
            "code": "WELDTECH001",
            "address": "г. Санкт-Петербург, пр. Обуховской обороны, 120",
            "phone": "+7 (812) 555-12-34",
            "email": "office@weldtech.ru", 
            "certification_body": "НАКС, TÜV"
        }
    ]
    
    created_companies = []
    for company_data in sample_companies:
        existing = db.query(CompanyModel).filter(CompanyModel.name == company_data["name"]).first()
        if not existing:
            db_company = CompanyModel(**company_data)
            db.add(db_company)
            created_companies.append(company_data["name"])
    
    try:
        db.commit()
        return {
            "message": "Sample companies created successfully",
            "created_count": len(created_companies),
            "created_companies": created_companies
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to create companies: {str(e)}"}

@app.post("/wps/create-sample")
def create_sample_wps(db: Session = Depends(get_db)):
    """Создать образцы WPS для тестирования"""
    companies = db.query(CompanyModel).all()
    if not companies:
        return {"error": "No companies found. Create companies first using /companies/create-sample"}
    
    sample_wps = [
        {
            "company_id": companies[0].id,
            "wps_number": "WPS-GMAW-001",
            "revision": "1",
            "title": "Сварка стали полуавтоматом в среде защитного газа",
            "welding_process": "GMAW",
            "base_material_spec": "ГОСТ 27772-2015",
            "base_material_grade": "09Г2С",
            "base_material_thickness_min": 3.0,
            "base_material_thickness_max": 20.0,
            "filler_material_spec": "ГОСТ 2246-70",
            "filler_material_classification": "Св-08Г2С",
            "filler_material_diameter": "1.2",
            "welding_positions": "PA,PB,PC",
            "joint_type": "BW",
            "current_type": "DC+",
            "current_range_min": 120,
            "current_range_max": 180,
            "voltage_range_min": 20.0,
            "voltage_range_max": 24.0,
            "shielding_gas_composition": "82% Ar + 18% CO2",
            "gas_flow_rate": 12.0,
            "status": "Active"
        },
        {
            "company_id": companies[0].id,
            "wps_number": "WPS-SMAW-001", 
            "revision": "2",
            "title": "Ручная дуговая сварка покрытыми электродами",
            "welding_process": "SMAW",
            "base_material_spec": "ГОСТ 27772-2015",
            "base_material_grade": "Ст3сп",
            "base_material_thickness_min": 5.0,
            "base_material_thickness_max": 30.0,
            "filler_material_spec": "ГОСТ 9466-75",
            "filler_material_classification": "УОНИ-13/55",
            "filler_material_diameter": "4.0",
            "welding_positions": "PA,PB,PC,PF,PG",
            "joint_type": "BW", 
            "current_type": "DC+",
            "current_range_min": 140,
            "current_range_max": 180,
            "voltage_range_min": 22.0,
            "voltage_range_max": 26.0,
            "preheat_temp_min": 20,
            "preheat_temp_max": 100,
            "status": "Active"
        }
    ]
    
    if len(companies) > 1:
        sample_wps.append({
            "company_id": companies[1].id,
            "wps_number": "WPS-GTAW-001",
            "revision": "1", 
            "title": "Аргонодуговая сварка нержавеющей стали",
            "welding_process": "GTAW",
            "base_material_spec": "ГОСТ 5632-2014",
            "base_material_grade": "12Х18Н10Т",
            "base_material_thickness_min": 1.0,
            "base_material_thickness_max": 8.0,
            "filler_material_spec": "ГОСТ 18143-72",
            "filler_material_classification": "Св-04Х19Н11М3",
            "filler_material_diameter": "2.0",
            "welding_positions": "PA,PB",
            "joint_type": "BW",
            "current_type": "DC-",
            "current_range_min": 80,
            "current_range_max": 120,
            "voltage_range_min": 10.0,
            "voltage_range_max": 14.0,
            "shielding_gas_composition": "100% Ar",
            "gas_flow_rate": 8.0,
            "status": "Draft"
        })
    
    created_wps = []
    for wps_data in sample_wps:
        existing = db.query(WPSModel).filter(
            WPSModel.company_id == wps_data["company_id"],
            WPSModel.wps_number == wps_data["wps_number"]
        ).first()
        if not existing:
            db_wps = WPSModel(**wps_data)
            db.add(db_wps)
            created_wps.append(wps_data["wps_number"])
    
    try:
        db.commit()
        return {
            "message": "Sample WPS created successfully",
            "created_count": len(created_wps),
            "created_wps": created_wps
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to create WPS: {str(e)}"}

@app.post("/wpqr/create-sample")
def create_sample_wpqr(db: Session = Depends(get_db)):
    """Создать образцы WPQR для тестирования"""
    companies = db.query(CompanyModel).all()
    wps_list = db.query(WPSModel).all()

    if not companies:
        return {"error": "No companies found. Create companies first using /companies/create-sample"}
    if not wps_list:
        return {"error": "No WPS found. Create WPS first using /wps/create-sample"}

    from datetime import datetime, timedelta

    sample_wpqr = [
        {
            "company_id": companies[0].id,
            "wps_id": wps_list[0].id,
            "wpqr_number": "WPQR-GMAW-001-2024",
            "test_date": datetime.now() - timedelta(days=30),
            "welder_name": "Сидоров Алексей Петрович",
            "welder_qualification": "НАКС-СД-001-2024",
            "actual_base_material": "09Г2С",
            "base_metal_thickness": 10.0,
            "actual_filler_material": "Св-08Г2С",
            "actual_welding_position": "PA",
            "actual_current": 150,
            "actual_voltage": 22.0,
            "actual_travel_speed": 25.0,
            "actual_heat_input": 1.32,
            "tensile_strength": 520.0,
            "tensile_result": "Pass",
            "bend_test_type": "Face",
            "bend_test_angle": 180,
            "bend_test_result": "Pass",
            "bend_test_notes": "Без дефектов",
            "impact_test_temp": 20,
            "impact_energy_weld": 85.0,
            "impact_result": "Pass",
            "macro_examination_result": "Pass",
            "macro_notes": "Структура однородная",
            "ndt_method": "RT",
            "ndt_result": "Pass",
            "overall_result": "Qualified",
            "qualified_thickness_range": "3-20mm",
            "qualified_positions": "PA,PB,PC",
            "tested_by": "Инженер по сварке Петров И.И.",
            "approved_by": "Главный сварщик Сидоров С.С.",
            "approved_date": datetime.now() - timedelta(days=25)
        },
        {
            "company_id": companies[0].id,
            "wps_id": wps_list[1].id if len(wps_list) > 1 else wps_list[0].id,
            "wpqr_number": "WPQR-SMAW-001-2024",
            "test_date": datetime.now() - timedelta(days=15),
            "welder_name": "Козлов Дмитрий Владимирович",
            "welder_qualification": "НАКС-РД-002-2024",
            "actual_base_material": "Ст3сп",
            "base_metal_thickness": 15.0,
            "actual_filler_material": "УОНИ-13/55",
            "actual_welding_position": "PB",
            "actual_current": 160,
            "actual_voltage": 24.0,
            "actual_travel_speed": 15.0,
            "actual_heat_input": 2.56,
            "tensile_strength": 480.0,
            "tensile_result": "Pass",
            "bend_test_type": "Root",
            "bend_test_angle": 180,
            "bend_test_result": "Pass",
            "bend_test_notes": "Испытание прошло успешно",
            "impact_test_temp": 0,
            "impact_energy_weld": 75.0,
            "impact_result": "Pass",
            "macro_examination_result": "Pass",
            "ndt_method": "UT",
            "ndt_result": "Pass",
            "overall_result": "Qualified",
            "qualified_thickness_range": "5-30mm",
            "qualified_positions": "PA,PB,PC,PF,PG",
            "tested_by": "Инженер по сварке Петров И.И.",
            "approved_by": "Главный сварщик Сидоров С.С.",
            "approved_date": datetime.now() - timedelta(days=10)
        }
    ]

    if len(companies) > 1 and len(wps_list) > 2:
        sample_wpqr.append({
            "company_id": companies[1].id,
            "wps_id": wps_list[2].id,
            "wpqr_number": "WPQR-GTAW-001-2024",
            "test_date": datetime.now() - timedelta(days=5),
            "welder_name": "Васильев Игорь Сергеевич",
            "welder_qualification": "НАКС-АД-003-2024",
            "actual_base_material": "12Х18Н10Т",
            "base_metal_thickness": 6.0,
            "actual_filler_material": "Св-04Х19Н11М3",
            "actual_welding_position": "PA",
            "actual_current": 100,
            "actual_voltage": 12.0,
            "actual_travel_speed": 12.0,
            "actual_heat_input": 1.0,
            "tensile_strength": 580.0,
            "tensile_result": "Pass",
            "bend_test_type": "Side",
            "bend_test_angle": 180,
            "bend_test_result": "Pass",
            "bend_test_notes": "Отличное качество сварного шва",
            "macro_examination_result": "Pass",
            "ndt_method": "PT",
            "ndt_result": "Pass",
            "overall_result": "Qualified",
            "qualified_thickness_range": "1-8mm",
            "qualified_positions": "PA,PB",
            "tested_by": "Инженер по сварке Семенов С.С.",
            "approved_by": "Главный технолог Федоров Ф.Ф.",
            "approved_date": datetime.now() - timedelta(days=2)
        })

    created_wpqr = []
    for wpqr_data in sample_wpqr:
        existing = db.query(WPQRModel).filter(
            WPQRModel.company_id == wpqr_data["company_id"],
            WPQRModel.wpqr_number == wpqr_data["wpqr_number"]
        ).first()
        if not existing:
            db_wpqr = WPQRModel(**wpqr_data)
            db.add(db_wpqr)
            created_wpqr.append(wpqr_data["wpqr_number"])
    
    try:
        db.commit()
        return {
            "message": "Sample WPQR created successfully",
            "created_count": len(created_wpqr),
            "created_wpqr": created_wpqr
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to create WPQR: {str(e)}"}

@app.get("/welders", response_model=List[Welder])
def get_welders(
    company_id: int = None, 
    status: str = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Получить список сварщиков с фильтрацией"""
    query = db.query(WelderModel)
    
    if company_id:
        query = query.filter(WelderModel.company_id == company_id)
    if status:
        query = query.filter(WelderModel.status.ilike(f"%{status}%"))
    
    welders = query.offset(skip).limit(limit).all()
    return welders

@app.get("/welders/{welder_id}", response_model=Welder)
def get_welder(welder_id: int, db: Session = Depends(get_db)):
    """Получить сварщика по ID"""
    welder = db.query(WelderModel).filter(WelderModel.id == welder_id).first()
    if welder is None:
        raise HTTPException(status_code=404, detail="Welder not found")
    return welder

@app.post("/welders", response_model=Welder, status_code=status.HTTP_201_CREATED)
def create_welder(welder: WelderCreate, db: Session = Depends(get_db)):
    """Создать нового сварщика"""
    company = db.query(CompanyModel).filter(CompanyModel.id == welder.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Проверяем уникальность табельного номера в компании
    if welder.employee_number:
        existing_welder = db.query(WelderModel).filter(
            WelderModel.company_id == welder.company_id,
            WelderModel.employee_number == welder.employee_number
        ).first()
        if existing_welder:
            raise HTTPException(
                status_code=400, 
                detail=f"Employee number '{welder.employee_number}' already exists in company '{company.name}'"
            )
    
    db_welder = WelderModel(**welder.dict())
    db.add(db_welder)
    db.commit()
    db.refresh(db_welder)
    return db_welder

@app.put("/welders/{welder_id}", response_model=Welder)
def update_welder(welder_id: int, welder_update: WelderUpdate, db: Session = Depends(get_db)):
    """Обновить сварщика"""
    welder = db.query(WelderModel).filter(WelderModel.id == welder_id).first()
    if welder is None:
        raise HTTPException(status_code=404, detail="Welder not found")
    
    update_data = welder_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(welder, field, value)
    
    db.commit()
    db.refresh(welder)
    return welder

@app.delete("/welders/{welder_id}")
def delete_welder(welder_id: int, db: Session = Depends(get_db)):
    """Удалить сварщика"""
    welder = db.query(WelderModel).filter(WelderModel.id == welder_id).first()
    if welder is None:
        raise HTTPException(status_code=404, detail="Welder not found")
    
    welder_name = f"{welder.first_name} {welder.last_name}"
    db.delete(welder)
    db.commit()
    return {"message": f"Welder '{welder_name}' deleted successfully", "deleted_id": welder_id}

@app.get("/welders/by-company/{company_id}")
def get_welders_by_company(company_id: int, db: Session = Depends(get_db)):
    """Получить всех сварщиков конкретной компании"""
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    welders = db.query(WelderModel).filter(WelderModel.company_id == company_id).all()
    
    return {
        "company": {"id": company.id, "name": company.name, "code": company.code},
        "welders_count": len(welders),
        "welders": [
            {
                "id": w.id,
                "full_name": f"{w.first_name} {w.last_name}",
                "employee_number": w.employee_number,
                "phone": w.phone,
                "status": w.status,
                "certificates_count": len(w.certificates),
                "hire_date": w.hire_date
            } for w in welders
        ]
    }

# =====================================
# WELDER CERTIFICATES CRUD ENDPOINTS
# =====================================

@app.get("/certificates", response_model=List[WelderCertificate])
def get_certificates(
    welder_id: int = None,
    company_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получить список сертификатов с фильтрацией"""
    query = db.query(WelderCertificateModel)
    
    if welder_id:
        query = query.filter(WelderCertificateModel.welder_id == welder_id)
    if company_id:
        query = query.filter(WelderCertificateModel.company_id == company_id)
    if status:
        query = query.filter(WelderCertificateModel.status.ilike(f"%{status}%"))
    
    certificates = query.offset(skip).limit(limit).all()
    return certificates

@app.get("/certificates/{certificate_id}", response_model=WelderCertificate)
def get_certificate(certificate_id: int, db: Session = Depends(get_db)):
    """Получить сертификат по ID"""
    certificate = db.query(WelderCertificateModel).filter(WelderCertificateModel.id == certificate_id).first()
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return certificate

@app.post("/certificates", response_model=WelderCertificate, status_code=status.HTTP_201_CREATED)
def create_certificate(certificate: WelderCertificateCreate, db: Session = Depends(get_db)):
    """Создать новый сертификат"""
    welder = db.query(WelderModel).filter(WelderModel.id == certificate.welder_id).first()
    if not welder:
        raise HTTPException(status_code=404, detail="Welder not found")
    
    company = db.query(CompanyModel).filter(CompanyModel.id == certificate.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Проверяем уникальность номера сертификата в компании
    existing_certificate = db.query(WelderCertificateModel).filter(
        WelderCertificateModel.company_id == certificate.company_id,
        WelderCertificateModel.certificate_number == certificate.certificate_number
    ).first()
    if existing_certificate:
        raise HTTPException(
            status_code=400, 
            detail=f"Certificate number '{certificate.certificate_number}' already exists in company '{company.name}'"
        )
    
    db_certificate = WelderCertificateModel(**certificate.dict())
    db.add(db_certificate)
    db.commit()
    db.refresh(db_certificate)
    return db_certificate

@app.put("/certificates/{certificate_id}", response_model=WelderCertificate)
def update_certificate(certificate_id: int, certificate_update: WelderCertificateUpdate, db: Session = Depends(get_db)):
    """Обновить сертификат"""
    certificate = db.query(WelderCertificateModel).filter(WelderCertificateModel.id == certificate_id).first()
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    update_data = certificate_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(certificate, field, value)
    
    db.commit()
    db.refresh(certificate)
    return certificate

@app.delete("/certificates/{certificate_id}")
def delete_certificate(certificate_id: int, db: Session = Depends(get_db)):
    """Удалить сертификат"""
    certificate = db.query(WelderCertificateModel).filter(WelderCertificateModel.id == certificate_id).first()
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    certificate_number = certificate.certificate_number
    db.delete(certificate)
    db.commit()
    return {"message": f"Certificate '{certificate_number}' deleted successfully", "deleted_id": certificate_id}

# =====================================
# CERTIFICATE FILE UPLOAD ENDPOINTS
# =====================================

@app.post("/certificates/{certificate_id}/upload-file")
async def upload_certificate_file(
    certificate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка файла сертификата"""
    
    # Проверяем, что сертификат существует
    certificate = db.query(WelderCertificateModel).filter(WelderCertificateModel.id == certificate_id).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Валидируем файл (PDF, JPG, PNG)
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Проверяем размер файла (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Создаем папку для сертификатов
    CERTIFICATES_DIR = Path("static") / "certificates"
    CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Удаляем старый файл, если есть
    if certificate.certificate_file_url:
        old_file_path = Path("static") / certificate.certificate_file_url.replace("/static/", "")
        if old_file_path.exists():
            try:
                old_file_path.unlink()
            except Exception as e:
                print(f"⚠️ Не удалось удалить старый файл {old_file_path}: {e}")
    
    # Сохраняем новый файл
    import uuid
    filename = f"cert_{certificate_id}_{uuid.uuid4()}{file_ext}"
    file_path = CERTIFICATES_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сохранения файла: {str(e)}"
        )
    
    # Обновляем запись в базе данных
    certificate.certificate_file_url = f"/static/certificates/{filename}"
    db.commit()
    db.refresh(certificate)
    
    return {
        "message": "Файл сертификата загружен успешно",
        "file_url": certificate.certificate_file_url,
        "filename": file.filename,
        "file_size": file_size
    }

# =====================================
# EXPIRING CERTIFICATES ENDPOINTS
# =====================================

@app.get("/companies/{company_id}/expiring-certificates", response_model=ExpiringCertificatesResponse)
def get_expiring_certificates(company_id: int, days_ahead: int = 60, db: Session = Depends(get_db)):
    """Получить истекающие сертификаты компании"""
    
    company = db.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Получаем сертификаты, истекающие в ближайшие days_ahead дней
    cutoff_date = date.today() + timedelta(days=days_ahead)
    
    certificates = db.query(WelderCertificateModel).join(WelderModel).filter(
        WelderCertificateModel.company_id == company_id,
        WelderCertificateModel.expiry_date <= cutoff_date,
        WelderCertificateModel.status == "Valid"
    ).all()
    
    # Группируем по уровню срочности
    critical = []  # < 30 дней
    urgent = []    # 30-60 дней  
    warning = []   # 60+ дней
    
    for cert in certificates:
        days_until_expiry = (cert.expiry_date - date.today()).days
        welder_name = f"{cert.welder.first_name} {cert.welder.last_name}"
        
        expiring_cert = ExpiringCertificate(
            certificate_id=cert.id,
            welder_name=welder_name,
            certificate_number=cert.certificate_number,
            welding_group=cert.welding_group,
            welding_method=cert.welding_method,
            expiry_date=cert.expiry_date,
            days_until_expiry=days_until_expiry,
            urgency_level="critical" if days_until_expiry < 30 else "urgent" if days_until_expiry < 60 else "warning"
        )
        
        if days_until_expiry < 0:
            critical.append(expiring_cert)  # Уже истек
        elif days_until_expiry < 30:
            critical.append(expiring_cert)
        elif days_until_expiry < 60:
            urgent.append(expiring_cert)
        else:
            warning.append(expiring_cert)
    
    return ExpiringCertificatesResponse(
        company_id=company_id,
        company_name=company.name,
        total_expiring=len(certificates),
        critical=critical,
        urgent=urgent,
        warning=warning
    )

# =====================================
# SAMPLE DATA CREATION FOR WELDERS
# =====================================

@app.post("/welders/create-sample")
def create_sample_welders(db: Session = Depends(get_db)):
    """Создать образцы сварщиков для тестирования"""
    companies = db.query(CompanyModel).all()
    if not companies:
        return {"error": "No companies found. Create companies first using /companies/create-sample"}
    
    from datetime import date, timedelta
    import random
    
    sample_welders = [
        {
            "company_id": companies[0].id,
            "first_name": "Иван",
            "last_name": "Петров",
            "middle_name": "Сергеевич",
            "phone": "+7 (900) 123-45-67",
            "email": "i.petrov@example.com",
            "employee_number": "0001",
            "status": "Active",
            "hire_date": date.today() - timedelta(days=365)
        },
        {
            "company_id": companies[0].id,
            "first_name": "Алексей",
            "last_name": "Сидоров",
            "middle_name": "Владимирович",
            "phone": "+7 (900) 234-56-78",
            "employee_number": "0002",
            "status": "Active",
            "hire_date": date.today() - timedelta(days=500)
        },
        {
            "company_id": companies[0].id,
            "first_name": "Михаил",
            "last_name": "Козлов",
            "phone": "+7 (900) 345-67-89",
            "employee_number": "0003",
            "status": "Active"
        }
    ]
    
    if len(companies) > 1:
        sample_welders.extend([
            {
                "company_id": companies[1].id,
                "first_name": "Дмитрий",
                "last_name": "Васильев",
                "middle_name": "Игоревич",
                "phone": "+7 (900) 456-78-90",
                "employee_number": "0001",
                "status": "Active"
            },
            {
                "company_id": companies[1].id,
                "first_name": "Сергей",
                "last_name": "Федоров",
                "phone": "+7 (900) 567-89-01",
                "employee_number": "0002",
                "status": "Active"
            }
        ])
    
    created_welders = []
    for welder_data in sample_welders:
        existing = db.query(WelderModel).filter(
            WelderModel.company_id == welder_data["company_id"],
            WelderModel.employee_number == welder_data["employee_number"]
        ).first()
        if not existing:
            db_welder = WelderModel(**welder_data)
            db.add(db_welder)
            created_welders.append(f"{welder_data['first_name']} {welder_data['last_name']}")
    
    try:
        db.commit()
        
        # Создаем образцы сертификатов для созданных сварщиков
        welders = db.query(WelderModel).all()
        created_certificates = []
        
        for welder in welders[-len(created_welders):]:  # Только для новых сварщиков
            # Создаем 1-2 сертификата на сварщика
            for i in range(random.randint(1, 2)):
                cert_data = {
                    "welder_id": welder.id,
                    "company_id": welder.company_id,
                    "certificate_number": f"НАКС-{welder.employee_number}-{i+1}-2024",
                    "certification_body": "НАКС" if i == 0 else random.choice(["НАКС", "AWS", "TÜV"]),
                    "welding_group": random.choice(["А", "Б", "В", "Г"]),
                    "welding_method": random.choice(["РД", "АД", "ПП", "ЭШС"]),
                    "welding_process": random.choice(["SMAW", "GMAW", "GTAW"]),
                    "base_material": random.choice(["Сталь углеродистая", "Сталь нержавеющая", "Алюминий"]),
                    "thickness_range": random.choice(["3-12мм", "5-20мм", "8-25мм"]),
                    "welding_positions": random.choice(["PA,PB", "PA,PB,PC", "Все положения"]),
                    "issue_date": date.today() - timedelta(days=random.randint(30, 700)),
                    "expiry_date": date.today() + timedelta(days=random.randint(-30, 400)),  # Некоторые истекают
                    "status": "Valid"
                }
                
                db_cert = WelderCertificateModel(**cert_data)
                db.add(db_cert)
                created_certificates.append(cert_data["certificate_number"])
        
        db.commit()
        
        return {
            "message": "Sample welders and certificates created successfully",
            "created_welders_count": len(created_welders),
            "created_welders": created_welders,
            "created_certificates_count": len(created_certificates),
            "created_certificates": created_certificates
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to create welders: {str(e)}"}
# =====================================
# ЗАВЕРШЕНИЕ И ОБРАБОТКА ОШИБОК
# =====================================

# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)