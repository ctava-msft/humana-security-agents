# Example usage of the Deploy-SentinelAutomationRule.ps1 script

# Set your Azure environment parameters
$params = @{
    JsonFilePath = ".\sentinel-automation-rule.json"
    SubscriptionId = "your-subscription-id-here"
    ResourceGroupName = "your-resource-group-name"
    WorkspaceName = "your-log-analytics-workspace-name"
}

# Deploy the automation rule
.\Deploy-SentinelAutomationRule.ps1 @params

# Optional: Deploy with a specific rule ID
# .\Deploy-SentinelAutomationRule.ps1 @params -RuleId "custom-rule-id-123"
