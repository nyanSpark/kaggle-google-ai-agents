# https://www.kaggle.com/code/kaggle5daysofai/day-3b-agent-memory

import os
import uuid
import asyncio
import sqlite3

from typing import Any, Dict

# Memory related ADK modules
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory, preload_memory
from google.genai import types

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
    initial_delay=15,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

################################
# This helper function manages a complete conversation session, handling session creation/retrieval, query processing, and response streaming.
################################
async def run_session(
    runner_instance: Runner, user_queries: list[str] | str, session_id: str = "default"
):
    """Helper function to run queries in a session and display responses."""
    print(f"\n### Session: {session_id}")

    # Create or retrieve session
    try:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
    except:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )

    # Convert single query to list
    if isinstance(user_queries, str):
        user_queries = [user_queries]

    # Process each query
    for query in user_queries:
        print(f"\nUser > {query}")
        query_content = types.Content(role="user", parts=[types.Part(text=query)])

        # Stream agent response
        async for event in runner_instance.run_async(
            user_id=USER_ID, session_id=session.id, new_message=query_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text and text != "None":
                    print(f"Model: > {text}")

print("✅ Helper functions defined.")


memory_service = (
    InMemoryMemoryService()
)  # ADK's built-in Memory Service for development and testing


async def auto_save_to_memory(callback_context):
    """Automatically save session to memory after each agent turn."""
    await callback_context._invocation_context.memory_service.add_session_to_memory(
        callback_context._invocation_context.session
    )
print("✅ Callback created.")


#########################################
# Implementing Tools and Sessions agent #
#########################################
# Define constants used throughout the notebook
APP_NAME = "MemoryDemoApp"
USER_ID = "demo_user"

# Create agent
# Agent with automatic memory saving
auto_memory_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="AutoMemoryAgent",
    instruction="Answer user questions.",
    tools=[preload_memory],
    after_agent_callback=auto_save_to_memory,  # Saves after each turn!
)
print("✅ Agent created with automatic memory saving!")



# Create Session Service
session_service = InMemorySessionService()  # Handles conversations



# Create a runner for the auto-save agent
# This connects our automated agent to the session and memory services
auto_runner = Runner(
    agent=auto_memory_agent,  # Use the agent with callback + preload_memory
    app_name=APP_NAME,
    session_service=session_service,  # Same services from Section 3
    memory_service=memory_service,
)
print("✅ Runner created.")


async def main():

    # Test 1: Tell the agent about a gift (first conversation)
    # The callback will automatically save this to memory when the turn completes
    await run_session(
        auto_runner,
        "I gifted a new toy to my nephew on his 1st birthday!",
        "auto-save-test",
    )

    # Test 2: Ask about the gift in a NEW session (second conversation)
    # The agent should retrieve the memory using preload_memory and answer correctly
    await run_session(
        auto_runner,
        "What did I gift my nephew?",
        "auto-save-test-2",  # Different session ID - proves memory works across sessions!
    )
    

if __name__ == "__main__":
    asyncio.run(main())



"""
TERMINAL OUTPUT


"""