@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ==^> Creating virtual environment
python -m venv venv
if errorlevel 1 (
    echo [ERROR] python not found. Install Python 3.12+ and check PATH.
    exit /b 1
)

echo ==^> Installing dependencies
call venv\Scripts\python.exe -m pip install --upgrade pip
call venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo ==^> Created .env - please edit it
) else (
    echo ==^> .env already exists - skipped
)

if not exist credentials mkdir credentials

echo.
echo Setup complete.
echo   1. Edit .env
echo   2. Put service-account JSON in credentials\
echo   3. Install NFC Port Software ^(Windows driver^) if not yet
echo   4. Run windows\check_reader.bat then windows\run_web.bat
echo.
pause
endlocal
