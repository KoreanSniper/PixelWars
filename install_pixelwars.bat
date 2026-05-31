@echo off
setlocal

set "REPO_ZIP=https://github.com/KoreanSniper/PixelWars/archive/refs/heads/main.zip"
set "INSTALL_DIR=%LOCALAPPDATA%\PixelWars"
set "TEMP_ZIP=%TEMP%\PixelWars-main.zip"
set "TEMP_DIR=%TEMP%\PixelWars-install"

echo PixelWars alpha 1.0.0 installer
echo.

where py >NUL 2>&1
if errorlevel 1 (
    where python >NUL 2>&1
    if errorlevel 1 (
        echo Python was not found or is not registered in PATH.
        echo Please install Python, then run this file again.
        echo Download: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if exist "%TEMP_ZIP%" del /f /q "%TEMP_ZIP%" >NUL 2>&1
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%" >NUL 2>&1
mkdir "%TEMP_DIR%" >NUL 2>&1

echo Downloading PixelWars from GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%REPO_ZIP%' -OutFile '%TEMP_ZIP%'"
if errorlevel 1 (
    echo Download failed.
    pause
    exit /b 1
)

echo Extracting files...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%TEMP_ZIP%' -DestinationPath '%TEMP_DIR%' -Force"
if errorlevel 1 (
    echo Extract failed.
    pause
    exit /b 1
)

if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" >NUL 2>&1
mkdir "%INSTALL_DIR%" >NUL 2>&1
xcopy "%TEMP_DIR%\PixelWars-main\*" "%INSTALL_DIR%\" /E /I /Y >NUL
if errorlevel 1 (
    echo File copy failed.
    pause
    exit /b 1
)

echo Installing Python packages...
where py >NUL 2>&1
if not errorlevel 1 (
    py -m pip install -r "%INSTALL_DIR%\requirements.txt"
) else (
    python -m pip install -r "%INSTALL_DIR%\requirements.txt"
)
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo Starting PixelWars...
cd /d "%INSTALL_DIR%"
call run.bat
