# backend/app/database.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base  # ← ДОБАВЛЕН ИМПОРТ
from sqlalchemy.orm import sessionmaker
import os

# Используем SQLite для начала
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wps_system.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для создания всех таблиц
def create_tables():
    # Импортируем модели чтобы они были зарегистрированы
    from .models import Company, WPS, WPQR, User
    from .models.welder import Welder, WelderCertificate
    Base.metadata.create_all(bind=engine)