# -*- coding: utf-8 -*-
"""Life safety / egress analysis tools (route analysis settings, paths of travel)"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_life_safety_tools(mcp, revit_get, revit_post, revit_image=None):
    """Register life-safety tools with the MCP server."""
    _ = revit_post, revit_image  # unused, kept for interface consistency

    @mcp.tool()
    async def get_route_analysis_settings(ctx: Context = None) -> str:
        """Get project-wide route (path of travel / egress) analysis settings,
        such as the vertical analysis zone used to detect obstacles."""
        response = await revit_get("/get_route_analysis_settings/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_paths_of_travel(ctx: Context = None) -> str:
        """Get a list of all path-of-travel (egress route) elements already
        placed in the model, including their computed length."""
        response = await revit_get("/list_paths_of_travel/", ctx)
        return format_response(response)
