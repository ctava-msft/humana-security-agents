@description('Name of the Logic App')
param name string

@description('Location for the Logic App')
param location string = resourceGroup().location

@description('Tags to apply to the Logic App')
param tags object = {}

@description('User assigned identity resource ID')
param userAssignedIdentityId string

@description('Storage account name for Logic App state')
param storageAccountName string

// Logic App with consumption plan
resource logicApp 'Microsoft.Logic/workflows@2019-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    state: 'Enabled'
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      contentVersion: '1.0.0.0'
      parameters: {
        '$connections': {
          defaultValue: {}
          type: 'Object'
        }
      }
      triggers: {
        manual: {
          type: 'Request'
          kind: 'Http'
          inputs: {
            schema: {
              type: 'object'
              properties: {
                action: {
                  type: 'string'
                }
                data: {
                  type: 'object'
                }
              }
            }
          }
        }
      }
      actions: {
        Initialize_variable: {
          type: 'InitializeVariable'
          inputs: {
            variables: [
              {
                name: 'ProcessingResult'
                type: 'string'
                value: 'Started processing security data'
              }
            ]
          }
        }
      }
      outputs: {}
    }
    parameters: {
      '$connections': {
        value: {}
      }
    }
  }
}

// Diagnostic settings for Logic App
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${name}'
  scope: logicApp
  properties: {
    storageAccountId: resourceId('Microsoft.Storage/storageAccounts', storageAccountName)
    logs: [
      {
        category: 'WorkflowRuntime'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

output name string = logicApp.name
output resourceId string = logicApp.id
output triggerUrl string = listCallbackURL('${logicApp.id}/triggers/manual', '2019-05-01').value
