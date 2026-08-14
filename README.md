# Bottom Bar Dock

Minimal i3 dock bar — pure PySide6, no system tool dependencies.

## Features

- **Left**: live clock + date
- **Center**: CPU % (color-coded: green < 50, amber < 80, red ≥ 80) · RAM %
- **Right**: 🎵 **GLAVA** button — toggles a thin color-only spectrum strip

## Glava integration

Clicking the button launches glava as a transparent dock window (30px tall, full-width).
Glava uses the `graph` module with only color bands — no bar shapes.

```bash
# Toggle via button in the bar, or CLI:
glava -d -m graph          # start
pkill glava                # stop
```

Config is auto-generated at startup (writes to `~/.config/glava/rc.glsl.tmp`).

## Install

```bash
pip3 install PySide6
python3 main.py --screen 1920x1080
```

## i3 config

Add to `~/.config/i3/config` (remove existing `bar {` block first):

```bash
exec_always --no-startup-id python3 ~/bottom-bar-dock/main.py
```

Reload: `i3-msg reload`

## Dependencies

- Python 3.8+
- PySide6 (`pip3 install PySide6`)
- glava (optional, for the spectrum strip)
