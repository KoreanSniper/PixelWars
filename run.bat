@echo off
setlocal
set PYTHONDONTWRITEBYTECODE=1

py main.py
if not errorlevel 1 goto END

python main.py
if not errorlevel 1 goto END

echo.
echo Python is not installed or not added to PATH.
echo Please install Python and try again.
echo Download: https://www.python.org/downloads/
echo.
pause
exit /b 1

:END
pause
exit /b 0