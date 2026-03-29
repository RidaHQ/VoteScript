@echo off
title Start Tor Service

:: Get current folder path
set "CURRENT_DIR=%~dp0"
set "TOR_DIR=%CURRENT_DIR%Tor"

echo ========================================
echo    START TOR PORTABLE
echo ========================================
echo.
echo Current folder: %CURRENT_DIR%
echo Tor folder: %TOR_DIR%
echo.

:: Check if Tor folder exists
if not exist "%TOR_DIR%" (
    echo ERROR: Tor folder not found!
    echo.
    echo Create "Tor" folder and put tor.exe inside
    echo.
    pause
    exit /b 1
)

:: Check if tor.exe exists
if not exist "%TOR_DIR%\tor.exe" (
    echo ERROR: tor.exe not found in %TOR_DIR%
    echo.
    pause
    exit /b 1
)

:: Check if torrc exists
if not exist "%TOR_DIR%\torrc" (
    echo WARNING: torrc not found, creating...
    (
        echo SocksPort 9050
        echo ControlPort 9051
        echo CookieAuthentication 1
        echo DataDirectory ./data
        echo Log notice file ./tor.log
    ) > "%TOR_DIR%\torrc"
    echo torrc created
)

:: SHOW TORRC CONTENT
echo.
echo torrc content:
type "%TOR_DIR%\torrc"
echo.

echo [1/4] Stop Tor service (if present)...
net stop tor >nul 2>&1
sc stop tor >nul 2>&1
if %errorlevel% equ 0 (
    echo    Tor service stopped
) else (
    echo    No active Tor service found
)

echo.
echo [2/4] Stop existing Tor processes...
taskkill /F /IM tor.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo    Tor processes terminated
) else (
    echo    No Tor processes found
)

echo.
echo [3/4] Stop Firefox (if needed)...
taskkill /F /IM firefox.exe >nul 2>&1

echo.
echo [4/4] Waiting 3 seconds...
timeout /t 3 /nobreak >nul

cls
echo ========================================
echo    START TOR PORTABLE
echo ========================================
echo.
echo Tor folder: %TOR_DIR%
echo Config file: torrc
echo.
echo Tor will start in background
echo No visible window
echo.
echo ========================================

:: Start Tor in background
start /B "" "%TOR_DIR%\tor.exe" -f "%TOR_DIR%\torrc"

:: Wait for Tor to start
echo Waiting for Tor to start...
timeout /t 5 /nobreak >nul

:: Check if ports are listening
echo.
echo Checking Tor ports:
netstat -an | findstr 9050
netstat -an | findstr 9051

echo.
echo Tor started in background!
echo.
echo Press any key to close this window
pause >nul