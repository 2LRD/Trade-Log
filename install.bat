@echo off
cd /d "%~dp0"
echo Installing Trade Log dependencies...
python --version
if errorlevel 1 (
    echo Python is not installed or not on PATH. Download it from https://python.org
    pause
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency install failed. See errors above.
    pause
    exit /b 1
)
echo.
echo Install complete. Run launch.bat to start the app, or launch_demo.bat for the demo.
pause
