# custom_components/marstek_venus_local/config_flow.py
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_LOOP_INTERVAL,
    DEFAULT_ES_STATUS_INTERVAL,
    DEFAULT_BAT_STATUS_INTERVAL,
    DEFAULT_ES_MODE_INTERVAL,
    DEFAULT_MIN_REQUEST_GAP,
    DEFAULT_UDP_TIMEOUT,
    CONF_LOOP_INTERVAL,
    CONF_ES_STATUS_INTERVAL,
    CONF_BAT_STATUS_INTERVAL,
    CONF_ES_MODE_INTERVAL,
    CONF_MIN_REQUEST_GAP,
    CONF_UDP_TIMEOUT,
)
from .coordinator import async_test_udp_connection


class MarstekVenusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            ok = await async_test_udp_connection(self.hass, host, port, DEFAULT_UDP_TIMEOUT)
            if not ok:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Marstek Venus ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                    options={
                        CONF_LOOP_INTERVAL: DEFAULT_LOOP_INTERVAL,
                        CONF_ES_STATUS_INTERVAL: DEFAULT_ES_STATUS_INTERVAL,
                        CONF_BAT_STATUS_INTERVAL: DEFAULT_BAT_STATUS_INTERVAL,
                        CONF_ES_MODE_INTERVAL: DEFAULT_ES_MODE_INTERVAL,
                        CONF_MIN_REQUEST_GAP: DEFAULT_MIN_REQUEST_GAP,
                        CONF_UDP_TIMEOUT: DEFAULT_UDP_TIMEOUT,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return MarstekVenusOptionsFlow(config_entry)


class MarstekVenusOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.entry.options

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LOOP_INTERVAL,
                    default=opts.get(CONF_LOOP_INTERVAL, DEFAULT_LOOP_INTERVAL),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_ES_STATUS_INTERVAL,
                    default=opts.get(CONF_ES_STATUS_INTERVAL, DEFAULT_ES_STATUS_INTERVAL),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_BAT_STATUS_INTERVAL,
                    default=opts.get(CONF_BAT_STATUS_INTERVAL, DEFAULT_BAT_STATUS_INTERVAL),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_ES_MODE_INTERVAL,
                    default=opts.get(CONF_ES_MODE_INTERVAL, DEFAULT_ES_MODE_INTERVAL),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_MIN_REQUEST_GAP,
                    default=opts.get(CONF_MIN_REQUEST_GAP, DEFAULT_MIN_REQUEST_GAP),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_UDP_TIMEOUT,
                    default=opts.get(CONF_UDP_TIMEOUT, DEFAULT_UDP_TIMEOUT),
                ): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
