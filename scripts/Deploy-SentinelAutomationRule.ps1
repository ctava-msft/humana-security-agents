<#
.SYNOPSIS
    Deploys a Microsoft Sentinel automation rule from a JSON file.

.DESCRIPTION
    This script reads a JSON file containing an automation rule definition and creates it in the specified Sentinel workspace.

.PARAMETER JsonFilePath
    Path to the JSON file containing the automation rule definition.

.PARAMETER SubscriptionId
    Azure subscription ID where Sentinel is deployed.

.PARAMETER ResourceGroupName
    Resource group name containing the Sentinel workspace.

.PARAMETER WorkspaceName
    Name of the Log Analytics workspace where Sentinel is enabled.

.PARAMETER RuleId
    Optional. Unique identifier for the automation rule. If not provided, a GUID will be generated.

.EXAMPLE
    .\Deploy-SentinelAutomationRule.ps1 -JsonFilePath ".\sentinel-automation-rule.json" -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupName "rg-sentinel" -WorkspaceName "law-sentinel"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JsonFilePath,

    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [string]$WorkspaceName,

    [Parameter(Mandatory = $false)]
    [string]$RuleId = [Guid]::NewGuid().ToString()
)

# Import required modules
Write-Host "Checking Azure PowerShell modules..." -ForegroundColor Cyan
if (-not (Get-Module -ListAvailable -Name Az.Accounts)) {
    Write-Error "Azure PowerShell module not found. Please install it using: Install-Module -Name Az -AllowClobber -Scope CurrentUser"
    exit 1
}

# Connect to Azure
Write-Host "Connecting to Azure..." -ForegroundColor Cyan
try {
    $context = Get-AzContext
    if (-not $context) {
        Connect-AzAccount
    }
    Set-AzContext -SubscriptionId $SubscriptionId -ErrorAction Stop
}
catch {
    Write-Error "Failed to connect to Azure: $_"
    exit 1
}

# Read and parse JSON file
Write-Host "Reading automation rule from JSON file..." -ForegroundColor Cyan
try {
    if (-not (Test-Path $JsonFilePath)) {
        throw "JSON file not found at path: $JsonFilePath"
    }
    $ruleDefinition = Get-Content -Path $JsonFilePath -Raw | ConvertFrom-Json
}
catch {
    Write-Error "Failed to read or parse JSON file: $_"
    exit 1
}

# Get access token
Write-Host "Getting access token..." -ForegroundColor Cyan
try {
    $token = (Get-AzAccessToken -ResourceUrl "https://management.azure.com/").Token
}
catch {
    Write-Error "Failed to get access token: $_"
    exit 1
}

# Construct API endpoint
$apiVersion = "2023-02-01"
$baseUrl = "https://management.azure.com"
$resourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.OperationalInsights/workspaces/$WorkspaceName"
$automationRuleUrl = "$baseUrl$resourceId/providers/Microsoft.SecurityInsights/automationRules/$RuleId`?api-version=$apiVersion"

# Prepare the request body
$requestBody = @{
    properties = @{
        displayName = $ruleDefinition.displayName
        order = $ruleDefinition.order
        triggeringLogic = $ruleDefinition.triggeringLogic
        actions = $ruleDefinition.actions
    }
}

if ($ruleDefinition.description) {
    $requestBody.properties.description = $ruleDefinition.description
}

# Convert to JSON
$jsonBody = $requestBody | ConvertTo-Json -Depth 10

# Create the automation rule
Write-Host "Creating automation rule '$($ruleDefinition.displayName)'..." -ForegroundColor Cyan
try {
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }

    $response = Invoke-RestMethod -Uri $automationRuleUrl -Method Put -Headers $headers -Body $jsonBody -ErrorAction Stop

    Write-Host "Successfully created automation rule!" -ForegroundColor Green
    Write-Host "Rule ID: $RuleId" -ForegroundColor Yellow
    Write-Host "Display Name: $($response.properties.displayName)" -ForegroundColor Yellow
    Write-Host "Status: $($response.properties.enabled)" -ForegroundColor Yellow
}
catch {
    Write-Error "Failed to create automation rule: $_"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Error "Response: $responseBody"
    }
    exit 1
}

# Validate deployment
Write-Host "`nValidating deployment..." -ForegroundColor Cyan
try {
    Start-Sleep -Seconds 5
    $validation = Invoke-RestMethod -Uri $automationRuleUrl -Method Get -Headers $headers -ErrorAction Stop
    
    if ($validation.properties.displayName -eq $ruleDefinition.displayName) {
        Write-Host "Automation rule successfully deployed and validated!" -ForegroundColor Green
    }
    else {
        Write-Warning "Automation rule was created but validation showed unexpected differences."
    }
}
catch {
    Write-Warning "Could not validate the deployment: $_"
}

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Update the webhook URI in the rule with your actual Function App URL" -ForegroundColor Yellow
Write-Host "2. Update the x-functions-key with your Function App's function key" -ForegroundColor Yellow
Write-Host "3. Test the automation rule by creating a test incident in Sentinel" -ForegroundColor Yellow
