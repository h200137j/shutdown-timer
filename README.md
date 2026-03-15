# Shutdown Timer

A simple desktop app to schedule and cancel system shutdowns.

## Download

Grab the latest `.deb` installer from the [Releases page](../../releases/latest) and install it with:

```bash
sudo apt install ./shutdown-timer_1.0.0_all.deb
```

## Requirements

- Python 3.8+
- PyQt6

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Usage

1. Set hours and/or minutes using the spinboxes
2. Click **Set Shutdown** to schedule
3. A live countdown will be displayed
4. Click **Cancel** to abort the shutdown at any time

> Note: Scheduling/cancelling a shutdown requires `sudo` privileges.
