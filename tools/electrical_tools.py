# -*- coding: utf-8 -*-
"""Electrical tools (circuits, panels, cable trays, conduits, wires, settings)"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_electrical_tools(mcp, revit_get, revit_post, revit_image=None):
    """Register electrical tools with the MCP server."""
    _ = revit_post, revit_image  # unused, kept for interface consistency

    @mcp.tool()
    async def list_circuits(ctx: Context = None) -> str:
        """Get a list of all electrical circuits in the current Revit model,
        including panel, load, voltage, current and wire size."""
        response = await revit_get("/list_circuits/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_panels(ctx: Context = None) -> str:
        """Get a list of all electrical equipment (panels, transformers, etc.)
        in the current Revit model."""
        response = await revit_get("/list_panels/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_cable_trays(ctx: Context = None) -> str:
        """Get a list of all cable trays in the current Revit model with
        width, height and length."""
        response = await revit_get("/list_cable_trays/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_conduits(ctx: Context = None) -> str:
        """Get a list of all conduits in the current Revit model with
        diameter and length."""
        response = await revit_get("/list_conduits/", ctx)
        return format_response(response)

    @mcp.tool()
    async def list_wires(ctx: Context = None) -> str:
        """Get a list of all electrical wires in the current Revit model."""
        response = await revit_get("/list_wires/", ctx)
        return format_response(response)

    @mcp.tool()
    async def get_electrical_settings(ctx: Context = None) -> str:
        """Get project-wide electrical settings: defined voltage types and
        distribution systems."""
        response = await revit_get("/get_electrical_settings/", ctx)
        return format_response(response)
