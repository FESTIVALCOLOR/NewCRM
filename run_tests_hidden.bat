@echo off
chcp 65001 >nul
cd /d C:\+CRM+\interior_studio

:: Убиваем старый CRM если остался
taskkill /f /im python.exe /fi "WINDOWTITLE eq Interior*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *Festival*" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Запуск UI тестов в фоновом режиме (UITEST_BG=1)
:: CRM окно стартует свёрнуто, фокус не крадётся
:: Прогресс-бар в консоли
.venv\Scripts\python.exe run_tests_hidden.py %*
pause
