#!/bin/bash
# ProTech NAS — System Disk RAID 1 (HA) Setup
# 將兩顆 HDD 設定為 RAID 1 鏡像，確保任一顆故障仍可開機
#
# ⚠ 警告：此腳本用於「全新安裝」時設定 RAID 1 系統碟。
#    若系統已安裝在單碟上，請使用 migrate-to-raid1.sh 進行線上遷移。
#
# 使用情境：
#   - 2 顆 HDD → 自動建立 RAID 1 鏡像（HA）
#   - 1 顆 HDD → 跳過，直接單碟使用
#
# 前置條件：
#   - Debian 12 / Ubuntu 22.04+
#   - mdadm 已安裝
#   - 兩顆 HDD 大小相近
#
set -e

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Auto-detect available non-system HDDs
detect_available_disks() {
    local system_disk
    system_disk=$(lsblk -no PKNAME $(findmnt -n -o SOURCE /) 2>/dev/null | head -1)

    local available=()
    for disk in $(lsblk -d -n -o NAME,TYPE | awk '$2=="disk"{print $1}'); do
        # Skip system disk, loop devices, and small devices (<10G)
        if [ "$disk" = "$system_disk" ]; then
            continue
        fi
        local size_bytes
        size_bytes=$(lsblk -b -d -n -o SIZE "/dev/$disk" 2>/dev/null || echo 0)
        if [ "$size_bytes" -gt 10737418240 ]; then  # > 10GB
            available+=("/dev/$disk")
        fi
    done
    echo "${available[@]}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

echo "╔══════════════════════════════════════════════════╗"
echo "║  ProTech NAS — System Disk HA (RAID 1) Setup     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "✗ This script must be run as root."
    exit 1
fi

# Check mdadm
if ! command -v mdadm &>/dev/null; then
    echo "Installing mdadm..."
    apt update && apt install -y mdadm
fi

# Detect disks
echo "[1/5] Detecting available HDDs..."
AVAILABLE_DISKS=($(detect_available_disks))
DISK_COUNT=${#AVAILABLE_DISKS[@]}

echo "  System disk: $(lsblk -no PKNAME $(findmnt -n -o SOURCE /) 2>/dev/null | head -1)"
echo "  Available data disks: ${AVAILABLE_DISKS[*]:-none}"
echo "  Count: $DISK_COUNT"
echo ""

if [ "$DISK_COUNT" -lt 2 ]; then
    echo "══════════════════════════════════════════════════════"
    echo "  Only $DISK_COUNT data disk(s) detected."
    echo "  RAID 1 (HA) requires at least 2 disks."
    echo "  → Skipping RAID setup. Using single disk mode."
    echo "══════════════════════════════════════════════════════"
    echo ""
    echo "Available disk(s) can be used as standalone data storage."
    echo "You can re-run this script after adding a second HDD."
    exit 0
fi

# Two disks available — proceed with RAID 1
DISK1="${AVAILABLE_DISKS[0]}"
DISK2="${AVAILABLE_DISKS[1]}"

echo "[2/5] Setting up RAID 1 mirror..."
echo "  Disk 1: $DISK1 ($(lsblk -d -n -o SIZE $DISK1))"
echo "  Disk 2: $DISK2 ($(lsblk -d -n -o SIZE $DISK2))"
echo ""

# Confirm
read -p "  ⚠ ALL DATA on $DISK1 and $DISK2 will be ERASED. Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "  Aborted."
    exit 1
fi

# Check if disks are mounted
for disk in "$DISK1" "$DISK2"; do
    mounts=$(lsblk -n -o MOUNTPOINT "$disk" | grep -v "^$" || true)
    if [ -n "$mounts" ]; then
        echo "  Unmounting partitions on $disk..."
        for mp in $mounts; do
            umount "$mp" 2>/dev/null || true
        done
    fi
done

# Wipe existing RAID superblocks and partition tables
echo "  Wiping disk signatures..."
for disk in "$DISK1" "$DISK2"; do
    mdadm --zero-superblock "$disk" 2>/dev/null || true
    wipefs -a "$disk" 2>/dev/null || true
    dd if=/dev/zero of="$disk" bs=1M count=10 2>/dev/null || true
done

# Create partitions (GPT)
echo "  Creating partitions..."
for disk in "$DISK1" "$DISK2"; do
    parted -s "$disk" mklabel gpt
    parted -s "$disk" mkpart primary 1MiB 100%
    parted -s "$disk" set 1 raid on
done

# Wait for kernel to recognize new partitions
sleep 2
partprobe "$DISK1" "$DISK2" 2>/dev/null || true
sleep 1

PART1="${DISK1}1"
PART2="${DISK2}1"

# Handle NVMe naming (p1 instead of 1)
if [[ "$DISK1" == *nvme* ]]; then PART1="${DISK1}p1"; fi
if [[ "$DISK2" == *nvme* ]]; then PART2="${DISK2}p1"; fi

echo ""
echo "[3/5] Creating RAID 1 array (md0)..."
mdadm --create /dev/md0 \
    --level=1 \
    --raid-devices=2 \
    --metadata=1.2 \
    "$PART1" "$PART2"

echo "  Waiting for initial sync to start..."
sleep 3
cat /proc/mdstat

# Format RAID array
echo ""
echo "[4/5] Formatting RAID array as ext4..."
mkfs.ext4 -F -L "nas-data" /dev/md0

# Mount
MOUNT_POINT="/mnt/nas-data"
mkdir -p "$MOUNT_POINT"
mount /dev/md0 "$MOUNT_POINT"

# Add to fstab
if ! grep -q "/dev/md0" /etc/fstab; then
    echo "/dev/md0  $MOUNT_POINT  ext4  defaults,nofail  0  2" >> /etc/fstab
fi

# Save RAID config
mdadm --detail --scan >> /etc/mdadm/mdadm.conf 2>/dev/null || \
mdadm --detail --scan >> /etc/mdadm.conf 2>/dev/null || true
update-initramfs -u 2>/dev/null || true

echo ""
echo "[5/5] RAID 1 setup complete!"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ RAID 1 (HA) Active                                   ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Array:      /dev/md0                                    ║"
echo "║  Mount:      $MOUNT_POINT                                ║"
echo "║  Disks:      $DISK1 + $DISK2                             ║"
echo "║  Status:     Syncing (background)                        ║"
echo "║                                                          ║"
echo "║  If one disk fails:                                      ║"
echo "║    - System continues running on remaining disk          ║"
echo "║    - Replace failed disk and rebuild:                    ║"
echo "║      mdadm --add /dev/md0 /dev/sdX1                     ║"
echo "║                                                          ║"
echo "║  Monitor:                                                ║"
echo "║    cat /proc/mdstat                                      ║"
echo "║    mdadm --detail /dev/md0                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Sync progress:"
cat /proc/mdstat | grep -A2 "md0"
