@echo off
echo ========================================
echo Clearing Windows Icon Cache
echo ========================================
echo.

echo Stopping Windows Explorer...
taskkill /f /im explorer.exe >nul 2>&1

echo Deleting icon cache files...
cd /d "%userprofile%\AppData\Local"

attrib -h IconCache.db >nul 2>&1
del IconCache.db /f /q >nul 2>&1

attrib -h iconcache_*.db >nul 2>&1
del iconcache_*.db /f /q >nul 2>&1

cd /d "%userprofile%\AppData\Local\Microsoft\Windows\Explorer"
attrib -h *.db >nul 2>&1
del *.db /f /q >nul 2>&1

echo Starting Windows Explorer...
start explorer.exe

echo.
echo ========================================
echo Icon cache cleared!
echo Please check your exe file icon now.
echo ========================================
echo.
pause
