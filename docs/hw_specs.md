# Intel N100 NAS 硬體規格

## CPU — Intel Processor N100

| 項目 | 規格 |
|------|------|
| 核心/執行緒 | 4C / 4T |
| 基礎頻率 | 1.0 GHz |
| 最大 Boost | 3.4 GHz |
| TDP | 6W |
| 製程 | Intel 7 (10nm) |
| 快取 | 6MB L3 |
| 內顯 | Intel UHD Graphics (24 EU) |
| 支援記憶體 | DDR4-3200 / DDR5-4800 |
| 最大記憶體 | 16GB (單通道) |
| PCIe | PCIe 3.0 x9 |

## 建議硬體配置

| 元件 | 建議規格 | 用途 |
|------|---------|------|
| 主機板 | Mini-ITX N100 (如 CWWK / Topton) | 含 4x SATA or 2x M.2 |
| 記憶體 | 16GB DDR4 SO-DIMM | NAS + Docker 運行 |
| 系統碟 | 256GB NVMe M.2 | OS + App |
| 資料碟 | 2-4x HDD (4TB+) | RAID 儲存 |
| 網路 | 2.5GbE x2 (Intel i226-V) | 高速傳輸 |
| 機殼 | NAS 專用 4-bay 機殼 | 散熱 + 硬碟安裝 |
| 電源 | 12V DC 或 FlexATX 200W | 低功耗供電 |

## 功耗估算

| 狀態 | 功耗 |
|------|------|
| 待機 (HDD 休眠) | ~8W |
| 一般使用 | ~15W |
| 滿載 (轉碼/RAID重建) | ~25W |
| 年度電費 (24/7, 15W avg, $5/kWh) | ~$660 TWD |

## 效能參考

- SMB 連續讀取：~280 MB/s (2.5GbE)
- Docker 容器：可同時跑 10+ 輕量容器
- 硬體轉碼：Intel QSV 支援 H.264/H.265 (Plex/Jellyfin)
- RAID 5 寫入：~150 MB/s (4x HDD)

## 相容 OS

- Debian 12 ✅
- Ubuntu Server 24.04 ✅
- Proxmox VE ✅
- TrueNAS SCALE ✅
