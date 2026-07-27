# -*- coding: UTF-8 -*-
"""
MEP Coordination Module for Revit MCP
Cross-discipline QA/coordination tools that work across electrical,
mechanical and plumbing at once: unconnected connectors, clash detection
and schedule data export.
"""

from pyrevit import routes, DB
import json
import logging

from utils import normalize_string, get_element_name, element_id_value

logger = logging.getLogger(__name__)

# Default MEP categories checked for unconnected connectors
DEFAULT_CONNECTOR_CATEGORIES = {
    "Ducts": DB.BuiltInCategory.OST_DuctCurves,
    "Flex Ducts": DB.BuiltInCategory.OST_FlexDuctCurves,
    "Pipes": DB.BuiltInCategory.OST_PipeCurves,
    "Flex Pipes": DB.BuiltInCategory.OST_FlexPipeCurves,
    "Conduits": DB.BuiltInCategory.OST_Conduit,
    "Cable Trays": DB.BuiltInCategory.OST_CableTray,
    "Duct Fittings": DB.BuiltInCategory.OST_DuctFitting,
    "Pipe Fittings": DB.BuiltInCategory.OST_PipeFitting,
    "Conduit Fittings": DB.BuiltInCategory.OST_ConduitFitting,
    "Cable Tray Fittings": DB.BuiltInCategory.OST_CableTrayFitting,
    "Duct Accessories": DB.BuiltInCategory.OST_DuctAccessory,
    "Pipe Accessories": DB.BuiltInCategory.OST_PipeAccessory,
}


def _get_connector_manager(element):
    """Get the ConnectorManager for an MEPCurve or a family instance with an MEPModel."""
    try:
        return element.ConnectorManager
    except AttributeError:
        pass
    try:
        return element.MEPModel.ConnectorManager
    except AttributeError:
        return None


def register_mep_coordination_routes(api):
    """Register all cross-discipline MEP coordination routes with the API"""

    @api.route("/check_unconnected_connectors/", methods=["POST"])
    def check_unconnected_connectors(doc, request):
        """
        Find MEP connectors (duct/pipe/conduit/cable tray) that are not
        connected to anything.

        Expected JSON payload (optional):
        {
            "categories": ["Ducts", "Pipes"]   // defaults to all MEP categories
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            data = {}
            if request and request.data:
                try:
                    data = (
                        json.loads(request.data)
                        if isinstance(request.data, str)
                        else request.data
                    )
                except Exception:
                    data = {}

            requested_categories = data.get("categories")
            category_names = (
                requested_categories
                if requested_categories
                else list(DEFAULT_CONNECTOR_CATEGORIES.keys())
            )

            unconnected = []
            elements_checked = 0
            connectors_checked = 0

            for cat_name in category_names:
                bic = DEFAULT_CONNECTOR_CATEGORIES.get(cat_name)
                if not bic:
                    continue

                try:
                    elements = (
                        DB.FilteredElementCollector(doc)
                        .OfCategory(bic)
                        .WhereElementIsNotElementType()
                        .ToElements()
                    )
                except Exception:
                    continue

                for elem in elements:
                    elements_checked += 1
                    try:
                        cm = _get_connector_manager(elem)
                        if not cm:
                            continue

                        type_elem = doc.GetElement(elem.GetTypeId())
                        type_name = (
                            normalize_string(get_element_name(type_elem))
                            if type_elem
                            else "Unknown"
                        )

                        for connector in cm.Connectors:
                            connectors_checked += 1
                            try:
                                if not connector.IsConnected:
                                    unconnected.append(
                                        {
                                            "element_id": element_id_value(elem.Id),
                                            "category": cat_name,
                                            "type_name": type_name,
                                        }
                                    )
                            except Exception:
                                continue
                    except Exception as e:
                        logger.warning(
                            "Could not check connectors for element: {}".format(str(e))
                        )
                        continue

            return routes.make_response(
                data={
                    "status": "success",
                    "unconnected_connectors": unconnected,
                    "unconnected_count": len(unconnected),
                    "elements_checked": elements_checked,
                    "connectors_checked": connectors_checked,
                    "categories_checked": category_names,
                }
            )

        except Exception as e:
            logger.error(
                "Failed to check unconnected connectors: {}".format(str(e))
            )
            return routes.make_response(
                data={
                    "error": "Failed to check unconnected connectors: {}".format(
                        str(e)
                    )
                },
                status=500,
            )

    @api.route("/check_clashes/", methods=["POST"])
    def check_clashes(doc, request):
        """
        Find geometric clashes between elements of two categories.

        Expected JSON payload:
        {
            "category_a": "Ducts",
            "category_b": "Structural Framing",
            "limit": 50
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            data = (
                json.loads(request.data)
                if isinstance(request.data, str)
                else request.data
            )

            category_a_name = data.get("category_a")
            category_b_name = data.get("category_b")
            limit = int(data.get("limit", 50))

            if not category_a_name or not category_b_name:
                return routes.make_response(
                    data={"error": "category_a and category_b are required"},
                    status=400,
                )

            categories = doc.Settings.Categories
            cat_a = None
            cat_b = None
            for cat in categories:
                if cat.Name == category_a_name:
                    cat_a = cat
                if cat.Name == category_b_name:
                    cat_b = cat

            if not cat_a:
                return routes.make_response(
                    data={"error": "Category '{}' not found".format(category_a_name)},
                    status=404,
                )
            if not cat_b:
                return routes.make_response(
                    data={"error": "Category '{}' not found".format(category_b_name)},
                    status=404,
                )

            elements_a = (
                DB.FilteredElementCollector(doc)
                .OfCategoryId(cat_a.Id)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            clashes = []
            elements_checked = 0

            for elem_a in elements_a:
                if len(clashes) >= limit:
                    break

                elements_checked += 1
                try:
                    intersect_filter = DB.ElementIntersectsElementFilter(elem_a)
                    category_filter = DB.ElementCategoryFilter(cat_b.Id)
                    combined = DB.LogicalAndFilter(category_filter, intersect_filter)

                    clashing = (
                        DB.FilteredElementCollector(doc)
                        .WherePasses(combined)
                        .WhereElementIsNotElementType()
                        .ToElements()
                    )

                    for elem_b in clashing:
                        if elem_b.Id == elem_a.Id:
                            continue
                        clashes.append(
                            {
                                "element_a_id": element_id_value(elem_a.Id),
                                "element_a_name": normalize_string(
                                    get_element_name(elem_a)
                                ),
                                "element_b_id": element_id_value(elem_b.Id),
                                "element_b_name": normalize_string(
                                    get_element_name(elem_b)
                                ),
                            }
                        )
                        if len(clashes) >= limit:
                            break
                except Exception as e:
                    logger.warning(
                        "Could not check clashes for element: {}".format(str(e))
                    )
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "clashes": clashes,
                    "clash_count": len(clashes),
                    "elements_checked": elements_checked,
                    "truncated": len(clashes) >= limit,
                    "category_a": category_a_name,
                    "category_b": category_b_name,
                }
            )

        except Exception as e:
            logger.error("Failed to check clashes: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to check clashes: {}".format(str(e))},
                status=500,
            )

    @api.route("/export_mep_schedule/", methods=["POST"])
    def export_mep_schedule(doc, request):
        """
        Get structured row/column data from an existing schedule view
        (e.g. a panel schedule, duct schedule or pipe schedule).

        Expected JSON payload:
        {
            "schedule_name": "Duct Schedule",
            "max_rows": 500
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            data = (
                json.loads(request.data)
                if isinstance(request.data, str)
                else request.data
            )
            schedule_name = data.get("schedule_name")
            max_rows = int(data.get("max_rows", 500))

            if not schedule_name:
                return routes.make_response(
                    data={"error": "schedule_name is required"}, status=400
                )

            schedules = (
                DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule).ToElements()
            )

            target = None
            available = []
            for sched in schedules:
                try:
                    sched_name = normalize_string(get_element_name(sched))
                    available.append(sched_name)
                    if sched_name == normalize_string(schedule_name):
                        target = sched
                except Exception:
                    continue

            if not target:
                return routes.make_response(
                    data={
                        "error": "Schedule '{}' not found".format(schedule_name),
                        "available_schedules": sorted(available)[:30],
                    },
                    status=404,
                )

            table_data = target.GetTableData()

            headers = []
            try:
                header_section = table_data.GetSectionData(DB.SectionType.Header)
                if header_section and header_section.NumberOfRows > 0:
                    last_row = header_section.NumberOfRows - 1
                    for c in range(header_section.NumberOfColumns):
                        headers.append(
                            target.GetCellText(DB.SectionType.Header, last_row, c)
                        )
            except Exception as e:
                logger.warning("Could not read schedule headers: {}".format(str(e)))

            rows = []
            truncated = False
            try:
                body_section = table_data.GetSectionData(DB.SectionType.Body)
                if body_section:
                    total_rows = body_section.NumberOfRows
                    num_cols = body_section.NumberOfColumns
                    rows_to_read = min(total_rows, max_rows)
                    truncated = total_rows > rows_to_read

                    for r in range(rows_to_read):
                        row = []
                        for c in range(num_cols):
                            row.append(target.GetCellText(DB.SectionType.Body, r, c))
                        rows.append(row)
            except Exception as e:
                logger.warning("Could not read schedule body: {}".format(str(e)))

            return routes.make_response(
                data={
                    "status": "success",
                    "schedule_name": schedule_name,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": truncated,
                }
            )

        except Exception as e:
            logger.error("Failed to export MEP schedule: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to export MEP schedule: {}".format(str(e))},
                status=500,
            )

    logger.info("MEP coordination routes registered successfully")
