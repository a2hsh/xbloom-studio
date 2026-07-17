"""Firmware update entity for the xBloom Studio integration.

**Read-only in this version.** The entity compares the machine's *installed*
firmware (reported by the machine over BLE) against the *latest* firmware the
xBloom cloud publishes for it, and surfaces release notes. It deliberately does
*not* expose an install button: the actual flash is YMODEM-over-BLE with
unconfirmed characteristics and real bricking risk, deferred until a live
capture confirms the wire protocol (see ``discovery/cloud-api-spec.md`` §4).

Two data sources, mirroring the rest of the integration:
  * **installed_version** — decoded from the machine's BLE ``RD_MachineInfo``
    heartbeat (``fw_version`` in the dispatched event) whenever Home Assistant
    is connected to the machine. Persisted across restarts via RestoreEntity so
    it survives a reload even while disconnected.
  * **latest_version** — the version the xBloom cloud reports for this serial
    (``tUpToDateFirmwareVersion.thtml``). Cloud is a login-gated feature, so the
    entity is only *available* when logged in.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .ble_entities import signal_event
from .const import CONF_PRODUCT_ID, DOMAIN
from .vendor.xbloom.exceptions import XBloomAPIError

_LOGGER = logging.getLogger(__name__)

# Firmware releases are rare — poll the cloud gently for the latest version.
SCAN_INTERVAL = timedelta(hours=6)
PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the firmware update entity."""
    async_add_entities([XBloomFirmwareUpdate(entry)])


class XBloomFirmwareUpdate(UpdateEntity, RestoreEntity):
    """Installed (BLE) vs latest (cloud) firmware — read-only."""

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
        self._was_logged_in = False

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
        # Firmware is a cloud feature — unavailable until logged in with a serial
        # and a fetched latest version to compare against.
        coordinator = self._entry.runtime_data.coordinator
        return bool(
            coordinator.cloud_logged_in and self._serial and self._latest
        )

    @property
    def installed_version(self) -> str | None:
        # Reported by the machine over BLE; None until a heartbeat is seen.
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

    async def async_added_to_hass(self) -> None:
        """Restore the last-seen installed version and subscribe to BLE events."""
        await super().async_added_to_hass()
        # Restore installed_version across restarts (the machine may be
        # disconnected at startup, so we can't re-read it immediately).
        if self._entry.runtime_data.installed_fw_version is None:
            last = await self.async_get_last_state()
            if last is not None:
                restored = last.attributes.get("installed_version")
                if restored:
                    self._entry.runtime_data.installed_fw_version = restored

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_event(self._entry.entry_id), self._on_ble_event
            )
        )

        # Re-check the cloud latest version when the login state flips on (so it
        # appears right after login, not on the next 6-hour tick) and clear it on
        # logout. Coordinator refreshes fire on recipe changes too, so we only act
        # on an actual login-state transition to avoid needless firmware calls.
        coordinator = self._entry.runtime_data.coordinator
        self._was_logged_in = coordinator.cloud_logged_in
        self.async_on_remove(
            coordinator.async_add_listener(self._on_coordinator_update)
        )

    def _on_coordinator_update(self) -> None:
        coordinator = self._entry.runtime_data.coordinator
        logged_in = coordinator.cloud_logged_in
        if logged_in and not self._was_logged_in:
            self._was_logged_in = True
            self.async_schedule_update_ha_state(force_refresh=True)
        elif not logged_in and self._was_logged_in:
            self._was_logged_in = False
            self._latest = None
            self.async_write_ha_state()

    def _on_ble_event(self, decoded: dict) -> None:
        """Capture the firmware version from the machine's BLE heartbeat."""
        version = decoded.get("fw_version")
        if not version or version == self._entry.runtime_data.installed_fw_version:
            return
        _LOGGER.debug("xbloom firmware: machine reports installed version %s", version)
        self._entry.runtime_data.installed_fw_version = version
        self.async_write_ha_state()

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
