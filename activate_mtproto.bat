@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   Активация MTProto (Pyrogram) - QR-код
echo ============================================
echo.
echo   VPN можно не отключать (QR не зависит от IP)
echo.
echo   Приготовьте телефон с Telegram!
echo.
pause

cd /d "%~dp0"

echo.
echo   Запуск... QR-код появится на экране.
echo.

.venv\Scripts\python.exe generate_session_qr.py

echo.
pause
