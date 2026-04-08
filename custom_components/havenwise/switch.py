"""Switch platform for Havenwise holiday mode."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HavenwiseCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [HavenwiseHolidayModeSwitch(data["coordinator"], data["client"], entry)]
    )


class HavenwiseHolidayModeSwitch(CoordinatorEntity, SwitchEntity):
    """Holiday mode toggle switch."""

    _attr_has_entity_name = True
    _attr_name = "Holiday Mode"
    _attr_icon = "mdi:beach"

    def __init__(self, coordinator: HavenwiseCoordinator, client, entry: ConfigEntry):
        super().__init__(coordinator)
        self.client = client
        self._attr_unique_id = f"{entry.entry_id}_holiday_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def is_on(self) -> bool:
        temps = self.coordinator.data.get("system_temps", {})
        return not temps.get("isHeatingOn", True) and not temps.get("isDhwOn", True)

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.client.enable_holiday_mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.client.disable_holiday_mode)
        await self.coordinator.async_request_refresh()
