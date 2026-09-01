# Linux Server Resource Monitor

A lightweight Python tool that watches CPU, RAM, and Disk usage on a Linux
server, checks them against configurable thresholds, logs every check, and
raises an alert (log entry + optional email) whenever a threshold is
exceeded.

```
Linux Server
     ↓
Python Script
     ↓
CPU ──┐
RAM ──┼──→ Check Threshold
Disk ─┘
          ↓
    Alert if exceeded
          ↓
    Log the incident
```

## Features

- Reads live CPU / RAM / Disk usage via [`psutil`](https://pypi.org/project/psutil/)
- Configurable thresholds via `config.yaml`
- Two log streams:
  - `logs/monitor.log` — every check (rotates at 1MB, 3 backups)
  - `logs/incidents.log` — only threshold breaches (rotates at 1MB, 5 backups)
- Optional email alerts via SMTP
- Run once, or loop forever at a fixed interval
- Ships with a `systemd` unit file to run as a background service

## Setup

```bash
git clone https://github.com/<your-username>/sys-monitor.git
cd sys-monitor
pip install -r requirements.txt
```

## Usage

Run a single check:

```bash
python3 monitor.py
```

Run continuously, checking every 60 seconds:

```bash
python3 monitor.py --loop 60
```

Use a custom config file:

```bash
python3 monitor.py --config /path/to/config.yaml
```

## Configuration

Edit `config.yaml`:

```yaml
cpu_percent: 80
ram_percent: 80
disk_percent: 85
disk_path: "/"
```

To enable email alerts, uncomment and fill in the `email:` block in
`config.yaml` (use an app password, not your real email password, if using
Gmail).

## Running as a systemd service

```bash
sudo cp -r . /opt/sys-monitor
sudo cp sys-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sys-monitor
sudo systemctl status sys-monitor
```

## Project structure

```
sys-monitor/
├── monitor.py            # main script
├── config.yaml            # thresholds
├── requirements.txt
├── sys-monitor.service    # systemd unit (optional)
├── logs/
│   ├── monitor.log         # generated at runtime
│   └── incidents.log       # generated at runtime
└── README.md
```

## Possible extensions

- Slack / Discord webhook alerts
- Prometheus / Grafana export
- Per-process resource tracking
- Dockerize it

## License

MIT
