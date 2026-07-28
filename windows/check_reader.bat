@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

if not exist venv\Scripts\python.exe (
    echo [ERROR] venv not found. Run windows\setup.bat first.
    exit /b 1
)

echo Listing PC/SC readers...
venv\Scripts\python.exe -c "from smartcard.System import readers; rs=readers(); print(rs if rs else '(none)'); print('OK' if any('PaSoRi' in str(r) or 'FeliCa' in str(r) or 'SONY' in str(r) for r in rs) else 'PaSoRi not found - install NFC Port Software and reconnect USB')"
if errorlevel 1 (
    echo.
    echo [ERROR] Python command failed. See message above.
)
echo.
pause
endlocal
