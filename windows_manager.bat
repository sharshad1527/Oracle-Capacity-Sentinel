@echo off
setlocal EnableDelayedExpansion

:: Configuration
set "WINDOW_TITLE=Oracle Capacity Sentinel"
set "SCRIPT_NAME=Scripts\desktop_engine.py"

:menu
cls
echo ==========================================
echo    Oracle Cloud Control Panel (WINDOWS)
echo ==========================================

:: Check if the process is running by looking for the specific Window Title
tasklist /v | findstr /i "%WINDOW_TITLE%" >nul
if %errorlevel% equ 0 (
    echo Status: [ RUNNING ]
) else (
    echo Status: [ STOPPED ]
)

echo ------------------------------------------
echo 1. Start Sentinel (Opens in new window)
echo 2. Stop ^& Kill Sentinel
echo 3. Exit Menu
echo ------------------------------------------
set /p choice="Select an option [1-3]: "

if "%choice%"=="1" goto start_sentinel
if "%choice%"=="2" goto stop_sentinel
if "%choice%"=="3" goto end
goto invalid

:start_sentinel
tasklist /v | findstr /i "%WINDOW_TITLE%" >nul
if %errorlevel% equ 0 (
    echo.
    echo Sentinel is already running! Look for the "%WINDOW_TITLE%" window.
    timeout /t 2 >nul
    goto menu
) else (
    echo.
    echo Starting Sentinel in a new window...
    :: Launches a new cmd window with the specific title running the python script
    start "%WINDOW_TITLE%" cmd /c "python %SCRIPT_NAME% & pause"
    timeout /t 2 >nul
    goto menu
)

:stop_sentinel
tasklist /v | findstr /i "%WINDOW_TITLE%" >nul
if %errorlevel% equ 0 (
    echo.
    echo Killing the Sentinel session...
    :: Kills any window matching the specific title
    taskkill /FI "WINDOWTITLE eq %WINDOW_TITLE%*" /T /F >nul 2>&1
    echo Stopped.
    timeout /t 2 >nul
    goto menu
) else (
    echo.
    echo Sentinel is not running.
    timeout /t 2 >nul
    goto menu
)

:invalid
echo.
echo Invalid option.
timeout /t 1 >nul
goto menu

:end
echo.
echo Exiting Control Panel...
endlocal
exit /b