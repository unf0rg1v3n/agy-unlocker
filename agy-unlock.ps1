#requires -version 3
# agy-unlocker: запускатор для PowerShell (Windows PowerShell 5.1 / PowerShell 7+).
$ErrorActionPreference = 'Stop'

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = $null
$pythonArgs = @()

function Test-AgyPython([string]$exe, [string[]]$preArgs) {
    # Кандидат годен, только если это настоящий интерпретатор Python 3.9+:
    # псевдонимы Microsoft Store (WindowsApps\python.exe) проходят Get-Command,
    # но не пробный запуск — без Python они печатают "Python was not found...".
    & $exe @preArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' *> $null
    return ($LASTEXITCODE -eq 0)
}

# Локальный venv имеет приоритет над системным интерпретатором.
foreach ($candidate in @(
    (Join-Path $dir '.venv\Scripts\python.exe'),
    (Join-Path $dir '.venv\bin\python')
)) {
    if ((Test-Path $candidate -PathType Leaf) -and (Test-AgyPython $candidate)) {
        $python = $candidate
        break
    }
}

# Get-Command -All выдаёт ВСЕ совпадения: ищем первый настоящий интерпретатор,
# даже если псевдоним Microsoft Store стоит в PATH раньше.
if (-not $python) {
    foreach ($cmd in @('python3', 'python', 'py')) {
        $preArgs = @()
        if ($cmd -eq 'py') { $preArgs = @('-3') }
        foreach ($resolved in @(Get-Command $cmd -All -ErrorAction SilentlyContinue)) {
            if ($resolved.Source -and (Test-AgyPython $resolved.Source $preArgs)) {
                $python = $resolved.Source
                $pythonArgs = $preArgs
                break
            }
        }
        if ($python) { break }
    }
}

if (-not $python) {
    Write-Host 'agy-unlock: не найден настоящий Python 3.9+.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Скорее всего, в Windows 11 команда "python" — это заглушка Microsoft Store,'
    Write-Host 'а сам Python не установлен. Любой из двух способов исправляет проблему:'
    Write-Host ''
    Write-Host '  1. Установите Python: https://www.python.org/downloads/'
    Write-Host '     На первом экране установщика включите "Add python.exe to PATH".'
    Write-Host '  2. Или отключите заглушки: Параметры - Приложения - Дополнительные'
    Write-Host '     параметры приложений - Псевдонимы выполнения приложений -'
    Write-Host '     выключите "python" и "py". Затем установите Python (способ 1).'
    Write-Host ''
    Write-Host 'После установки откройте НОВОЕ окно терминала и повторите команду.'
    exit 1
}

$env:PYTHONPATH = $dir + [IO.Path]::PathSeparator + $env:PYTHONPATH
& $python @pythonArgs -m agy_unlocker --shell=powershell @args
exit $LASTEXITCODE
