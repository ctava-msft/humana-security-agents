# =============================================================================
# SECURITY INCIDENT PROCESSOR WITH MCP PROTOCOL SUPPORT
# =============================================================================
#
# This application provides a security incident processing system built with:
#
# 1. Azure Functions - Serverless compute for incident processing
#    - HTTP triggers - Standard RESTful API endpoints accessible over HTTP
#    - MCP triggers - Model Context Protocol for AI agent integration (e.g., GitHub Copilot)
#    - Sentinel incident receiver - Process security incidents from Azure Sentinel
#
# 2. Azure Cosmos DB - NoSQL database for incident storage
#    - Stores security incidents and action plans from Sentinel
#    - Enables SQL-like queries through the Cosmos DB SQL API
#
# 3. Azure OpenAI - Provides AI models for incident analysis
#    - Analyzes security incidents and generates action plans
#    - Converts natural language queries to SQL for incident search
#    - Uses gpt-5 for intelligent analysis and recommendations
#
# 4. Azure API Management - Secure API gateway
#    - Rate limiting, authentication, and monitoring
#    - Centralizes API management and security policies
#
# The application provides both HTTP endpoints and MCP tools for security incident
# management, enabling AI assistants to query and analyze incidents using natural language.

import json
import logging
import os
import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

import azure.functions as func
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

# Initialize the Azure Functions app
app = func.FunctionApp()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Environment variables for Azure services
COSMOS_ENDPOINT_ENV = "COSMOS_ENDPOINT"
COSMOS_DATABASE_NAME_ENV = "COSMOSDB_DATABASE_NAME"
COSMOS_CONTAINER_NAME_ENV = "COSMOSDB_CONTAINER_NAME"
AZURE_OPENAI_ENDPOINT_ENV = "AZURE_OPENAI_ENDPOINT"
OPENAI_MODEL_NAME_ENV = "OPENAI_MODEL_NAME"
AZURE_OPENAI_API_VERSION_ENV = "AZURE_OPENAI_API_VERSION"

# Default values
DEFAULT_DATABASE_NAME = "securitydata"
DEFAULT_CONTAINER_NAME = "incidents"
DEFAULT_API_VERSION = "2024-02-15-preview"

# Incident severity levels
SEVERITY_LEVELS = {
    "Informational": 1,
    "Low": 2,
    "Medium": 3,
    "High": 4,
    "Critical": 5
}

# =============================================================================
# UTILITY CLASSES FOR MCP TOOL DEFINITIONS
# =============================================================================

class ToolProperty:
    """
    Defines a property for an MCP tool, including its name, data type, and description.
    
    These properties are used by AI assistants (like GitHub Copilot) to understand:
    - What inputs each tool expects
    - What data types those inputs should be
    - How to describe each input to users
    """
    def __init__(self, property_name: str, property_type: str, description: str):
        self.propertyName = property_name
        self.propertyType = property_type
        self.description = description
        
    def to_dict(self):
        """Converts the property definition to a dictionary format for JSON serialization."""
        return {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }

# =============================================================================
# SENTINEL INCIDENT PROCESSOR CLASS
# =============================================================================

class SentinelIncidentProcessor:
    """
    Processes security incidents from Azure Sentinel, generates action plans,
    and stores incident data in Cosmos DB.
    """
    
    def __init__(self):
        """Initialize the incident processor with Azure service connections."""
        self.cosmos_client = None
        self.database = None
        self.container = None
        self.openai_client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure all clients are properly initialized."""
        if not self._initialized:
            await self._setup_cosmos_client()
            await self._setup_openai_client()
            self._initialized = True
    
    async def _setup_cosmos_client(self):
        """Set up Cosmos DB client with managed identity authentication."""
        try:
            cosmos_endpoint = os.getenv(COSMOS_ENDPOINT_ENV)
            if not cosmos_endpoint:
                raise ValueError(f"Missing required environment variable: {COSMOS_ENDPOINT_ENV}")
            
            # Use managed identity for authentication
            credential = DefaultAzureCredential()
            self.cosmos_client = CosmosClient(cosmos_endpoint, credential=credential)
            
            database_name = os.getenv(COSMOS_DATABASE_NAME_ENV, DEFAULT_DATABASE_NAME)
            container_name = os.getenv(COSMOS_CONTAINER_NAME_ENV, DEFAULT_CONTAINER_NAME)
            
            self.database = self.cosmos_client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)
            
            logger.info("Successfully connected to Cosmos DB for incidents")
            
        except Exception as e:
            logger.error(f"Error setting up Cosmos DB client: {e}")
            raise
    
    async def _setup_openai_client(self):
        """Set up Azure OpenAI client for incident analysis."""
        try:
            endpoint = os.getenv(AZURE_OPENAI_ENDPOINT_ENV)
            if not endpoint:
                raise ValueError(f"Missing required environment variable: {AZURE_OPENAI_ENDPOINT_ENV}")
            
            api_version = os.getenv(AZURE_OPENAI_API_VERSION_ENV, DEFAULT_API_VERSION)
            credential = DefaultAzureCredential()
            
            async def get_azure_ad_token():
                token = await credential.get_token("https://cognitiveservices.azure.com/.default")
                return token.token
            
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                azure_ad_token_provider=get_azure_ad_token
            )
            
            logger.info("Successfully connected to Azure OpenAI for incident analysis")
            
        except Exception as e:
            logger.error(f"Error setting up Azure OpenAI client: {e}")
            raise
    
    async def analyze_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a security incident and generate an action plan using Azure OpenAI.
        
        Args:
            incident_data: The incident data from Sentinel
            
        Returns:
            Analysis results including action plan and risk assessment
        """
        await self._ensure_initialized()
        
        if not self.openai_client:
            raise RuntimeError("OpenAI client not properly initialized")
        
        # Extract incident details
        title = incident_data.get("title", "Unknown incident")
        description = incident_data.get("description", "")
        severity = incident_data.get("severity", "Unknown")
        entities = incident_data.get("relatedEntities", [])
        tactics = incident_data.get("tactics", [])
        
        system_message = """You are a security incident response expert. Analyze the provided security incident and create a detailed action plan.

        For each incident, provide:
        1. Risk Assessment (Critical/High/Medium/Low)
        2. Immediate Actions (steps to take within 1 hour)
        3. Short-term Actions (steps to take within 24 hours)
        4. Long-term Actions (preventive measures)
        5. Required Teams (which teams need to be involved)
        6. Estimated Resolution Time
        7. Business Impact Assessment
        
        Format your response as JSON with these exact fields:
        {
            "risk_level": "Critical|High|Medium|Low",
            "immediate_actions": ["action1", "action2"],
            "short_term_actions": ["action1", "action2"],
            "long_term_actions": ["action1", "action2"],
            "required_teams": ["team1", "team2"],
            "estimated_resolution_hours": number,
            "business_impact": "description",
            "analysis_summary": "brief summary"
        }"""
        
        user_message = f"""Analyze this security incident:
        
        Title: {title}
        Severity: {severity}
        Description: {description}
        Tactics: {', '.join(tactics) if tactics else 'None identified'}
        Entities Involved: {len(entities)} entities
        
        Entity Details:
        {json.dumps(entities[:5], indent=2) if entities else 'No entities'}"""
        
        try:
            model_name = os.getenv(OPENAI_MODEL_NAME_ENV, "gpt-5")
            
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            logger.info(f"Generated analysis for incident: {title}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing incident: {e}")
            # Return a default analysis on error
            return {
                "risk_level": severity,
                "immediate_actions": ["Investigate incident", "Assess impact"],
                "short_term_actions": ["Review logs", "Document findings"],
                "long_term_actions": ["Update security policies"],
                "required_teams": ["Security Operations"],
                "estimated_resolution_hours": 24,
                "business_impact": "Unable to determine",
                "analysis_summary": f"Error during analysis: {str(e)}"
            }
    
    async def store_incident(self, incident_data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store incident and analysis in Cosmos DB.
        
        Args:
            incident_data: The raw incident data from Sentinel
            analysis: The AI-generated analysis and action plan
            
        Returns:
            Storage result with document ID
        """
        await self._ensure_initialized()
        
        if not self.container:
            raise RuntimeError("Cosmos DB container not properly initialized")
        
        try:
            # Create incident document
            document = {
                "id": str(uuid.uuid4()),
                "document_type": "security_incident",
                "incident_id": incident_data.get("incidentId") or incident_data.get("id"),
                "title": incident_data.get("title") or incident_data.get("incidentName"),
                "severity": incident_data.get("severity"),
                "severity_level": SEVERITY_LEVELS.get(incident_data.get("severity", "Unknown"), 0),
                "status": incident_data.get("status", "New"),
                "created_time": incident_data.get("createdTimeUtc", datetime.utcnow().isoformat()),
                "last_modified_time": incident_data.get("lastModifiedTimeUtc", datetime.utcnow().isoformat()),
                "description": incident_data.get("description"),
                "tactics": incident_data.get("tactics", []),
                "techniques": incident_data.get("techniques", []),
                "entities": incident_data.get("relatedEntities", []),
                "alerts": incident_data.get("relatedAlerts", []),
                "analysis": analysis,
                "action_plan_status": "Pending",
                "processed_time": datetime.utcnow().isoformat(),
                "raw_data": incident_data
            }
            
            # Store in Cosmos DB
            result = await self.container.create_item(document)
            
            logger.info(f"Stored incident {document['incident_id']} with ID {document['id']}")
            
            return {
                "success": True,
                "document_id": document["id"],
                "incident_id": document["incident_id"]
            }
            
        except Exception as e:
            logger.error(f"Error storing incident: {e}")
            raise
    
    async def query_incidents(self, query: str) -> List[Dict[str, Any]]:
        """
        Query incidents using natural language converted to SQL.
        
        Args:
            query: Natural language query about incidents
            
        Returns:
            List of matching incidents
        """
        await self._ensure_initialized()
        
        # Generate SQL query for incidents
        sql_query = await self.generate_incident_sql(query)
        
        # Execute query
        try:
            items = []
            items_iterable = self.container.query_items(query=sql_query)
            
            async for item in items_iterable:
                items.append(item)
            
            logger.info(f"Incident query returned {len(items)} results")
            return items
            
        except Exception as e:
            logger.error(f"Error querying incidents: {e}")
            raise
    
    async def generate_incident_sql(self, natural_language_query: str) -> str:
        """
        Convert natural language query about incidents to SQL.
        
        Args:
            natural_language_query: The user's question about incidents
            
        Returns:
            Generated SQL query string for CosmosDB
        """
        await self._ensure_initialized()
        
        schema = """
        Container: incidents
        Document Structure:
        - id: Unique document ID
        - document_type: Always "security_incident"
        - incident_id: Sentinel incident ID
        - title: Incident title
        - severity: Severity level (Critical/High/Medium/Low/Informational)
        - severity_level: Numeric severity (1-5)
        - status: Incident status
        - created_time: When incident was created
        - analysis.risk_level: AI-assessed risk level
        - analysis.immediate_actions: List of immediate actions
        - action_plan_status: Status of action plan execution
        """
        
        system_message = f"""You are an expert SQL query generator for security incident data.
        
        {schema}
        
        Rules:
        1. Always include WHERE c.document_type = 'security_incident' in your queries
        2. Use proper CosmosDB SQL syntax
        
        Common query patterns:
        - "Show critical incidents" -> SELECT * FROM c WHERE c.document_type = 'security_incident' AND c.severity = 'Critical'
        - "Find incidents from today" -> SELECT * FROM c WHERE c.document_type = 'security_incident' AND c.created_time >= '{{today}}'
        - "Get high risk incidents" -> SELECT * FROM c WHERE c.document_type = 'security_incident' AND c.analysis.risk_level = 'High'
        - "Show pending action plans" -> SELECT * FROM c WHERE c.document_type = 'security_incident' AND c.action_plan_status = 'Pending'
        
        Convert this query to CosmosDB SQL: {natural_language_query}"""
        
        try:
            model_name = os.getenv(OPENAI_MODEL_NAME_ENV, "gpt-5")
            
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_message}],
                max_tokens=500,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            
            logger.info(f"Generated incident SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating incident SQL: {e}")
            raise
    
    async def get_sample_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sample incidents from the container.
        
        Args:
            limit: Maximum number of incidents to return
            
        Returns:
            List of sample incidents
        """
        await self._ensure_initialized()
        
        if not self.container:
            raise RuntimeError("Cosmos DB container not properly initialized")
        
        try:
            query = f"SELECT TOP {limit} * FROM c WHERE c.document_type = 'security_incident' ORDER BY c.severity_level DESC"
            items = []
            items_iterable = self.container.query_items(query=query)
            
            async for item in items_iterable:
                items.append(item)
            
            logger.info(f"Retrieved {len(items)} sample incidents")
            return items
            
        except Exception as e:
            logger.error(f"Error retrieving sample incidents: {e}")
            raise

# Initialize incident processor
incident_processor = SentinelIncidentProcessor()

# =============================================================================
# MCP TOOL PROPERTY DEFINITIONS
# =============================================================================

# Properties for the query_incidents tool
tool_properties_query_incidents = [
    ToolProperty("query", "string", "Natural language query about security incidents. For example: 'Show all critical incidents from the last 24 hours' or 'Find incidents with pending action plans'"),
]

# Convert tool properties to JSON for MCP tool registration
tool_properties_query_incidents_json = json.dumps([prop.to_dict() for prop in tool_properties_query_incidents])

# =============================================================================
# SENTINEL INCIDENT ENDPOINTS
# =============================================================================

@app.route(route="sentinel-receiver", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def sentinel_receiver(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger to receive security incidents from Azure Sentinel.
    Processes incidents, generates action plans, and stores in Cosmos DB.
    """
    try:
        logger.info("Processing Sentinel incident")
        
        # Parse incident data
        body = req.get_json()
        incident = body.get("properties") or body
        
        # Extract key fields
        title = incident.get("title") or incident.get("incidentName")
        severity = incident.get("severity", "Unknown")
        incident_id = incident.get("incidentId") or incident.get("id")
        
        logger.info(f"Received incident {incident_id} ({severity}): {title}")
        
        # Analyze incident and generate action plan
        analysis = await incident_processor.analyze_incident(incident)
        
        # Store incident with analysis
        storage_result = await incident_processor.store_incident(incident, analysis)
        
        # Prepare response
        response_data = {
            "success": True,
            "incident_id": incident_id,
            "document_id": storage_result["document_id"],
            "title": title,
            "severity": severity,
            "risk_level": analysis.get("risk_level"),
            "immediate_actions": analysis.get("immediate_actions", []),
            "estimated_resolution_hours": analysis.get("estimated_resolution_hours"),
            "message": f"Incident processed and action plan generated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Successfully processed incident {incident_id}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as ex:
        logger.exception("Failed to process Sentinel payload")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": str(ex),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=400,
            headers={"Content-Type": "application/json"}
        )

@app.route(route="incidents", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def http_query_incidents(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to query stored security incidents.
    """
    try:
        logger.info("Processing incident query request")
        
        # Get query parameter
        query = req.params.get('query', 'SELECT * FROM c WHERE c.document_type = "security_incident" ORDER BY c.severity_level DESC')
        
        # Query incidents
        incidents = await incident_processor.query_incidents(query)
        
        result = {
            "success": True,
            "query": query,
            "incidents": incidents,
            "count": len(incidents),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error querying incidents: {e}")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@app.route(route="incident-actions", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_update_incident_actions(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to update the status of incident action plans.
    """
    try:
        logger.info("Processing incident action update")
        
        req_body = req.get_json()
        document_id = req_body.get("document_id")
        action_status = req_body.get("action_status")  # Pending, In Progress, Completed
        notes = req_body.get("notes", "")
        
        if not document_id or not action_status:
            return func.HttpResponse(
                json.dumps({"error": "Missing required fields: document_id, action_status"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Update incident document
        await incident_processor._ensure_initialized()
        
        # Read existing document
        document = await incident_processor.container.read_item(
            item=document_id,
            partition_key=document_id
        )
        
        # Update fields
        document["action_plan_status"] = action_status
        document["action_plan_notes"] = notes
        document["action_plan_updated"] = datetime.utcnow().isoformat()
        
        # Save updated document
        await incident_processor.container.replace_item(
            item=document_id,
            body=document
        )
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "document_id": document_id,
                "action_status": action_status,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error updating incident actions: {e}")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# MCP tool for querying incidents
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="query_incidents",
    description="Query security incidents from Azure Sentinel stored in the database. You can search for incidents by severity, status, risk level, or time period. Returns incident details with AI-generated action plans.",
    toolProperties=tool_properties_query_incidents_json
)
async def mcp_query_incidents(req: str) -> str:
    """
    MCP tool trigger for querying security incidents.
    Allows AI assistants to search and analyze stored security incidents.
    """
    try:
        logger.info("Processing MCP incident query request")
        
        # Parse the MCP request
        req_data = json.loads(req)
        args = req_data.get("arguments", {})
        query = args.get("query", "").strip()
        
        if not query:
            return json.dumps({
                "error": "Query parameter is required",
                "success": False
            })
        
        # Query incidents
        incidents = await incident_processor.query_incidents(query)
        
        # Format results for MCP response
        summary = f"Query: {query}\n"
        summary += f"Results: {len(incidents)} incidents found\n\n"
        
        if incidents:
            summary += "Incident Summary:\n"
            for i, incident in enumerate(incidents[:5]):
                summary += f"\n{i+1}. {incident.get('title', 'Unknown')}\n"
                summary += f"   - Severity: {incident.get('severity', 'Unknown')}\n"
                summary += f"   - Risk Level: {incident.get('analysis', {}).get('risk_level', 'Not assessed')}\n"
                summary += f"   - Status: {incident.get('action_plan_status', 'Unknown')}\n"
                summary += f"   - Created: {incident.get('created_time', 'Unknown')}\n"
                
                actions = incident.get('analysis', {}).get('immediate_actions', [])
                if actions:
                    summary += f"   - Immediate Actions: {', '.join(actions[:2])}\n"
            
            if len(incidents) > 5:
                summary += f"\n... and {len(incidents) - 5} more incidents\n"
        else:
            summary += "No incidents matching your query.\n"
        
        return json.dumps({
            "success": True,
            "query": query,
            "summary": summary,
            "incidents": incidents,
            "count": len(incidents),
            "timestamp": datetime.utcnow().isoformat()
        }, default=str)
        
    except Exception as e:
        logger.error(f"Error in mcp_query_incidents: {e}", exc_info=True)
        return json.dumps({
            "error": f"Error querying incidents: {str(e)}",
            "success": False,
            "timestamp": datetime.utcnow().isoformat()
        })

@app.route(route="sample-incidents", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def http_get_sample_incidents(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to get sample incident data."""
    try:
        logger.info("Processing sample incidents request")
        
        # Get limit parameter
        limit = int(req.params.get('limit', '10'))
        limit = min(max(limit, 1), 100)  # Ensure between 1 and 100
        
        # Get sample incidents
        sample_incidents = await incident_processor.get_sample_incidents(limit)
        
        result = {
            "sample_incidents": sample_incidents,
            "count": len(sample_incidents),
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Sample incidents retrieved: {len(sample_incidents)} records")
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in http_get_sample_incidents: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": f"Internal server error: {str(e)}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# Health check endpoint
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def http_health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring and load balancing."""
    try:
        logger.info("Processing health check")
        
        # Test CosmosDB connection
        try:
            await incident_processor._ensure_initialized()
            if incident_processor.container:
                cosmos_status = "healthy"
            else:
                cosmos_status = "not initialized"
        except Exception as e:
            cosmos_status = f"unhealthy: {str(e)}"
        
        # Test OpenAI connection
        try:
            if incident_processor.openai_client:
                openai_status = "healthy"
            else:
                openai_status = "not initialized"
        except Exception as e:
            openai_status = f"unhealthy: {str(e)}"
        
        all_healthy = cosmos_status == "healthy" and openai_status == "healthy"
        
        health_status = {
            "status": "healthy" if all_healthy else "degraded",
            "cosmos_db": cosmos_status,
            "azure_openai": openai_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "security-incident-processor"
        }
        
        logger.info(f"Health check completed: {health_status['status']}")
        
        return func.HttpResponse(
            json.dumps(health_status),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# =============================================================================
# INITIALIZE SAMPLE INCIDENTS ON STARTUP
# =============================================================================

@app.function_name("initialize_sample_incidents")
@app.timer_trigger(schedule="0 0 0 1 1 *", arg_name="timer", run_on_startup=True)  # Run once on startup
async def initialize_sample_incidents(timer: func.TimerRequest) -> None:
    """Initialize sample incident data on function app startup."""
    try:
        logger.info("Initializing sample incident data")
        
        # Check if data already exists
        existing_incidents = await incident_processor.get_sample_incidents(1)
        if existing_incidents:
            logger.info("Sample incidents already exist, skipping initialization")
            return
        
        # Sample incident data
        sample_incident = {
            "incidentId": "INC-001",
            "title": "Suspicious PowerShell Activity Detected",
            "severity": "High",
            "status": "New",
            "description": "Multiple PowerShell commands with obfuscation detected on production server",
            "createdTimeUtc": datetime.utcnow().isoformat(),
            "tactics": ["Execution", "Defense Evasion"],
            "techniques": ["T1059.001", "T1027"],
            "relatedEntities": [
                {"type": "Host", "name": "PROD-WEB-01"},
                {"type": "Account", "name": "svc_web"}
            ]
        }
        
        # Analyze and store sample incident
        analysis = await incident_processor.analyze_incident(sample_incident)
        await incident_processor.store_incident(sample_incident, analysis)
        
        logger.info("Sample incident initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing sample incidents: {e}", exc_info=True)