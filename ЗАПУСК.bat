@echo off
chcp 65001 >nul
title Кадастр объектов недвижимости - Сервер
echo ============================================
echo   Кадастр объектов недвижимости - ЗАПУСК
echo ============================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ОШИБКА: Python не найден. Установите Python 3.12+
    echo.
    pause
    exit /b 1
)
echo Python найден.

echo.
echo Переход в папку backend...
cd /d "%~dp0backend"

if not exist ".env" (
    echo Создание файла .env...
    (
        echo DATABASE_URL=sqlite+aiosqlite:///./cadastre.db
        echo SECRET_KEY=change-me-in-production
        echo ACCESS_TOKEN_EXPIRE_MINUTES=60
        echo APP_NAME=Кадастр объектов недвижимости
        echo DEBUG=false
    ) > .env
    echo Файл .env создан.
)

echo.
echo Проверка зависимостей...
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Зависимости не найдены. Установка...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ОШИБКА: не удалось установить зависимости.
        echo.
        pause
        exit /b 1
    )
    echo Зависимости установлены.
) else (
    echo Зависимости уже установлены.
)

if not exist "cadastre.db" (
    echo Создание базы данных и администратора...
    python seed_admin.py 2>nul
)

echo.
echo ============================================
echo   Приложение запущено.
echo   Закройте это окно для остановки.
echo ============================================
echo.
start http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
