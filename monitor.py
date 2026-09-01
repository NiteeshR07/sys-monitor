#!/usr/bin/env python3
"""
Linux Server Resource Monitor
------------------------------
Checks CPU, RAM, and Disk usage against configurable thresholds.
Logs every check, and raises an alert (logged + optional console/email)
whenever a threshold is exceeded.

Usage:
    python3 monitor.py                     # run once
    python3 monitor.py --loop 60           # run every 60 seconds forever
    python3 monitor.py --config config.yaml
"""

import argparse
import logging
import smtplib
import sys
import time
from dataclasses import dataclass
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil
import yaml

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class Thresholds:
    cpu_percent: float = 80.0
    ram_percent: float = 80.0
    disk_percent: float = 85.0
    disk_path: str = "/"


def load_config(path: Path) -> Thresholds:
    """Load thresholds from a YAML file, falling back to defaults if missing."""
    if not path.exists():
        return Thresholds()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return Thresholds(
        cpu_percent=data.get("cpu_percent", 80.0),
        ram_percent=data.get("ram_percent", 80.0),
        disk_percent=data.get("disk_percent", 85.0),
        disk_path=data.get("disk_path", "/"),
    )


# --------------------------------------------------------------------------- #
# Logging setup — separate handlers for general activity vs. incidents
# --------------------------------------------------------------------------- #
def setup_logging() -> tuple[logging.Logger, logging.Logger]:
    activity_logger = logging.getLogger("activity")
    activity_logger.setLevel(logging.INFO)
    activity_handler = RotatingFileHandler(
        LOG_DIR / "monitor.log", maxBytes=1_000_000, backupCount=3
    )
    activity_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    activity_logger.addHandler(activity_handler)
    activity_logger.addHandler(logging.StreamHandler(sys.stdout))

    incident_logger = logging.getLogger("incidents")
    incident_logger.setLevel(logging.WARNING)
    incident_handler = RotatingFileHandler(
        LOG_DIR / "incidents.log", maxBytes=1_000_000, backupCount=5
    )
    incident_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    incident_logger.addHandler(incident_handler)

    return activity_logger, incident_logger


# --------------------------------------------------------------------------- #
# Metric collection
# --------------------------------------------------------------------------- #
def get_metrics(disk_path: str) -> dict:
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(disk_path).percent,
    }


def check_thresholds(metrics: dict, thresholds: Thresholds) -> list[str]:
    """Return a list of human-readable breach messages (empty if all OK)."""
    breaches = []
    if metrics["cpu"] >= thresholds.cpu_percent:
        breaches.append(
            f"CPU usage {metrics['cpu']:.1f}% >= threshold {thresholds.cpu_percent}%"
        )
    if metrics["ram"] >= thresholds.ram_percent:
        breaches.append(
            f"RAM usage {metrics['ram']:.1f}% >= threshold {thresholds.ram_percent}%"
        )
    if metrics["disk"] >= thresholds.disk_percent:
        breaches.append(
            f"Disk usage ({thresholds.disk_path}) {metrics['disk']:.1f}% "
            f">= threshold {thresholds.disk_percent}%"
        )
    return breaches


# --------------------------------------------------------------------------- #
# Alerting
# --------------------------------------------------------------------------- #
def send_email_alert(subject: str, body: str, email_cfg: dict) -> None:
    """Optional email alert. Only fires if email_cfg is fully populated."""
    required = ["smtp_server", "smtp_port", "sender", "password", "recipient"]
    if not email_cfg or not all(email_cfg.get(k) for k in required):
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_cfg["sender"]
    msg["To"] = email_cfg["recipient"]

    with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
        server.starttls()
        server.login(email_cfg["sender"], email_cfg["password"])
        server.send_message(msg)


# --------------------------------------------------------------------------- #
# Main check cycle
# --------------------------------------------------------------------------- #
def run_check(thresholds: Thresholds, activity_log, incident_log, email_cfg=None):
    metrics = get_metrics(thresholds.disk_path)
    activity_log.info(
        f"CPU={metrics['cpu']:.1f}% RAM={metrics['ram']:.1f}% "
        f"Disk={metrics['disk']:.1f}%"
    )

    breaches = check_thresholds(metrics, thresholds)
    if breaches:
        message = "; ".join(breaches)
        activity_log.warning(f"THRESHOLD EXCEEDED: {message}")
        incident_log.warning(message)
        if email_cfg:
            send_email_alert(
                subject="[ALERT] Server resource threshold exceeded",
                body=message,
                email_cfg=email_cfg,
            )
    return metrics, breaches


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Linux Server Resource Monitor")
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH,
        help="Path to config.yaml (default: ./config.yaml)"
    )
    parser.add_argument(
        "--loop", type=int, default=0,
        help="Run continuously, checking every N seconds. Default: run once."
    )
    args = parser.parse_args()

    thresholds = load_config(args.config)
    activity_log, incident_log = setup_logging()

    activity_log.info(
        f"Monitor started | thresholds: CPU>={thresholds.cpu_percent}% "
        f"RAM>={thresholds.ram_percent}% Disk>={thresholds.disk_percent}%"
    )

    if args.loop > 0:
        try:
            while True:
                run_check(thresholds, activity_log, incident_log)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            activity_log.info("Monitor stopped by user.")
    else:
        run_check(thresholds, activity_log, incident_log)


if __name__ == "__main__":
    main()
