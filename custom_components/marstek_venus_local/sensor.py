# custom_components/marstek_venus_local/sensor.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekVenusCoordinator, dig


@dataclass(frozen=True, kw_only=True)
class VenusSensorEntityDescription(SensorEntityDescription):
    path: str


# ---- Sensors ----
SENSORS: list[VenusSensorEntityDescription] = [
    # device (constant)
    VenusSensorEntityDescription(key="device", name="device", path="device_name"),

    # diagnostics
    VenusSensorEntityDescription(key="last_request", name="last_request", path="last_request"),
    VenusSensorEntityDescription(key="last_error", name="last_error", path="last_error"),
    VenusSensorEntityDescription(key="last_es_ok", name="last_es_ok", path="last_es_ok"),
    VenusSensorEntityDescription(key="last_bat_ok", name="last_bat_ok", path="last_bat_ok"),
    VenusSensorEntityDescription(key="last_mode_ok", name="last_mode_ok", path="last_mode_ok"),

    # Battery (Bat.GetStatus)
    VenusSensorEntityDescription(key="bat_soc", name="bat_soc", path="bat.soc", native_unit_of_measurement=PERCENTAGE),
    VenusSensorEntityDescription(
        key="bat_temp",
        name="bat_temp",
        path="bat.bat_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VenusSensorEntityDescription(
        key="bat_capacity",
        name="bat_capacity",
        path="bat.bat_capacity",
        native_unit_of_measurement="Wh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VenusSensorEntityDescription(
        key="rated_capacity",
        name="rated_capacity",
        path="bat.rated_capacity",
        native_unit_of_measurement="Wh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # ES (ES.GetStatus)
    VenusSensorEntityDescription(
        key="ongrid_power",
        name="ongrid_power",
        path="es.ongrid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VenusSensorEntityDescription(
        key="offgrid_power",
        name="offgrid_power",
        path="es.offgrid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VenusSensorEntityDescription(
        key="total_grid_output_energy",
        name="total_grid_output_energy",
        path="es.total_grid_output_energy",
        native_unit_of_measurement="Wh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    VenusSensorEntityDescription(
        key="total_grid_input_energy",
        name="total_grid_input_energy",
        path="es.total_grid_input_energy",
        native_unit_of_measurement="Wh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    VenusSensorEntityDescription(
        key="total_load_energy",
        name="total_load_energy",
        path="es.total_load_energy",
        native_unit_of_measurement="Wh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),

    # Mode (ES.GetMode)
    VenusSensorEntityDescription(key="mode", name="mode", path="mode.mode"),
]

# Diese Keys bekommen KEINE _stable Version mehr:
NO_STABLE_KEYS: set[str] = {
    "device",
    "rated_capacity",
    "last_bat_ok",
    "last_error",
    "last_es_ok",
    "last_mode_ok",
    "last_request",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: MarstekVenusCoordinator = hass.data[DOMAIN][entry.entry_id]

    device_identifier = f"{coordinator.host}:{coordinator.port}"
    device_info = DeviceInfo(
        identifiers={(DOMAIN, device_identifier)},
        name="Marstek Venus E 3.0",
        manufacturer="Marstek",
        model="Venus E 3.0",
    )

    entities: list[SensorEntity] = []
    for desc in SENSORS:
        # normale Sensoren immer
        entities.append(MarstekVenusSensor(coordinator, device_identifier, device_info, desc, stable=False))

        # stable Sensoren nur, wenn nicht ausgeschlossen
        if desc.key not in NO_STABLE_KEYS:
            entities.append(MarstekVenusSensor(coordinator, device_identifier, device_info, desc, stable=True))

    async_add_entities(entities, True)


class MarstekVenusSensor(CoordinatorEntity[MarstekVenusCoordinator], SensorEntity, RestoreEntity):
    entity_description: VenusSensorEntityDescription

    def __init__(
        self,
        coordinator: MarstekVenusCoordinator,
        device_identifier: str,
        device_info: DeviceInfo,
        desc: VenusSensorEntityDescription,
        stable: bool,
    ) -> None:
        super().__init__(coordinator)
        self._device_info = device_info
        self.entity_description = desc
        self._stable = stable

        suffix = "_stable" if stable else ""
        self._attr_unique_id = f"{device_identifier}:{desc.key}{suffix}"
        self._attr_name = f"Venus {desc.name}{suffix}"

        self._last_native_value: Any | None = None
        self._has_value = False

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # For stable sensors: restore last state so they don't start as unknown after restart.
        if self._stable:
            last = await self.async_get_last_state()
            if last is not None and last.state not in (None, "unknown", "unavailable"):
                self._last_native_value = last.state
                self._has_value = True

    @property
    def available(self) -> bool:
        # Stable sensors: once we have any value (restored or received), never go unavailable.
        if self._stable and self._has_value:
            return True
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        data = self.coordinator.data
        if not isinstance(data, dict):
            return self._last_native_value if (self._stable and self._has_value) else None

        val = dig(data, self.entity_description.path)

        # If no new value: stable keeps old; non-stable becomes None
        if val is None:
            return self._last_native_value if (self._stable and self._has_value) else None

        # Normalize numbers similarly to your current behavior
        if isinstance(val, (int, float)):
            if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
                val_norm: Any = float(val)
            else:
                val_norm = int(round(float(val), 0))
        else:
            val_norm = val

        if self._stable:
            self._last_native_value = val_norm
            self._has_value = True

        return val_norm
