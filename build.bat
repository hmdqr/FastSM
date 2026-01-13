@echo off
REM Build script for FastSM using Nuitka

echo ========================================
echo Building FastSM with Nuitka
echo ========================================
echo.

REM Check if Nuitka is installed
python -m nuitka --version
if errorlevel 1 (
    echo Nuitka is not installed. Installing...
    pip install nuitka
    if errorlevel 1 (
        echo Failed to install Nuitka
        pause
        exit /b 1
    )
)

REM Run the build script
python build.py

echo.
pause
