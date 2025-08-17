# Setup Cosmos DB containers for medical data and security incidents

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$CosmosAccountName,
    
    [string]$DatabaseName = "medicaldata"
)

Write-Host "Setting up Cosmos DB containers..." -ForegroundColor Green

# Create database if it doesn't exist
az cosmosdb sql database create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroupName `
    --name $DatabaseName

Write-Host "Created database: $DatabaseName" -ForegroundColor Yellow

# Create medical_records container
az cosmosdb sql container create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroupName `
    --database-name $DatabaseName `
    --name "medical_records" `
    --partition-key-path "/MEDCode" `
    --throughput 400

Write-Host "Created container: medical_records" -ForegroundColor Yellow

# Create security_incidents container
az cosmosdb sql container create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroupName `
    --database-name $DatabaseName `
    --name "security_incidents" `
    --partition-key-path "/id" `
    --throughput 400

Write-Host "Created container: security_incidents" -ForegroundColor Yellow

Write-Host "Cosmos DB setup complete!" -ForegroundColor Green
