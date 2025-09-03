# 📦 Dependencies Management

## Backend Dependencies

### Production (`requirements.txt`)
```bash
pip install -r backend/requirements.txt
```
**Минимальный набор для production:**
- FastAPI + Uvicorn (web framework)
- SQLAlchemy + Alembic (database)  
- ReportLab + Pillow (PDF generation)
- Pydantic (validation)
- Essential utilities

### Development (`requirements-dev.txt`)
```bash
pip install -r backend/requirements-dev.txt
```
**Дополнительные инструменты для разработки:**
- Testing tools (pytest, coverage)
- Code quality (black, flake8, mypy, isort)
- Development utilities

### Production-only (`requirements-prod.txt`)
```bash
pip install -r backend/requirements-prod.txt
```
**Только необходимое для production сервера**

## Frontend Dependencies

### Core Dependencies
- **React 18** + TypeScript
- **Material-UI** (components + icons)
- **React Router** (navigation)
- **Axios** (HTTP client)
- **Lucide React** (additional icons)

### Removed Dependencies
- ✅ `@mui/x-data-grid` - не используется
- ✅ Перенесены testing libraries в devDependencies

## Installation Commands

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt  # or requirements-dev.txt
```

### Frontend Setup  
```bash
cd frontend
npm install
npm start
```

## Dependency Analysis Results

### ✅ Verified Used Dependencies
All dependencies in requirements.txt are **actually imported** in the codebase:
- FastAPI, SQLAlchemy, ReportLab confirmed via code analysis
- No unused dependencies detected

### 🗑️ Removed Dependencies
- `pydantic-settings` - not used
- `openpyxl`, `pandas` - not imported anywhere
- `@mui/x-data-grid` - not used in frontend

### 📊 Bundle Size Impact
- Backend: ~15 dependencies (was ~18)
- Frontend: ~14 dependencies (was ~15)
- Reduced install time and bundle size