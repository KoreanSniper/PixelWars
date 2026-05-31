@echo off
setlocal
set PYTHONDONTWRITEBYTECODE=1

where py >NUL 2>&1
if not errorlevel 1 (
    py main.py
    goto end
)

where python >NUL 2>&1
if not errorlevel 1 (
    python main.py
    goto end
)

echo Python was not found or is not registered in PATH.
echo Please install Python, then run this file again.
echo.
echo Download: https://www.python.org/downloads/

:end
pause
