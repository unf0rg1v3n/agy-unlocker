@echo off
rem agy-unlocker: запускатор для cmd.exe (Windows).
setlocal
set "DIR=%~dp0"

if exist "%DIR%.venv\Scripts\python.exe" (
    set "PYTHONPATH=%DIR%;%PYTHONPATH%"
    "%DIR%.venv\Scripts\python.exe" -m agy_unlocker --shell=cmd %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHONPATH=%DIR%;%PYTHONPATH%"
    python -m agy_unlocker --shell=cmd %*
    exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHONPATH=%DIR%;%PYTHONPATH%"
    py -3 -m agy_unlocker --shell=cmd %*
    exit /b %errorlevel%
)

echo agy-unlock: Python 3.9+ не найден. Установите: https://www.python.org/downloads/
exit /b 1
