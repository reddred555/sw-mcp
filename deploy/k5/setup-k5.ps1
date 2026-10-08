#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Розгортання бази К5: папки, розпакування архівів, Trusted Locations.
.DESCRIPTION
    1. Створює структуру папок D:\K5\
    2. Розпаковує архіви К5 з робочого столу
    3. Реєструє Trusted Locations для Access в реєстрі
    4. Вимикає блокування макросів
.NOTES
    Запускати: PowerShell від Адміністратора
    .\setup-k5.ps1
#>

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIG
# ============================================================
$k5Root       = "D:\K5"
$k5Backup     = "D:\K5\_backup"
$k5Base       = "D:\K5\base"
$k5Updates    = "D:\K5\updates"
$k5Temp       = "D:\K5\_temp"

$desktopPath  = "$env:USERPROFILE\Desktop"
$publicDesktop = "$env:PUBLIC\Desktop"

# Archives to look for (in order of deployment)
$archives = @(
    @{ Pattern = "K5-033-ka*";        Target = $k5Base;    Name = "K5 Base v033" },
    @{ Pattern = "Nv5-048R*";         Target = $k5Updates; Name = "K5 Update Nv5-048R" },
    @{ Pattern = "Nv-V-5-48-Rita*";   Target = $k5Updates; Name = "K5 Update Rita v48" }
)

Write-Host "=== K5 Database Deployment ===" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# 1. CREATE FOLDERS
# ============================================================
Write-Host "[1/5] Створення структури папок..." -ForegroundColor Yellow

$folders = @($k5Root, $k5Backup, $k5Base, $k5Updates, $k5Temp)
foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Host "  [+] $folder" -ForegroundColor Green
    } else {
        Write-Host "  [=] $folder (вже існує)" -ForegroundColor DarkGray
    }
}

# ============================================================
# 2. CHECK FOR ARCHIVER
# ============================================================
Write-Host ""
Write-Host "[2/5] Пошук архіватора..." -ForegroundColor Yellow

$unrarExe = $null
$sevenZipExe = $null

# Check 7-Zip
$sevenZipPaths = @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe"
)
foreach ($p in $sevenZipPaths) {
    if (Test-Path $p) { $sevenZipExe = $p; break }
}

# Check WinRAR
$winrarPaths = @(
    "C:\Program Files\WinRAR\UnRAR.exe",
    "C:\Program Files (x86)\WinRAR\UnRAR.exe",
    "C:\Program Files\WinRAR\WinRAR.exe",
    "C:\Program Files (x86)\WinRAR\WinRAR.exe"
)
foreach ($p in $winrarPaths) {
    if (Test-Path $p) { $unrarExe = $p; break }
}

if ($sevenZipExe) {
    Write-Host "  [OK] 7-Zip: $sevenZipExe" -ForegroundColor Green
    $archiver = "7zip"
} elseif ($unrarExe) {
    Write-Host "  [OK] WinRAR: $unrarExe" -ForegroundColor Green
    $archiver = "winrar"
} else {
    Write-Host "  [!] Архіватор не знайдено (7-Zip або WinRAR)." -ForegroundColor Red
    Write-Host "      Завантажте 7-Zip: https://www.7-zip.org/download.html" -ForegroundColor Yellow
    Write-Host "      Після встановлення запустіть цей скрипт знову." -ForegroundColor Yellow
    exit 1
}

# ============================================================
# 3. FIND AND EXTRACT ARCHIVES
# ============================================================
Write-Host ""
Write-Host "[3/5] Пошук та розпакування архівів К5..." -ForegroundColor Yellow

$searchPaths = @($desktopPath, $publicDesktop)

foreach ($archive in $archives) {
    $found = $null
    foreach ($searchPath in $searchPaths) {
        $candidates = Get-ChildItem -Path $searchPath -Filter "$($archive.Pattern).rar" -ErrorAction SilentlyContinue
        if (-not $candidates) {
            $candidates = Get-ChildItem -Path $searchPath -Filter "$($archive.Pattern).zip" -ErrorAction SilentlyContinue
        }
        if ($candidates) {
            $found = $candidates | Select-Object -First 1
            break
        }
    }

    if ($found) {
        Write-Host "  [OK] Знайдено: $($found.Name)" -ForegroundColor Green

        $targetDir = $archive.Target
        $extractDir = Join-Path $targetDir ($found.BaseName)

        if (Test-Path $extractDir) {
            Write-Host "       Вже розпаковано, пропускаю" -ForegroundColor DarkGray
            continue
        }

        Write-Host "       Розпаковую в $targetDir ..." -ForegroundColor Yellow

        if ($archiver -eq "7zip") {
            & $sevenZipExe x $found.FullName "-o$targetDir" -y | Out-Null
        } else {
            if ($unrarExe -match "UnRAR") {
                & $unrarExe x $found.FullName $targetDir\ -y | Out-Null
            } else {
                & $unrarExe x $found.FullName $targetDir\ | Out-Null
            }
        }

        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
            Write-Host "       [OK] Розпаковано" -ForegroundColor Green
        } else {
            Write-Host "       [!] Помилка розпакування (код $LASTEXITCODE)" -ForegroundColor Red
        }
    } else {
        Write-Host "  [--] $($archive.Name) не знайдено на робочому столі" -ForegroundColor DarkGray
    }
}

# Also copy non-archived .accdb/.mdb from desktop
Write-Host ""
Write-Host "  Пошук .accdb/.mdb файлів на робочому столі..." -ForegroundColor Yellow
foreach ($searchPath in $searchPaths) {
    $dbFiles = Get-ChildItem -Path $searchPath -Include "*.accdb","*.mdb" -Recurse -ErrorAction SilentlyContinue
    foreach ($db in $dbFiles) {
        $dest = Join-Path $k5Base $db.Name
        if (-not (Test-Path $dest)) {
            Copy-Item -Path $db.FullName -Destination $dest
            Write-Host "  [+] Скопійовано: $($db.Name)" -ForegroundColor Green
        }
    }
}

# ============================================================
# 4. BACKUP
# ============================================================
Write-Host ""
Write-Host "[4/5] Створення бекапу..." -ForegroundColor Yellow

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = Join-Path $k5Backup $timestamp

$dbFilesInBase = Get-ChildItem -Path $k5Base -Include "*.accdb","*.mdb" -Recurse -ErrorAction SilentlyContinue
if ($dbFilesInBase) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    foreach ($db in $dbFilesInBase) {
        Copy-Item -Path $db.FullName -Destination $backupDir
        Write-Host "  [+] Бекап: $($db.Name) -> $backupDir" -ForegroundColor Green
    }
} else {
    Write-Host "  [--] .accdb/.mdb файли ще не знайдені в $k5Base" -ForegroundColor DarkGray
}

# ============================================================
# 5. CONFIGURE ACCESS TRUSTED LOCATIONS
# ============================================================
Write-Host ""
Write-Host "[5/5] Налаштування Trusted Locations в реєстрі..." -ForegroundColor Yellow

$accessVersions = @("16.0", "15.0", "14.0")
$trustedPaths = @($k5Root, $k5Base, $k5Updates)

foreach ($ver in $accessVersions) {
    $regBase = "HKCU:\Software\Microsoft\Office\$ver\Access\Security\Trusted Locations"

    if (-not (Test-Path "HKCU:\Software\Microsoft\Office\$ver\Access")) {
        continue
    }

    Write-Host "  Знайдено Access $ver" -ForegroundColor Green

    # Ensure Trusted Locations key exists
    if (-not (Test-Path $regBase)) {
        New-Item -Path $regBase -Force | Out-Null
    }

    $locationIndex = 100
    foreach ($trustedPath in $trustedPaths) {
        $locationKey = Join-Path $regBase "Location$locationIndex"
        if (-not (Test-Path $locationKey)) {
            New-Item -Path $locationKey -Force | Out-Null
        }
        Set-ItemProperty -Path $locationKey -Name "Path" -Value "$trustedPath\"
        Set-ItemProperty -Path $locationKey -Name "AllowSubfolders" -Value 1 -Type DWord
        Set-ItemProperty -Path $locationKey -Name "Description" -Value "K5 Production Database"
        Write-Host "  [+] Trusted Location: $trustedPath (Access $ver)" -ForegroundColor Green
        $locationIndex++
    }

    # Disable VBA macro notification (enable all macros for trusted locations)
    $securityKey = "HKCU:\Software\Microsoft\Office\$ver\Access\Security"
    Set-ItemProperty -Path $securityKey -Name "VBAWarnings" -Value 1 -Type DWord
    Write-Host "  [+] Макроси увімкнено для Access $ver" -ForegroundColor Green
}

# ============================================================
# DONE
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  K5 Deployment Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Структура:" -ForegroundColor White
Write-Host "  D:\K5\base\      - основна база К5" -ForegroundColor White
Write-Host "  D:\K5\updates\   - оновлення" -ForegroundColor White
Write-Host "  D:\K5\_backup\   - бекапи" -ForegroundColor White
Write-Host ""
Write-Host "Наступні кроки:" -ForegroundColor Yellow
Write-Host "  1. Відкрийте .accdb файл з D:\K5\base\ в Access" -ForegroundColor White
Write-Host "  2. Перевірте що форми та макроси працюють" -ForegroundColor White
Write-Host "  3. Якщо база split - налаштуйте Linked Tables" -ForegroundColor White
Write-Host "  4. Запустіть setup-python.ps1 для інтеграції з Claude" -ForegroundColor White
