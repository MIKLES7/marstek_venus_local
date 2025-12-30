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
from .discovery import async_discover_devices

CONF_DEVICE = "device"
DEVICE_MANUAL = "__manual__"

DISCOVERY_TIMEOUT = 2.0  # seconds


class MarstekVenusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Start with discovery list, allow manual IP fallback."""
        errors: dict[str, str] = {}

        # If submitted
        if user_input is not None:
            choice = user_input[CONF_DEVICE]
            if choice == DEVICE_MANUAL:
                return await self.async_step_manual()

            host = choice
            port = DEFAULT_PORT

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

        # Discovery (build choices)
        devices = await async_discover_devices(self.hass, DEFAULT_PORT, DISCOVERY_TIMEOUT)

        choices: dict[str, str] = {}
        for d in devices:
            ip = d.get("ip")
            if not ip:
                continue

            # Make a nice label (best-effort)
            label_parts = [ip]
            if d.get("device_name"):
                label_parts.append(str(d["device_name"]))
            elif d.get("name"):
                label_parts.append(str(d["name"]))
            elif d.get("model"):
                label_parts.append(str(d["model"]))
            elif d.get("serial"):
                label_parts.append(f"SN {d['serial']}")
            elif d.get("sn"):
                label_parts.append(f"SN {d['sn']}")

            choices[ip] = " - ".join(label_parts)

        # Always include manual fallback
        choices[DEVICE_MANUAL] = "Manual IP eingeben"

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE): vol.In(choices),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_manual(self, user_input: dict | None = None) -> FlowResult:
        """Manual IP entry fallback."""
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
        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return MarstekVenusOptionsFlowHandler(config_entry)


class MarstekVenusOptionsFlowHandler(config_entries.OptionsFlow):
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
