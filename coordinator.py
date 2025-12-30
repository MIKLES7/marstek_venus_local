from __future__ import annotations

import asyncio
import json
import logging
import socket
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_LOOP_INTERVAL,
    CONF_ES_STATUS_INTERVAL,
    CONF_BAT_STATUS_INTERVAL,
    CONF_ES_MODE_INTERVAL,
    CONF_MIN_REQUEST_GAP,
    CONF_UDP_TIMEOUT,
    DEFAULT_LOOP_INTERVAL,
    DEFAULT_ES_STATUS_INTERVAL,
    DEFAULT_BAT_STATUS_INTERVAL,
    DEFAULT_ES_MODE_INTERVAL,
    DEFAULT_MIN_REQUEST_GAP,
    DEFAULT_UDP_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


def dig(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _is_trueish(v: Any) -> bool:
    """Accept only real truthy values from the API."""
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, (int, float)):
        return v == 1
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "ok")
    return False


class _UdpClient:
    """Blocking UDP client (socket reused), executed in executor thread."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self._host = host
        self._port = port
        self._timeout = float(timeout)
        self._sock: socket.socket | None = None

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _ensure_socket(self) -> socket.socket:
        if self._sock is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(self._timeout)
            s.connect((self._host, self._port))
            self._sock = s
        return self._sock

    def call(self, payload: dict[str, Any]) -> dict[str, Any]:
        s = self._ensure_socket()
        try:
            data = json.dumps(payload).encode("utf-8")
            s.send(data)
            resp = s.recv(65535)
            return json.loads(resp.decode("utf-8"))
        except Exception:
            self.close()
            raise


async def async_test_udp_connection(hass: HomeAssistant, host: str, port: int, timeout: float) -> bool:
    """Quick connectivity check used by config flow."""
    def _test() -> bool:
        client = _UdpClient(host, port, timeout)
        try:
            r = client.call({"id": 1, "method": "ES.GetStatus", "params": {"id": 0}})
            return isinstance(r, dict) and ("result" in r or "error" in r)
        except Exception:
            return False
        finally:
            client.close()

    return await hass.async_add_executor_job(_test)


@dataclass
class SchedulerConfig:
    loop_interval: int
    es_status_interval: int
    bat_status_interval: int
    es_mode_interval: int
    min_request_gap: int
    udp_timeout: float


class VenusScheduler:
    """Loop; per tick at most ONE UDP request."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, cfg: SchedulerConfig) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.cfg = cfg

        self._lock = asyncio.Lock()
        self._client = _UdpClient(host, port, cfg.udp_timeout)

        self._data: dict[str, Any] = {
            "ts": None,
            "host": host,
            "port": port,
            "device_name": "Marstek Venus E 3.0",
            "bat": None,
            "es": None,
            "mode": None,
            # diagnostics
            "last_request": None,
            "last_error": None,
            "last_es_ok": None,
            "last_bat_ok": None,
            "last_mode_ok": None,
        }

        self._last_es_status: float | None = None
        self._last_bat_status: float | None = None
        self._last_es_mode: float | None = None
        self._last_request_ts: float | None = None

    async def async_close(self) -> None:
        def _close() -> None:
            self._client.close()

        await self.hass.async_add_executor_job(_close)

    def _now(self) -> float:
        return dt_util.utcnow().timestamp()

    def _iso_now(self) -> str:
        return dt_util.utcnow().isoformat()

    async def _call(self, method: str, params: dict[str, Any] | None, rpc_id: int) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": rpc_id, "method": method}
        if params is not None:
            payload["params"] = params

        def _do_call() -> dict[str, Any]:
            return self._client.call(payload)

        return await self.hass.async_add_executor_job(_do_call)

    async def _respect_min_gap(self) -> None:
        now = self._now()
        if self._last_request_ts is None:
            return
        gap = float(self.cfg.min_request_gap) - (now - self._last_request_ts)
        if gap > 0:
            await asyncio.sleep(gap)

    async def async_set_mode(self, mode: str) -> bool:
        """
        Set operating mode via ES.SetMode and VERIFY via ES.GetMode.
        We do NOT fake-update the mode sensor anymore.
        ES.SetMode response contains result.set_result boolean per API docs. :contentReference[oaicite:1]{index=1}
        """
        async with self._lock:
            await self._respect_min_gap()

            now = self._now()
            self._data["ts"] = self._iso_now()
            self._data["last_request"] = "ES.SetMode"

            # Payloads follow Open API examples (Auto/AI/Manual). :contentReference[oaicite:2]{index=2}
            if mode == "Auto":
                cfg = {"mode": "Auto", "auto_cfg": {"enable": 1}}
            elif mode == "AI":
                cfg = {"mode": "AI", "ai_cfg": {"enable": 1}}
            elif mode == "Manual":
                # Minimal "do nothing" slot: power 0, enabled, 1 minute window.
                # Many firmwares reject ES.SetMode Manual without manual_cfg. :contentReference[oaicite:3]{index=3}
                cfg = {
                    "mode": "Manual",
                    "manual_cfg": {
                        "time_num": 9,
                        "start_time": "00:00",
                        "end_time": "00:01",
                        "week_set": 127,
                        "power": 0,
                        "enable": 1,
                    },
                }
            else:
                self._data["last_error"] = f"Unsupported mode: {mode}"
                return False

            try:
                # Some firmwares are picky; harmless to include config.id as well.
                params = {"id": 0, "config": {"id": 0, **cfg}}
                r_set = await self._call("ES.SetMode", params, 20)
                self._last_request_ts = self._now()

                set_result = dig(r_set, "result.set_result")
                ok = _is_trueish(set_result)

                if not ok:
                    self._data["last_error"] = {"ES.SetMode": r_set}
                    return False

                # Give the device a tiny moment, then verify via ES.GetMode. :contentReference[oaicite:4]{index=4}
                await asyncio.sleep(0.3)
                await self._respect_min_gap()

                self._data["last_request"] = "ES.GetMode"
                r_mode = await self._call("ES.GetMode", {"id": 0}, 21)
                self._last_request_ts = self._now()

                if "result" not in r_mode:
                    self._data["last_error"] = {"ES.GetMode_after_set": r_mode}
                    return False

                actual_mode = dig(r_mode, "result.mode")
                self._data["mode"] = r_mode["result"]
                self._data["last_mode_ok"] = self._iso_now()

                if actual_mode != mode:
                    self._data["last_error"] = {
                        "mode_mismatch": {"requested": mode, "actual": actual_mode, "set_response": r_set}
                    }
                    return False

                self._data["last_error"] = None
                # Force next periodic mode poll to refresh again later
                self._last_es_mode = None
                return True

            except Exception as e:
                self._last_request_ts = self._now()
                self._data["last_error"] = str(e)
                return False

    async def tick(self) -> dict[str, Any]:
        async with self._lock:
            now = self._now()
            self._data["ts"] = self._iso_now()

            if self._last_request_ts is not None and (now - self._last_request_ts) < int(self.cfg.min_request_gap):
                return self._data

            due_es = self._last_es_status is None or (now - self._last_es_status) >= int(self.cfg.es_status_interval)
            due_bat = self._last_bat_status is None or (now - self._last_bat_status) >= int(self.cfg.bat_status_interval)
            due_mode = self._last_es_mode is None or (now - self._last_es_mode) >= int(self.cfg.es_mode_interval)

            if not (due_es or due_bat or due_mode):
                return self._data

            try:
                if due_es:
                    self._data["last_request"] = "ES.GetStatus"
                    r = await self._call("ES.GetStatus", {"id": 0}, 12)
                    self._last_request_ts = now

                    if "result" in r:
                        self._data["es"] = r["result"]
                        self._last_es_status = now
                        self._data["last_es_ok"] = self._iso_now()
                        self._data["last_error"] = None
                    else:
                        self._data["last_error"] = {"ES.GetStatus": r.get("error", r)}

                elif due_bat:
                    self._data["last_request"] = "Bat.GetStatus"
                    r = await self._call("Bat.GetStatus", {"id": 0}, 11)
                    self._last_request_ts = now

                    if "result" in r:
                        self._data["bat"] = r["result"]
                        self._last_bat_status = now
                        self._data["last_bat_ok"] = self._iso_now()
                        self._data["last_error"] = None
                    else:
                        self._data["last_error"] = {"Bat.GetStatus": r.get("error", r)}

                else:
                    self._data["last_request"] = "ES.GetMode"
                    r = await self._call("ES.GetMode", {"id": 0}, 13)
                    self._last_request_ts = now

                    if "result" in r:
                        self._data["mode"] = r["result"]
                        self._last_es_mode = now
                        self._data["last_mode_ok"] = self._iso_now()
                        self._data["last_error"] = None
                    else:
                        self._data["last_error"] = {"ES.GetMode": r.get("error", r)}

            except Exception as e:
                self._last_request_ts = now
                self._data["last_error"] = str(e)

            return self._data


class MarstekVenusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]

        opts = entry.options
        cfg = SchedulerConfig(
            loop_interval=int(opts.get(CONF_LOOP_INTERVAL, DEFAULT_LOOP_INTERVAL)),
            es_status_interval=int(opts.get(CONF_ES_STATUS_INTERVAL, DEFAULT_ES_STATUS_INTERVAL)),
            bat_status_interval=int(opts.get(CONF_BAT_STATUS_INTERVAL, DEFAULT_BAT_STATUS_INTERVAL)),
            es_mode_interval=int(opts.get(CONF_ES_MODE_INTERVAL, DEFAULT_ES_MODE_INTERVAL)),
            min_request_gap=int(opts.get(CONF_MIN_REQUEST_GAP, DEFAULT_MIN_REQUEST_GAP)),
            udp_timeout=float(opts.get(CONF_UDP_TIMEOUT, DEFAULT_UDP_TIMEOUT)),
        )

        self.scheduler = VenusScheduler(hass, self.host, self.port, cfg)

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN} {self.host}",
            update_interval=timedelta(seconds=cfg.loop_interval),
            update_method=self._async_update,
        )

    async def _async_update(self) -> dict[str, Any]:
        try:
            return await self.scheduler.tick()
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_mode(self, mode: str) -> bool:
        return await self.scheduler.async_set_mode(mode)

    async def async_close(self) -> None:
        await self.scheduler.async_close()
