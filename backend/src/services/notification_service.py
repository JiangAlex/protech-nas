"""Notification service — send alerts via Email, Telegram, Webhook."""

import json
import os
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from uuid import uuid4

# ─── Configuration ────────────────────────────────────────────────────────────

NOTIFY_CONFIG_DIR = "/etc/protech-nas/notifications"
NOTIFY_SETTINGS_FILE = os.path.join(NOTIFY_CONFIG_DIR, "settings.json")
NOTIFY_HISTORY_FILE = os.path.join(NOTIFY_CONFIG_DIR, "history.json")


def _ensure_config_dir():
    os.makedirs(NOTIFY_CONFIG_DIR, exist_ok=True)


def _load_settings() -> dict:
    _ensure_config_dir()
    if not os.path.exists(NOTIFY_SETTINGS_FILE):
        return {
            "email": {"enabled": False, "smtp_host": "", "smtp_port": 587, "username": "", "password": "", "from_addr": "", "to_addr": ""},
            "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
            "webhook": {"enabled": False, "url": ""},
        }
    try:
        with open(NOTIFY_SETTINGS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"email": {"enabled": False}, "telegram": {"enabled": False}, "webhook": {"enabled": False}}


def _save_settings(settings: dict):
    _ensure_config_dir()
    with open(NOTIFY_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    os.chmod(NOTIFY_SETTINGS_FILE, 0o600)


def _load_history() -> list:
    if not os.path.exists(NOTIFY_HISTORY_FILE):
        return []
    try:
        with open(NOTIFY_HISTORY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_history(history: list):
    _ensure_config_dir()
    # Keep last 200 notifications
    with open(NOTIFY_HISTORY_FILE, "w") as f:
        json.dump(history[-200:], f, indent=2, default=str)


# ─── Settings CRUD ────────────────────────────────────────────────────────────

def get_notification_settings() -> dict:
    """Get notification channel settings (passwords masked).

    Returns:
        {"success": bool, "email": dict, "telegram": dict, "webhook": dict}
    """
    settings = _load_settings()

    # Mask sensitive fields
    safe = json.loads(json.dumps(settings))
    if safe.get("email", {}).get("password"):
        safe["email"]["password"] = "***"
    if safe.get("telegram", {}).get("bot_token"):
        safe["telegram"]["bot_token"] = "***" + safe["telegram"]["bot_token"][-4:]
    return {"success": True, **safe}


def update_notification_settings(config: dict) -> dict:
    """Update notification settings.

    Args:
        config: {"email": {...}, "telegram": {...}, "webhook": {...}}

    Returns:
        {"success": bool, "message": str}
    """
    current = _load_settings()

    # Merge — only update provided channels
    if "email" in config:
        current["email"] = {**current.get("email", {}), **config["email"]}
    if "telegram" in config:
        current["telegram"] = {**current.get("telegram", {}), **config["telegram"]}
    if "webhook" in config:
        current["webhook"] = {**current.get("webhook", {}), **config["webhook"]}

    _save_settings(current)
    return {"success": True, "message": "Notification settings updated"}


# ─── Send Notification ────────────────────────────────────────────────────────

def send_notification(channel: str, title: str, body: str) -> dict:
    """Send a notification via specified channel.

    Args:
        channel: "email" | "telegram" | "webhook" | "all"
        title: Notification title.
        body: Notification body text.

    Returns:
        {"success": bool, "message": str}
    """
    settings = _load_settings()
    results = []

    channels = [channel] if channel != "all" else ["email", "telegram", "webhook"]

    for ch in channels:
        if ch == "email" and settings.get("email", {}).get("enabled"):
            results.append(_send_email(settings["email"], title, body))
        elif ch == "telegram" and settings.get("telegram", {}).get("enabled"):
            results.append(_send_telegram(settings["telegram"], title, body))
        elif ch == "webhook" and settings.get("webhook", {}).get("enabled"):
            results.append(_send_webhook(settings["webhook"], title, body))
        elif ch not in ("email", "telegram", "webhook"):
            results.append({"channel": ch, "success": False, "error": f"Unknown channel: {ch}"})

    # Record to history
    history = _load_history()
    history.append({
        "id": str(uuid4())[:8],
        "title": title,
        "body": body,
        "level": "info",
        "read": False,
        "created_at": datetime.now().isoformat(),
        "channel": channel,
    })
    _save_history(history)

    failures = [r for r in results if not r.get("success", True)]
    if failures:
        return {"success": False, "message": "; ".join(f.get("error", "") for f in failures)}
    return {"success": True, "message": "Notification sent"}


def _send_email(config: dict, title: str, body: str) -> dict:
    """Send email via SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"] = config.get("from_addr", "")
        msg["To"] = config.get("to_addr", "")
        msg["Subject"] = f"[ProTech NAS] {title}"
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587))
        server.starttls()
        if config.get("username") and config.get("password"):
            server.login(config["username"], config["password"])
        server.send_message(msg)
        server.quit()
        return {"channel": "email", "success": True}
    except Exception as e:
        return {"channel": "email", "success": False, "error": f"Email failed: {str(e)[:100]}"}


def _send_telegram(config: dict, title: str, body: str) -> dict:
    """Send Telegram message."""
    try:
        bot_token = config.get("bot_token", "")
        chat_id = config.get("chat_id", "")
        text = f"*{title}*\n{body}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return {"channel": "telegram", "success": True}
    except Exception as e:
        return {"channel": "telegram", "success": False, "error": f"Telegram failed: {str(e)[:100]}"}


def _send_webhook(config: dict, title: str, body: str) -> dict:
    """Send webhook POST."""
    try:
        url = config.get("url", "")
        payload = json.dumps({"title": title, "body": body, "timestamp": datetime.now().isoformat()}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return {"channel": "webhook", "success": True}
    except Exception as e:
        return {"channel": "webhook", "success": False, "error": f"Webhook failed: {str(e)[:100]}"}


# ─── Notification History ─────────────────────────────────────────────────────

def list_notifications(unread_only: bool = False) -> dict:
    """List notification history.

    Args:
        unread_only: If True, only return unread notifications.

    Returns:
        {"success": bool, "notifications": list[dict]}
    """
    history = _load_history()
    if unread_only:
        history = [n for n in history if not n.get("read")]
    # Return newest first
    return {"success": True, "notifications": list(reversed(history))}


def mark_read(notification_id: str) -> dict:
    """Mark a notification as read.

    Returns:
        {"success": bool}
    """
    history = _load_history()
    found = False
    for n in history:
        if n.get("id") == notification_id:
            n["read"] = True
            found = True
            break

    if not found:
        return {"success": False, "error": f"Notification {notification_id} not found"}

    _save_history(history)
    return {"success": True}
