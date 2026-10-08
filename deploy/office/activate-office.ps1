#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Активація Office 2019 через KMSAuto з робочого столу.
.NOTES
    Запускати: PowerShell від Адміністратора
    .\activate-office.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "=== Активація Office 2019 ===" -ForegroundColor Cyan

# --- Find KMSAuto on Desktop ---
$desktopPaths = @(
    "$env:USERPROFILE\Desktop",
    "$env:PUBLIC\Desktop",
    "C:\Users\Admin\Desktop"
)

$kmsFound = $false
foreach ($desktop in $desktopPaths) {
    $kmsPatterns = @(
        (Join-Path $desktop "KMSAuto*\KMSAuto*.exe"),
        (Join-Path $desktop "KMSAuto*.exe")
    )
    foreach ($pattern in $kmsPatterns) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            Write-Host "[OK] Знайдено KMSAuto: $($found.FullName)" -ForegroundColor Green
            Write-Host "[...] Запускаю KMSAuto..." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "  У вікні KMSAuto:" -ForegroundColor White
            Write-Host "  1. Натисніть 'Активація' або 'Activation'" -ForegroundColor White
            Write-Host "  2. Виберіть 'Активувати Office'" -ForegroundColor White
            Write-Host "  3. Дочекайтеся 'Продукт успішно активовано'" -ForegroundColor White
            Write-Host ""
            Start-Process -FilePath $found.FullName
            $kmsFound = $true
            break
        }
    }
    if ($kmsFound) { break }
}

if (-not $kmsFound) {
    Write-Host "[!] KMSAuto не знайдено на робочому столі." -ForegroundColor Red
    Write-Host "    Шукав у:" -ForegroundColor Yellow
    foreach ($p in $desktopPaths) { Write-Host "      $p" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "    Знайдіть KMSAuto вручну і запустіть." -ForegroundColor Yellow
}

# --- Verify activation ---
Write-Host ""
Write-Host "Після активації перевірте командою:" -ForegroundColor Cyan
Write-Host '  cscript "C:\Program Files (x86)\Microsoft Office\Office16\OSPP.VBS" /dstatus' -ForegroundColor White
