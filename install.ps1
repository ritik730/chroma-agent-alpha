# install.ps1
# Interactive Installer for CHROMA-AGENT-ALPHA

Clear-Host
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      CHROMA-AGENT-ALPHA LABORATORY SYSTEM INSTALLER    " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "This script configures the local pipeline, virtual environments,"
Write-Host "folder watcher links, and desktop shortcuts."
Write-Host ""

# Ensure absolute installation path
$InstallDir = "C:\chroma-agent-alpha"
if ($PSScriptRoot -ne $InstallDir) {
    Write-Host "[WARNING] Installer is running from $PSScriptRoot." -ForegroundColor Yellow
    Write-Host "It is highly recommended to run this project from $InstallDir." -ForegroundColor Yellow
}

# 1. Prompt for API Key
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "1. AI API Configuration" -ForegroundColor Green
$ApiKey = ""
while (-not $ApiKey) {
    $ApiKey = Read-Host "Please enter your OpenRouter API Key"
    if ($ApiKey) { $ApiKey = $ApiKey.Trim() }
    if (-not $ApiKey) {
        Write-Host "[Error] API Key cannot be empty." -ForegroundColor Red
    }
}

# 2. Prompt for Folder X (instrument drops)
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "2. Instrument Output Directory Configuration" -ForegroundColor Green
Write-Host "Specify the folder where your GC-MS or HPLC instrument writes its output files."
$FolderX = ""
while (-not $FolderX) {
    $FolderX = Read-Host "Enter the absolute folder path (e.g. D:\InstrumentData\GCMS_Output)"
    if ($FolderX) { $FolderX = $FolderX.Trim() }
    if (-not $FolderX) {
         Write-Host "[Error] Path cannot be empty." -ForegroundColor Red
         continue
    }
    if (-not (Test-Path $FolderX)) {
         Write-Host "Folder '$FolderX' does not exist." -ForegroundColor Yellow
         $Create = Read-Host "Would you like to create this folder now? (y/n)"
         if ($Create -and $Create.ToLower().StartsWith('y')) {
             try {
                 New-Item -ItemType Directory -Path $FolderX -Force | Out-Null
                 Write-Host "Successfully created folder: $FolderX" -ForegroundColor Green
             } catch {
                 Write-Host "[Error] Failed to create folder. Please ensure path is valid." -ForegroundColor Red
                 $FolderX = ""
             }
         } else {
             $FolderX = ""
         }
    }
}

# 3. Create .env file
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "3. Generating Environment Configuration (.env)" -ForegroundColor Green
$EnvPath = Join-Path $InstallDir ".env"
$EnvContent = @"
OPENROUTER_API_KEY=$ApiKey
CHROMA_BASE_DIR=$InstallDir
"@
[System.IO.File]::WriteAllText($EnvPath, $EnvContent)
Write-Host "Configuration saved to $EnvPath" -ForegroundColor Green

# 4. Check for Python & setup venv
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "4. Setting up Python Virtual Environment" -ForegroundColor Green
$PythonCmd = "python"
# Check if python is in path
try {
    $pyVersion = & $PythonCmd --version 2>&1
    Write-Host "Found Python: $pyVersion"
    # Parse version number (e.g. Python 3.13.1)
    if ($pyVersion -match 'Python (\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 13) {
            Write-Host ""
            Write-Host "[WARNING] COMPATIBILITY ALERT" -ForegroundColor Yellow
            Write-Host "You are running Python $major.$minor. Several key scientific libraries" -ForegroundColor Yellow
            Write-Host "(specifically 'numba' / 'matchms') do not support Python 3.13+ yet." -ForegroundColor Yellow
            Write-Host "If you continue, the installer will build the environment but some" -ForegroundColor Yellow
            Write-Host "downstream deconvolution & spectral matching steps will fail." -ForegroundColor Yellow
            Write-Host "It is highly recommended to install Python 3.10 - 3.12 (e.g. 3.12.9) instead." -ForegroundColor Yellow
            Write-Host ""
            $Choice = Read-Host "Do you want to exit the setup now to install Python 3.12? (y/n)"
            if (-not $Choice -or $Choice.ToLower().StartsWith('y')) {
                Write-Host "Exiting setup. Please install Python 3.12 and run this installer again." -ForegroundColor Cyan
                exit 1
            }
        }
    }
} catch {
    Write-Host "[Error] Python not found in system PATH. Please install Python 3.10 - 3.12." -ForegroundColor Red
    exit 1
}

$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment at $VenvDir..."
    & $PythonCmd -m venv $VenvDir
} else {
    Write-Host "Virtual environment already exists at $VenvDir."
}

# Install dependencies
Write-Host "Installing Python scientific packages (this might take a minute)..."
$PipCmd = Join-Path $VenvDir "Scripts\pip.exe"
& $PipCmd install --upgrade pip | Out-Null
& $PipCmd install -r (Join-Path $InstallDir "requirements.txt")
Write-Host "Python dependencies successfully installed." -ForegroundColor Green

# 5. Setup Directory Junction
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "5. Linking Watcher Folder raw_data -> $FolderX" -ForegroundColor Green
$RawDataPath = Join-Path $InstallDir "raw_data"

# Check if raw_data already exists
if (Test-Path $RawDataPath) {
    # Check if it's a junction or directory
    $item = Get-Item $RawDataPath
    if ($item.Attributes -match "ReparsePoint") {
        Write-Host "Removing existing folder link..."
        cmd.exe /c rmdir "$RawDataPath"
    } else {
        # Check if it has files
        $files = Get-ChildItem $RawDataPath -File
        if ($files.Count -gt 0) {
            Write-Host "[WARNING] $RawDataPath already exists and contains files." -ForegroundColor Yellow
            $BackupName = "raw_data_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss")
            $BackupPath = Join-Path $InstallDir $BackupName
            Write-Host "Moving existing files to $BackupPath..."
            Rename-Item -Path $RawDataPath -NewName $BackupName
        } else {
            # Empty folder, delete it
            Remove-Item $RawDataPath -Recurse -Force
        }
    }
}

# Create junction link
Write-Host "Creating link pointing to $FolderX..."
cmd.exe /c mklink /J "$RawDataPath" "$FolderX"
Write-Host "Folder junction successfully established." -ForegroundColor Green

# 6. Check for Node.js / n8n
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "6. Checking Workflow Manager (n8n)" -ForegroundColor Green
$NpmCheck = Get-Command npm -ErrorAction SilentlyContinue
if ($NpmCheck) {
    Write-Host "Found npm: $($NpmCheck.Source)"
    Write-Host "Checking if n8n is installed..."
    $n8nCheck = Get-Command n8n -ErrorAction SilentlyContinue
    if (-not $n8nCheck) {
        Write-Host "n8n is not installed globally. Attempting installation..."
        npm install -g n8n
    } else {
        Write-Host "n8n is already installed globally." -ForegroundColor Green
    }
} else {
    Write-Host "[WARNING] Node.js/npm not detected in PATH." -ForegroundColor Yellow
    Write-Host "Please install Node.js (https://nodejs.org) to run n8n for folder triggers." -ForegroundColor Yellow
}

# 7. Create Desktop Shortcuts
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "7. Setting up Desktop Shortcuts" -ForegroundColor Green
$DesktopDir = [Environment]::GetFolderPath("Desktop")
$DesktopPath = [System.IO.Path]::Combine($DesktopDir, "Start_All_Chroma_Services.cmd")
$StopDesktopPath = [System.IO.Path]::Combine($DesktopDir, "Stop_All_Chroma_Services.cmd")

Copy-Item -Path (Join-Path $InstallDir "start_all_services.cmd") -Destination $DesktopPath -Force
Copy-Item -Path (Join-Path $InstallDir "stop_all_services.cmd") -Destination $StopDesktopPath -Force

Write-Host "Shortcuts copied to Desktop:" -ForegroundColor Green
Write-Host "  - Start_All_Chroma_Services.cmd"
Write-Host "  - Stop_All_Chroma_Services.cmd"

# 8. Run Verification Test
Write-Host ""
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "8. System Verification" -ForegroundColor Green
$Verify = Read-Host "Would you like to run the GNN deconvolution verification test? (y/n)"
if ($Verify -and $Verify.ToLower().StartsWith('y')) {
    Write-Host "Running verification script (scripts/run_demo.py)..." -ForegroundColor Cyan
    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    & $PythonExe (Join-Path $InstallDir "scripts/run_demo.py")
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "       CHROMA-AGENT-ALPHA SETUP COMPLETED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "To start the autonomous loop:"
Write-Host "  1. Double-click the 'Start_All_Chroma_Services.cmd' on your Desktop."
Write-Host "  2. Go to http://localhost:5678 in your browser."
Write-Host "  3. Import the workflow: C:\chroma-agent-alpha\n8n\chroma_workflow.json"
Write-Host "  4. Ensure the workflow is ACTIVE."
Write-Host "  5. Now, any file dropped in folder X will be processed automatically!"
Write-Host "========================================================" -ForegroundColor Green
Write-Host "Setup finished. Press Enter to exit..."
$null = Read-Host
