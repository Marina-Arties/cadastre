@echo off
chcp 65001 >nul
title Кадастр - Публичный доступ через интернет

echo ============================================
echo   ЗАПУСК ПУБЛИЧНОГО ДОСТУПА
echo ============================================
echo.

echo Остановка старых процессов...
taskkill /F /IM cloudflared.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo Запуск сервера...
cd /d "%~dp0backend"
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Ожидание запуска сервера...
timeout /t 5 /nobreak >nul

echo Запуск туннеля Cloudflare...
if not exist "%TEMP%\cloudflared.exe" (
    echo Скачивание cloudflared...
    curl -s -L -o "%TEMP%\cloudflared.exe" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)

echo.
echo ============================================
echo   Туннель запускается...
echo   Ссылка появится ниже через 10 секунд
echo ============================================

del "%TEMP%\cf_url.log" 2>nul
start /b cmd /c "%TEMP%\cloudflared.exe tunnel --protocol http2 --url http://localhost:8000 > %TEMP%\cf_url.log 2>&1"

timeout /t 12 /nobreak >nul

echo.
echo ============================================
for /f "tokens=*" %%a in ('findstr "trycloudflare" %TEMP%\cf_url.log') do (
    echo   ПУБЛИЧНАЯ ССЫЛКА:
    echo   %%a
    echo.
    echo   Открываю в браузере...
    start %%a
    goto :done
)
echo   Ошибка: ссылка не получена.
echo   Проверьте интернет-соединение.
echo ============================================
:done
echo.
echo   Не закрывайте это окно!
echo   Ссылка работает, пока окно открыто.
echo   Для остановки — закройте окно.
echo.
pause >nul
