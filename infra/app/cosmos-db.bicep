@description('Azure region for all resources.')
param location string

@description('Tags for all resources.')
param tags object

@description('Cosmos DB account name')
param accountName string

@description('The name for the security database')
param databaseName string = 'securitydata'

@description('The name for the security container')
param containerName string = 'security_records'

@description('Array of identity IDs that should have data contributor access')
param dataContributorIdentityIds array = []

// Create Cosmos DB account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

// Create security database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Create security records container
resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
      }
    }
  }
}

// Assign Cosmos DB Data Contributor role to identities
var cosmosDBDataContributorRoleDefinitionId = '00000000-0000-0000-0000-000000000002'

resource roleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = [for principalId in dataContributorIdentityIds: {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, principalId, cosmosDBDataContributorRoleDefinitionId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDBDataContributorRoleDefinitionId}'
    principalId: principalId
    scope: cosmosAccount.id
  }
}]

// Outputs
output accountName string = cosmosAccount.name
output documentEndpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = databaseName
output containerName string = containerName
