# -*- coding: UTF-8 -*-
"""
Plumbing Module for Revit MCP
Provides read access to pipes, piping systems and project pipe settings
(Autodesk.Revit.DB.Plumbing).
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


def _param_value(element, name, default=None):
    """Best-effort read of a parameter's display value (string) by name."""
    try:
        param = element.LookupParameter(name)
        if param and param.HasValue:
            return param.AsValueString() or param.AsDouble()
    except Exception:
        pass
    return default


def register_plumbing_routes(api):
    """Register all plumbing routes with the API"""

    @api.route("/list_pipes/", methods=["GET"])
    def list_pipes(doc):
        """Get a list of all pipes and flex pipes in the model with size and system"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            pipes = (
                DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.Pipe).ToElements()
            )
            flex_pipes = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Plumbing.FlexPipe)
                .ToElements()
            )

            results = []
            for elem, is_flex in [(p, False) for p in pipes] + [
                (p, True) for p in flex_pipes
            ]:
                try:
                    type_elem = doc.GetElement(elem.GetTypeId())

                    system_name = None
                    system = _safe(lambda: elem.MEPSystem)
                    if system:
                        system_name = normalize_string(get_element_name(system))

                    level_name = None
                    level_id = _safe(lambda: elem.LevelId)
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        level = doc.GetElement(level_id)
                        if level:
                            level_name = normalize_string(get_element_name(level))

                    results.append(
                        {
                            "id": element_id_value(elem.Id),
                            "is_flex": is_flex,
                            "type_name": normalize_string(get_element_name(type_elem))
                            if type_elem
                            else "Unknown",
                            "diameter": _param_value(elem, "Diameter"),
                            "length": _param_value(elem, "Length"),
                            "slope": _param_value(elem, "Slope"),
                            "system": system_name,
                            "level": level_name,
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process pipe: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={"status": "success", "pipes": results, "total_pipes": len(results)}
            )

        except Exception as e:
            logger.error("Failed to list pipes: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list pipes: {}".format(str(e))}, status=500
            )

    @api.route("/list_piping_systems/", methods=["GET"])
    def list_piping_systems(doc):
        """Get a list of all piping systems (sanitary, heating, fire protection, etc.)"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            systems = DB.FilteredElementCollector(doc).OfClass(
                DB.Plumbing.PipingSystem
            )

            results = []
            for system in systems:
                try:
                    base_equipment_name = None
                    base_equipment = _safe(lambda: system.BaseEquipment)
                    if base_equipment:
                        base_equipment_name = normalize_string(
                            get_element_name(base_equipment)
                        )

                    results.append(
                        {
                            "id": element_id_value(system.Id),
                            "name": normalize_string(get_element_name(system)),
                            "system_type": _safe(lambda: str(system.SystemType)),
                            "base_equipment": base_equipment_name,
                            "is_well_connected": _safe(
                                lambda: system.IsWellConnected
                            ),
                            "element_count": _safe(lambda: system.Elements.Size, 0),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "Could not process piping system: {}".format(str(e))
                    )
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "piping_systems": results,
                    "total_systems": len(results),
                }
            )

        except Exception as e:
            logger.error("Failed to list piping systems: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list piping systems: {}".format(str(e))},
                status=500,
            )

    @api.route("/get_pipe_settings/", methods=["GET"])
    def get_pipe_settings(doc):
        """Get project-wide pipe settings and sizing parameters"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            settings = DB.Plumbing.PipeSettings.GetPipeSettings(doc)
            if not settings:
                return routes.make_response(
                    data={"error": "Could not read pipe settings"}, status=500
                )

            parameters = []
            try:
                for param in settings.Parameters:
                    try:
                        if not param.HasValue:
                            continue
                        parameters.append(
                            {
                                "name": normalize_string(param.Definition.Name),
                                "value": param.AsValueString()
                                or normalize_string(str(param.AsDouble())),
                            }
                        )
                    except Exception:
                        continue
            except Exception as e:
                logger.warning("Could not read pipe settings parameters: {}".format(str(e)))

            return routes.make_response(
                data={
                    "status": "success",
                    "id": element_id_value(settings.Id),
                    "parameters": parameters,
                }
            )

        except Exception as e:
            logger.error("Failed to get pipe settings: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to get pipe settings: {}".format(str(e))},
                status=500,
            )

    logger.info("Plumbing routes registered successfully")
