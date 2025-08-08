# 📌 DEV CHECKPOINT — 08.08.2025

## 1. Структура проекта
```
wps-management-system/
│
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── main.py          # Основные маршруты API
│   │   ├── models/          # SQLAlchemy модели (Company, WPS, WPQR)
│   │   ├── database.py      # Подключение к БД
│   │   └── ...              
│   ├── requirements.txt     # Зависимости backend
│   └── ...
│
├── frontend/                # React + MUI frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── WPS.tsx
│   │   │   └── WPQR.tsx
│   │   ├── services/api.ts  # API сервисы (wpsApi, wpqrApi)
│   │   └── ...
│   └── package.json
│
└── tools/                   # Вспомогательные скрипты
    └── apply_fix.py
```

## 2. Что реализовано
✅ **Backend**
- CRUD API для:
  - **Companies**
  - **WPS** (Welding Procedure Specification)
  - **WPQR** (Welder Performance Qualification Record)
- Генерация тестовых данных (`create-sample`) для WPS и WPQR
- Исправлены ошибки в ключах (`company_code` → `code`)
- Нормализация данных при создании WPS
- Генерация PDF для WPS и WPQR

✅ **Frontend**
- Страницы WPS и WPQR с:
  - Списком записей
  - Поиском
  - Фильтрацией
  - Удалением записей
  - Кнопкой **скачивания PDF**
- Исправленный `fetch` с обходом кэширования

## 3. Что улучшено / исправлено
- Исправлены несоответствия ключей моделей и JSON
- Убраны дубликаты ключей в API
- Фикс нормализации позиций сварки (`welding_positions`)
- PDF скачивается корректно (но текст в некоторых местах отображается квадратами — нужна замена шрифта)

## 4. 📡 API эндпоинты

| Метод  | URL                                | Описание |
|--------|------------------------------------|----------|
| **Companies** |
| GET    | `/companies`                       | Получить список компаний |
| POST   | `/companies`                       | Создать новую компанию |
| GET    | `/companies/{id}`                  | Получить компанию по ID |
| PUT    | `/companies/{id}`                  | Обновить данные компании |
| DELETE | `/companies/{id}`                  | Удалить компанию |
| POST   | `/companies/create-sample`         | Создать тестовые компании |
| **WPS** |
| GET    | `/wps`                             | Получить список WPS |
| POST   | `/wps`                             | Создать новый WPS |
| GET    | `/wps/{id}`                        | Получить WPS по ID |
| PUT    | `/wps/{id}`                        | Обновить WPS |
| DELETE | `/wps/{id}`                        | Удалить WPS |
| POST   | `/wps/create-sample`               | Создать тестовые WPS |
| GET    | `/api/pdf/wps/{id}`                 | Скачать PDF WPS |
| **WPQR** |
| GET    | `/wpqr`                            | Получить список WPQR |
| POST   | `/wpqr`                            | Создать новый WPQR |
| GET    | `/wpqr/{id}`                        | Получить WPQR по ID |
| PUT    | `/wpqr/{id}`                        | Обновить WPQR |
| DELETE | `/wpqr/{id}`                        | Удалить WPQR |
| POST   | `/wpqr/create-sample`               | Создать тестовые WPQR |
| GET    | `/api/pdf/wpqr/{id}`                 | Скачать PDF WPQR |

## 5. Следующие шаги
1. **PDF улучшение**
   - Подключить шрифты с поддержкой кириллицы
   - Красивое оформление таблиц в PDF
2. **Редактирование записей**
   - Реализовать формы редактирования WPS и WPQR на фронте
3. **Аутентификация**
   - Добавить логин/пароль для доступа к API
4. **Улучшение поиска**
   - Фильтры по датам, компаниям, материалам
5. **Docker**
   - Сделать docker-compose для запуска backend + frontend + PostgreSQL
