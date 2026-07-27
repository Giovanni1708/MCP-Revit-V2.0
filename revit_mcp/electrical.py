# -*- coding: UTF-8 -*-
"""
Electrical Module for Revit MCP
Provides read access to electrical circuits, panels, cable trays, conduits,
wires and project electrical settings (Autodesk.Revit.DB.Electrical).
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


def _param_double(element, name, default=None):
    """Best-effort read of a parameter's display value (string) by name."""
    try:
        param = element.LookupParameter(name)
        if param and param.HasValue:
            return param.AsValueString() or param.AsDouble()
    except Exception:
        pass
    return default


def register_electrical_routes(api):
    """Register all electrical routes with the API"""

    @api.route("/list_circuits/", methods=["GET"])
    def list_circuits(doc):
        """Get a list of all electrical circuits (ElectricalSystem) in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            systems = DB.FilteredElementCollector(doc).OfClass(
                DB.Electrical.ElectricalSystem
            )

            circuits = []
            for system in systems:
                try:
                    panel_name = None
                    base_equipment = _safe(lambda: system.BaseEquipment)
                    if base_equipment:
                        panel_name = normalize_string(get_element_name(base_equipment))

                    circuits.append(
                        {
                            "id": element_id_value(system.Id),
                            "name": normalize_string(get_element_name(system)),
                            "circuit_number": _safe(lambda: system.CircuitNumber),
                            "system_type": _safe(lambda: str(system.SystemType)),
                            "panel": panel_name,
                            "load_name": _safe(
                                lambda: normalize_string(system.LoadName)
                            ),
                            "rating": _safe(lambda: system.Rating),
                            "voltage": _safe(lambda: system.Voltage),
                            "apparent_load": _safe(lambda: system.ApparentLoad),
                            "true_load": _safe(lambda: system.TrueLoad),
                            "apparent_current": _safe(
                                lambda: system.ApparentCurrent
                            ),
                            "power_factor": _safe(lambda: system.PowerFactor),
                            "voltage_drop": _safe(lambda: system.VoltageDrop),
                            "wire_size": _safe(
                                lambda: normalize_string(system.WireSizeString)
                            ),
                            "is_well_connected": _safe(
                                lambda: not system.IsMultipleNetwork
                            ),
                            "element_count": _safe(lambda: system.Elements.Size, 0),
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process circuit: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "circuits": circuits,
                    "total_circuits": len(circuits),
                }
            )

        except Exception as e:
            logger.error("Failed to list circuits: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list circuits: {}".format(str(e))},
                status=500,
            )

    @api.route("/list_panels/", methods=["GET"])
    def list_panels(doc):
        """Get a list of all electrical equipment (panels, transformers, etc.)"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            equipment = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            panels = []
            for elem in equipment:
                try:
                    level_name = None
                    level_id = _safe(lambda: elem.LevelId)
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        level = doc.GetElement(level_id)
                        if level:
                            level_name = normalize_string(get_element_name(level))

                    type_elem = doc.GetElement(elem.GetTypeId())

                    panels.append(
                        {
                            "id": element_id_value(elem.Id),
                            "name": normalize_string(get_element_name(elem)),
                            "type_name": normalize_string(
                                get_element_name(type_elem)
                            )
                            if type_elem
                            else "Unknown",
                            "level": level_name,
                            "rating": _param_double(elem, "Rating"),
                            "distribution_system": _param_double(
                                elem, "Distribution System"
                            ),
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process panel: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "panels": panels,
                    "total_panels": len(panels),
                }
            )

        except Exception as e:
            logger.error("Failed to list panels: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list panels: {}".format(str(e))},
                status=500,
            )

    @api.route("/list_cable_trays/", methods=["GET"])
    def list_cable_trays(doc):
        """Get a list of all cable trays and cable tray runs in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Electrical.CableTray)
                .ToElements()
            )

            cable_trays = []
            for elem in elements:
                try:
                    type_elem = doc.GetElement(elem.GetTypeId())
                    cable_trays.append(
                        {
                            "id": element_id_value(elem.Id),
                            "type_name": normalize_string(
                                get_element_name(type_elem)
                            )
                            if type_elem
                            else "Unknown",
                            "width": _param_double(elem, "Width"),
                            "height": _param_double(elem, "Height"),
                            "length": _param_double(elem, "Length"),
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process cable tray: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "cable_trays": cable_trays,
                    "total_cable_trays": len(cable_trays),
                }
            )

        except Exception as e:
            logger.error("Failed to list cable trays: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list cable trays: {}".format(str(e))},
                status=500,
            )

    @api.route("/list_conduits/", methods=["GET"])
    def list_conduits(doc):
        """Get a list of all conduits and conduit runs in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.Electrical.Conduit)
                .ToElements()
            )

            conduits = []
            for elem in elements:
                try:
                    type_elem = doc.GetElement(elem.GetTypeId())
                    conduits.append(
                        {
                            "id": element_id_value(elem.Id),
                            "type_name": normalize_string(
                                get_element_name(type_elem)
                            )
                            if type_elem
                            else "Unknown",
                            "diameter": _param_double(elem, "Diameter"),
                            "length": _param_double(elem, "Length"),
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process conduit: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={
                    "status": "success",
                    "conduits": conduits,
                    "total_conduits": len(conduits),
                }
            )

        except Exception as e:
            logger.error("Failed to list conduits: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list conduits: {}".format(str(e))},
                status=500,
            )

    @api.route("/list_wires/", methods=["GET"])
    def list_wires(doc):
        """Get a list of all electrical wires in the model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            elements = (
                DB.FilteredElementCollector(doc).OfClass(DB.Electrical.Wire).ToElements()
            )

            wires = []
            for elem in elements:
                try:
                    type_elem = doc.GetElement(elem.GetTypeId())
                    wires.append(
                        {
                            "id": element_id_value(elem.Id),
                            "wire_type": normalize_string(get_element_name(type_elem))
                            if type_elem
                            else "Unknown",
                            "length": _param_double(elem, "Length"),
                            "number_of_conductors": _safe(
                                lambda: elem.NumberOfConductors
                            ),
                        }
                    )
                except Exception as e:
                    logger.warning("Could not process wire: {}".format(str(e)))
                    continue

            return routes.make_response(
                data={"status": "success", "wires": wires, "total_wires": len(wires)}
            )

        except Exception as e:
            logger.error("Failed to list wires: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list wires: {}".format(str(e))}, status=500
            )

    @api.route("/get_electrical_settings/", methods=["GET"])
    def get_electrical_settings(doc):
        """Get project-wide electrical settings (voltage types, distribution systems)"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            settings = DB.Electrical.ElectricalSetting.GetElectricalSettings(doc)
            if not settings:
                return routes.make_response(
                    data={"error": "Could not read electrical settings"}, status=500
                )

            voltage_types = []
            try:
                for vt in settings.VoltageTypes:
                    try:
                        voltage_types.append(
                            {
                                "name": normalize_string(get_element_name(vt)),
                                "voltage": _safe(lambda: vt.Voltage),
                            }
                        )
                    except Exception:
                        continue
            except Exception as e:
                logger.warning("Could not read voltage types: {}".format(str(e)))

            distribution_systems = []
            try:
                for ds in settings.DistributionSysTypes:
                    try:
                        distribution_systems.append(
                            normalize_string(get_element_name(ds))
                        )
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(
                    "Could not read distribution system types: {}".format(str(e))
                )

            return routes.make_response(
                data={
                    "status": "success",
                    "voltage_types": voltage_types,
                    "distribution_systems": distribution_systems,
                }
            )

        except Exception as e:
            logger.error("Failed to get electrical settings: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to get electrical settings: {}".format(str(e))},
                status=500,
            )

    logger.info("Electrical routes registered successfully")
