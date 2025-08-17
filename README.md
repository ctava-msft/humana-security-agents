<!--
---
name: Security Agent Service with MCP Tools
description: A serverless security monitoring and incident response service using Azure Functions, Azure OpenAI, Cosmos DB, and API Management.
page_type: sample
languages:
- python
- bicep
- azdeveloper
products:
- azure-functions
- azure-openai
- azure-cosmos-db
- azure-api-management
- azure-ai-services
urlFragment: security-agent
---
-->

<p align="center">
  <b>Security Agent · Intelligent Security Monitoring Service with MCP Tools</b>
</p>

Security Agent is an **Azure Functions**–based reference application that provides intelligent security monitoring, threat detection, and incident response capabilities. The service exposes functionality through **MCP (Model Context Protocol) tools** consumable by GitHub Copilot Chat and other MCP‑aware clients, and provides a secure API gateway through **Azure API Management**.

* **Natural Language Security Queries** – converts plain English queries to security insights using **Azure OpenAI gpt-4o**
* **Security Event Storage** – persists security events and incidents in **Cosmos DB**
* **Secure API Gateway** – exposes endpoints through **Azure API Management** with rate limiting and authentication
* **MCP Protocol Support** – integrates with GitHub Copilot and other AI assistants as interactive tools
* **Enterprise Security** – designed with security best practices for incident response and threat monitoring
* **Sample Data Included** – automatically loads sample security events on startup

The project ships with reproducible **azd** infrastructure, so `azd up` will stand up the entire stack – Functions, Cosmos DB, Azure OpenAI, and API Management – in a single command.

## Features

* **Threat Detection** – analyze security events using gpt-4o for anomaly detection
* **Security Event Query** – query security incidents with natural language interface
* **Incident Response** – automated incident classification and response recommendations
* **Secure API Gateway** – Azure API Management with rate limiting and authentication
* **MCP Protocol Support** – integrate with GitHub Copilot and other AI assistants
* **Auto Sample Data** – automatically loads sample security events on first deployment
* **Comprehensive Logging** – Application Insights integration with security audit trails

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analyze-threat` | POST | Analyze security events and detect threats using AI |
| `/api/security-events` | GET | Retrieve security events and incidents |
| `/api/incident-response` | POST | Generate incident response recommendations |
| `/api/security-logs` | POST | Upload new security events |  
| `/api/health` | GET | Health check endpoint |

### MCP Tools

| Tool Name | Purpose |
|-----------|---------|
| `analyze_security_threat` | Analyze security events and detect potential threats using AI |
| `query_security_events` | Query historical security events and incidents |
| `generate_incident_response` | Generate incident response recommendations based on threat analysis |

## Getting Started

### Prerequisites

* Azure subscription with appropriate permissions
* Azure CLI (`az`) installed
* Azure Developer CLI (`azd`) installed
* Python 3.11+ for local development

### Quick Deployment

```bash
# Clone the repository
git clone <repository-url>
cd humana-security-agents

# Login to Azure
azd auth login

# Deploy everything
azd up
```

The deployment will:
1. Create all Azure resources (Functions, Cosmos DB, OpenAI, API Management)
2. Deploy the function app code
3. Configure API Management with proper endpoints
4. Load sample security events automatically

### Local Development

```bash
# Install dependencies
pip install -r src/requirements.txt

# Generate local settings from deployed resources
./scripts/generate-settings.sh

# Run locally
cd src
func start
```

## Usage Examples

### Via HTTP API

```bash
# Analyze potential security threat
curl -X POST "https://your-function-app.azurewebsites.net/api/analyze-threat" \
  -H "Content-Type: application/json" \
  -d '{"event": "Multiple failed login attempts from IP 192.168.1.100"}'

# Get security events
curl "https://your-function-app.azurewebsites.net/api/security-events?severity=high&limit=10"

# Generate incident response
curl -X POST "https://your-function-app.azurewebsites.net/api/incident-response" \
  -H "Content-Type: application/json" \
  -d '{"incident_type": "data_breach", "severity": "critical"}'

# Health check
curl "https://your-function-app.azurewebsites.net/api/health"
```

### Local Development Setup

```shell
# Create virtual environment
python -m venv .venv 
.\.venv\Scripts\activate

# Install dependencies
pip install -r src/requirements.txt
```

### Via API Management

```bash
# Query through APIM gateway
curl -X POST "https://your-apim.azure-api.net/security/analyze-threat" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: YOUR-KEY" \
  -d '{"event": "Suspicious network activity detected on port 22"}'
```

### Sample Natural Language Queries

- "Show me all critical security events from the last 24 hours"
- "Find all failed authentication attempts today"  
- "Analyze potential data exfiltration events"
- "Show me all incidents involving privileged accounts"
- "Find security events from suspicious IP addresses"

## Architecture

The solution uses a serverless architecture with these Azure services:

- **Azure Functions** - Serverless compute hosting the API endpoints
- **Azure Cosmos DB** - NoSQL database storing security events and incidents
- **Azure OpenAI** - gpt-4o model for threat analysis and natural language processing
- **Azure API Management** - Secure API gateway with rate limiting
- **Application Insights** - Monitoring, logging, and security audit trails

## Sample Data Structure

The system works with security event data:

```json
{
  "id": "unique-identifier",
  "event_type": "authentication_failure",
  "severity": "high",
  "source_ip": "192.168.1.100",
  "target_resource": "database-server-01",
  "description": "Multiple failed login attempts detected",
  "timestamp": "2024-01-01T00:00:00Z",
  "user_account": "admin@company.com",
  "status": "investigating"
}
```

Sample data is automatically loaded including:
- Authentication failures
- Network intrusion attempts
- Data access violations
- Privilege escalation events
- Suspicious API calls

## Security & Compliance

- **Managed Identity** authentication between all Azure services
- **HTTPS only** communication
- **API Management** gateway with subscription keys and rate limiting
- **Application Insights** for comprehensive security audit trails
- **Network isolation** ready (Private Endpoints can be enabled)

### Required Azure Role Assignments

The managed identity requires these permissions:
* **Cosmos DB Data Contributor** - for reading/writing security events
* **Storage Blob Data Owner and Queue Data Contributor** - for Azure Functions storage
* **Application Insights Monitoring Metrics Publisher** - for telemetry
* **Azure AI Project Developer** - for AI services access

For production deployments, we recommend:
* Restrict inbound traffic with Private Endpoints + VNet integration
* Enable network security features like service endpoints and firewall rules
* Implement Zero Trust security principles
* Enable Azure Defender for enhanced threat protection

## Monitoring & Diagnostics

The solution includes comprehensive monitoring:

- **Application Insights** integration for all functions
- **Security audit logging** throughout the application
- **Health check endpoint** for service monitoring
- **Custom metrics** for threat detection performance
- **Distributed tracing** for security event correlation
- **Real-time alerts** for critical security incidents

## Resources

* Blog – *Build AI agent tools using Remote MCP with Azure Functions* ([Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/build-ai-agent-tools-using-remote-mcp-with-azure-functions/4401059))
* Model Context Protocol spec – [https://aka.ms/mcp](https://aka.ms/mcp)
* Azure Functions Remote MCP docs – [https://aka.ms/azure-functions-mcp](https://aka.ms/azure-functions-mcp)
* Develop Python apps for Azure AI – [https://learn.microsoft.com/azure/developer/python/azure-ai-for-python-developers](https://learn.microsoft.com/azure/developer/python/azure-ai-for-python-developers)
* Azure Security Best Practices – [https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns)

## Contributing

Standard **fork → branch → PR** workflow. Use *Conventional Commits* (`feat:`, `fix:`) in commit messages.

## License

MIT © Microsoft Corporation
---

## Contributing

Standard **fork → branch → PR** workflow. Use *Conventional Commits* (`feat:`, `fix:`) in commit messages.

---

## License

MIT © Microsoft Corporation
