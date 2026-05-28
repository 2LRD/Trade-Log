@echo off
setlocal
title Trade Log
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo.
    echo  [!] Trade Log is not set up yet.
    echo.
    echo  Please run "INSTALL - Double-Click This First.bat" first.
    echo.
    pause & exit /b 1
)

echo.
echo  Starting Trade Log...
echo  Your browser will open automatically.
echo  Keep this window open — close it to stop Trade Log.
echo.

"%PYTHON%" -m streamlit run "%~dp0app.py" --server.port 8502 --server.headless true --browser.gatherUsageStats false

echo.
echo  Trade Log has stopped.
pause
endlocal
