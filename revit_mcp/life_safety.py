# -*- coding: UTF-8 -*-
"""
Life Safety Module for Revit MCP
Provides read access to egress / path-of-travel analysis
(Autodesk.Revit.DB.Analysis.RouteAnalysisSettings / PathOfTravel).
"""

from pyrevit import routes, DB
import logging

from utils import normalize_string, get_element_name, element_id_value

logger = logging.getLogger(__name__)


def _safe(getter, default=None):
    """Call a zero-arg getter, returning default on any failure."""
    try:
        value = getter()
        return value if value is not None else default
    except Exception:
        return default


def register_life_safety_routes(api):
    """Register all life-safety / egress analysis routes with the API"""

    @api.route("/get_route_analysis_settings/", methods=["GET"])
    def get_route_analysis_settings(doc):
        """Get project-wide route (path of travel) analysis settings"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            settings = DB.Analysis.RouteAnalysisSettings.GetRouteAnalysisSettings(doc)
            if not settings:
                return routes.make_response(
                    data={"error": "Could not read route analysis settings"},
                    status=500,
                )

            return routes.make_response(
                data={
                    "status": "success",
                    "id": element_id_value(settings.Id),
                    "analysis_zone_top_offset": _safe(
                        lambda: settings.AnalysisZoneTopOffset
                    ),
                    "analysis_zone_bottom_offset": _safe(
                        lambda: settings.AnalysisZoneBottomOffset
                    ),
                    "minimum_length": _safe(lambda: settings.MinimumLength),
                    "ignore_imports": _safe(lambda: settings.IgnoreImports),
                }
            )

        except Exception as e:
            logger.error(
                "Failed to get route analysis settings: {}".format(str(e))
            )
            return routes.make_response(
                data={
                    "error": "Failed to get route analysis settings: {}".format(
                        str(e)
                    )
                },
                status=500,
            )

    @api.route("/list_paths_of_travel/", methods=["GET"])
    def list_paths_of_travel(doc):
        """Get a list of all path-of-travel (egress route) elements in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Analysis.PathOfTravel)
                .ToElements()
            )

            paths = []
            for elem in elements:
                try:
                    length = None
                    try:
                        waypoints = list(elem.GetWaypoints())
                        if len(waypoints) >= 2:
                            total = 0.0
                            for i in range(len(waypoints) - 1):
                                total += waypoints[i].DistanceTo(waypoints[i + 1])
                            length = round(total, 2)
                    except Exception:
                        pass

                    view_name = None
                    view_id = _safe(lambda: elem.OwnerViewId)
                    if view_id and view_id != DB.ElementId.InvalidElementId:
                        view = doc.GetElement(view_id)
                        if view:
                            view_name = normalize_string(get_element_name(view))

                    paths.append(
                        {
                            "id": element_id_value(elem.Id),
                            "name": normalize_string(get_element_name(elem)),
                            "view": view_name,
                            "length": length,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "Could not process path of travel: {}".format(str(e))
                    )
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "paths_of_travel": paths,
                    "total_paths": len(paths),
                }
            )

        except Exception as e:
            logger.error("Failed to list paths of travel: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list paths of travel: {}".format(str(e))},
                status=500,
            )

    logger.info("Life safety routes registered successfully")
