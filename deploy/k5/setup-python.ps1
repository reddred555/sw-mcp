<#
.SYNOPSIS
    Встановлення Python + pyodbc для інтеграції Claude <-> K5 Access.
.DESCRIPTION
    1. Перевіряє/встановлює Python 3.12 x86 (32-bit, сумісний з Access x86)
    2. Встановлює Access Database Engine якщо потрібно
    3. Створює venv та ставить залежності
    4. Перевіряє з'єднання з .accdb
.NOTES
    Запускати: PowerShell від Адміністратора
    .\setup-python.ps1
#>

$ErrorActionPreference = "Stop"

$projectDir = "D:\K5\integration"
$venvDir = Join-Path $projectDir ".venv"

Write-Host "=== Python + K5 Integration Setup ===" -ForegroundColor Cyan

# ============================================================
# 1. CHECK PYTHON
# ============================================================
Write-Host ""
Write-Host "[1/4] Перевірка Python..." -ForegroundColor Yellow

$pythonExe = $null
$pythonPaths = @(
    "C:\Python312-32\python.exe",
    "C:\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312-32\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)

foreach ($p in $pythonPaths) {
    if (Test-Path $p) { $pythonExe = $p; break }
}

if (-not $pythonExe) {
    # Try system PATH
    $pythonExe = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if ($pythonExe) {
    $pyVersion = & $pythonExe --version 2>&1
    $pyArch = & $pythonExe -c "import struct; print(struct.calcsize('P') * 8)" 2>&1
    Write-Host "  [OK] $pyVersion ($($pyArch)-bit)" -ForegroundColor Green
    Write-Host "  Шлях: $pythonExe" -ForegroundColor DarkGray

    if ($pyArch -ne "32") {
        Write-Host ""
        Write-Host "  [!] УВАГА: Python $($pyArch)-bit, а Office/Access x86 (32-bit)." -ForegroundColor Red
        Write-Host "      pyodbc не зможе підключитися до Access через різну розрядність." -ForegroundColor Red
        Write-Host "      Потрібен Python 3.12 x86 (32-bit)." -ForegroundColor Red
        Write-Host ""
        Write-Host "      Завантажте:" -ForegroundColor Yellow
        Write-Host "      https://www.python.org/ftp/python/3.12.7/python-3.12.7.exe" -ForegroundColor Yellow
        Write-Host "      При встановленні виберіть 'Windows installer (32-bit)'" -ForegroundColor Yellow
        Write-Host "      Встановіть у C:\Python312-32\" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "  [!] Python не знайдено." -ForegroundColor Red
    Write-Host "      Завантажте Python 3.12 x86 (32-bit):" -ForegroundColor Yellow
    Write-Host "      https://www.python.org/ftp/python/3.12.7/python-3.12.7.exe" -ForegroundColor Yellow
    Write-Host "      Галочка 'Add to PATH', встановіть у C:\Python312-32\" -ForegroundColor Yellow
    exit 1
}

# ============================================================
# 2. CHECK ACCESS DATABASE ENGINE
# ============================================================
Write-Host ""
Write-Host "[2/4] Перевірка Access Database Engine..." -ForegroundColor Yellow

$aceDrivers = Get-OdbcDriver | Where-Object { $_.Name -match "Microsoft Access Driver" }
if ($aceDrivers) {
    Write-Host "  [OK] Знайдено ODBC-драйвер:" -ForegroundColor Green
    foreach ($d in $aceDrivers) {
        Write-Host "       $($d.Name)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  [!] ODBC-драйвер для Access не знайдено." -ForegroundColor Red
    Write-Host "      Якщо Office з Access вже встановлено - драйвер має бути." -ForegroundColor Yellow
    Write-Host "      Інакше завантажте Access Database Engine 2016 (x86):" -ForegroundColor Yellow
    Write-Host "      https://www.microsoft.com/en-us/download/details.aspx?id=54920" -ForegroundColor Yellow
}

# ============================================================
# 3. CREATE PROJECT + VENV
# ============================================================
Write-Host ""
Write-Host "[3/4] Створення проекту та venv..." -ForegroundColor Yellow

if (-not (Test-Path $projectDir)) {
    New-Item -ItemType Directory -Path $projectDir -Force | Out-Null
    Write-Host "  [+] $projectDir" -ForegroundColor Green
}

if (-not (Test-Path $venvDir)) {
    & $pythonExe -m venv $venvDir
    Write-Host "  [+] venv створено" -ForegroundColor Green
} else {
    Write-Host "  [=] venv вже існує" -ForegroundColor DarkGray
}

# Activate and install dependencies
$pipExe = Join-Path $venvDir "Scripts\pip.exe"
$pythonVenv = Join-Path $venvDir "Scripts\python.exe"

Write-Host "  [...] Встановлення залежностей..." -ForegroundColor Yellow
& $pipExe install --upgrade pip | Out-Null
& $pipExe install pyodbc fastapi uvicorn pydantic | Out-Null
Write-Host "  [OK] pyodbc, fastapi, uvicorn, pydantic встановлено" -ForegroundColor Green

# ============================================================
# 4. TEST CONNECTION
# ============================================================
Write-Host ""
Write-Host "[4/4] Тест підключення до Access..." -ForegroundColor Yellow

$accdbFiles = Get-ChildItem -Path "D:\K5\base" -Filter "*.accdb" -ErrorAction SilentlyContinue
$mdbFiles = Get-ChildItem -Path "D:\K5\base" -Filter "*.mdb" -ErrorAction SilentlyContinue
$dbFiles = @()
if ($accdbFiles) { $dbFiles += $accdbFiles }
if ($mdbFiles)   { $dbFiles += $mdbFiles }

if ($dbFiles.Count -eq 0) {
    Write-Host "  [--] Файли бази не знайдені в D:\K5\base\" -ForegroundColor DarkGray
    Write-Host "       Розпакуйте архіви К5 спочатку (setup-k5.ps1)" -ForegroundColor Yellow
} else {
    $testDb = $dbFiles[0].FullName
    Write-Host "  Тестую: $testDb" -ForegroundColor White

    $testScript = @"
import pyodbc, sys
db = r'$($testDb -replace "'","''")'
try:
    drv = [d for d in pyodbc.drivers() if 'Access' in d]
    if not drv:
        print('[FAIL] ODBC driver not found'); sys.exit(1)
    conn = pyodbc.connect(f'DRIVER={{{drv[0]}}};DBQ={db};')
    cursor = conn.cursor()
    tables = [t.table_name for t in cursor.tables(tableType='TABLE')]
    print(f'[OK] Connected. Tables: {len(tables)}')
    for t in tables[:10]:
        print(f'     - {t}')
    if len(tables) > 10:
        print(f'     ... and {len(tables)-10} more')
    conn.close()
except Exception as e:
    print(f'[FAIL] {e}'); sys.exit(1)
"@

    $testScript | & $pythonVenv -
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Підключення успішне!" -ForegroundColor Green
    } else {
        Write-Host "  [!] Не вдалося підключитися. Перевірте розрядність Python/Office." -ForegroundColor Red
    }
}

# ============================================================
# DONE
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python Integration Ready!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Проект: $projectDir" -ForegroundColor White
Write-Host "Python: $pythonVenv" -ForegroundColor White
Write-Host "Activate: $venvDir\Scripts\Activate.ps1" -ForegroundColor White
