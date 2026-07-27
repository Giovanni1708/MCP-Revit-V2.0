# -*- coding: UTF-8 -*-
"""
Mechanical Module for Revit MCP
Provides read access to spaces, zones, ducts, mechanical systems and
project duct settings (Autodesk.Revit.DB.Mechanical).
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


def register_mechanical_routes(api):
    """Register all mechanical routes with the API"""

    @api.route("/list_spaces/", methods=["GET"])
    def list_spaces(doc):
        """Get a list of all MEP spaces in the model with area, volume and loads"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Mechanical.Space)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            spaces = []
            for space in elements:
                try:
                    area = _safe(lambda: space.Area, 0)
                    is_placed = bool(area and area > 0)

                    level_name = None
                    level = _safe(lambda: space.Level)
                    if level:
                        level_name = normalize_string(get_element_name(level))

                    zone_name = None
                    zone = _safe(lambda: space.Zone)
                    if zone:
                        zone_name = normalize_string(get_element_name(zone))

                    space_info = {
                        "id": element_id_value(space.Id),
                        "name": normalize_string(get_element_name(space)),
                        "number": _safe(lambda: normalize_string(space.Number)),
                        "level": level_name,
                        "zone": zone_name,
                        "is_placed": is_placed,
                    }

                    if is_placed:
                        space_info["area"] = round(area, 2)
                        space_info["volume"] = _safe(
                            lambda: round(space.Volume, 2)
                        )
                        space_info["design_heating_load"] = _safe(
                            lambda: space.DesignHeatingLoad
                        )
                        space_info["design_cooling_load"] = _safe(
                            lambda: space.DesignCoolingLoad
                        )
                        space_info["number_of_people"] = _safe(
                            lambda: space.NumberofPeople
                        )

                    spaces.append(space_info)
                except Exception as e:
                    logger.warning("Could not process space: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={"status": "success", "spaces": spaces, "total_spaces": len(spaces)}
            )

        except Exception as e:
            logger.error("Failed to list spaces: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list spaces: {}".format(str(e))}, status=500
            )

    @api.route("/list_zones/", methods=["GET"])
    def list_zones(doc):
        """Get a list of all HVAC zones in the model with their contained spaces"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Mechanical.Zone)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            zones = []
            for zone in elements:
                try:
                    space_count = 0
                    try:
                        space_count = zone.Spaces.Size
                    except Exception:
                        pass

                    zones.append(
                        {
                            "id": element_id_value(zone.Id),
                            "name": normalize_string(get_element_name(zone)),
                            "space_count": space_count,
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process zone: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={"status": "success", "zones": zones, "total_zones": len(zones)}
            )

        except Exception as e:
            logger.error("Failed to list zones: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list zones: {}".format(str(e))}, status=500
            )

    @api.route("/list_ducts/", methods=["GET"])
    def list_ducts(doc):
        """Get a list of all ducts and flex ducts in the model with size and system"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            ducts = (
                DB.FilteredElementCollector(doc).OfClass(DB.Mechanical.Duct).ToElements()
            )
            flex_ducts = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Mechanical.FlexDuct)
                .ToElements()
            )

            results = []
            for elem, is_flex in [(d, False) for d in ducts] + [
                (d, True) for d in flex_ducts
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
                            "width": _param_value(elem, "Width"),
                            "height": _param_value(elem, "Height"),
                            "length": _param_value(elem, "Length"),
                            "system": system_name,
                            "level": level_name,
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process duct: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={"status": "success", "ducts": results, "total_ducts": len(results)}
            )

        except Exception as e:
            logger.error("Failed to list ducts: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list ducts: {}".format(str(e))}, status=500
            )

    @api.route("/list_mechanical_systems/", methods=["GET"])
    def list_mechanical_systems(doc):
        """Get a list of all mechanical (duct) systems in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            systems = DB.FilteredElementCollector(doc).OfClass(
                DB.Mechanical.MechanicalSystem
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
                        "Could not process mechanical system: {}".format(str(e))
                    )
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "mechanical_systems": results,
                    "total_systems": len(results),
                }
            )

        except Exception as e:
            logger.error("Failed to list mechanical systems: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to list mechanical systems: {}".format(str(e))
                },
                status=500,
            )

    @api.route("/get_duct_settings/", methods=["GET"])
    def get_duct_settings(doc):
        """Get project-wide duct settings and sizing parameters"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            settings = DB.Mechanical.DuctSettings.GetDuctSettings(doc)
            if not settings:
                return routes.make_response(
                    data={"error": "Could not read duct settings"}, status=500
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
                logger.warning("Could not read duct settings parameters: {}".format(str(e)))

            return routes.make_response(
                data={
                    "status": "success",
                    "id": element_id_value(settings.Id),
                    "parameters": parameters,
                }
            )

        except Exception as e:
            logger.error("Failed to get duct settings: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to get duct settings: {}".format(str(e))},
                status=500,
            )

    logger.info("Mechanical routes registered successfully")
