"""Sensor platform for Havenwise energy and performance data."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HavenwiseCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = [
    {
        "key": "total_cop",
        "name": "Total COP",
        "icon": "mdi:lightning-bolt",
        "unit": "x",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _perf_today(d, "total", "cop"),
    },
    {
        "key": "heating_cop",
        "name": "Heating COP",
        "icon": "mdi:radiator",
        "unit": "x",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _perf_today(d, "heating", "cop"),
    },
    {
        "key": "dhw_cop",
        "name": "Hot Water COP",
        "icon": "mdi:water-boiler",
        "unit": "x",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _perf_today(d, "dhw", "cop"),
    },
    {
        "key": "energy_consumed",
        "name": "Energy Consumed Today",
        "icon": "mdi:flash",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL,
        "value_fn": lambda d: _perf_today(d, "total", "energy_consumed"),
    },
    {
        "key": "energy_produced",
        "name": "Heat Energy Produced Today",
        "icon": "mdi:fire",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL,
        "value_fn": lambda d: _perf_today(d, "total", "energy_produced"),
    },
    {
        "key": "energy_cost",
        "name": "Energy Cost Today",
        "icon": "mdi:currency-gbp",
        "unit": "GBP",
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.TOTAL,
        "value_fn": lambda d: _perf_today_field(d, "energy_cost_gbp"),
    },
    {
        "key": "effective_tariff",
        "name": "Effective Tariff",
        "icon": "mdi:tag-outline",
        "unit": "p/kWh",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _perf_today_field(d, "energy_effective_tariff_pence"),
    },
    {
        "key": "room_temperature",
        "name": "Room Temperature",
        "icon": None,
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _system_temp(d, "roomTemp"),
    },
    {
        "key": "dhw_temperature",
        "name": "Hot Water Temperature",
        "icon": None,
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda d: _system_temp(d, "dhwTemp"),
    },
]


def _perf_today(data: dict, category: str, field: str):
    perf = data.get("performance")
    if not perf or not perf.get("data"):
        return None
    today = perf["data"][-1]
    return today.get(category, {}).get(field)


def _perf_today_field(data: dict, field: str):
    perf = data.get("performance")
    if not perf or not perf.get("data"):
        return None
    return perf["data"][-1].get(field)


def _system_temp(data: dict, field: str):
    val = data.get("system_temps", {}).get(field)
    return float(val) if val is not None else None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities(
        [HavenwiseSensor(coordinator, entry, defn) for defn in SENSOR_DEFINITIONS]
    )


class HavenwiseSensor(CoordinatorEntity, SensorEntity):
    """Havenwise sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HavenwiseCoordinator, entry: ConfigEntry, defn: dict
    ):
        super().__init__(coordinator)
        self._defn = defn
        self._attr_unique_id = f"{entry.entry_id}_{defn['key']}"
        self._attr_name = defn["name"]
        self._attr_native_unit_of_measurement = defn["unit"]
        self._attr_device_class = defn["device_class"]
        self._attr_state_class = defn["state_class"]
        if defn["icon"]:
            self._attr_icon = defn["icon"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def native_value(self):
        value = self._defn["value_fn"](self.coordinator.data)
        _LOGGER.debug(
            "Sensor %s value: %s (last_updated=%s)",
            self._defn["key"],
            value,
            self.coordinator.last_update_success_time,
        )
        return value
