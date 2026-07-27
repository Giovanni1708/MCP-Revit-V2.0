# -*- coding: utf-8 -*-
"""Plumbing tools (pipes, piping systems, settings)"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_plumbing_tools(mcp, revit_get, revit_post, revit_image=None):
    """Register plumbing tools with the MCP server."""
    _ = revit_post, revit_image  # unused, kept for interface consistency

    @mcp.tool()
    async def list_pipes(ctx: Context = None) -> str:
        """Get a list of all pipes and flex pipes in the current Revit model,
        including diameter, length, system and level."""
        response = await revit_get("/list_pipes/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_piping_systems(ctx: Context = None) -> str:
        """Get a list of all piping systems in the current Revit model
        (sanitary, heating, fire protection/sprinklers, etc.)."""
        response = await revit_get("/list_piping_systems/", ctx)
        return format_response(response)

    @mcp.tool()
    async def get_pipe_settings(ctx: Context = None) -> str:
        """Get project-wide pipe settings and sizing parameters."""
        response = await revit_get("/get_pipe_settings/", ctx)
        return format_response(response)
