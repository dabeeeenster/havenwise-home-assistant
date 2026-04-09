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
        _LOGGER.info("Havenwise coordinator update triggered")
        try:
            data = await self.hass.async_add_executor_job(self._fetch_data)
            _LOGGER.info("Havenwise coordinator update completed successfully")
            return data
        except HavenwiseAuthError as err:
            _LOGGER.error("Havenwise auth failed during update: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except HavenwiseConnectionError as err:
            _LOGGER.error("Havenwise connection error during update: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.error("Havenwise unexpected error during update: %s", err, exc_info=True)
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _fetch_data(self) -> dict:
        _LOGGER.debug("Starting data fetch from Havenwise API")

        profile = self.client.get_profile()
        _LOGGER.debug("Profile fetched: %s", profile)

        system_temps = self.client.get_system_temps()
        _LOGGER.debug("System temps fetched: %s", system_temps)

        heating_settings = self.client.get_heating_settings()
        _LOGGER.debug("Heating settings fetched: %s", heating_settings)

        heating_override = None
        try:
            heating_override = self.client.get_heating_override()
            _LOGGER.debug("Heating override fetched: %s", heating_override)
        except Exception as err:
            _LOGGER.debug("No heating override active: %s", err)

        performance = None
        try:
            performance = self.client.get_performance_stats(week=1)
            _LOGGER.debug(
                "Performance fetched: %d data points, last=%s",
                len(performance.get("data", [])) if performance else 0,
                performance.get("data", [])[-1] if performance and performance.get("data") else "N/A",
            )
        except Exception as err:
            _LOGGER.warning("Could not fetch performance stats: %s", err)

        result = {
            "profile": profile,
            "system_temps": system_temps or {},
            "heating_settings": heating_settings,
            "heating_override": heating_override,
            "performance": performance,
        }
        _LOGGER.debug("Coordinator data updated successfully")
        return result
