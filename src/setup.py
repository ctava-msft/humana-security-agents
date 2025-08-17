"""
Azure Functions + AI Agent Tutorial
Demonstrates how to use Azure Functions with Azure AI Foundry SDKs.

This script:
1. Sets up an AI Agent with Azure Function Tool
2. Creates an agent that can invoke Azure Functions via storage queues
3. Tests the agent by sending prompts that trigger function calls
4. Retrieves processed results from the output queue

Note: This example is for demonstration purposes only and does not provide 
genuine medical or health advice.
"""

# Standard imports
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureFunctionTool, AzureFunctionStorageQueue, MessageRole

# Load env variables from .env in parent dir
notebook_path = Path().absolute()
parent_dir = notebook_path.parent
load_dotenv(parent_dir / '.env')

# Create AI Project Client
try:
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(exclude_managed_identity_credential=True, exclude_environment_credential=True),
        conn_str=os.environ["PROJECT_CONNECTION_STRING"],
    )
    print("✅ Successfully initialized AIProjectClient")
except Exception as e:
    print(f"❌ Error initializing AIProjectClient: {e}")

# Create Agent with Azure Function Tool
# Define a tool that references our function and the input + output queues
try:
    storage_endpoint = os.environ["STORAGE_SERVICE_ENDPONT"]  # Notice it's spelled STORAGE_SERVICE_ENDPONT in sample
except KeyError:
    print("❌ Please ensure STORAGE_SERVICE_ENDPONT is set in your environment.")
    storage_endpoint = None

agent = None
if storage_endpoint:
    # Create the AzureFunctionTool object
    azure_function_tool = AzureFunctionTool(
        name="foo",
        description="Get comedic or silly advice from 'Foo'.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question to ask Foo."},
                "outputqueueuri": {"type": "string", "description": "The output queue URI."}
            },
        },
        input_queue=AzureFunctionStorageQueue(
            queue_name="azure-function-foo-input",
            storage_service_endpoint=storage_endpoint,
        ),
        output_queue=AzureFunctionStorageQueue(
            queue_name="azure-function-tool-output",
            storage_service_endpoint=storage_endpoint,
        ),
    )

    # Construct the agent with the function tool attached
    with project_client:
        agent = project_client.agents.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="azure-function-agent-foo",
            instructions=(
                "You are a helpful health and fitness support agent.\n" 
                "If the user says 'What would foo say?' then call the foo function.\n" 
                "Always specify the outputqueueuri as '" + storage_endpoint + "/azure-function-tool-output'.\n"
                "Respond with 'Foo says: <response>' after the tool call."
            ),
            tools=azure_function_tool.definitions,
        )
    print(f"🎉 Created agent, agent ID: {agent.id}")
else:
    print("Skipping agent creation, no storage_endpoint.")

def run_foo_question(user_question: str, agent_id: str):
    """
    Test the agent by simulating a user message that triggers the function call.
    Creates a conversation thread, posts a user question, and runs the agent.
    
    The Agent Service will place a message on the azure-function-foo-input queue.
    The function will handle it and place a response in azure-function-tool-output.
    The agent will pick that up automatically and produce a final answer.
    """
    # 1) Create a new thread
    thread = project_client.agents.create_thread()
    print(f"📝 Created thread, thread ID: {thread.id}")

    # 2) Create a user message
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_question
    )
    print(f"💬 Created user message, ID: {message.id}")

    # 3) Create and process agent run
    run = project_client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent_id
    )
    print(f"🤖 Run finished with status: {run.status}")
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # 4) Retrieve messages
    messages = project_client.agents.list_messages(thread_id=thread.id)
    print("\n🗣️ Conversation:")
    for m in reversed(messages.data):  # oldest first
        msg_str = ""
        if m.content:
            msg_str = m.content[-1].text.value if len(m.content) > 0 else ""
        print(f"{m.role.upper()}: {msg_str}\n")

    return thread, run

# If the agent was created, let's test it!
if agent:
    my_thread, my_run = run_foo_question(
        user_question="What is the best post-workout snack? What would foo say?",
        agent_id=agent.id
    )

# Cleanup - remove the agent when done
# In real scenarios, you might keep your agent for repeated usage
if agent:
    try:
        project_client.agents.delete_agent(agent.id)
        print(f"🗑️ Deleted agent: {agent.name}")
    except Exception as e:
        print(f"❌ Error deleting agent: {e}")
