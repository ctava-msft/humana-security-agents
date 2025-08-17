param name string
param location string = resourceGroup().location
param tags object = {}
param applicationInsightsName string = ''
param appSettings object = {}
param serviceName string = 'api'
param storageAccountName string
param deploymentStorageContainerName string
param virtualNetworkSubnetId string = ''
param instanceMemoryMB int = 2048
param maximumInstanceCount int = 100
param identityId string = ''
param identityClientId string = ''
param aiServicesId string
param resourceToken string

param runtimeName string = 'python'
param runtimeVersion string = '3.11'

@allowed(['SystemAssigned', 'UserAssigned'])
param identityType string = 'UserAssigned'

var abbrs = loadJsonContent('../abbreviations.json')

var applicationInsightsIdentity = 'ClientId=${identityClientId};Authorization=AAD'

// The application backend is a function app
module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'appserviceplan'
  params: {
    name: '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
  }
}

resource stg 'Microsoft.Storage/storageAccounts@2022-09-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

// Role definitions
var websiteContributorRoleId = 'de139f84-1756-47ae-9be6-808fbbe84772'
var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'

module api 'br/public:avm/res/web/site:0.15.1' = {
  name: '${serviceName}-functions-module'
  params: {
    name: name
    location: location
    kind: 'functionapp,linux'
    tags: union(tags, { 'azd-service-name': serviceName })
    managedIdentities: {
      systemAssigned: identityType == 'SystemAssigned'
      userAssignedResourceIds: [
        '${identityId}'
      ]
    }
    serverFarmResourceId: appServicePlan.outputs.resourceId
    functionAppConfig: {
      location: location
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${stg.properties.primaryEndpoints.blob}${deploymentStorageContainerName}'
          authentication: {
            type: identityType == 'SystemAssigned' ? 'SystemAssignedIdentity' : 'UserAssignedIdentity'
            userAssignedIdentityResourceId: identityType == 'UserAssigned' ? identityId : '' 
          }
        }
      }
      scaleAndConcurrency: {
        instanceMemoryMB: instanceMemoryMB
        maximumInstanceCount: maximumInstanceCount
      }
      runtime: {
        name: runtimeName
        version: runtimeVersion
      }
    }
    appSettingsKeyValuePairs: union(appSettings,
      {
        AzureWebJobsStorage__blobServiceUri: stg.properties.primaryEndpoints.blob
        AzureWebJobsStorage__queueServiceUri: stg.properties.primaryEndpoints.queue
        AzureWebJobsStorage__tableServiceUri: stg.properties.primaryEndpoints.table
        AzureWebJobsStorage__credential: 'managedidentity'
        AzureWebJobsStorage__clientId : identityClientId
        APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString
        APPLICATIONINSIGHTS_AUTHENTICATION_STRING: applicationInsightsIdentity
        AzureWebJobsFeatureFlags: 'EnableWorkerIndexing'
        AZURE_OPENAI_KEY: listKeys(aiServicesId, '2023-10-01-preview').key1
        PYTHON_ENABLE_WORKER_EXTENSIONS: '1'
        PYTHON_ISOLATE_WORKER_DEPENDENCIES: '1'
        AZURE_CLIENT_ID: identityClientId
        FUNCTIONS_EXTENSION_VERSION: '~4'
        AzureWebJobsDisableHomepage: 'true'
      })
    virtualNetworkSubnetId: !empty(virtualNetworkSubnetId) ? virtualNetworkSubnetId : null
    siteConfig: {
      alwaysOn: false
      cors: {
        allowedOrigins: ['*']
        supportCredentials: false
      }
      functionAppScaleLimit: maximumInstanceCount
      use32BitWorkerProcess: false
    }
    authSettingV2Configuration: {
      globalValidation: {
        requireAuthentication: false
        unauthenticatedClientAction: 'AllowAnonymous'
      }
      httpSettings: {
        requireHttps: true
        routes: {
          apiPrefix: '/.auth'
        }
      }
      platform: {
        enabled: true
        runtimeVersion: '~1'
      }
    }
  }
}

// Grant Website Contributor role to the managed identity on the Function App
resource websiteContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (identityType == 'UserAssigned') {
  name: guid(api.name, identityId, websiteContributorRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', websiteContributorRoleId)
    principalId: reference(identityId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage Blob Data Owner role to the managed identity on the storage account
resource storageBlobDataOwnerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (identityType == 'UserAssigned') {
  name: guid(stg.id, identityId, storageBlobDataOwnerRoleId)
  scope: stg
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    principalId: reference(identityId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

output SERVICE_API_NAME string = api.outputs.name
output SERVICE_API_IDENTITY_PRINCIPAL_ID string = identityType == 'SystemAssigned' ? api.outputs.?systemAssignedMIPrincipalId ?? '' : ''
output SERVICE_API_URI string = 'https://${api.outputs.defaultHostname}'
