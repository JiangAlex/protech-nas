"""Printer service — manage USB printers shared over the network via CUPS/IPP.

Wraps the CUPS command-line tools:
  - lpstat   : list configured printers and job queues
  - lpinfo   : discover connected (e.g. USB) printers and available drivers
  - lpadmin  : add / remove / configure printers (requires root)
  - cupsenable / cupsaccept : enable a printer and accept jobs (requires root)
  - lp       : submit a test page
  - cancel   : cancel a print job

Sharing model: a printer added here is configured with
``printer-is-shared=true`` so CUPS exposes it over IPP on port 631 to the
local network (also usable as AirPrint / IPP Everywhere).
"""

import re
import subprocess

# CUPS printer/class names allow letters, digits, underscore, hyphen and dot,
# but NOT space, slash or '#'. We enforce a conservative allowlist to avoid
# command injection since names flow into privileged commands.
_PRINTER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]} (is CUPS installed?)"
    except Exception as e:  # pragma: no cover - defensive
        return -1, "", str(e)


def _sudo_run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command with sudo and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]} (is CUPS installed?)"
    except Exception as e:  # pragma: no cover - defensive
        return -1, "", str(e)


def _valid_name(name: str) -> bool:
    """Validate a CUPS printer name against the allowlist."""
    return bool(name) and bool(_PRINTER_NAME_PATTERN.match(name))


# ─── Discovery ────────────────────────────────────────────────────────────────

def discover_printers() -> dict:
    """Discover connected printer devices (USB, network) via ``lpinfo -v``.

    Returns candidate device URIs that can be used when adding a printer.
    Only direct/USB style devices are the primary target here.
    """
    rc, out, err = _run(["lpinfo", "-v"])
    if rc != 0:
        return {"success": False, "error": err.strip() or "lpinfo failed"}

    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "<class> <device-uri>", e.g. "direct usb://EPSON/..."
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        dev_class, uri = parts[0], parts[1]
        devices.append({"class": dev_class, "uri": uri})
    return {"success": True, "devices": devices}


# ─── Listing ──────────────────────────────────────────────────────────────────

def list_printers() -> dict:
    """List configured printers with their state and share status."""
    rc, out, err = _run(["lpstat", "-l", "-p"])
    if rc != 0:
        # lpstat returns non-zero when there are no printers; treat empty as success.
        if "No destinations added" in (out + err) or not (out + err).strip():
            return {"success": True, "printers": []}
        return {"success": False, "error": err.strip() or "lpstat failed"}

    printers: dict[str, dict] = {}
    current = None
    for line in out.splitlines():
        # "printer <name> is idle.  enabled since ..."
        m = re.match(r"printer\s+(\S+)\s+is\s+(\w+)", line)
        if m:
            current = m.group(1)
            printers[current] = {
                "name": current,
                "state": m.group(2),
                "enabled": "disabled" not in line,
                "shared": None,
                "device_uri": None,
            }

    # Enrich with share status + device URI where available.
    for name, info in printers.items():
        rc2, out2, _ = _run([
            "lpstat", "-l", "-v", name,
        ])
        if rc2 == 0:
            for line in out2.splitlines():
                # "device for <name>: usb://..."
                dm = re.match(rf"device for {re.escape(name)}:\s*(.+)", line)
                if dm:
                    info["device_uri"] = dm.group(1).strip()
        # printer-is-shared via lpoptions
        rc3, out3, _ = _run(["lpoptions", "-p", name])
        if rc3 == 0:
            info["shared"] = "printer-is-shared=true" in out3

    return {"success": True, "printers": list(printers.values())}


# ─── Add & share ────────────────────────────────────────────────────────────--

def add_printer(name: str, device_uri: str, driver: str = "everywhere", shared: bool = True) -> dict:
    """Add a printer and (by default) share it over the network via CUPS/IPP.

    Args:
        name: CUPS printer name (validated).
        device_uri: Device URI from discover_printers (e.g. usb://EPSON/...).
        driver: PPD/driver model. "everywhere" uses IPP Everywhere / driverless,
                which suits most modern printers; pass a specific PPD name (from
                ``lpinfo -m``) for older devices.
        shared: Whether to enable network sharing (printer-is-shared).

    Returns {"success": bool, ...}.
    """
    if not _valid_name(name):
        return {"success": False, "error": f"Invalid printer name: {name!r}"}
    if not device_uri or "://" not in device_uri:
        return {"success": False, "error": f"Invalid device URI: {device_uri!r}"}

    # Build lpadmin command. -E (after -p) enables the printer and accepts jobs.
    cmd = ["lpadmin", "-p", name, "-v", device_uri, "-E"]
    if driver == "everywhere":
        cmd += ["-m", "everywhere"]
    else:
        cmd += ["-m", driver]
    cmd += ["-o", f"printer-is-shared={'true' if shared else 'false'}"]

    rc, out, err = _sudo_run(cmd)
    if rc != 0:
        return {"success": False, "error": err.strip() or "lpadmin failed"}

    # Ensure the printer is enabled and accepting jobs (idempotent).
    _sudo_run(["cupsenable", name])
    _sudo_run(["cupsaccept", name])

    return {
        "success": True,
        "message": f"Printer '{name}' added"
                   + (" and shared over the network" if shared else ""),
        "name": name,
        "shared": shared,
    }


def set_printer_shared(name: str, shared: bool) -> dict:
    """Enable or disable network sharing for an existing printer."""
    if not _valid_name(name):
        return {"success": False, "error": f"Invalid printer name: {name!r}"}
    rc, out, err = _sudo_run([
        "lpadmin", "-p", name, "-o", f"printer-is-shared={'true' if shared else 'false'}",
    ])
    if rc != 0:
        return {"success": False, "error": err.strip() or "lpadmin failed"}
    return {"success": True, "name": name, "shared": shared}


def remove_printer(name: str) -> dict:
    """Remove a configured printer."""
    if not _valid_name(name):
        return {"success": False, "error": f"Invalid printer name: {name!r}"}
    rc, out, err = _sudo_run(["lpadmin", "-x", name])
    if rc != 0:
        return {"success": False, "error": err.strip() or "lpadmin failed"}
    return {"success": True, "message": f"Printer '{name}' removed"}


# ─── Jobs ─────────────────────────────────────────────────────────────────────

def list_jobs(name: str) -> dict:
    """List the print queue for a printer."""
    if not _valid_name(name):
        return {"success": False, "error": f"Invalid printer name: {name!r}"}
    rc, out, err = _run(["lpstat", "-o", name])
    if rc != 0:
        return {"success": False, "error": err.strip() or "lpstat failed"}

    jobs = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # "<name>-<jobid>  <user>  <size>  <date>"
        parts = line.split()
        if parts:
            jobs.append({"job": parts[0], "raw": line})
    return {"success": True, "jobs": jobs}


def cancel_job(job_id: str) -> dict:
    """Cancel a print job by its id (e.g. 'EPSON-42')."""
    # Job ids share the printer-name charset plus a trailing '-<num>'.
    if not job_id or not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,159}$", job_id):
        return {"success": False, "error": f"Invalid job id: {job_id!r}"}
    rc, out, err = _sudo_run(["cancel", job_id])
    if rc != 0:
        return {"success": False, "error": err.strip() or "cancel failed"}
    return {"success": True, "message": f"Job '{job_id}' cancelled"}


def print_test_page(name: str) -> dict:
    """Send the CUPS test page to a printer."""
    if not _valid_name(name):
        return {"success": False, "error": f"Invalid printer name: {name!r}"}
    test_file = "/usr/share/cups/data/testprint"
    rc, out, err = _run(["lp", "-d", name, test_file])
    if rc != 0:
        return {"success": False, "error": err.strip() or "lp failed"}
    return {"success": True, "message": f"Test page sent to '{name}'", "output": out.strip()}
