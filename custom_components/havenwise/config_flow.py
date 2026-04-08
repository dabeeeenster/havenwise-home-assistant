"""Config flow for Havenwise integration."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import HavenwiseAuthError, HavenwiseClient, HavenwiseConnectionError
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)


class HavenwiseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Havenwise."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            client = HavenwiseClient(user_input["email"], user_input["password"])
            try:
                data = await self.hass.async_add_executor_job(client.login)
            except HavenwiseAuthError:
                errors["base"] = "invalid_auth"
            except (HavenwiseConnectionError, Exception):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(data["localId"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["email"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
