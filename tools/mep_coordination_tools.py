# -*- coding: utf-8 -*-
"""Cross-discipline MEP coordination/QA tools (unconnected connectors, clashes, schedules)"""

from mcp.server.fastmcp import Context
from typing import List, Optional
from .utils import format_response


def register_mep_coordination_tools(mcp, revit_get, revit_post, revit_image=None):
    """Register cross-discipline MEP coordination tools with the MCP server."""
    _ = revit_get, revit_image  # unused, kept for interface consistency

    @mcp.tool()
    async def check_unconnected_connectors(
        categories: Optional[List[str]] = None, ctx: Context = None
    ) -> str:
        """
        Find MEP connectors (duct/pipe/conduit/cable tray ends) that are not
        connected to anything else — a common coordination problem where
        loose ends go unnoticed until construction.

        Args:
            categories: Optional list of categories to check (e.g. ["Ducts", "Pipes"]).
                Defaults to all MEP categories: Ducts, Flex Ducts, Pipes, Flex Pipes,
                Conduits, Cable Trays and their fittings/accessories.
            ctx: MCP context for logging

        Returns:
            List of unconnected connectors grouped by element, with counts checked.
        """
        try:
            data = {}
            if categories:
                data["categories"] = categories

            if ctx:
                await ctx.info("Checking for unconnected MEP connectors")
            response = await revit_post(
                "/check_unconnected_connectors/", data, ctx, timeout=60.0
            )
            return format_response(response)

        except Exception as e:
            error_msg = "Error checking unconnected connectors: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def check_clashes(
        category_a: str, category_b: str, limit: int = 50, ctx: Context = None
    ) -> str:
        """
        Find geometric clashes between elements of two categories
        (e.g. "Ducts" vs "Structural Framing"), using the same intersection
        logic as Revit's built-in Interference Report.

        Args:
            category_a: Name of the first category (e.g. "Ducts")
            category_b: Name of the second category (e.g. "Structural Framing")
            limit: Maximum number of clash pairs to return (default 50)
            ctx: MCP context for logging

        Returns:
            List of clashing element pairs with their ids and names.
        """
        try:
            data = {
                "category_a": category_a,
                "category_b": category_b,
                "limit": limit,
            }

            if ctx:
                await ctx.info(
                    "Checking clashes between {} and {}".format(
                        category_a, category_b
                    )
                )
            response = await revit_post("/check_clashes/", data, ctx, timeout=90.0)
            return format_response(response)

        except Exception as e:
            error_msg = "Error checking clashes: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def export_mep_schedule(
        schedule_name: str, max_rows: int = 500, ctx: Context = None
    ) -> str:
        """
        Get structured row/column data from an existing schedule view
        (e.g. a panel schedule, duct schedule or pipe schedule) without
        needing to open or recreate the schedule.

        Args:
            schedule_name: Exact name of the schedule view
            max_rows: Maximum number of data rows to return (default 500)
            ctx: MCP context for logging

        Returns:
            Column headers and row data extracted from the schedule.
        """
        try:
            data = {"schedule_name": schedule_name, "max_rows": max_rows}

            if ctx:
                await ctx.info("Exporting schedule: {}".format(schedule_name))
            response = await revit_post(
                "/export_mep_schedule/", data, ctx, timeout=60.0
            )
            return format_response(response)

        except Exception as e:
            error_msg = "Error exporting schedule: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg
