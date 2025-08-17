# Setup Cosmos DB container for security incidents

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$CosmosAccountName,
    
    [string]$DatabaseName = "securitydata"
)

Write-Host "Setting up Cosmos DB for security incidents..." -ForegroundColor Green

# Create database if it doesn't exist
az cosmosdb sql database create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroupName `
    --name $DatabaseName

Write-Host "Created database: $DatabaseName" -ForegroundColor Yellow

# Create incidents container
az cosmosdb sql container create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroupName `
    --database-name $DatabaseName `
    --name "incidents" `
    --partition-key-path "/id" `
    --throughput 400

Write-Host "Created container: incidents" -ForegroundColor Yellow

Write-Host "Cosmos DB setup complete!" -ForegroundColor Green
