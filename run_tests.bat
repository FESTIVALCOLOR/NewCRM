@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Interior Studio CRM — Test Runner
echo ========================================
echo.

:: Настройки
set "VENV=.venv\Scripts\python.exe"
set "LOG_DIR=tests\logs"
set "TIMESTAMP=%date:~6,4%-%date:~3,2%-%date:~0,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

:: Создать директорию для логов
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Файлы логов
set "CLIENT_LOG=%LOG_DIR%\client_%TIMESTAMP%.log"
set "UI_LOG=%LOG_DIR%\ui_%TIMESTAMP%.log"
set "DB_LOG=%LOG_DIR%\db_%TIMESTAMP%.log"
set "SUMMARY_LOG=%LOG_DIR%\summary_%TIMESTAMP%.log"

echo [1/4] Запуск Client тестов...
echo.
%VENV% -m pytest tests/client/ -v --tb=short --no-header -q 2>&1 | tee "%CLIENT_LOG%"
set CLIENT_EXIT=%ERRORLEVEL%

echo.
echo [2/4] Запуск UI тестов (offscreen)...
echo.
set QT_QPA_PLATFORM=offscreen
%VENV% -m pytest tests/ui/ -v --tb=short --no-header -q 2>&1 | tee "%UI_LOG%"
set UI_EXIT=%ERRORLEVEL%

echo.
echo [3/4] Запуск DB тестов...
echo.
%VENV% -m pytest tests/db/ -v --tb=short --no-header -q 2>&1 | tee "%DB_LOG%"
set DB_EXIT=%ERRORLEVEL%

echo.
echo [4/4] Генерация отчёта...
echo.

:: Считаем результаты
echo ======================================== > "%SUMMARY_LOG%"
echo   Interior Studio CRM — Test Summary >> "%SUMMARY_LOG%"
echo   %date% %time% >> "%SUMMARY_LOG%"
echo ======================================== >> "%SUMMARY_LOG%"
echo. >> "%SUMMARY_LOG%"
echo Client tests exit code: %CLIENT_EXIT% >> "%SUMMARY_LOG%"
echo UI tests exit code: %UI_EXIT% >> "%SUMMARY_LOG%"
echo DB tests exit code: %DB_EXIT% >> "%SUMMARY_LOG%"
echo. >> "%SUMMARY_LOG%"
echo Logs saved to: >> "%SUMMARY_LOG%"
echo   %CLIENT_LOG% >> "%SUMMARY_LOG%"
echo   %UI_LOG% >> "%SUMMARY_LOG%"
echo   %DB_LOG% >> "%SUMMARY_LOG%"

echo.
echo ========================================
echo   РЕЗУЛЬТАТЫ
echo ========================================
echo   Client: %CLIENT_EXIT% (0=OK)
echo   UI:     %UI_EXIT% (0=OK)
echo   DB:     %DB_EXIT% (0=OK)
echo ========================================
echo   Логи: %LOG_DIR%\
echo   Summary: %SUMMARY_LOG%
echo ========================================

if %CLIENT_EXIT% NEQ 0 exit /b 1
if %UI_EXIT% NEQ 0 exit /b 1
if %DB_EXIT% NEQ 0 exit /b 1
exit /b 0
