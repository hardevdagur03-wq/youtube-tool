@echo off
cd /d %~dp0
echo Starting YouTube Export Tool...
echo.
echo Open http://localhost:8000 in your browser after startup.
echo.
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -m uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    python -m uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload
)
pause
