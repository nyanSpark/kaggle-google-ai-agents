# https://www.kaggle.com/code/kaggle5daysofai/day-4a-agent-observability#Foundational-pillars-of-Agent-Observability

import os
import uuid
import asyncio
import sqlite3
import logging

from typing import Any, Dict

# Memory related ADK modules
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory, preload_memory
from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search

from google.genai import types
from typing import List

print("✅ ADK components imported successfully.")


from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import google_search

from google.genai import types
from typing import List


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


def count_papers(papers: List[str]):
    """
    This function counts the number of papers in a list of strings.
    Args:
      papers: A list of strings, where each string is a research paper.
    Returns:
      The number of papers in the list.
    """
    return len(papers)





# Google search agent
google_search_agent = LlmAgent(
    name="google_search_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    description="Searches for information using Google search",
    instruction="Use the google_search tool to find information on the given topic. Return the raw search results.",
    tools=[google_search],
)


# Root agent
research_agent_with_plugin = LlmAgent(
    name="research_paper_finder_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""Your task is to find research papers and count them. 
   
   You must follow these steps:
   1) Find research papers on the user provided topic using the 'google_search_agent'. 
   2) Then, pass the papers to 'count_papers' tool to count the number of papers returned.
   3) Return both the list of research papers and the total number of papers.
   """,
    tools=[AgentTool(agent=google_search_agent), count_papers],
)
print("✅ Agent created")



from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import (
    LoggingPlugin,
)  # <---- 1. Import the Plugin
from google.genai import types
import asyncio

runner = InMemoryRunner(
    agent=research_agent_with_plugin,
    plugins=[
        LoggingPlugin()
    ],  # <---- 2. Add the plugin. Handles standard Observability logging across ALL agents
)
print("✅ Runner configured")


print("🚀 Running agent with LoggingPlugin...")
print("📊 Watch the comprehensive logging output below:\n")
async def main():
    response = await runner.run_debug("Find recent papers on quantum computing")

if __name__ == "__main__":
    asyncio.run(main())


"""
TERMINAL OUTPUT

✅ ADK components imported successfully.
✅ Gemini API key setup complete.
✅ Agent created
✅ Runner configured
🚀 Running agent with LoggingPlugin...
📊 Watch the comprehensive logging output below:


 ### Created new session: debug_session_id

User > Find recent papers on quantum computing
[logging_plugin] 🚀 USER MESSAGE RECEIVED
[logging_plugin]    Invocation ID: e-b7180c2e-cfb2-4f6b-b6fc-a7fa54c036e3
[logging_plugin]    Session ID: debug_session_id
[logging_plugin]    User ID: debug_user_id
[logging_plugin]    App Name: InMemoryRunner
[logging_plugin]    Root Agent: research_paper_finder_agent
[logging_plugin]    User Content: text: 'Find recent papers on quantum computing'
[logging_plugin] 🏃 INVOCATION STARTING
[logging_plugin]    Invocation ID: e-b7180c2e-cfb2-4f6b-b6fc-a7fa54c036e3
[logging_plugin]    Starting Agent: research_paper_finder_agent
[logging_plugin] 🤖 AGENT STARTING
[logging_plugin]    Agent Name: research_paper_finder_agent
[logging_plugin]    Invocation ID: e-b7180c2e-cfb2-4f6b-b6fc-a7fa54c036e3
[logging_plugin] 🧠 LLM REQUEST
[logging_plugin]    Model: gemini-2.5-flash-lite
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    System Instruction: 'Your task is to find research papers and count them. 
   
   You must follow these steps:
   1) Find research papers on the user provided topic using the 'google_search_agent'. 
   2) Then, pass the p...'
[logging_plugin]    Available Tools: ['google_search_agent', 'count_papers']
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
[logging_plugin] 🧠 LLM RESPONSE
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Content: function_call: google_search_agent
[logging_plugin]    Token Usage - Input: 240, Output: 21
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: 72c25a02-ce92-47b0-b8aa-a014ae0ed7bb
[logging_plugin]    Author: research_paper_finder_agent
[logging_plugin]    Content: function_call: google_search_agent
[logging_plugin]    Final Response: False
[logging_plugin]    Function Calls: ['google_search_agent']
[logging_plugin] 🔧 TOOL STARTING
[logging_plugin]    Tool Name: google_search_agent
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Function Call ID: adk-2b70a1a9-d3bf-4c0b-91a6-868a4bcf873d
[logging_plugin]    Arguments: {'request': 'recent papers on quantum computing'}
[logging_plugin] 🚀 USER MESSAGE RECEIVED
[logging_plugin]    Invocation ID: e-efb59eec-04b4-4036-bad6-62412b2a94a6
[logging_plugin]    Session ID: 13b7abc8-e9de-439d-ad58-13e0ffe74afe
[logging_plugin]    User ID: debug_user_id
[logging_plugin]    App Name: InMemoryRunner
[logging_plugin]    Root Agent: google_search_agent
[logging_plugin]    User Content: text: 'recent papers on quantum computing'
[logging_plugin] 🏃 INVOCATION STARTING
[logging_plugin]    Invocation ID: e-efb59eec-04b4-4036-bad6-62412b2a94a6
[logging_plugin]    Starting Agent: google_search_agent
[logging_plugin] 🤖 AGENT STARTING
[logging_plugin]    Agent Name: google_search_agent
[logging_plugin]    Invocation ID: e-efb59eec-04b4-4036-bad6-62412b2a94a6
[logging_plugin] 🧠 LLM REQUEST
[logging_plugin]    Model: gemini-2.5-flash-lite
[logging_plugin]    Agent: google_search_agent
[logging_plugin]    System Instruction: 'Use the google_search tool to find information on the given topic. Return the raw search results.

You are an agent. Your internal name is "google_search_agent". The description about you is "Searches...'
[logging_plugin] 🧠 LLM RESPONSE
[logging_plugin]    Agent: google_search_agent
[logging_plugin]    Content: text: 'The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 2025. Researchers and tech companies are making pro...'
[logging_plugin]    Token Usage - Input: 58, Output: 634
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: 33f69752-9f3b-4e75-946f-2ad8806ed05e
[logging_plugin]    Author: google_search_agent
[logging_plugin]    Content: text: 'The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 2025. Researchers and tech companies are making pro...'
[logging_plugin]    Final Response: True
[logging_plugin] 🤖 AGENT COMPLETED
[logging_plugin]    Agent Name: google_search_agent
[logging_plugin]    Invocation ID: e-efb59eec-04b4-4036-bad6-62412b2a94a6
[logging_plugin] ✅ INVOCATION COMPLETED
[logging_plugin]    Invocation ID: e-efb59eec-04b4-4036-bad6-62412b2a94a6
[logging_plugin]    Final Agent: google_search_agent
[logging_plugin] 🔧 TOOL COMPLETED
[logging_plugin]    Tool Name: google_search_agent
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Function Call ID: adk-2b70a1a9-d3bf-4c0b-91a6-868a4bcf873d
[logging_plugin]    Result: The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 2025. Researchers and tech companies are making progress in stability, scalability, and usability, bringing quantum systems closer to commercial viabil...}
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: a11bd96b-58a5-4bd2-ad91-43dc02dcb91d
[logging_plugin]    Author: research_paper_finder_agent
[logging_plugin]    Content: function_response: google_search_agent
[logging_plugin]    Final Response: False
[logging_plugin]    Function Responses: ['google_search_agent']
[logging_plugin] 🧠 LLM REQUEST
[logging_plugin]    Model: gemini-2.5-flash-lite
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    System Instruction: 'Your task is to find research papers and count them. 
   
   You must follow these steps:
   1) Find research papers on the user provided topic using the 'google_search_agent'. 
   2) Then, pass the p...'
[logging_plugin]    Available Tools: ['google_search_agent', 'count_papers']
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
[logging_plugin] 🧠 LLM RESPONSE
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Content: function_call: count_papers
[logging_plugin]    Token Usage - Input: 887, Output: 624
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: 9757ec1c-cc22-47cc-b253-52fcfc51f728
[logging_plugin]    Author: research_paper_finder_agent
[logging_plugin]    Content: function_call: count_papers
[logging_plugin]    Final Response: False
[logging_plugin]    Function Calls: ['count_papers']
[logging_plugin] 🔧 TOOL STARTING
[logging_plugin]    Tool Name: count_papers
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Function Call ID: adk-7d87c43d-e92b-4016-8f50-5dc51e398dac
[logging_plugin]    Arguments: {'papers': ['The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 2025. Researchers and tech companies are making progress in stability, scalability, and usability, bringing quantum systems closer to comm...}
[logging_plugin] 🔧 TOOL COMPLETED
[logging_plugin]    Tool Name: count_papers
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Function Call ID: adk-7d87c43d-e92b-4016-8f50-5dc51e398dac
[logging_plugin]    Result: 1
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: 45a0da6b-8c71-4970-b6b1-cf376e99847e
[logging_plugin]    Author: research_paper_finder_agent
[logging_plugin]    Content: function_response: count_papers
[logging_plugin]    Final Response: False
[logging_plugin]    Function Responses: ['count_papers']
[logging_plugin] 🧠 LLM REQUEST
[logging_plugin]    Model: gemini-2.5-flash-lite
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    System Instruction: 'Your task is to find research papers and count them. 
   
   You must follow these steps:
   1) Find research papers on the user provided topic using the 'google_search_agent'. 
   2) Then, pass the p...'
[logging_plugin]    Available Tools: ['google_search_agent', 'count_papers']
[logging_plugin] 🧠 LLM RESPONSE
[logging_plugin]    Agent: research_paper_finder_agent
[logging_plugin]    Content: text: 'Here are the recent papers on quantum computing: The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 20...'
[logging_plugin]    Token Usage - Input: 1526, Output: 613
[logging_plugin] 📢 EVENT YIELDED
[logging_plugin]    Event ID: 57e5e8f4-4cd6-43f5-90b6-92be43f51494
[logging_plugin]    Author: research_paper_finder_agent
[logging_plugin]    Content: text: 'Here are the recent papers on quantum computing: The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 20...'
[logging_plugin]    Final Response: True
research_paper_finder_agent > Here are the recent papers on quantum computing: The field of quantum computing is experiencing rapid advancements, with significant breakthroughs occurring in 2024 and projections for even more in 2025. Researchers and tech companies are making progress in stability, scalability, and usability, bringing quantum systems closer to commercial viability.

Key developments and trends include:

**Hardware and Qubit Advancements:**
*   **Increased Qubit Milestones:** In 2024, several companies achieved record qubit counts while simultaneously improving performance, including higher coherence times and better gate fidelity. For instance, Google announced its 105-qubit Willow processor, which is five times more coherent than its previous Sycamore processor. IBM's roadmap includes the Kookaburra processor with 1,386 qubits in a multi-chip configuration.
*   **Logical Qubits and Error Correction:** A major focus is shifting towards "logical qubits," which are more stable and error-resistant than physical qubits. Companies like Google have demonstrated practical quantum error correction systems that detect and correct errors in real-time. Atom Computing, in collaboration with Microsoft, is developing machines with reliable logical qubits.
*   **Novel Architectures:** Researchers are exploring new architectures, such as light-based platforms with optical cavities for efficient photon collection from atoms. IBM is developing modular quantum data centers like Quantum System 2, designed for scalability by connecting multiple processors.
*   **New Qubit Materials:** Advancements in materials science are crucial. For example, a new tantalum-silicon qubit has demonstrated coherence for over a millisecond, and research into topological superconductors aims to create more stable qubits.

**Software and Algorithms:**
*   **Quantum Computing and AI Convergence:** A significant trend in 2024 was the intersection of quantum computing and artificial intelligence, exploring quantum-enhanced machine learning, faster neural network optimization, and improved data sampling.
*   **Cloud-Based Access:** Access to quantum computing is becoming more democratized through cloud platforms, open-source SDKs, and educational tools.

**Investment and Commercialization:**
*   **Increased Investment:** The quantum computing sector has seen substantial investment, with billions of dollars invested in 2024 and projected for 2025, driven by both private companies and governments.
*   **Commercial Viability:** The focus is shifting towards "utility-scale operation," where the computational value of quantum computers exceeds their cost.

**Emerging Applications:**
*   **Scientific Simulation:** Quantum computers are being used for complex simulations in areas like physics and chemistry.
*   **Cryptography:** Quantum algorithms like Grover's search algorithm have the potential to impact current cryptographic methods.

Overall, 2024 has been a pivotal year for quantum computing, moving from theoretical concepts to tangible progress. The coming years are expected to bring further breakthroughs, paving the way for more powerful and applicable quantum machines.

There is 1 paper on this topic.
[logging_plugin] 🤖 AGENT COMPLETED
[logging_plugin]    Agent Name: research_paper_finder_agent
[logging_plugin]    Invocation ID: e-b7180c2e-cfb2-4f6b-b6fc-a7fa54c036e3
[logging_plugin] ✅ INVOCATION COMPLETED
[logging_plugin]    Invocation ID: e-b7180c2e-cfb2-4f6b-b6fc-a7fa54c036e3
[logging_plugin]    Final Agent: research_paper_finder_agent
"""
