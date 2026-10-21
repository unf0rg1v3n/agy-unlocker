@echo off
rem agy-unlocker: запускатор для cmd.exe (Windows).
rem
rem Кандидаты проверяются пробным запуском, а не только "where": "из коробки"
rem в Windows 11 команды python/py — псевдонимы Microsoft Store, которые не
rem являются интерпретатором (печатают "Python was not found..." и выходят
rem с кодом 9009). Пробный запуск такие заглушки отсекает.
setlocal EnableExtensions
set "DIR=%~dp0"
set "PYTHONPATH=%DIR%;%PYTHONPATH%"
set "PROBE=import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
set "PYTHON_BIN="
set "PYTHON_PRE="

rem Локальный venv имеет приоритет над системным интерпретатором.
if exist "%DIR%.venv\Scripts\python.exe" (
    "%DIR%.venv\Scripts\python.exe" -c "%PROBE%" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_BIN=%DIR%.venv\Scripts\python.exe"
        goto run
    )
)

rem where выдаёт ВСЕ совпадения: пробуем каждый .exe и берём первый
rem настоящий интерпретатор, даже если псевдоним Microsoft Store стоит
rem в PATH раньше настоящего Python.
for /f "delims=" %%P in ('where python 2^>nul') do (
    if /i "%%~xP"==".exe" (
        "%%P" -c "%PROBE%" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_BIN=%%P"
            goto run
        )
    )
)
for /f "delims=" %%P in ('where py 2^>nul') do (
    if /i "%%~xP"==".exe" (
        "%%P" -3 -c "%PROBE%" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_BIN=%%P"
            set "PYTHON_PRE=-3"
            goto run
        )
    )
)

rem Обратная совместимость: батник-шимы (редкость эпохи conda) пробовать
rem нельзя — вызов .bat изнутри блока for ломает парсер. Берём первый
rem вслепую, как делала первая версия этой обёртки.
if not defined PYTHON_BIN (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if /i not "%%~xP"==".exe" (
            set "PYTHON_BIN=%%P"
            goto run
        )
    )
)
if not defined PYTHON_BIN (
    for /f "delims=" %%P in ('where py 2^>nul') do (
        if /i not "%%~xP"==".exe" (
            set "PYTHON_BIN=%%P"
            set "PYTHON_PRE=-3"
            goto run
        )
    )
)

if not defined PYTHON_BIN goto no_python

:run
"%PYTHON_BIN%" %PYTHON_PRE% -m agy_unlocker --shell=cmd %*
exit /b %errorlevel%

:no_python
echo agy-unlock: не найден настоящий Python 3.9+.
echo.
echo Скорее всего, в Windows 11 команда "python" — это заглушка Microsoft Store,
echo а сам Python не установлен. Любой из двух способов исправляет проблему:
echo.
echo   1. Установите Python: https://www.python.org/downloads/
echo      На первом экране установщика включите "Add python.exe to PATH".
echo   2. Или отключите заглушки: Параметры - Приложения - Дополнительные
echo      параметры приложений - Псевдонимы выполнения приложений -
echo      выключите "python" и "py". Затем установите Python (способ 1).
echo.
echo После установки откройте НОВОЕ окно терминала и повторите команду.
exit /b 1
