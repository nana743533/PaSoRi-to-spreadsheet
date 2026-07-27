@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

if exist .env (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" set "%%A=%%B"
    )
)

if not exist venv\Scripts\python.exe (
    echo [ERROR] venv not found. Run windows\setup.bat first.
    exit /b 1
)

echo Starting Web UI at http://127.0.0.1:5000
venv\Scripts\python.exe app.py %*
endlocal
