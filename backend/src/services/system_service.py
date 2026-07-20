"""System service — collects system info via psutil."""

import platform
import time
import psutil


def get_system_info() -> dict:
    """Get system overview: CPU, RAM, disk, network, uptime."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    # Memory
    mem = psutil.virtual_memory()

    # Disk usage (root partition)
    disk = psutil.disk_usage("/")

    # Network I/O
    net = psutil.net_io_counters()

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else 0,
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
        },
        "uptime": f"{days}d {hours}h {minutes}m",
        "uptime_seconds": uptime_seconds,
    }
