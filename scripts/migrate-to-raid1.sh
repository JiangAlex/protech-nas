#!/bin/bash
# ProTech NAS — Migrate Running System to RAID 1 (Boot Mirror)
# 將目前單碟的系統碟線上遷移為 RAID 1，實現開機 HA
#
# 原理：
#   1. 在第二顆 HDD 建立降級 RAID 1 (只有一個成員)
#   2. 複製系統到 RAID 上
#   3. 安裝 GRUB 到兩顆碟
#   4. 將原始碟加入 RAID 完成鏡像
#
# ⚠ 高風險操作 — 請先備份重要資料！
#
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ProTech NAS — System Disk Migration to RAID 1 (HA)      ║"
echo "║                                                          ║"
echo "║  ⚠ WARNING: This modifies your boot disk!               ║"
echo "║     Please ensure you have a backup before proceeding.   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "✗ Must run as root."
    exit 1
fi

# ─── Detect current system ────────────────────────────────────────────────────

ROOT_SOURCE=$(findmnt -n -o SOURCE /)
ROOT_DISK=$(lsblk -no PKNAME "$ROOT_SOURCE" | head -1)

echo "Current system:"
echo "  Root partition: $ROOT_SOURCE"
echo "  System disk:    /dev/$ROOT_DISK"
echo ""

# Find second disk
SECOND_DISK=""
for disk in $(lsblk -d -n -o NAME,TYPE | awk '$2=="disk"{print $1}'); do
    if [ "$disk" != "$ROOT_DISK" ]; then
        size_bytes=$(lsblk -b -d -n -o SIZE "/dev/$disk" 2>/dev/null || echo 0)
        if [ "$size_bytes" -gt 10737418240 ]; then
            SECOND_DISK="/dev/$disk"
            break
        fi
    fi
done

if [ -z "$SECOND_DISK" ]; then
    echo "✗ No second disk found for RAID 1 mirror."
    echo "  Available disks:"
    lsblk -d -o NAME,SIZE,TYPE,MODEL
    exit 1
fi

echo "Second disk found: $SECOND_DISK ($(lsblk -d -n -o SIZE $SECOND_DISK))"
echo ""
echo "Plan:"
echo "  1. Clone partition layout from /dev/$ROOT_DISK to $SECOND_DISK"
echo "  2. Create degraded RAID 1 with $SECOND_DISK"
echo "  3. Copy system files to RAID"
echo "  4. Install GRUB on both disks"
echo "  5. Add /dev/$ROOT_DISK to complete the mirror"
echo ""

read -p "⚠ This will ERASE $SECOND_DISK. Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo " This is a complex migration. For production use,"
echo " we recommend a fresh install with RAID 1 using:"
echo "   sudo bash scripts/setup-raid1-ha.sh"
echo ""
echo " For a live migration guide, see:"
echo "   docs/raid1-migration.md"
echo "═══════════════════════════════════════════════════"
echo ""
echo "The automated live migration is not yet implemented"
echo "due to the high risk of data loss. Please use the"
echo "data disk RAID 1 setup (setup-raid1-ha.sh) for now."
echo ""
echo "Alternatively, reinstall the OS with RAID 1 from"
echo "the installer (Debian/Ubuntu support mdadm RAID"
echo "during installation)."
