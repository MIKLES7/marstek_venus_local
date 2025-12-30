from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MarstekVenusCoordinator


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordinator: MarstekVenusCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data if isinstance(coordinator.data, dict) else {}

    # Host/IP is usually fine, but if you want it redacted, say so and I redact it.
    return {
        "entry": {
            "host": coordinator.host,
            "port": coordinator.port,
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
        },
        "data": data,
    }
