import os
import uuid
import asyncio
import sqlite3

from typing import Any, Dict

# Google ADK modules
from google.genai import types
from google.adk.agents import LlmAgent, Agent
from google.adk.apps.app import App, ResumabilityConfig, EventsCompactionConfig
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.tool_context import ToolContext

# MCP (Model Context Protocol) — used for stdio server params
from mcp import StdioServerParameters

print("✅ ADK components imported successfully.")

# Local .env load
def load_api_key():
    """Load API key from .env file using only built-in functions"""
    try:
        with open('../.env', 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    # Split on first '=' only
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        if key == "GOOGLE_API_KEY":
                            return value
        return None
    except FileNotFoundError:
        return None

# Set Google API key
try:
    api_key = load_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    print("✅ Gemini API key setup complete.")
except Exception as e:
    print(f"🔑 Authentication Error: Confirm 'GOOGLE_API_KEY'. Details: {e}")

retry_config = types.HttpRetryOptions(
    attempts=10,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=30,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# Define helper functions that will be reused throughout the notebook
async def run_session(runner_instance: Runner, 
                    user_queries: list[str] | str = None,
                    session_name: str = "default"):
    print(f"\n ### Session: {session_name}")

    # Get app name from the Runner
    app_name = runner_instance.app_name

    # Attempt to create a new session or retrieve an existing one
    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    except:
        session = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )

    # Process queries if provided
    if user_queries:
        # Convert single query to list for uniform processing
        if type(user_queries) == str:
            user_queries = [user_queries]

        # Process each query in the list sequentially
        for query in user_queries:
            print(f"\nUser > {query}")

            # Convert the query string to the ADK Content format
            query = types.Content(role="user", parts=[types.Part(text=query)])

            # Stream the agent's response asynchronously
            async for event in runner_instance.run_async(
                user_id=USER_ID, session_id=session.id, new_message=query
            ):
                # Check if the event contains valid content
                if event.content and event.content.parts:
                    # Filter out empty or "None" responses before printing
                    if (
                        event.content.parts[0].text != "None"
                        and event.content.parts[0].text
                    ):
                        print(f"{MODEL_NAME} > ", event.content.parts[0].text)
    else:
        print("No queries!")

print("✅ Helper functions defined.")

#########################################
# Implementing persistent session agent #
#########################################
APP_NAME = "default"  # Application
USER_ID = "default"  # User
SESSION = "default"  # Session

MODEL_NAME = "gemini-3-flash-preview"

# Step 1: Create the same agent (notice we use LlmAgent this time)
chatbot_agent = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="text_chat_bot",
    description="A text chatbot with persistent memory",
)

# Re-define our app with Events Compaction enabled
research_app_compacting = App(
    name="research_app_compacting",
    root_agent=chatbot_agent,
    # This is the new part!
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Trigger compaction every 3 invocations
        overlap_size=1,  # Keep 1 previous turn for context
    ),
)

db_url = "sqlite:///my_agent_data_compact.db"  # Local SQLite file
session_service = DatabaseSessionService(db_url=db_url)
print("✅ Upgraded to persistent sessions!")
print(f"   - Database: my_agent_data.db")
print(f"   - Sessions will survive restarts!")

# Create a new runner for our upgraded app
research_runner_compacting = Runner(
    app=research_app_compacting, session_service=session_service
)
print("✅ Research App upgraded with Events Compaction!")


def check_data_in_db():
    with sqlite3.connect("my_agent_data.db") as connection:
        cursor = connection.cursor()
        result = cursor.execute(
            "select app_name, session_id, author, content from events"
        )
        print([_[0] for _ in result.description])
        for each in result.fetchall():
            print(each)


async def main():
    
    # Turn 1
    await run_session(
        research_runner_compacting,
        "What is the latest news about AI in healthcare?",
        "compaction_demo",
    )

    # Turn 2
    await run_session(
        research_runner_compacting,
        "Are there any new developments in drug discovery?",
        "compaction_demo",
    )

    # Turn 3 - Compaction should trigger after this turn!
    await run_session(
        research_runner_compacting,
        "Tell me more about the second development you found.",
        "compaction_demo",
    )

    # Turn 4
    await run_session(
        research_runner_compacting,
        "Who are the main companies involved in that?",
        "compaction_demo",
    )

    # PEEK Database
    # check_data_in_db()

    # Get the final session state
    final_session = await session_service.get_session(
        app_name=research_runner_compacting.app_name,
        user_id=USER_ID,
        session_id="compaction_demo",
    )

    print("--- Searching for Compaction Summary Event ---")
    found_summary = False
    for event in final_session.events:
        # Compaction events have a 'compaction' attribute
        if event.actions and event.actions.compaction:
            print("\n✅ SUCCESS! Found the Compaction Event:")
            print(f"  Author: {event.author}")
            print(f"\n Compacted information: {event}")
            found_summary = True
            break

    if not found_summary:
        print(
            "\n❌ No compaction event found. Try increasing the number of turns in the demo."
        )

if __name__ == "__main__":
    asyncio.run(main())