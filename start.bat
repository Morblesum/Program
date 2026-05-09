@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   TOPCON Eye Data System - Start
echo ========================================
echo.
echo [INFO] Checking Python environment...
echo.

REM Check if this is the packaged version
if exist "TOPCON眼科数据管理系统.exe" (
    echo [OK] Packaged version detected
    echo.
    echo ========================================
    echo   Starting Packaged Application...
    echo ========================================
    echo.
    echo [1/2] Starting TOPCON Eye Data System...
    start "" "TOPCON眼科数据管理系统.exe"
    echo.
    echo [2/2] Waiting for service to start...
    timeout /t 3 /nobreak >nul
    echo.
    echo ========================================
    echo   System Started Successfully!
    echo ========================================
    echo.
    echo API Service: http://localhost:8000
    echo Web Interface: http://localhost:8501
    echo.
    echo Tips:
    echo   - The program will auto-start both backend and frontend
    echo   - Put XML files in this folder to auto-monitor
    echo   - Close the console window to stop services
    echo.
    echo Opening web interface in browser...
    timeout /t 2 /nobreak >nul
    start http://localhost:8501
    echo.
    echo ========================================
    pause
) else (
    echo [OK] Python detected
    echo.
    echo Checking dependencies...
    python -c "import fastapi, streamlit, sqlalchemy" 2>nul
    if errorlevel 1 (
        echo [ERROR] Dependencies not installed
        echo Please run: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [OK] Dependencies ready
    echo.
    echo ========================================
    echo   Starting Services...
    echo ========================================
    echo.
    echo [1/2] Starting FastAPI service...
    start "TOPCON Backend" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo.
    echo [2/2] Starting Streamlit interface...
    start "TOPCON Frontend" cmd /c "python -m streamlit run app/streamlit_app.py --server.headless=true"
    echo.
    echo ========================================
    echo   System Started Successfully!
    echo ========================================
    echo.
    echo API Service: http://localhost:8000
    echo Web Interface: http://localhost:8501
    echo.
    echo Tips: 
    echo   - Close both windows to stop services
    echo   - Put XML files in this folder to auto-monitor
    echo.
    timeout /t 3 /nobreak >nul
    echo Opening web interface in browser...
    start http://localhost:8501
    echo.
    echo ========================================
    pause
)
