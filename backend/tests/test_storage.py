"""Tests for storage service functions."""

import pytest
from src.services.storage_service import (
    list_disks,
    list_mounts,
    get_raid_status,
    format_disk,
    get_smart_info,
)


class TestListDisks:
    def test_returns_success(self):
        result = list_disks()
        assert result["success"] is True
        assert "devices" in result

    def test_devices_is_list(self):
        result = list_disks()
        assert isinstance(result["devices"], list)


class TestListMounts:
    def test_returns_success(self):
        result = list_mounts()
        assert result["success"] is True
        assert "mounts" in result

    def test_mounts_have_fields(self):
        result = list_mounts()
        if result["mounts"]:
            mount = result["mounts"][0]
            assert "device" in mount
            assert "mount_point" in mount


class TestGetRaidStatus:
    def test_returns_success(self):
        result = get_raid_status()
        assert result["success"] is True
        assert "mdstat" in result


class TestFormatDisk:
    def test_rejects_system_disk(self):
        """Should never allow formatting /dev/sda."""
        result = format_disk("/dev/sda", "ext4")
        assert result["success"] is False
        assert "protected" in result["error"].lower() or "disallowed" in result["error"].lower()

    def test_rejects_sda1(self):
        result = format_disk("/dev/sda1", "ext4")
        assert result["success"] is False

    def test_rejects_invalid_fs(self):
        result = format_disk("/dev/sdb1", "ntfs")
        assert result["success"] is False
        assert "unsupported" in result["error"].lower()

    def test_rejects_empty_device(self):
        result = format_disk("", "ext4")
        assert result["success"] is False

    def test_accepts_exfat_fs_type(self):
        """exFAT should be in the supported list (even if device doesn't exist)."""
        result = format_disk("/dev/sdb1", "exfat")
        # Will fail because device doesn't exist, but should NOT fail on fs_type validation
        assert "unsupported" not in result.get("error", "").lower()


class TestGetSmartInfo:
    def test_rejects_invalid_device(self):
        """Invalid device path should be rejected."""
        result = get_smart_info("/etc/passwd")
        assert result["success"] is False
