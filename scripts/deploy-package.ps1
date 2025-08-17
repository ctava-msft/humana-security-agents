#!/usr/bin/env pwsh

# Azure Functions Deployment Package Script
# This script creates a deployment-ready zip file for the Azure Functions Python app

param(
    [string]$OutputPath = ".\deployment",
    [string]$ZipName = "humana-security-agents-function-app.zip",
    [switch]$Clean = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Creating Azure Functions deployment package..." -ForegroundColor Green

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "📁 Project root: $ProjectRoot" -ForegroundColor Cyan

# Create output directory
$DeploymentDir = Join-Path $ProjectRoot $OutputPath
if ($Clean -and (Test-Path $DeploymentDir)) {
    Write-Host "🧹 Cleaning existing deployment directory..." -ForegroundColor Yellow
    Remove-Item $DeploymentDir -Recurse -Force
}

if (!(Test-Path $DeploymentDir)) {
    New-Item -ItemType Directory -Path $DeploymentDir -Force | Out-Null
}

$TempBuildDir = Join-Path $DeploymentDir "build"
if (Test-Path $TempBuildDir) {
    Remove-Item $TempBuildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempBuildDir -Force | Out-Null

Write-Host "📁 Build directory: $TempBuildDir" -ForegroundColor Cyan

# Copy function app files
Write-Host "📄 Copying function app files..." -ForegroundColor Yellow

$SrcDir = Join-Path $ProjectRoot "src"
Write-Host "📁 Looking for src directory: $SrcDir" -ForegroundColor Cyan

if (Test-Path $SrcDir) {
    # Copy all files and directories from src
    Write-Host "📂 Copying all files from src directory..." -ForegroundColor Yellow
    
    # Get all items in src directory
    $SrcItems = Get-ChildItem -Path $SrcDir -Recurse
    
    foreach ($Item in $SrcItems) {
        $RelativePath = $Item.FullName.Substring($SrcDir.Length + 1)
        $DestPath = Join-Path $TempBuildDir $RelativePath
        
        if ($Item.PSIsContainer) {
            # Create directory if it doesn't exist
            if (!(Test-Path $DestPath)) {
                New-Item -ItemType Directory -Path $DestPath -Force | Out-Null
                Write-Host "  📁 Created directory: $RelativePath" -ForegroundColor Cyan
            }
        } else {
            # Copy file, excluding certain file types
            $Extension = $Item.Extension.ToLower()
            $ExcludedExtensions = @('.pyc', '.pyo', '.pyd', '.log', '.tmp')
            $ExcludedDirs = @('__pycache__', '.pytest_cache', '.coverage', 'htmlcov')
            
            # Check if file is in an excluded directory
            $IsInExcludedDir = $false
            foreach ($ExcludedDir in $ExcludedDirs) {
                if ($RelativePath -like "*$ExcludedDir*") {
                    $IsInExcludedDir = $true
                    break
                }
            }
            
            if (-not $ExcludedExtensions.Contains($Extension) -and -not $IsInExcludedDir) {
                # Ensure destination directory exists
                $DestDir = Split-Path -Parent $DestPath
                if ($DestDir -and !(Test-Path $DestDir)) {
                    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
                }
                
                Copy-Item $Item.FullName $DestPath -Force
                Write-Host "  ✓ $RelativePath" -ForegroundColor Green
            } else {
                Write-Host "  ⏭️ Skipped: $RelativePath" -ForegroundColor Gray
            }
        }
    }
} else {
    Write-Error "Source directory not found: $SrcDir"
    exit 1
}

# Create the zip file
Write-Host "🗜️ Creating deployment zip file..." -ForegroundColor Yellow
$ZipPath = Join-Path $DeploymentDir $ZipName

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

# Use compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($TempBuildDir, $ZipPath)

Write-Host "  ✓ Created: $ZipPath" -ForegroundColor Green

# Get file size
$ZipSize = [Math]::Round((Get-Item $ZipPath).Length / 1KB, 2)
Write-Host "  📊 Size: $ZipSize KB" -ForegroundColor Cyan

# Clean up temp directory
Write-Host "🧹 Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item $TempBuildDir -Recurse -Force

# List contents of zip file for verification
Write-Host "`n📋 Package Contents:" -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
foreach ($Entry in $Zip.Entries) {
    Write-Host "  📄 $($Entry.FullName)" -ForegroundColor White
}
$Zip.Dispose()

Write-Host "`n✅ Deployment package created successfully!" -ForegroundColor Green
Write-Host "📦 Package: $ZipPath" -ForegroundColor Cyan
Write-Host "🚀 Ready for Azure Functions deployment!" -ForegroundColor Green

# Display next steps
Write-Host "`n📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure application settings in Azure Portal" -ForegroundColor White
Write-Host "2. Deploy using Azure CLI:" -ForegroundColor White
Write-Host "   az functionapp deployment source config-zip --src $ZipName" -ForegroundColor Gray
Write-Host "3. Or deploy using Functions Core Tools:" -ForegroundColor White
Write-Host "   func azure functionapp publish <app-name> --python" -ForegroundColor Gray