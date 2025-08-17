@description('The name of the Cosmos DB account')
param cosmosDbAccountName string

@description('The role definition ID to assign')
param roleDefinitionId string

@description('The principal ID to assign the role to')
param principalId string

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosDbAccountName
}

resource roleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, roleDefinitionId, principalId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${roleDefinitionId}'
    principalId: principalId
    scope: cosmosAccount.id
  }
}
