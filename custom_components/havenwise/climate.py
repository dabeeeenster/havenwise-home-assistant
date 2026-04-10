"""Climate platform for Havenwise heating."""

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HavenwiseCoordinator

PRESET_BOOST = "boost"
PRESET_AWAY = "away"
PRESET_NONE = "none"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HavenwiseClimate(data["coordinator"], data["client"], entry)])


class HavenwiseClimate(CoordinatorEntity, ClimateEntity):
    """Havenwise heating climate entity."""

    _attr_has_entity_name = True
    _attr_force_update = True
    _attr_name = "Heating"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [PRESET_NONE, PRESET_BOOST, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator: HavenwiseCoordinator, client, entry: ConfigEntry):
        super().__init__(coordinator)
        self.client = client
        self._attr_unique_id = f"{entry.entry_id}_heating"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Havenwise Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": coordinator.data.get("profile", {}).get(
                "api_connection_type", "Heat Pump"
            ),
        }

    @property
    def current_temperature(self) -> float | None:
        temps = self.coordinator.data.get("system_temps", {})
        val = temps.get("roomTemp")
        return float(val) if val is not None else None

    @property
    def target_temperature(self) -> float | None:
        settings = self.coordinator.data.get("heating_settings", {})
        return settings.get("heating_setback_temp") or settings.get("setback_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        temps = self.coordinator.data.get("system_temps", {})
        return HVACMode.HEAT if temps.get("isHeatingOn") else HVACMode.OFF

    @property
    def preset_mode(self) -> str:
        temps = self.coordinator.data.get("system_temps", {})
        override = self.coordinator.data.get("heating_override")

        if not temps.get("isHeatingOn"):
            return PRESET_AWAY

        if override and isinstance(override, dict) and override.get("override"):
            flow_temp = override["override"].get("flow_temperature", 0)
            if flow_temp > 25:
                return PRESET_BOOST

        return PRESET_NONE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.hass.async_add_executor_job(
                self.client.disable_holiday_mode, True, False
            )
        elif hvac_mode == HVACMode.OFF:
            await self.hass.async_add_executor_job(
                self.client.enable_holiday_mode, True, False
            )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.hass.async_add_executor_job(
                self.client.update_heating_settings, {"heating_setback_temp": temp}
            )
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_BOOST:
            await self.hass.async_add_executor_job(
                self.client.start_heating_override, {"flow_temperature": 55}
            )
        elif preset_mode == PRESET_AWAY:
            await self.hass.async_add_executor_job(
                self.client.enable_holiday_mode, True, False
            )
        elif preset_mode == PRESET_NONE:
            await self.hass.async_add_executor_job(self.client.stop_heating_override)
            await self.hass.async_add_executor_job(
                self.client.disable_holiday_mode, True, False
            )
        await self.coordinator.async_request_refresh()
