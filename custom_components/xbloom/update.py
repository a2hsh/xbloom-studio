"""Firmware update entity for the xBloom Studio integration.

**Read-only in this version.** The entity surfaces the latest firmware the
xBloom cloud publishes for this machine (version + release notes), so a user
can see when an update is available. It deliberately does *not* expose an
install button: the actual flash is YMODEM-over-BLE with unconfirmed
characteristics and real bricking risk, and is deferred until a live capture
confirms the wire protocol (see ``discovery/cloud-api-spec.md`` §4).

Gating (per the integration's design): firmware is a **cloud** capability, so
this entity is only available when the user is logged in to the xBloom cloud.
When logged out it reports unavailable — no cloud calls are made.

The cloud version check is a plain (unauthenticated) ``client-api`` endpoint,
but we still gate on login to keep "cloud features require login" consistent
and because it needs the machine serial the account is bound to.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_PRODUCT_ID, DOMAIN
from .vendor.xbloom.exceptions import XBloomAPIError

_LOGGER = logging.getLogger(__name__)

# Firmware releases are rare — poll gently.
SCAN_INTERVAL = timedelta(hours=6)
PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the firmware update entity."""
    async_add_entities([XBloomFirmwareUpdate(entry)])


class XBloomFirmwareUpdate(UpdateEntity):
    """Shows the latest available xBloom firmware (read-only)."""

    _attr_has_entity_name = True
    _attr_translation_key = "xbloom_firmware"
    _attr_unique_id = "xbloom_firmware"
    # No UpdateEntityFeature.INSTALL — read-only surface.
    _attr_supported_features = 0

    def __init__(self, entry) -> None:
        self._entry = entry
        self._serial = entry.data.get(CONF_PRODUCT_ID)
        self._latest: str | None = None
        self._release_summary: str | None = None
        self._release_url: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "xbloom_studio")},
            name="xBloom Studio",
            manufacturer="xBloom",
            model="Studio",
        )

    @property
    def available(self) -> bool:
        # Firmware is a cloud feature — unavailable until logged in and we have
        # a serial and a fetched version.
        coordinator = self._entry.runtime_data.coordinator
        return bool(
            coordinator.cloud_logged_in and self._serial and self._latest
        )

    @property
    def installed_version(self) -> str | None:
        # Best-effort: filled from the BLE MachineInfo heartbeat when available.
        return self._entry.runtime_data.installed_fw_version

    @property
    def latest_version(self) -> str | None:
        return self._latest

    @property
    def release_summary(self) -> str | None:
        return self._release_summary

    @property
    def release_url(self) -> str | None:
        return self._release_url

    async def async_update(self) -> None:
        """Poll the cloud for the latest firmware for this machine."""
        coordinator = self._entry.runtime_data.coordinator
        if not coordinator.cloud_logged_in or not self._serial:
            self._latest = None
            return
        cloud = self._entry.runtime_data.cloud
        try:
            info = await cloud.firmware_check(self._serial)
        except (XBloomAPIError, aiohttp.ClientError) as err:
            _LOGGER.debug("xbloom firmware check failed: %s", err)
            return
        if info is None:
            self._latest = None
            return
        self._latest = info["version"]
        self._release_summary = info.get("notes_en") or info.get("notes_zh")
        self._release_url = info.get("download_url")
