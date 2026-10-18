#requires -version 3
# agy-unlocker: запускатор для PowerShell (Windows PowerShell 5.1 / PowerShell 7+).
$ErrorActionPreference = 'Stop'

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = $null
$pythonArgs = @()

foreach ($candidate in @(
    (Join-Path $dir '.venv\Scripts\python.exe'),
    (Join-Path $dir '.venv\bin\python')
)) {
    if (Test-Path $candidate) { $python = $candidate; break }
}

if (-not $python) {
    foreach ($cmd in @('python3', 'python')) {
        $resolved = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($resolved) { $python = $resolved.Source; break }
    }
}

if (-not $python) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $python = $py.Source; $pythonArgs = @('-3') }
}

if (-not $python) {
    Write-Host 'agy-unlock: не найден Python 3.9+. Установите: https://www.python.org/downloads/' -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = $dir + [IO.Path]::PathSeparator + $env:PYTHONPATH
& $python @pythonArgs -m agy_unlocker --shell=powershell @args
exit $LASTEXITCODE
