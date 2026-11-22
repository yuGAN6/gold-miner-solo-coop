@echo off
chcp 65001 >nul
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Manage-Mod.ps1" -Mode Uninstall -GameDirectory "%~1"
set "MOD_RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %MOD_RESULT%
