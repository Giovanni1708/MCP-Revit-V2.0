# -*- coding: utf-8 -*-
import os
import secrets
import sys
from pathlib import Path

import httpx
import anyio
from mcp.server.fastmcp import FastMCP, Image, Context
import base64
from typing import Optional, Dict, Any, Union

# Create a generic MCP server for interacting with Revit
# Use stateless_http=True and json_response=True for better compatibility
mcp = FastMCP(
    "Revit MCP Server",
    host="127.0.0.1",
    port=8000,
    stateless_http=True,
    json_response=True
)

# --- API key auth for HTTP transports ---
# pyRevit Routes and this MCP server have no built-in auth (see README), so
# once this server is exposed to the internet (e.g. via a dev tunnel for
# Copilot Studio) every HTTP request must present a shared secret.
API_KEY_HEADER = "X-API-Key"
API_KEY_FILE = Path(__file__).parent / ".revit_mcp_api_key"


def get_or_create_api_key() -> str:
    """Read the API key from env, then from a local file, or generate+persist one."""
    env_key = os.environ.get("REVIT_MCP_API_KEY")
    if env_key:
        return env_key
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text().strip()
    key = secrets.token_urlsafe(32)
    API_KEY_FILE.write_text(key)
    return key


def with_api_key_auth(app):
    """Wrap an ASGI app so every request must send a matching X-API-Key header."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    api_key = get_or_create_api_key()

    class ApiKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.headers.get(API_KEY_HEADER) != api_key:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app.add_middleware(ApiKeyMiddleware)
    return app

# Configuration
REVIT_HOST = "localhost"
REVIT_PORT = 48884  # Default pyRevit Routes port
BASE_URL = f"http://{REVIT_HOST}:{REVIT_PORT}/revit_mcp"


async def revit_get(endpoint: str, ctx: Context = None, **kwargs) -> Union[Dict, str]:
    """Simple GET request to Revit API"""
    return await _revit_call("GET", endpoint, ctx=ctx, **kwargs)


async def revit_post(endpoint: str, data: Dict[str, Any], ctx: Context = None, **kwargs) -> Union[Dict, str]:
    """Simple POST request to Revit API"""
    return await _revit_call("POST", endpoint, data=data, ctx=ctx, **kwargs)


async def revit_image(endpoint: str, ctx: Context = None) -> Union[Image, str]:
    """GET request that returns an Image object"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{BASE_URL}{endpoint}")
            
            if response.status_code == 200:
                data = response.json()
                image_bytes = base64.b64decode(data["image_data"])
                return Image(data=image_bytes, format="png")
            else:
                return f"Error: {response.status_code} - {response.text}"
    except httpx.TimeoutException:
        return "Error: Image export timed out after 60 seconds."
    except Exception as e:
        msg = str(e) or type(e).__name__
        return f"Error: {msg}"


async def _revit_call(method: str, endpoint: str, data: Dict = None, ctx: Context = None,
                     timeout: float = 30.0, params: Dict = None) -> Union[Dict, str]:
    """Internal function handling all HTTP calls"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{BASE_URL}{endpoint}"

            if method == "GET":
                response = await client.get(url, params=params)
            else:  # POST
                response = await client.post(url, json=data, headers={"Content-Type": "application/json"})

            return response.json() if response.status_code == 200 else f"Error: {response.status_code} - {response.text}"
    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout} seconds. The operation may still be running in Revit."
    except Exception as e:
        msg = str(e) or type(e).__name__
        return f"Error: {msg}"


# Register all tools BEFORE the main block
from tools import register_tools
register_tools(mcp, revit_get, revit_post, revit_image)


async def run_http_async(include_sse: bool):
    """Run the streamable-http app (optionally with SSE routes added too), behind API-key auth."""
    import uvicorn

    # Get the streamable-http app first - it has the proper lifespan
    # that initializes the session manager's task group
    http_app = mcp.streamable_http_app()

    if include_sse:
        # SSE doesn't need special lifespan - it creates task groups
        # per-request in connect_sse(). Add its routes to the http app
        # (preserving the http app's lifespan).
        sse_app = mcp.sse_app()
        for route in sse_app.routes:
            http_app.routes.append(route)

    http_app = with_api_key_auth(http_app)

    config = uvicorn.Config(
        http_app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    transport = "stdio"

    if "--sse" in sys.argv:
        transport = "sse"
    elif "--http" in sys.argv or "--streamable-http" in sys.argv:
        transport = "streamable-http"
    elif "--combined" in sys.argv:
        transport = "combined"

    if transport in ("streamable-http", "combined"):
        print(f"Starting {'combined SSE + streamable-http' if transport == 'combined' else 'streamable-http'} "
              f"server on http://{mcp.settings.host}:{mcp.settings.port} (endpoint: /mcp)...")
        print(f"API key required on every request (header '{API_KEY_HEADER}'): {get_or_create_api_key()}")
        anyio.run(run_http_async, transport == "combined")
        sys.exit(0)

    mcp.run(transport=transport)