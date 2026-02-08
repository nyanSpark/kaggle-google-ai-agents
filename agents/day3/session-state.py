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


#################
# TOOL CREATION #
#################
# Define scope levels for state keys (following best practices)
USER_NAME_SCOPE_LEVELS = ("temp", "user", "app")

# This demonstrates how tools can write to session state using tool_context.
# The 'user:' prefix indicates this is user-specific data.
def save_userinfo(
    tool_context: ToolContext, user_name: str, country: str
) -> Dict[str, Any]:
    """
    Tool to record and save user name and country in session state.

    Args:
        user_name: The username to store in session state
        country: The name of the user's country
    """
    # Write to session state using the 'user:' prefix for user data
    tool_context.state["user:name"] = user_name
    tool_context.state["user:country"] = country

    return {"status": "success"}


# This demonstrates how tools can read from session state.
def retrieve_userinfo(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool to retrieve user name and country from session state.
    """
    # Read from session state
    user_name = tool_context.state.get("user:name", "Username not found")
    country = tool_context.state.get("user:country", "Country not found")

    return {"status": "success", "user_name": user_name, "country": country}


print("✅ Tools created.")

#########################################
# Implementing Tools and Sessions agent #
#########################################
APP_NAME = "default"  # Application
USER_ID = "default"  # User
SESSION = "default"  # Session

MODEL_NAME = "gemini-3-flash-preview"

# Create an agent with session state tools
root_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="text_chat_bot",
    description="""A text chatbot.
    Tools for managing user context:
    * To record username and country when provided use `save_userinfo` tool. 
    * To fetch username and country when required use `retrieve_userinfo` tool.
    """,
    tools=[save_userinfo, retrieve_userinfo],  # Provide the tools to the agent
)

# Set up session service and runner
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, session_service=session_service, app_name="default")

print("✅ Agent with session state tools initialized!")


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
    
    # Test conversation demonstrating session state
    await run_session(
        runner,
        [
            "Hi there, how are you doing today? What is my name?",  # Agent shouldn't know the name yet
            "My name is Sam. I'm from Poland.",  # Provide name - agent should save it
            "What is my name? Which country am I from?",  # Agent should recall from session state
        ],
        "state-demo-session",
    )




    # Retrieve the session and inspect its state
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="state-demo-session"
    )
    print("Session State Contents:")
    print(session.state)
    print("\n🔍 Notice the 'user:name' and 'user:country' keys storing our data!")





    # Start a completely new session - the agent won't know our name
    await run_session(
        runner,
        ["Hi there, how are you doing today? What is my name?"],
        "new-isolated-session",
    )





    # Check the state of the new session
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="new-isolated-session"
    )
    print("New Session State:")
    print(session.state)
    # Note: Depending on implementation, you might see shared state here.
    # This is where the distinction between session-specific and user-specific state becomes important.

    import os
    if os.path.exists("my_agent_data.db"):
        os.remove("my_agent_data.db")
        print("✅ Cleaned up old database files")

if __name__ == "__main__":
    asyncio.run(main())



"""
TERMINAL OUTPUT

✅ ADK components imported successfully.
✅ Gemini API key setup complete.
✅ Helper functions defined.
✅ Tools created.
✅ Agent with session state tools initialized!

 ### Session: state-demo-session

User > Hi there, how are you doing today? What is my name?
gemini-3-flash-preview >  Hello! I'm doing great, thank you for asking. To tell you your name, I'll need you to have told me it previously. Have you set your name with me before?

User > My name is Sam. I'm from Poland.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
gemini-3-flash-preview >  It's nice to meet you, Sam! I've saved your information. How can I help you further?

User > What is my name? Which country am I from?
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
gemini-3-flash-preview >  Your name is Sam and you are from Poland.
Session State Contents:
{'user:name': 'Sam', 'user:country': 'Poland'}

🔍 Notice the 'user:name' and 'user:country' keys storing our data!

 ### Session: new-isolated-session

User > Hi there, how are you doing today? What is my name?
gemini-3-flash-preview >  Hello! I'm doing well, thank you for asking. I can't recall your name just yet. Can you please tell me what it is?

New Session State:
{'user:name': 'Sam', 'user:country': 'Poland'}
"""