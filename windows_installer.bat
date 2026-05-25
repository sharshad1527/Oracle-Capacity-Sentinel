@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo    OCS Windows Environment Installer
echo ==========================================
echo.

:: Check for Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please download and install Python from: https://www.python.org/downloads/
    echo IMPORTANT: Check the box "Add Python to PATH" at the bottom of the installer!
    echo.
    pause
    exit /b
)

echo [OK] Python is installed.
echo Updating pip...
python -m pip install --upgrade pip >nul 2>&1

echo Installing Oracle Cloud Infrastructure (OCI) SDK...
python -m pip install oci

echo.
echo ==========================================
echo [SUCCESS] Dependencies installed!
echo Cleaning up environment files...
echo ==========================================

:: Create cleanup directory
if not exist otherOSmanagers mkdir otherOSmanagers

:: Move irrelevant managers and installers
if exist linux_manager.bash move linux_manager.bash otherOSmanagers\ >nul
if exist termux_manager.bash move termux_manager.bash otherOSmanagers\ >nul
if exist linux_installer.bash move linux_installer.bash otherOSmanagers\ >nul
if exist termux_installer.bash move termux_installer.bash otherOSmanagers\ >nul

echo Starting the Interactive Setup Wizard...
pause
python interactive_setup_wizard.py

echo.
echo Setup Complete! You can now use "windows_manager.bat".
echo Archiving installer...
:: Moves itself out of the root folder!
move "%~nx0" otherOSmanagers\ >nul