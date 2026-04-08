"""Water heater platform for Havenwise hot water."""

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HavenwiseCoordinator

STATE_IDLE = "idle"
STATE_HEATING = "heating"
STATE_BOOST = "boost"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [HavenwiseWaterHeater(data["coordinator"], data["client"], entry)]
    )


class HavenwiseWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Havenwise hot water entity."""

    _attr_has_entity_name = True
    _attr_name = "Hot Water"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = [STATE_IDLE, STATE_HEATING, STATE_BOOST]
    _attr_supported_features = (
        WaterHeaterEntityFeature.AWAY_MODE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )

    def __init__(self, coordinator: HavenwiseCoordinator, client, entry: ConfigEntry):
        super().__init__(coordinator)
        self.client = client
        self._attr_unique_id = f"{entry.entry_id}_hot_water"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def current_temperature(self) -> float | None:
        temps = self.coordinator.data.get("system_temps", {})
        val = temps.get("dhwTemp")
        return float(val) if val is not None else None

    @property
    def target_temperature(self) -> float | None:
        return 45.0

    @property
    def is_away_mode_on(self) -> bool:
        temps = self.coordinator.data.get("system_temps", {})
        return not temps.get("isDhwOn", True)

    @property
    def current_operation(self) -> str:
        temps = self.coordinator.data.get("system_temps", {})
        if temps.get("isDhwBoostOn") or temps.get("is_dhw_boost_active"):
            return STATE_BOOST
        if temps.get("is_dhw_cycle_active"):
            return STATE_HEATING
        return STATE_IDLE

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_BOOST:
            await self.hass.async_add_executor_job(self.client.start_hot_water_boost)
        elif operation_mode == STATE_IDLE:
            await self.hass.async_add_executor_job(self.client.stop_hot_water_boost)
        await self.coordinator.async_request_refresh()

    async def async_turn_away_mode_on(self) -> None:
        await self.hass.async_add_executor_job(
            self.client.enable_holiday_mode, False, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_away_mode_off(self) -> None:
        await self.hass.async_add_executor_job(
            self.client.disable_holiday_mode, False, True
        )
        await self.coordinator.async_request_refresh()
