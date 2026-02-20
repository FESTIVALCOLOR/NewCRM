@echo off
chcp 65001 >nul
cd /d C:\+CRM+\interior_studio

echo ========================================
echo  UI Тесты - сессия uitester
echo ========================================
echo.
echo  Тесты сами запустят CRM (~8 мин)
echo  Переключайтесь обратно:
echo    Ctrl+Alt+Del - Сменить пользователя
echo.
echo  Результаты в: test_results.output
echo ========================================
echo.

:: Убиваем старый CRM если остался
taskkill /f /im python.exe /fi "WINDOWTITLE eq Interior*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *Festival*" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Запускаем тесты (pytest сам запустит CRM через фикстуру app_process)
echo Запускаю тесты...
.venv\Scripts\python.exe -m pytest tests/ui/test_clients_extended.py tests/ui/test_contracts_extended.py -v --timeout=120 --tb=line 2>&1 > test_results.output

:: Парсим результаты
.venv\Scripts\python.exe tests/ui/parse_results.py test_results.output > test_results_summary.txt 2>&1

:: Звуковой сигнал
powershell -Command "[console]::beep(800,300); Start-Sleep -m 200; [console]::beep(1000,300); Start-Sleep -m 200; [console]::beep(1200,500)"

echo.
echo ========================================
type test_results_summary.txt
echo ========================================
pause
