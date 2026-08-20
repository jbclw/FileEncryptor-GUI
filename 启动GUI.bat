@echo off
title FileEncryptor GUI
cd /d "%~dp0"

echo ============================================
echo   FileEncryptor GUI Launcher
echo ============================================
echo.

set "PY="

REM Check local directory
if exist "python.exe" (
    python.exe -c "import winpty; import tkinter" 2>nul
    if not errorlevel 1 set "PY=python.exe"
)

REM Check common install paths (with winpty+tkinter check)
if not defined PY call :check "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY call :check "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY call :check "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY call :check "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY call :check "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PY call :check "C:\Python314\python.exe"
if not defined PY call :check "C:\Python313\python.exe"
if not defined PY call :check "C:\Python312\python.exe"
if not defined PY call :check "C:\Python311\python.exe"
if not defined PY call :check "C:\Python310\python.exe"

REM Check py launcher
if not defined PY (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import winpty; import tkinter" 2>nul
        if not errorlevel 1 set "PY=py -3"
    )
)

REM Check PATH python
if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 (
        python -c "import winpty; import tkinter" 2>nul
        if not errorlevel 1 set "PY=python"
    )
)

if not defined PY (
    echo.
    echo [ERROR] Python with winpty and tkinter not found.
    echo.
    echo Please install:
    echo   1. Python 3.10+ from https://www.python.org/downloads/
    echo   2. Then run: pip install pywinpty psutil
    echo.
    pause
    exit /b 1
)

echo Python: %PY%
echo.
echo Starting GUI...
echo.

%PY% -m app.ui.gui

if errorlevel 1 (
    echo.
    echo [ERROR] GUI exited with code %ERRORLEVEL%
    echo.
    pause
)

goto :eof

:check
if exist "%~1" (
    "%~1" -c "import winpty; import tkinter" 2>nul
    if not errorlevel 1 set "PY=%~1"
)
goto :eof
