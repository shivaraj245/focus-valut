@echo off
echo ========================================
echo FocusVault - Quick Start Script
echo ========================================
echo.

echo Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running!
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo Docker found!
echo.

echo Starting FocusVault services...
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo FocusVault is starting!
echo ========================================
echo.
echo Access URLs:
echo   Backend API:  http://localhost:8000/docs
echo   Frontend:     http://localhost:3000
echo   Qdrant:       http://localhost:6333/dashboard
echo.
echo Next steps:
echo   1. Load Chrome extension from 'extension' folder
echo   2. Configure extension settings (API URL: http://localhost:8000/api)
echo   3. Start browsing learning content
echo   4. View dashboard at http://localhost:3000
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
pause
