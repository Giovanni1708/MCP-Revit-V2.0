# -*- coding: utf-8 -*-
"""Mechanical tools (spaces, zones, ducts, mechanical systems, settings)"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_mechanical_tools(mcp, revit_get, revit_post, revit_image=None):
    """Register mechanical tools with the MCP server."""
    _ = revit_post, revit_image  # unused, kept for interface consistency

    @mcp.tool()
    async def list_spaces(ctx: Context = None) -> str:
        """Get a list of all MEP spaces in the current Revit model, including
        area, volume, level, zone and heating/cooling loads."""
        response = await revit_get("/list_spaces/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_zones(ctx: Context = None) -> str:
        """Get a list of all HVAC zones in the current Revit model with their
        contained space count."""
        response = await revit_get("/list_zones/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_ducts(ctx: Context = None) -> str:
        """Get a list of all ducts and flex ducts in the current Revit model,
        including size, level and connected system."""
        response = await revit_get("/list_ducts/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_mechanical_systems(ctx: Context = None) -> str:
        """Get a list of all mechanical (duct) systems in the current Revit
        model, including connection status and base equipment."""
        response = await revit_get("/list_mechanical_systems/", ctx)
        return format_response(response)

    @mcp.tool()
    async def get_duct_settings(ctx: Context = None) -> str:
        """Get project-wide duct settings and sizing parameters."""
        response = await revit_get("/get_duct_settings/", ctx)
        return format_response(response)
