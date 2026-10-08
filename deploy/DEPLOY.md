# K5 Deployment Guide — DESKTOP-15JM1RV

## Prerequisites

- Windows 11 Pro x64 (25H2)
- Xeon E5-2667 v4, 64 GB RAM
- Internet connection
- Admin rights

## Execution Order

All scripts run from **PowerShell (Administrator)**.

### Step 0. System Check

```powershell
.\deploy\k5\check-system.ps1
```

Shows: disks, RAM, Office, archivers, Python, Node.js, ODBC drivers.
Run first to understand what's already installed.

---

### Step 1. Install Node.js + Claude Code

1. Download Node.js 20 LTS from https://nodejs.org (LTS, Windows Installer x64)
2. Install with defaults ("Add to PATH" must be checked)
3. Reopen PowerShell as Admin

```powershell
node --version
npm --version
npm install -g @anthropic-ai/claude-code
claude
```

---

### Step 2. Install Office 2019 Pro Plus x86

```powershell
.\deploy\office\install-office.ps1
```

Then activate:

```powershell
.\deploy\office\activate-office.ps1
```

---

### Step 3. Deploy K5 Database

```powershell
.\deploy\k5\setup-k5.ps1
```

Creates `D:\K5\` structure, extracts archives, configures Trusted Locations.

---

### Step 4. Python + Integration Layer

```powershell
.\deploy\k5\setup-python.ps1
```

Installs Python 3.12 x86 venv with pyodbc, tests connection to .accdb.

---

## Folder Structure

```
D:\K5\
  base\           <- main K5 database (.accdb)
  updates\        <- version updates (Nv5-048R, Rita)
  integration\    <- Python + FastAPI bridge
    .venv\        <- Python virtual environment
  _backup\        <- timestamped backups
  _temp\          <- temporary files
```

## Troubleshooting

**pyodbc can't connect to Access:**
Python and Office must be the same bitness (both x86 or both x64).
Recommended: Office x86 + Python x86.

**Macros blocked in Access:**
Run `setup-k5.ps1` again — it sets Trusted Locations via registry.

**Archive extraction fails:**
Install 7-Zip from https://www.7-zip.org/download.html
