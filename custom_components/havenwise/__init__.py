"""The Havenwise integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import HavenwiseClient
from .const import DOMAIN, PLATFORMS, MANUFACTURER
from .coordinator import HavenwiseCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Havenwise from a config entry."""
    client = HavenwiseClient(entry.data["email"], entry.data["password"])
    await hass.async_add_executor_job(client.login)

    coordinator = HavenwiseCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
