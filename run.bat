@echo off
chcp 65001 >nul
echo ========================================
echo Interior Studio CRM - Запуск приложения
echo ========================================
echo.

REM Проверка существования виртуального окружения
if not exist ".venv\Scripts\python.exe" (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    echo Создайте его командой: python -m venv .venv
    pause
    exit /b 1
)

echo [OK] Виртуальное окружение найдено
echo [INFO] Запуск приложения...
echo.

REM Запуск приложения
.venv\Scripts\python.exe main.py

REM Если приложение завершилось с ошибкой
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой!
    pause
)
