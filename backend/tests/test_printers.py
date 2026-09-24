"""Tests for printer_service — CUPS/IPP printer sharing.

These tests mock the CUPS CLI calls (_run / _sudo_run) so they run without a
real CUPS install or a physical printer.
"""

import pytest
from src.services import printer_service as ps


# ─── Name validation ──────────────────────────────────────────────────────────

class TestNameValidation:
    def test_valid_names(self):
        assert ps._valid_name("EPSON_L3150")
        assert ps._valid_name("hp-officejet.1")

    def test_rejects_injection_and_bad_chars(self):
        assert not ps._valid_name("")
        assert not ps._valid_name("a b")          # space
        assert not ps._valid_name("a;rm -rf /")   # shell metachar
        assert not ps._valid_name("../etc")        # slash


# ─── discover_printers ──────────────────────────────────────────────────────--

class TestDiscover:
    def test_parses_lpinfo(self, monkeypatch):
        out = "direct usb://EPSON/L3150?serial=X\nnetwork ipp://printer.local/ipp\n"
        monkeypatch.setattr(ps, "_run", lambda cmd, timeout=30: (0, out, ""))
        res = ps.discover_printers()
        assert res["success"] is True
        uris = [d["uri"] for d in res["devices"]]
        assert "usb://EPSON/L3150?serial=X" in uris
        assert res["devices"][0]["class"] == "direct"

    def test_error_propagates(self, monkeypatch):
        monkeypatch.setattr(ps, "_run", lambda cmd, timeout=30: (1, "", "boom"))
        res = ps.discover_printers()
        assert res["success"] is False
        assert "boom" in res["error"]


# ─── list_printers ────────────────────────────────────────────────────────────

class TestListPrinters:
    def test_empty(self, monkeypatch):
        monkeypatch.setattr(ps, "_run", lambda cmd, timeout=30: (1, "", "No destinations added."))
        res = ps.list_printers()
        assert res["success"] is True
        assert res["printers"] == []

    def test_parses_and_enriches(self, monkeypatch):
        def fake_run(cmd, timeout=30):
            if cmd[:2] == ["lpstat", "-l"] and "-p" in cmd and "-v" not in cmd:
                return (0, "printer EPSON is idle.  enabled since now\n", "")
            if "-v" in cmd:
                return (0, "device for EPSON: usb://EPSON/L3150\n", "")
            if cmd[:1] == ["lpoptions"]:
                return (0, "copies=1 printer-is-shared=true\n", "")
            return (0, "", "")
        monkeypatch.setattr(ps, "_run", fake_run)
        res = ps.list_printers()
        assert res["success"] is True
        p = res["printers"][0]
        assert p["name"] == "EPSON"
        assert p["state"] == "idle"
        assert p["enabled"] is True
        assert p["shared"] is True
        assert p["device_uri"] == "usb://EPSON/L3150"


# ─── add_printer ──────────────────────────────────────────────────────────────

class TestAddPrinter:
    def test_rejects_bad_name(self):
        res = ps.add_printer("bad name", "usb://x")
        assert res["success"] is False

    def test_rejects_bad_uri(self):
        res = ps.add_printer("EPSON", "not-a-uri")
        assert res["success"] is False

    def test_builds_lpadmin_with_share(self, monkeypatch):
        calls = []
        def fake_sudo(cmd, timeout=60):
            calls.append(cmd)
            return (0, "", "")
        monkeypatch.setattr(ps, "_sudo_run", fake_sudo)
        res = ps.add_printer("EPSON", "usb://EPSON/L3150", driver="everywhere", shared=True)
        assert res["success"] is True
        # First call is the lpadmin add
        add = calls[0]
        assert add[0] == "lpadmin"
        assert "-p" in add and "EPSON" in add
        assert "-v" in add and "usb://EPSON/L3150" in add
        assert "-m" in add and "everywhere" in add
        assert "printer-is-shared=true" in add
        # enable + accept follow
        assert ["cupsenable", "EPSON"] in calls
        assert ["cupsaccept", "EPSON"] in calls

    def test_share_false(self, monkeypatch):
        calls = []
        monkeypatch.setattr(ps, "_sudo_run", lambda cmd, timeout=60: (calls.append(cmd) or (0, "", "")))
        ps.add_printer("EPSON", "usb://x/y", shared=False)
        assert "printer-is-shared=false" in calls[0]


# ─── set_printer_shared / remove / jobs / cancel / test ────────────────────────

class TestOtherOps:
    def test_set_shared(self, monkeypatch):
        calls = []
        monkeypatch.setattr(ps, "_sudo_run", lambda cmd, timeout=60: (calls.append(cmd) or (0, "", "")))
        res = ps.set_printer_shared("EPSON", True)
        assert res["success"] is True
        assert "printer-is-shared=true" in calls[0]

    def test_remove(self, monkeypatch):
        calls = []
        monkeypatch.setattr(ps, "_sudo_run", lambda cmd, timeout=60: (calls.append(cmd) or (0, "", "")))
        res = ps.remove_printer("EPSON")
        assert res["success"] is True
        assert calls[0] == ["lpadmin", "-x", "EPSON"]

    def test_remove_bad_name(self):
        assert ps.remove_printer("a;b")["success"] is False

    def test_list_jobs(self, monkeypatch):
        monkeypatch.setattr(ps, "_run", lambda cmd, timeout=30: (0, "EPSON-1 alex 1024 Mon\n", ""))
        res = ps.list_jobs("EPSON")
        assert res["success"] is True
        assert res["jobs"][0]["job"] == "EPSON-1"

    def test_cancel_job_validates(self):
        assert ps.cancel_job("bad id")["success"] is False

    def test_cancel_job(self, monkeypatch):
        calls = []
        monkeypatch.setattr(ps, "_sudo_run", lambda cmd, timeout=60: (calls.append(cmd) or (0, "", "")))
        res = ps.cancel_job("EPSON-1")
        assert res["success"] is True
        assert calls[0] == ["cancel", "EPSON-1"]

    def test_test_page(self, monkeypatch):
        calls = []
        monkeypatch.setattr(ps, "_run", lambda cmd, timeout=30: (calls.append(cmd) or (0, "request id is EPSON-2", "")))
        res = ps.print_test_page("EPSON")
        assert res["success"] is True
        assert calls[0][0] == "lp" and "EPSON" in calls[0]
