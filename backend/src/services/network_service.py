"""Network service — network interface management."""

import subprocess
import json


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def list_interfaces() -> dict:
    """List all network interfaces with IP, MAC, status, and speed.

    Returns:
        {
            "success": bool,
            "interfaces": list[{
                "name": str,
                "mac": str,
                "ipv4": str | None,
                "ipv6": str | None,
                "status": "up" | "down",
                "speed_mbps": int | None,
                "mtu": int
            }]
        }
    """
    rc, out, err = _run(["ip", "-j", "addr", "show"])
    if rc != 0:
        return {"success": False, "error": f"ip command failed: {err.strip()}"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse ip output"}

    interfaces = []
    for iface in data:
        name = iface.get("ifname", "")

        # Skip loopback
        if name == "lo":
            continue

        mac = iface.get("address", "")
        mtu = iface.get("mtu", 0)
        status = "up" if iface.get("operstate", "").upper() == "UP" else "down"

        # Extract IPv4 and IPv6
        ipv4 = None
        ipv6 = None
        for addr_info in iface.get("addr_info", []):
            family = addr_info.get("family", "")
            local = addr_info.get("local", "")
            prefixlen = addr_info.get("prefixlen", "")
            if family == "inet" and not ipv4:
                ipv4 = f"{local}/{prefixlen}" if prefixlen else local
            elif family == "inet6" and not ipv6:
                # Skip link-local unless no other IPv6
                if not local.startswith("fe80"):
                    ipv6 = f"{local}/{prefixlen}" if prefixlen else local
                elif ipv6 is None:
                    ipv6 = f"{local}/{prefixlen}" if prefixlen else local

        # Get speed
        speed_mbps = _get_interface_speed(name)

        interfaces.append({
            "name": name,
            "mac": mac,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "status": status,
            "speed_mbps": speed_mbps,
            "mtu": mtu,
        })

    return {"success": True, "interfaces": interfaces}


def _get_interface_speed(name: str) -> int | None:
    """Read interface speed from /sys/class/net/{name}/speed."""
    try:
        speed = int(open(f"/sys/class/net/{name}/speed").read().strip())
        # -1 means unknown (e.g. interface is down)
        return speed if speed > 0 else None
    except (FileNotFoundError, ValueError, OSError):
        return None


import re
import time
import ipaddress


def configure_interface(name: str, config: dict) -> dict:
    """Configure a network interface (IP/DHCP/DNS/gateway).

    Args:
        name: Interface name (e.g. "eth0").
        config: {
            "method": "dhcp" | "static",
            "ip": "192.168.1.100/24",   # required if static
            "gateway": "192.168.1.1",    # optional
            "dns": ["8.8.8.8", "1.1.1.1"]  # optional
        }

    Returns:
        {"success": bool, "message": str}

    WARNING: Incorrect configuration may cause network loss.
    """
    method = config.get("method", "dhcp")
    if method not in ("dhcp", "static"):
        return {"success": False, "error": f"Invalid method: {method}"}

    # Validate interface exists
    rc, _, _ = _run(["ip", "link", "show", name])
    if rc != 0:
        return {"success": False, "error": f"Interface {name} not found"}

    if method == "static":
        ip_addr = config.get("ip", "")
        if not ip_addr:
            return {"success": False, "error": "IP address required for static configuration"}
        try:
            ipaddress.ip_interface(ip_addr)
        except ValueError:
            return {"success": False, "error": f"Invalid IP address: {ip_addr}"}

        gateway = config.get("gateway", "")
        if gateway:
            try:
                ipaddress.ip_address(gateway)
            except ValueError:
                return {"success": False, "error": f"Invalid gateway: {gateway}"}

        dns_list = config.get("dns", [])
        for d in dns_list:
            try:
                ipaddress.ip_address(d)
            except ValueError:
                return {"success": False, "error": f"Invalid DNS: {d}"}

    # Detect Netplan or ifupdown
    import os
    if os.path.isdir("/etc/netplan"):
        return _configure_netplan(name, config)
    else:
        return _configure_ifupdown(name, config)


def _configure_netplan(name: str, config: dict) -> dict:
    """Write Netplan config."""
    import yaml
    from pathlib import Path

    method = config.get("method", "dhcp")
    netplan_file = Path(f"/etc/netplan/60-protech-{name}.yaml")

    if method == "dhcp":
        netplan_config = {
            "network": {
                "version": 2,
                "ethernets": {
                    name: {"dhcp4": True}
                }
            }
        }
    else:
        eth_config = {
            "dhcp4": False,
            "addresses": [config["ip"]],
        }
        if config.get("gateway"):
            eth_config["routes"] = [{"to": "default", "via": config["gateway"]}]
        if config.get("dns"):
            eth_config["nameservers"] = {"addresses": config["dns"]}

        netplan_config = {
            "network": {
                "version": 2,
                "ethernets": {name: eth_config}
            }
        }

    try:
        netplan_file.write_text(yaml.dump(netplan_config, default_flow_style=False))
        rc, _, err = _run(["netplan", "apply"], timeout=15)
        if rc != 0:
            return {"success": False, "error": f"netplan apply failed: {err.strip()}"}
        return {"success": True, "message": f"Interface {name} configured via Netplan"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _configure_ifupdown(name: str, config: dict) -> dict:
    """Write /etc/network/interfaces.d/ config."""
    from pathlib import Path

    method = config.get("method", "dhcp")
    conf_file = Path(f"/etc/network/interfaces.d/{name}")

    if method == "dhcp":
        content = f"auto {name}\niface {name} inet dhcp\n"
    else:
        ip_parts = config["ip"].split("/")
        address = ip_parts[0]
        prefix = ip_parts[1] if len(ip_parts) > 1 else "24"

        content = f"auto {name}\niface {name} inet static\n"
        content += f"    address {address}/{prefix}\n"
        if config.get("gateway"):
            content += f"    gateway {config['gateway']}\n"
        if config.get("dns"):
            content += f"    dns-nameservers {' '.join(config['dns'])}\n"

    try:
        conf_file.write_text(content)
        _run(["ifdown", name], timeout=5)
        rc, _, err = _run(["ifup", name], timeout=15)
        if rc != 0:
            return {"success": False, "error": f"ifup failed: {err.strip()}"}
        return {"success": True, "message": f"Interface {name} configured via ifupdown"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Firewall ─────────────────────────────────────────────────────────────────

def list_firewall_rules() -> dict:
    """List iptables firewall rules.

    Returns:
        {"success": bool, "rules": list[dict]}
    """
    rc, out, err = _run(["iptables", "-L", "INPUT", "-n", "--line-numbers", "-v"])
    if rc != 0:
        return {"success": False, "error": f"iptables failed: {err.strip()}"}

    rules = []
    lines = out.strip().split("\n")
    for line in lines[2:]:  # Skip headers
        parts = line.split()
        if len(parts) >= 9:
            rules.append({
                "id": parts[0],
                "packets": parts[1],
                "bytes": parts[2],
                "target": parts[3],
                "protocol": parts[4],
                "opt": parts[5],
                "source": parts[7],
                "destination": parts[8],
                "extra": " ".join(parts[9:]) if len(parts) > 9 else "",
            })

    return {"success": True, "rules": rules}


def add_firewall_rule(rule: dict) -> dict:
    """Add an iptables firewall rule.

    Args:
        rule: {"chain": "INPUT", "protocol": "tcp", "port": 443, "source": "0.0.0.0/0", "target": "ACCEPT"}
    """
    chain = rule.get("chain", "INPUT")
    protocol = rule.get("protocol", "tcp")
    port = rule.get("port")
    source = rule.get("source", "0.0.0.0/0")
    target = rule.get("target", "ACCEPT")

    if chain not in ("INPUT", "OUTPUT", "FORWARD"):
        return {"success": False, "error": f"Invalid chain: {chain}"}
    if protocol not in ("tcp", "udp", "icmp"):
        return {"success": False, "error": f"Invalid protocol: {protocol}"}
    if target not in ("ACCEPT", "DROP", "REJECT"):
        return {"success": False, "error": f"Invalid target: {target}"}
    if port and (not isinstance(port, int) or port < 1 or port > 65535):
        return {"success": False, "error": f"Invalid port: {port}"}

    cmd = ["iptables", "-A", chain, "-p", protocol, "-s", source]
    if port:
        cmd += ["--dport", str(port)]
    cmd += ["-j", target]

    rc, _, err = _run(cmd)
    if rc != 0:
        return {"success": False, "error": f"iptables failed: {err.strip()}"}
    return {"success": True, "message": "Rule added"}


def delete_firewall_rule(rule_id: int, chain: str = "INPUT") -> dict:
    """Delete an iptables rule by line number.

    Args:
        rule_id: Line number from list_firewall_rules.
        chain: Chain name.
    """
    if chain not in ("INPUT", "OUTPUT", "FORWARD"):
        return {"success": False, "error": f"Invalid chain: {chain}"}

    rc, _, err = _run(["iptables", "-D", chain, str(rule_id)])
    if rc != 0:
        return {"success": False, "error": f"iptables delete failed: {err.strip()}"}
    return {"success": True, "message": f"Rule {rule_id} deleted from {chain}"}


# ─── Realtime Network Stats ──────────────────────────────────────────────────

def get_realtime_stats(interval: float = 1.0) -> dict:
    """Get real-time network speed per interface (bytes/sec).

    Args:
        interval: Sampling interval in seconds (default 1.0).

    Returns:
        {"success": bool, "interfaces": list[{"name": str, "rx_bytes_per_sec": int, "tx_bytes_per_sec": int}]}
    """
    import os

    def read_stats():
        stats = {}
        net_dir = "/sys/class/net"
        try:
            for iface in os.listdir(net_dir):
                if iface == "lo":
                    continue
                try:
                    rx = int(open(f"{net_dir}/{iface}/statistics/rx_bytes").read().strip())
                    tx = int(open(f"{net_dir}/{iface}/statistics/tx_bytes").read().strip())
                    stats[iface] = {"rx": rx, "tx": tx}
                except (FileNotFoundError, ValueError):
                    continue
        except FileNotFoundError:
            pass
        return stats

    stats1 = read_stats()
    time.sleep(min(interval, 3.0))  # Cap at 3 seconds
    stats2 = read_stats()

    interfaces = []
    for name in stats2:
        if name in stats1:
            rx_per_sec = int((stats2[name]["rx"] - stats1[name]["rx"]) / interval)
            tx_per_sec = int((stats2[name]["tx"] - stats1[name]["tx"]) / interval)
            interfaces.append({
                "name": name,
                "rx_bytes_per_sec": max(rx_per_sec, 0),
                "tx_bytes_per_sec": max(tx_per_sec, 0),
            })

    return {"success": True, "interfaces": interfaces}


# ─── Network Diagnostics ─────────────────────────────────────────────────────

import socket
import struct as _struct


def ping(host: str, count: int = 4) -> dict:
    """Execute ping test.

    Args:
        host: Target hostname or IP.
        count: Number of pings (1-20).

    Returns:
        {"success": bool, "host": str, "packets_sent": int, "packets_received": int, "avg_ms": float, "output": str}
    """
    if not host or not re.match(r"^[a-zA-Z0-9\-._]+$", host):
        return {"success": False, "error": f"Invalid host: {host}"}
    count = max(1, min(count, 20))

    rc, out, err = _run(["ping", "-c", str(count), "-W", "3", host], timeout=count * 5 + 5)

    # Parse results
    packets_sent = count
    packets_received = 0
    avg_ms = 0.0

    for line in out.split("\n"):
        if "packets transmitted" in line:
            parts = line.split(",")
            for p in parts:
                p = p.strip()
                if "received" in p:
                    try:
                        packets_received = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass
        if "avg" in line and "/" in line:
            # rtt min/avg/max/mdev = 1.234/5.678/9.012/1.234 ms
            try:
                stats = line.split("=")[1].strip().split("/")
                avg_ms = float(stats[1])
            except (IndexError, ValueError):
                pass

    return {
        "success": True,
        "host": host,
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "avg_ms": avg_ms,
        "output": out,
    }


def traceroute(host: str) -> dict:
    """Execute traceroute.

    Args:
        host: Target hostname or IP.

    Returns:
        {"success": bool, "hops": list[dict], "output": str}
    """
    if not host or not re.match(r"^[a-zA-Z0-9\-._]+$", host):
        return {"success": False, "error": f"Invalid host: {host}"}

    rc, out, err = _run(["traceroute", "-n", "-m", "20", "-w", "2", host], timeout=60)

    if rc == 127:
        return {"success": False, "error": "traceroute not installed"}

    hops = []
    for line in out.strip().split("\n")[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 2:
            hop_num = parts[0]
            ip = parts[1] if parts[1] != "*" else "*"
            rtt = 0.0
            for p in parts[2:]:
                try:
                    rtt = float(p)
                    break
                except ValueError:
                    continue
            hops.append({"hop": int(hop_num) if hop_num.isdigit() else 0, "ip": ip, "rtt_ms": rtt})

    return {"success": True, "hops": hops, "output": out}


def dns_lookup(domain: str, record_type: str = "A") -> dict:
    """Perform DNS lookup.

    Args:
        domain: Domain to query.
        record_type: Record type (A, AAAA, MX, CNAME, TXT, NS).

    Returns:
        {"success": bool, "domain": str, "records": list[str], "server": str}
    """
    if not domain or not re.match(r"^[a-zA-Z0-9\-._]+$", domain):
        return {"success": False, "error": f"Invalid domain: {domain}"}

    valid_types = ("A", "AAAA", "MX", "CNAME", "TXT", "NS", "SOA", "PTR")
    record_type = record_type.upper()
    if record_type not in valid_types:
        return {"success": False, "error": f"Invalid record type: {record_type}. Allowed: {', '.join(valid_types)}"}

    rc, out, err = _run(["dig", "+short", "+time=5", domain, record_type])
    if rc == 127:
        return {"success": False, "error": "dig not installed (install dnsutils)"}

    records = [line.strip() for line in out.strip().split("\n") if line.strip()]

    # Get server
    rc2, out2, _ = _run(["dig", "+short", "+time=5", domain, record_type, "+stats"])
    server = ""
    for line in (out2 or "").split("\n"):
        if "SERVER:" in line:
            server = line.split("SERVER:")[1].strip()
            break

    return {"success": True, "domain": domain, "records": records, "server": server}


def send_wol(mac: str) -> dict:
    """Send Wake-on-LAN magic packet.

    Args:
        mac: Target MAC address (format XX:XX:XX:XX:XX:XX).

    Returns:
        {"success": bool, "message": str}
    """
    # Validate MAC format
    if not mac or not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
        return {"success": False, "error": f"Invalid MAC address format: {mac}. Expected XX:XX:XX:XX:XX:XX"}

    # Build magic packet
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    # Send via UDP broadcast
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, ("255.255.255.255", 9))
        sock.close()
        return {"success": True, "message": f"WOL packet sent to {mac}"}
    except OSError as e:
        return {"success": False, "error": f"Failed to send WOL: {str(e)}"}
