#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Завантажує та встановлює Office 2019 Pro Plus x86 з Access.
.DESCRIPTION
    1. Завантажує Office Deployment Tool (ODT) з Microsoft
    2. Розпаковує setup.exe
    3. Завантажує Office-файли за configuration.xml
    4. Встановлює Office
.NOTES
    Запускати: PowerShell від Адміністратора
    .\install-office.ps1
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = "D:\OfficeInstall"
$configFile = Join-Path $scriptDir "configuration.xml"

Write-Host "=== Office 2019 Pro Plus x86 Installer ===" -ForegroundColor Cyan

# --- 1. Create work directory ---
if (-not (Test-Path $workDir)) {
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    Write-Host "[OK] Створено $workDir" -ForegroundColor Green
}

# --- 2. Download Office Deployment Tool ---
$odtUrl = "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB8A7D4A7E/officedeploymenttool_18324-20030.exe"
$odtExe = Join-Path $workDir "ODTSetup.exe"

if (-not (Test-Path $odtExe)) {
    Write-Host "[...] Завантаження Office Deployment Tool..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $odtUrl -OutFile $odtExe -UseBasicParsing
        Write-Host "[OK] ODT завантажено" -ForegroundColor Green
    }
    catch {
        Write-Host "[!] Не вдалося завантажити ODT автоматично." -ForegroundColor Red
        Write-Host "    Завантажте вручну:" -ForegroundColor Red
        Write-Host "    https://www.microsoft.com/en-us/download/details.aspx?id=49117" -ForegroundColor Yellow
        Write-Host "    Збережіть у $workDir як ODTSetup.exe" -ForegroundColor Yellow
        exit 1
    }
}

# --- 3. Extract ODT (setup.exe) ---
$setupExe = Join-Path $workDir "setup.exe"
if (-not (Test-Path $setupExe)) {
    Write-Host "[...] Розпакування ODT..." -ForegroundColor Yellow
    Start-Process -FilePath $odtExe -ArgumentList "/quiet /extract:$workDir" -Wait
    Write-Host "[OK] setup.exe розпаковано" -ForegroundColor Green
}

# --- 4. Copy configuration.xml ---
$targetConfig = Join-Path $workDir "configuration.xml"
Copy-Item -Path $configFile -Destination $targetConfig -Force
Write-Host "[OK] configuration.xml скопійовано" -ForegroundColor Green

# --- 5. Download Office files ---
Write-Host "[...] Завантаження файлів Office (може зайняти 10-20 хв)..." -ForegroundColor Yellow
$downloadProcess = Start-Process -FilePath $setupExe -ArgumentList "/download $targetConfig" -WorkingDirectory $workDir -Wait -PassThru
if ($downloadProcess.ExitCode -ne 0) {
    Write-Host "[!] Помилка при завантаженні Office. Код: $($downloadProcess.ExitCode)" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Файли Office завантажено" -ForegroundColor Green

# --- 6. Install Office ---
Write-Host "[...] Встановлення Office 2019 Pro Plus x86..." -ForegroundColor Yellow
Write-Host "     Це може зайняти 5-15 хвилин. Не закривайте це вікно." -ForegroundColor Yellow
$installProcess = Start-Process -FilePath $setupExe -ArgumentList "/configure $targetConfig" -WorkingDirectory $workDir -Wait -PassThru
if ($installProcess.ExitCode -ne 0) {
    Write-Host "[!] Помилка при встановленні. Код: $($installProcess.ExitCode)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Office 2019 встановлено! ===" -ForegroundColor Green
Write-Host "Наступний крок: запустіть activate-office.ps1 для активації" -ForegroundColor Cyan
