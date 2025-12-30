# custom_components/marstek_venus_local/discovery.py
from __future__ import annotations

import json
import socket
from typing import Any

from homeassistant.core import HomeAssistant


def _discover_blocking(port: int, timeout: float) -> list[dict[str, Any]]:
    """Broadcast Marstek.GetDevice and collect responses."""
    payload = {"id": 1, "method": "Marstek.GetDevice", "params": {}}
    data = json.dumps(payload).encode("utf-8")

    found: dict[str, dict[str, Any]] = {}

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)

        # Send to limited broadcast
        s.sendto(data, ("255.255.255.255", int(port)))

        # Collect until timeout
        while True:
            try:
                resp, addr = s.recvfrom(65535)
            except TimeoutError:
                break
            except OSError:
                break

            ip = addr[0]
            try:
                parsed = json.loads(resp.decode("utf-8", errors="ignore"))
            except Exception:
                continue

            # Try to extract something useful for display
            info: dict[str, Any] = {"ip": ip}
            if isinstance(parsed, dict):
                result = parsed.get("result")
                if isinstance(result, dict):
                    # common guesses (depends on firmware)
                    for key in ("device_name", "name", "model", "sn", "serial", "id", "mac"):
                        if key in result and result[key]:
                            info[key] = result[key]
                info["raw"] = parsed

            found[ip] = info

    finally:
        s.close()

    return list(found.values())


async def async_discover_devices(
    hass: HomeAssistant,
    port: int,
    timeout: float = 2.0,
) -> list[dict[str, Any]]:
    """Async wrapper around blocking UDP discovery."""
    return await hass.async_add_executor_job(_discover_blocking, port, timeout)
