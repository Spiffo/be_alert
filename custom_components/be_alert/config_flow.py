"""Config flow for BE Alert integration."""

from __future__ import annotations

from typing import Any
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import callback
from homeassistant.helpers import selector

# Import all constants from const.py
from .const import (
    DOMAIN,
    LOCATION_SOURCE_DEVICE,
    LOCATION_SOURCE_ZONE,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class BEAlertConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the multi-step config flow for BE Alert."""

    VERSION = 1

    @staticmethod
    def is_matching(_source: Any) -> bool:  # pylint: disable=arguments-differ
        """Return if the source is matching."""
        return False

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial user setup step.

        This step is shown when the user first adds the integration.
        It checks if an instance is already configured and if not, creates a
        single entry for the integration hub.
        """
        # Abort if an instance is already configured.
        _LOGGER.warning("ConfigFlow.async_step_user: Started.")
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # If the user confirms, create the single config entry. The options
        # dictionary is initialized here.
        _LOGGER.warning(
            "ConfigFlow.async_step_user: Creating single hub entry."
        )
        if user_input is not None:
            return self.async_create_entry(
                title="BE Alert", data={}, options={}
            )

        # Show a simple form to confirm the setup.
        return self.async_show_form(step_id="user")

    # ------------------- OPTIONS FLOW -------------------
    @staticmethod
    @callback
    # pylint: disable-next=unused-argument
    def async_get_options_flow(_config_entry):
        """Return options flow handler."""
        return BEAlertOptionsFlow(_config_entry)


class BEAlertOptionsFlow(config_entries.OptionsFlow):
    """BE Alert options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the BE Alert options flow."""
        super().__init__()
        self._entry: config_entries.ConfigEntry = config_entry
        _LOGGER.warning("OptionsFlow.__init__: Initializing options flow.")
        self._sensor_type: str | None = None

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Display the main menu for the options flow.

        This menu allows the user to add or remove sensors, or change global
        settings.
        """
        _LOGGER.warning(
            "OptionsFlow.async_step_init: Showing menu for entry %s.",
            self._entry.entry_id,
        )
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_sensor", "remove_sensor", "settings"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the global settings for the integration.

        This step allows the user to configure settings like the polling
        interval.
        """
        _LOGGER.warning("OptionsFlow.async_step_settings: Started.")
        options = dict(self._entry.options or {})
        if user_input is not None:
            _LOGGER.warning(
                "OptionsFlow.async_step_settings: User input received: %s",
                user_input,
            )
            new_options = {**options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=options.get(
                        "scan_interval", DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            }
        )
        return self.async_show_form(
            step_id="settings",
            data_schema=schema,
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the first step of adding a new sensor: choosing its type.

        The user can choose to add a sensor for all alerts, or a
        location-based sensor for a zone or device.
        """
        _LOGGER.warning("OptionsFlow.async_step_add_sensor: Started.")
        options = dict(self._entry.options or {})
        if user_input is not None:
            sensor_type = user_input["sensor_type"]
            _LOGGER.warning(
                "OptionsFlow.async_step_add_sensor: User selected: %s",
                sensor_type,
            )
            if sensor_type == "all":
                # Handle 'all' sensor immediately
                sensors = list(options.get("sensors", []))
                if "all" not in [s.get("type") for s in sensors]:
                    sensors.append({"type": "all"})
                    new_options = {**options, "sensors": sensors}
                    _LOGGER.warning(
                        "OptionsFlow.async_step_add_sensor: Adding 'all' "
                        "sensor. New options: %s",
                        new_options,
                    )
                    return self.async_create_entry(title="", data=new_options)
                return self.async_abort(reason="all_sensor_exists")

            self._sensor_type = sensor_type
            # Move to the next step for zone/device
            return await self.async_step_select_entity()

        schema = vol.Schema(
            {
                vol.Required("sensor_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        mode=selector.SelectSelectorMode.LIST,
                        options=[
                            "all",
                            LOCATION_SOURCE_ZONE,
                            LOCATION_SOURCE_DEVICE,
                        ],
                    )
                )
            }
        )
        return self.async_show_form(step_id="add_sensor", data_schema=schema)

    async def async_step_select_entity(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the selection of an entity for a location-based sensor.

        This step filters and shows a list of eligible entities (zones or
        device trackers/persons) for the user to select from.
        """
        _LOGGER.warning("OptionsFlow.async_step_select_entity: Started.")
        options = dict(self._entry.options or {})
        errors = {}
        sensor_type = self._sensor_type
        if sensor_type == LOCATION_SOURCE_DEVICE:
            _LOGGER.warning(
                "OptionsFlow.async_step_select_entity: Filtering for "
                "device/person entities."
            )
            # Build a list of eligible entities: persons and device_trackers
            # with GPS source that have location attributes.
            eligible_entities = [
                state.entity_id
                for domain in ("person", "device_tracker")
                for state in self.hass.states.async_all(domain)
                if state.attributes.get("latitude") is not None
                and state.attributes.get("longitude") is not None
                and (
                    domain == "person"
                    or state.attributes.get("source_type") == "gps"
                )
            ]

            selector_cfg = selector.EntitySelectorConfig(
                include_entities=eligible_entities
            )
        else:  # LOCATION_SOURCE_ZONE
            _LOGGER.warning(
                "OptionsFlow.async_step_select_entity: Filtering for "
                "zone entities."
            )
            selector_cfg = selector.EntitySelectorConfig(domain="zone")

        if user_input is not None:
            entity_id = user_input[CONF_ENTITY_ID]
            _LOGGER.warning(
                "OptionsFlow.async_step_select_entity: User selected "
                "entity_id: %s",
                entity_id,
            )
            sensors = list(options.get("sensors", []))
            # Check for duplicates
            if not any(s.get(CONF_ENTITY_ID) == entity_id for s in sensors):
                sensors.append(
                    {"type": sensor_type, CONF_ENTITY_ID: entity_id}
                )
                new_options = {**options, "sensors": sensors}
                _LOGGER.warning(
                    "OptionsFlow.async_step_select_entity: Adding sensor. "
                    "New options: %s",
                    new_options,
                )
                return self.async_create_entry(title="", data=new_options)

            errors["base"] = "entity_already_configured"

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                    selector_cfg
                )
            }
        )
        return self.async_show_form(
            step_id="select_entity", data_schema=schema, errors=errors
        )

    async def async_step_remove_sensor(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the removal of an existing sensor.

        This step lists all configured sensors and allows the user to select
        one for removal.
        """
        _LOGGER.warning("OptionsFlow.async_step_remove_sensor: Started.")
        options = dict(self._entry.options or {})
        sensors = list(options.get("sensors", []))

        # Create a list of sensors that can be removed
        sensor_map = {}
        for sensor in sensors:
            if sensor["type"] == "all":
                sensor_map["all_sensor"] = "BE Alert All"
            else:
                entity_id = sensor[CONF_ENTITY_ID]
                state = self.hass.states.get(entity_id)
                name = state.name if state else entity_id
                sensor_map[entity_id] = (
                    f"{sensor['type'].capitalize()}: {name}"
                )

        if not sensor_map:
            return self.async_abort(reason="no_sensors_to_remove")

        if user_input is not None:
            entity_to_remove = user_input["sensor_to_remove"]
            _LOGGER.warning(
                "OptionsFlow.async_step_remove_sensor: User chose to "
                "remove: %s",
                entity_to_remove,
            )

            new_sensors = []
            for sensor in sensors:
                # Check if the current sensor in the loop is the one to be
                # removed
                if (
                    sensor["type"] == "all"
                    and entity_to_remove == "all_sensor"
                ):
                    continue
                if sensor.get(CONF_ENTITY_ID) == entity_to_remove:
                    continue
                new_sensors.append(sensor)

            new_options = {**options, "sensors": new_sensors}
            _LOGGER.warning(
                "OptionsFlow.async_step_remove_sensor: Removing sensor. "
                "New options: %s",
                new_options,
            )
            return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {vol.Required("sensor_to_remove"): vol.In(sensor_map)}
        )
        return self.async_show_form(
            step_id="remove_sensor", data_schema=schema
        )
