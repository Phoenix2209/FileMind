@echo off
title FileMind Launcher
echo Starting FileMind...
echo.

REM Check if Ollama is already running, if not start it in background
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Starting Ollama server in background...
    start /B ollama serve
    timeout /t 3 /nobreak >NUL
) else (
    echo Ollama is already running.
)

echo Launching FileMind window...
python main.py

pause