"""DataUpdateCoordinator for Havenwise."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HavenwiseClient, HavenwiseAuthError, HavenwiseConnectionError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HavenwiseCoordinator(DataUpdateCoordinator):
    """Fetch data from Havenwise API."""

    def __init__(self, hass: HomeAssistant, client: HavenwiseClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except HavenwiseAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except HavenwiseConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _fetch_data(self) -> dict:
        profile = self.client.get_profile()
        system_temps = self.client.get_system_temps()
        heating_settings = self.client.get_heating_settings()

        heating_override = None
        try:
            heating_override = self.client.get_heating_override()
        except Exception:
            _LOGGER.debug("No heating override active")

        performance = None
        try:
            performance = self.client.get_performance_stats(week=1)
        except Exception:
            _LOGGER.debug("Could not fetch performance stats")

        return {
            "profile": profile,
            "system_temps": system_temps or {},
            "heating_settings": heating_settings,
            "heating_override": heating_override,
            "performance": performance,
        }
