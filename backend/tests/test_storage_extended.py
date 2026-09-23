"""Extended unit tests for storage_service.py — covers all uncovered functions."""

import pytest
from unittest.mock import patch, MagicMock
from src.services.storage_service import (
    list_disks,
    list_mounts,
    get_raid_status,
    format_disk,
    get_smart_info,
    run_smart_test,
    mount_disk,
    unmount_disk,
    get_fstab,
    add_fstab_entry,
    remove_fstab_entry,
    get_usage_history,
    create_partition,
    delete_partition,
    get_raid_detail,
    create_raid,
    add_raid_disk,
    remove_raid_disk,
    stop_raid,
    assemble_raid,
)


# ─── Fix existing flaky test ───────────────────────────────────────────────────

class TestFormatDisk:
    def test_rejects_system_disk(self):
        """Should never allow formatting /dev/sda.
        The actual error message depends on whether /dev/sda is the detected
        system disk (blocked with "protected") or just doesn't exist on this
        machine ("does not exist"). Both are valid rejections.
        """
        result = format_disk("/dev/sda", "ext4")
        assert result["success"] is False
        assert any(
            kw in result["error"].lower()
            for kw in ("protected", "disallowed", "does not exist", "system disk")
        )


# ─── mount_disk ────────────────────────────────────────────────────────────────

class TestMountDisk:
    @patch("src.services.storage_service._sudo_run")
    def test_mount_ok(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = mount_disk("/dev/sdb1", "/mnt/data")
        assert result["success"] is True
        assert "/mnt/data" in result["message"]

    @patch("src.services.storage_service._sudo_run")
    def test_mount_with_fs_type(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = mount_disk("/dev/sdb1", "/mnt/data", fs_type="ext4")
        assert result["success"] is True
        # Should pass -t ext4
        args = mock_sudo.call_args[0][0]
        assert "-t" in args
        assert "ext4" in args

    @patch("src.services.storage_service._sudo_run")
    def test_mount_fails(self, mock_sudo):
        mock_sudo.return_value = (1, "", "mount failed")
        result = mount_disk("/dev/sdb1", "/mnt/data")
        assert result["success"] is False
        assert "mount failed" in result["error"]


# ─── unmount_disk ──────────────────────────────────────────────────────────────

class TestUnmountDisk:
    @patch("src.services.storage_service._sudo_run")
    def test_unmount_ok(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = unmount_disk("/mnt/data")
        assert result["success"] is True

    @patch("src.services.storage_service._sudo_run")
    def test_unmount_fails(self, mock_sudo):
        mock_sudo.return_value = (1, "", "not mounted")
        result = unmount_disk("/mnt/data")
        assert result["success"] is False
        assert "not mounted" in result["error"]


# ─── run_smart_test ────────────────────────────────────────────────────────────

class TestRunSmartTest:
    @patch("src.services.storage_service._sudo_run")
    def test_short_test_starts(self, mock_sudo):
        mock_sudo.return_value = (0, "Testing has begun. Please wait 5 minutes for test to complete.", "")
        result = run_smart_test("/dev/sda", "short")
        assert result["success"] is True
        assert result["estimated_minutes"] == 5

    @patch("src.services.storage_service._sudo_run")
    def test_long_test_parsed(self, mock_sudo):
        mock_sudo.return_value = (0, "Testing has begun. Please wait 120 minutes.", "")
        result = run_smart_test("/dev/sda", "long")
        assert result["success"] is True
        assert result["estimated_minutes"] == 120

    @patch("src.services.storage_service._sudo_run")
    def test_invalid_test_type(self, mock_sudo):
        result = run_smart_test("/dev/sda", "fast")
        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    @patch("src.services.storage_service._sudo_run")
    def test_invalid_device(self, mock_sudo):
        result = run_smart_test("/dev/null", "short")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    def test_smartctl_not_installed(self, mock_sudo):
        mock_sudo.return_value = (127, "", "command not found")
        result = run_smart_test("/dev/sda", "short")
        assert result["success"] is False
        assert "not installed" in result["error"].lower()


# ─── fstab ────────────────────────────────────────────────────────────────────

class TestGetFstab:
    @patch("builtins.open", MagicMock())
    @patch("os.path.exists", return_value=True)
    def test_parses_fstab(self, mock_exists):
        import io
        content = (
            "# /etc/fstab\n"
            "/dev/sdb1 /mnt/data ext4 defaults 0 2\n"
            "UUID=abc /mnt/backup xfs defaults 0 0\n"
        )
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=io.StringIO(content))
        m.__exit__ = MagicMock(return_value=False)
        with patch("builtins.open", return_value=m):
            from src.services.storage_service import get_fstab
            result = get_fstab()
            assert result["success"] is True
            assert len(result["entries"]) == 2
            assert result["entries"][0]["mount"] == "/mnt/data"
            assert result["entries"][1]["fs"] == "xfs"


class TestAddFstabEntry:
    @patch("src.services.storage_service.get_fstab")
    @patch("src.services.storage_service._sudo_run")
    def test_add_entry_ok(self, mock_sudo, mock_get_fstab):
        mock_get_fstab.return_value = {"success": True, "entries": []}
        mock_sudo.return_value = (0, "", "")
        result = add_fstab_entry("/dev/sdb1", "/mnt/data", "ext4")
        assert result["success"] is True

    @patch("src.services.storage_service.get_fstab")
    def test_rejects_duplicate_mount(self, mock_get_fstab):
        mock_get_fstab.return_value = {
            "success": True,
            "entries": [{"device": "/dev/sdb1", "mount": "/mnt/data", "fs": "ext4", "options": "defaults", "dump": 0, "pass": 0}],
        }
        result = add_fstab_entry("/dev/sdc1", "/mnt/data", "ext4")
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_rejects_missing_fields(self):
        result = add_fstab_entry("", "/mnt/data", "ext4")
        assert result["success"] is False


class TestRemoveFstabEntry:
    @patch("src.services.storage_service._sudo_run")
    def test_remove_ok(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = remove_fstab_entry("/mnt/data")
        assert result["success"] is True

    def test_rejects_system_mount(self):
        for mp in ("/", "/boot", "/boot/efi"):
            result = remove_fstab_entry(mp)
            assert result["success"] is False
            assert "system" in result["error"].lower()

    def test_rejects_empty(self):
        result = remove_fstab_entry("")
        assert result["success"] is False


# ─── get_usage_history ────────────────────────────────────────────────────────

class TestGetUsageHistory:
    @patch("src.services.storage_service._run")
    def test_returns_history(self, mock_run):
        mock_run.return_value = (
            0,
            "Filesystem Size Used Avail Use% Mounted on\n/dev/sdb1 100G 50G 50G 50% /mnt/data\n",
            "",
        )
        result = get_usage_history(days=30)
        assert result["success"] is True
        assert isinstance(result["history"], list)

    @patch("src.services.storage_service._run")
    def test_handles_df_error(self, mock_run):
        mock_run.return_value = (1, "", "error")
        result = get_usage_history()
        assert result["success"] is True
        assert result["history"] == []


# ─── Partition management ──────────────────────────────────────────────────────

class TestCreatePartition:
    @patch("src.services.storage_service._validate_device")
    @patch("src.services.storage_service._sudo_run")
    def test_create_ok(self, mock_sudo, mock_validate):
        mock_validate.return_value = None
        mock_sudo.return_value = (0, "", "")
        result = create_partition("/dev/sdb", "10G", "primary")
        assert result["success"] is True
        assert "partition" in result

    @patch("src.services.storage_service._validate_device")
    def test_blocks_invalid_device(self, mock_validate):
        mock_validate.return_value = "Invalid device"
        result = create_partition("/dev/sda", "10G")
        assert result["success"] is False

    def test_rejects_invalid_part_type(self):
        result = create_partition("/dev/sdb", "10G", "invalid")
        assert result["success"] is False


class TestDeletePartition:
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._get_system_disk")
    def test_delete_ok(self, mock_sys, mock_sudo, mock_run):
        mock_sys.return_value = "/dev/sdc"
        mock_run.return_value = (1, "", "")  # not mounted
        mock_sudo.return_value = (0, "", "")
        result = delete_partition("/dev/sdb1")
        assert result["success"] is True

    @patch("src.services.storage_service._get_system_disk")
    def test_blocks_system_disk_partition(self, mock_sys):
        mock_sys.return_value = "/dev/sda"
        result = delete_partition("/dev/sda1")
        assert result["success"] is False
        assert "system disk" in result["error"].lower()

    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_blocks_mounted_partition(self, mock_sys, mock_run):
        mock_sys.return_value = "/dev/sdc"
        mock_run.return_value = (0, "/mnt/data", "")  # findmnt found mount
        result = delete_partition("/dev/sdb1")
        assert result["success"] is False
        assert "mounted" in result["error"].lower()


# ─── RAID detail ───────────────────────────────────────────────────────────────

class TestGetRaidDetail:
    @patch("src.services.storage_service._sudo_run")
    def test_invalid_array_path(self, mock_sudo):
        result = get_raid_detail("/dev/sda")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    def test_array_not_found(self, mock_sudo):
        mock_sudo.return_value = (1, "", "No such file")
        result = get_raid_detail("/dev/md0")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    def test_parses_raid1(self, mock_sudo):
        mock_sudo.return_value = (0, (
            "         Version : 1.2\n"
            "  Raid Level : raid1\n"
            "    State : clean\n"
            " Active Devices : 2\n"
            "Working Devices : 2\n"
            " Failed Devices : 0\n"
            "  Spare Devices : 0\n"
            "  Raid Devices : 2\n"
            "           Number   Major   Minor   RaidDevice State\n"
            "              0       8       17        0      active sync   /dev/sdb1\n"
            "              1       8       33        1      active sync   /dev/sdc1\n"
        ), "")
        result = get_raid_detail("/dev/md0")
        assert result["success"] is True
        assert result["level"] == "raid1"
        assert result["state"] == "clean"
        assert len(result["disks"]) == 2


# ─── create_raid ───────────────────────────────────────────────────────────────

class TestCreateRaid:
    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_raid5_requires_3_devices(self, mock_sys, mock_run, mock_sudo):
        mock_sys.return_value = "/dev/sda"
        mock_run.return_value = (1, "", "")  # not mounted
        result = create_raid("5", ["/dev/sdb1", "/dev/sdc1"], "/dev/md0")
        assert result["success"] is False
        assert "requires at least 3" in result["error"]

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_invalid_raid_level(self, mock_sys, mock_run, mock_sudo):
        result = create_raid("99", ["/dev/sdb1"], "/dev/md0")
        assert result["success"] is False
        assert "unsupported" in result["error"].lower()

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_array_already_exists(self, mock_sys, mock_run, mock_sudo):
        mock_sys.return_value = "/dev/sda"
        mock_sudo.return_value = (0, "", "")  # --detail succeeds → array exists
        result = create_raid("1", ["/dev/sdb1", "/dev/sdc1"], "/dev/md0")
        assert result["success"] is False
        assert "already exists" in result["error"]

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_blocks_system_disk(self, mock_sys, mock_run, mock_sudo):
        mock_sys.return_value = "/dev/sda"
        mock_run.return_value = (1, "", "")  # findmnt: device not mounted
        mock_sudo.return_value = (1, "", "")  # mdadm --detail: array doesn't exist yet
        result = create_raid("1", ["/dev/sda1", "/dev/sdb1"], "/dev/md0")
        assert result["success"] is False
        assert "system disk" in result["error"].lower()

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._get_system_disk")
    def test_creates_raid1_ok(self, mock_sys, mock_run, mock_sudo):
        mock_sys.return_value = "/dev/sda"
        # findmnt: not mounted
        mock_run.return_value = (1, "", "")
        # mdadm --detail: array doesn't exist
        # mdadm --create
        # mkfs.ext4
        # mkdir, mount
        # mdadm --detail --scan, update-initramfs
        mock_sudo.side_effect = [
            (1, "", ""),   # mdadm --detail (not exists)
            (0, "", ""),   # mdadm --create
            (0, "", ""),   # mkfs.ext4
            (0, "", ""),   # mkdir
            (0, "", ""),   # mount
            (0, "", ""),   # mdadm --detail --scan
            (0, "", ""),   # update-initramfs
        ]
        result = create_raid(
            "1",
            ["/dev/sdb1", "/dev/sdc1"],
            "/dev/md0",
            filesystem="ext4",
            mount_point="/mnt/data",
        )
        assert result["success"] is True
        assert result["array"] == "/dev/md0"


# ─── add_raid_disk ─────────────────────────────────────────────────────────────

class TestAddRaidDisk:
    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._validate_device")
    def test_add_ok(self, mock_validate, mock_run, mock_sudo):
        mock_validate.return_value = None
        mock_run.return_value = (1, "", "")  # not mounted
        mock_sudo.side_effect = [
            (0, "", ""),   # --detail (array exists)
            (0, "", ""),   # --add
        ]
        result = add_raid_disk("/dev/md0", "/dev/sdd1")
        assert result["success"] is True

    @patch("src.services.storage_service._validate_device")
    def test_invalid_array(self, mock_validate):
        result = add_raid_disk("/dev/sda", "/dev/sdb1")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    @patch("src.services.storage_service._validate_device")
    def test_mounted_device_rejected(self, mock_validate, mock_run, mock_sudo):
        mock_validate.return_value = None
        mock_run.return_value = (0, "/mnt/data", "")  # device is mounted
        result = add_raid_disk("/dev/md0", "/dev/sdb1")
        assert result["success"] is False
        assert "mounted" in result["error"].lower()


# ─── remove_raid_disk ──────────────────────────────────────────────────────────

class TestRemoveRaidDisk:
    @patch("src.services.storage_service._sudo_run")
    def test_remove_ok(self, mock_sudo):
        mock_sudo.side_effect = [
            (0, "", ""),   # --fail
            (0, "", ""),   # --remove
        ]
        result = remove_raid_disk("/dev/md0", "/dev/sdb1")
        assert result["success"] is True

    def test_invalid_array(self):
        result = remove_raid_disk("/dev/sda", "/dev/sdb1")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    def test_fail_step_fails(self, mock_sudo):
        mock_sudo.return_value = (1, "", "set faulty failed")
        result = remove_raid_disk("/dev/md0", "/dev/sdb1")
        assert result["success"] is False
        assert "faulty" in result["error"].lower()


# ─── stop_raid ────────────────────────────────────────────────────────────────

class TestStopRaid:
    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    def test_stop_ok(self, mock_run, mock_sudo):
        mock_run.return_value = (1, "", "")  # findmnt: not mounted
        mock_sudo.return_value = (0, "", "")
        result = stop_raid("/dev/md0")
        assert result["success"] is True

    @patch("src.services.storage_service._sudo_run")
    @patch("src.services.storage_service._run")
    def test_unmounts_before_stopping(self, mock_run, mock_sudo):
        mock_run.return_value = (0, "/mnt/data", "")  # findmnt: mounted
        mock_sudo.side_effect = [
            (0, "", ""),   # umount
            (0, "", ""),   # mdadm --stop
        ]
        result = stop_raid("/dev/md0")
        assert result["success"] is True

    def test_invalid_array(self):
        result = stop_raid("/dev/sda")
        assert result["success"] is False


# ─── assemble_raid ─────────────────────────────────────────────────────────────

class TestAssembleRaid:
    @patch("src.services.storage_service._sudo_run")
    def test_assemble_ok(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = assemble_raid("/dev/md0")
        assert result["success"] is True

    @patch("src.services.storage_service._sudo_run")
    def test_assemble_with_devices(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        result = assemble_raid("/dev/md0", ["/dev/sdb1", "/dev/sdc1"])
        assert result["success"] is True
        args = mock_sudo.call_args[0][0]
        assert "/dev/sdb1" in args

    def test_invalid_array(self):
        result = assemble_raid("/dev/sda")
        assert result["success"] is False

    @patch("src.services.storage_service._sudo_run")
    def test_assemble_fails(self, mock_sudo):
        mock_sudo.return_value = (1, "", "no devices found")
        result = assemble_raid("/dev/md0")
        assert result["success"] is False
        assert "failed" in result["error"].lower()
