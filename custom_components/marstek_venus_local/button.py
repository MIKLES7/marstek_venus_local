# custom_components/marstek_venus_local/button.py
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekVenusCoordinator


@dataclass(frozen=True, kw_only=True)
class VenusButtonEntityDescription(ButtonEntityDescription):
    mode: str


BUTTONS: list[VenusButtonEntityDescription] = [
    VenusButtonEntityDescription(key="auto_mode", name="Auto mode", mode="Auto"),
    VenusButtonEntityDescription(key="ai_mode", name="AI mode", mode="AI"),
    VenusButtonEntityDescription(key="manual_mode", name="Manual mode", mode="Manual"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: MarstekVenusCoordinator = hass.data[DOMAIN][entry.entry_id]

    device_identifier = f"{coordinator.host}:{coordinator.port}"
    device_info = DeviceInfo(
        identifiers={(DOMAIN, device_identifier)},
        name="Marstek Venus E 3.0",
        manufacturer="Marstek",
        model="Venus E 3.0",
    )

    entities: list[ButtonEntity] = [
        MarstekVenusModeButton(coordinator, device_identifier, device_info, desc) for desc in BUTTONS
    ]
    async_add_entities(entities, True)


class MarstekVenusModeButton(CoordinatorEntity[MarstekVenusCoordinator], ButtonEntity):
    entity_description: VenusButtonEntityDescription

    def __init__(
        self,
        coordinator: MarstekVenusCoordinator,
        device_identifier: str,
        device_info: DeviceInfo,
        desc: VenusButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._device_info = device_info

        self._attr_unique_id = f"{device_identifier}:{desc.key}"
        self._attr_name = f"Venus {desc.name}"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    async def async_press(self) -> None:
        ok = await self.coordinator.async_set_mode(self.entity_description.mode)
        await self.coordinator.async_request_refresh()
        if not ok:
            self.coordinator.logger.warning(
                "Failed to set mode to %s", self.entity_description.mode
            )
