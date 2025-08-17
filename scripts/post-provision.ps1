# Post-provision orchestration script
# This script runs after Azure resources are provisioned

Write-Host "Starting post-provision tasks..." -ForegroundColor Green

try {
    # Step 1: Generate application settings
    Write-Host "Generating application settings..." -ForegroundColor Yellow
    & "$PSScriptRoot\generate-settings.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to generate settings"
    }
    
    Write-Host "Settings generated successfully" -ForegroundColor Green
    
    # Step 2: Deploy package
    Write-Host "Deploying package..." -ForegroundColor Yellow
    & "$PSScriptRoot\deploy-package.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to deploy package"
    }
    
    Write-Host "Package deployed successfully" -ForegroundColor Green
    Write-Host "Post-provision tasks completed successfully!" -ForegroundColor Green
}
catch {
    Write-Error "Post-provision failed: $_"
    exit 1
}
