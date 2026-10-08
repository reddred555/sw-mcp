<#
.SYNOPSIS
    Перевірка системи перед розгортанням К5.
.DESCRIPTION
    Показує стан: диски, RAM, Office, архіватори, Python, ODBC.
    Запускати першим перед усіма іншими скриптами.
.NOTES
    .\check-system.ps1
#>

Write-Host "=== System Check for K5 Deployment ===" -ForegroundColor Cyan
Write-Host "  Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor DarkGray
Write-Host "  Computer: $env:COMPUTERNAME" -ForegroundColor DarkGray
Write-Host "  User: $env:USERNAME" -ForegroundColor DarkGray
Write-Host ""

# --- OS ---
Write-Host "[OS]" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "  $($os.Caption) $($os.Version)" -ForegroundColor White
Write-Host "  Architecture: $($os.OSArchitecture)" -ForegroundColor White

# --- CPU ---
Write-Host ""
Write-Host "[CPU]" -ForegroundColor Yellow
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Write-Host "  $($cpu.Name)" -ForegroundColor White
Write-Host "  Cores: $($cpu.NumberOfCores), Threads: $($cpu.NumberOfLogicalProcessors)" -ForegroundColor White

# --- RAM ---
Write-Host ""
Write-Host "[RAM]" -ForegroundColor Yellow
$totalRAM = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeRAM = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
Write-Host "  Total: $totalRAM GB, Free: $freeRAM GB" -ForegroundColor White

# --- Disks ---
Write-Host ""
Write-Host "[Disks]" -ForegroundColor Yellow
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $total = [math]::Round($_.Size / 1GB, 1)
    $free = [math]::Round($_.FreeSpace / 1GB, 1)
    $pct = [math]::Round(($_.FreeSpace / $_.Size) * 100, 0)
    $color = if ($pct -lt 10) { "Red" } elseif ($pct -lt 25) { "Yellow" } else { "Green" }
    Write-Host "  $($_.DeviceID) Total: $total GB, Free: $free GB ($pct%)" -ForegroundColor $color
}

# --- Office ---
Write-Host ""
Write-Host "[Microsoft Office]" -ForegroundColor Yellow
$officePaths = @(
    "C:\Program Files\Microsoft Office\Office16\MSACCESS.EXE",
    "C:\Program Files (x86)\Microsoft Office\Office16\MSACCESS.EXE",
    "C:\Program Files\Microsoft Office\root\Office16\MSACCESS.EXE",
    "C:\Program Files (x86)\Microsoft Office\root\Office16\MSACCESS.EXE"
)
$accessFound = $false
foreach ($p in $officePaths) {
    if (Test-Path $p) {
        $fileInfo = Get-Item $p
        $is32 = $p -match "Program Files \(x86\)" -or $p -match "root"
        Write-Host "  [OK] Access found: $p" -ForegroundColor Green
        Write-Host "       Version: $($fileInfo.VersionInfo.ProductVersion)" -ForegroundColor DarkGray
        $accessFound = $true
        break
    }
}
if (-not $accessFound) {
    Write-Host "  [--] Microsoft Access not found" -ForegroundColor Red
}

# --- Archivers ---
Write-Host ""
Write-Host "[Archivers]" -ForegroundColor Yellow
$sevenZip = Test-Path "C:\Program Files\7-Zip\7z.exe"
$winrar = Test-Path "C:\Program Files\WinRAR\WinRAR.exe"
if ($sevenZip) { Write-Host "  [OK] 7-Zip" -ForegroundColor Green }
if ($winrar)   { Write-Host "  [OK] WinRAR" -ForegroundColor Green }
if (-not $sevenZip -and -not $winrar) {
    Write-Host "  [--] No archiver found (need 7-Zip or WinRAR)" -ForegroundColor Red
}

# --- Python ---
Write-Host ""
Write-Host "[Python]" -ForegroundColor Yellow
$pyExe = Get-Command python -ErrorAction SilentlyContinue
if ($pyExe) {
    $pyVer = & python --version 2>&1
    $pyArch = & python -c "import struct; print(struct.calcsize('P') * 8)" 2>&1
    Write-Host "  [OK] $pyVer ($($pyArch)-bit)" -ForegroundColor Green
    Write-Host "       Path: $($pyExe.Source)" -ForegroundColor DarkGray
} else {
    Write-Host "  [--] Python not found" -ForegroundColor Red
}

# --- Node.js ---
Write-Host ""
Write-Host "[Node.js]" -ForegroundColor Yellow
$nodeExe = Get-Command node -ErrorAction SilentlyContinue
if ($nodeExe) {
    $nodeVer = & node --version 2>&1
    Write-Host "  [OK] Node.js $nodeVer" -ForegroundColor Green
    $npmVer = & npm --version 2>&1
    Write-Host "  [OK] npm $npmVer" -ForegroundColor Green
} else {
    Write-Host "  [--] Node.js not found" -ForegroundColor Red
}

# --- Claude Code ---
Write-Host ""
Write-Host "[Claude Code]" -ForegroundColor Yellow
$claudeExe = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeExe) {
    Write-Host "  [OK] Claude Code installed" -ForegroundColor Green
    Write-Host "       Path: $($claudeExe.Source)" -ForegroundColor DarkGray
} else {
    Write-Host "  [--] Claude Code not installed" -ForegroundColor Red
    Write-Host "       Run: npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
}

# --- ODBC Drivers ---
Write-Host ""
Write-Host "[ODBC Drivers (Access)]" -ForegroundColor Yellow
$drivers = Get-OdbcDriver -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Access|ACE" }
if ($drivers) {
    foreach ($d in $drivers) {
        Write-Host "  [OK] $($d.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "  [--] No Access ODBC driver found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Check Complete ===" -ForegroundColor Cyan
