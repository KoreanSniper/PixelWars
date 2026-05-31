@echo off
chcp 65001 >NUL
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
        echo Python이 설치되어 있지 않거나 PATH에 등록되어 있지 않습니다.
        echo Python을 설치한 뒤 다시 실행해주세요.
        echo 다운로드: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

if exist "%TEMP_ZIP%" del /f /q "%TEMP_ZIP%" >NUL 2>&1
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%" >NUL 2>&1
mkdir "%TEMP_DIR%" >NUL 2>&1

echo GitHub에서 PixelWars를 다운로드합니다...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%REPO_ZIP%' -OutFile '%TEMP_ZIP%'"
if errorlevel 1 (
    echo 다운로드에 실패했습니다.
    pause
    exit /b 1
)

echo 압축을 해제합니다...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%TEMP_ZIP%' -DestinationPath '%TEMP_DIR%' -Force"
if errorlevel 1 (
    echo 압축 해제에 실패했습니다.
    pause
    exit /b 1
)

if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" >NUL 2>&1
mkdir "%INSTALL_DIR%" >NUL 2>&1
xcopy "%TEMP_DIR%\PixelWars-main\*" "%INSTALL_DIR%\" /E /I /Y >NUL
if errorlevel 1 (
    echo 설치 파일 복사에 실패했습니다.
    pause
    exit /b 1
)

echo 필요한 Python 패키지를 설치합니다...
where py >NUL 2>&1
if not errorlevel 1 (
    py -m pip install -r "%INSTALL_DIR%\requirements.txt"
) else (
    python -m pip install -r "%INSTALL_DIR%\requirements.txt"
)
if errorlevel 1 (
    echo 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

echo PixelWars를 실행합니다...
cd /d "%INSTALL_DIR%"
call run.bat
