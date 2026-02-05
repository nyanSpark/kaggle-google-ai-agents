import os
import asyncio
from pathlib import Path
import base64

import warnings
warnings.filterwarnings("ignore", message=".*asyncgen*")

# --- Imports (unchanged) ---
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

try:
    from IPython.display import Image as IPImage, display as ipy_display
    USE_IPYTHON = True
except ImportError:
    USE_IPYTHON = False

# --- 1. Load API Key ---
def load_api_key():
    """Load API key from .env file using only built-in functions"""
    try:
        with open('../.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        if key == "GOOGLE_API_KEY":
                            return value
        return None
    except FileNotFoundError:
        return None

try:
    api_key = load_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    print("✅ Gemini API key setup complete.")
except Exception as e:
    print(f"🔑 Authentication Error: {e}")
    exit(1)

# --- 2. Retry config ---
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# nodeJS pip install needed
# --- 3. MCP tool setup (unchanged) ---
mcp_image_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-everything",
            ],
        ),
        timeout=30,
    )
)
print("✅ MCP Tool created")

# --- 4. Agent ---
image_agent = LlmAgent(
    model=Gemini(model="gemini-3-flash-preview", retry_options=retry_config),
    name="image_agent",
    instruction="Use the MCP Tool to generate images for user queries",
    tools=[mcp_image_server],
)
runner = InMemoryRunner(agent=image_agent)

# --- 5. Helper: save image + optional inline display ---
def save_and_display_image(b64_str: str, label="") -> bool:
    """Saves Base64 image to disk; optionally displays if IPython available."""
    try:
        img_bytes = base64.b64decode(b64_str)
        out_dir = Path("generated_images")
        out_dir.mkdir(exist_ok=True)

        # Generate unique filename
        count = len(list(out_dir.glob("image_*.png"))) + 1
        filepath = str(out_dir / f"image_{count:03d}.png")

        with open(filepath, "wb") as f:
            f.write(img_bytes)

        print(f"[✅ Saved image] {filepath} (from {label})")
        
        # Try inline display if in Jupyter-like environment
        if USE_IPYTHON and b64_str:
            ipy_display(IPImage(data=img_bytes))
        return True

    except Exception as e:
        print(f"[⚠️ Image save/display error] {e}")
        return False


# --- 6. Extract image from event (robust & minimal) ---
def extract_images_from_event(event, seen: set):
    """Extract images from a single ADK event, using known MCP structure."""
    # Early exit if no parts
    if not hasattr(event, "content") or not event.content:
        return

    for i, part in enumerate(event.content.parts):
        # Only process tool result parts (not model text parts)
        func_resp = getattr(part, "function_response", None)
        if not func_resp:
            continue
        
        # MCP response is always in function_response.response["content"]
        resp_data = func_resp.response
        if not isinstance(resp_data, dict):
            continue  # Skip non-dict responses

        content_list = resp_data.get("content", [])
        if not isinstance(content_list, list):
            continue

        # Look for image part (typically index 1)
        for j, item in enumerate(content_list):
            if isinstance(item, dict) and item.get("type") == "image":
                data = item.get("data")
                if isinstance(data, str) and len(data) > 0 and data not in seen:
                    seen.add(data)
                    label = f"content.parts[{i}].function_response.response.content[{j}]"
                    save_and_display_image(data, label=label)


# --- 7. Run agent and extract images ---
async def run_debug():
    print("\n🧠 Running agent...")
    
    # Get events (ADK returns list of Event)
    events = await runner.run_debug("Provide a sample tiny image", verbose=True)

    # If result is string (fallback), wrap in list
    if isinstance(events, str):
        events = [types.Content(role="user", parts=[types.Part(text=events)])]

    print(f"\n📊 Received {len(events)} event(s)")

    seen_images = set()

    for i, event in enumerate(events):
        part_type = type(event).__name__
        print(f"\n[Event {i+1}] Type: {part_type}")

        # Extract text (if any)
        if hasattr(event, "content") and event.content:
            for part in getattr(event.content, "parts", []):
                text = getattr(part, "text", None)
                # if text:
                    # print(f"[Text] {text}")

        # ✅ Now extract images cleanly
        extract_images_from_event(event, seen_images)

    print("\n✅ Done. Images saved to `generated_images/` folder.")

# --- 8. Run! ---
if __name__ == "__main__":
    try:
        asyncio.run(run_debug())
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted.")

# Kaggle MCP Server - For dataset and notebook operations
# McpToolset(
#     connection_params=StdioConnectionParams(
#         server_params=StdioServerParameters(
#             command='npx',
#             args=[
#                 '-y',
#                 'mcp-remote',
#                 'https://www.kaggle.com/mcp'
#             ],
#         ),
#         timeout=30,
#     )
# )
# What it provides:
# 📊 Search and download Kaggle datasets
# 📓 Access notebook metadata
# 🏆 Query competition information etc.,
# Learn more: Kaggle MCP Documentation
# https://www.kaggle.com/docs/mcp



# 👉 GitHub MCP Server - For PR/Issue analysis
# McpToolset(
#     connection_params=StreamableHTTPServerParams(
#         url="https://api.githubcopilot.com/mcp/",
#         headers={
#             "Authorization": f"Bearer {GITHUB_TOKEN}",
#             "X-MCP-Toolsets": "all",
#             "X-MCP-Readonly": "true"
#         },
#     ),
# )
# More resources: ADK Third-party Tools Documentation
# https://google.github.io/adk-docs/tools/third-party/
