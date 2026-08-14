# Bottom Bar Dock

Standalone i3 dock bar replacing i3bar — workspace buttons, system stats (CPU/RAM/disk/network), clock, battery, volume, WiFi info.

## Install

```bash
pip3 install PySide6
python3 main.py --screen $(xrandr | grep '*' | awk '{print $1}')
```

## i3 config

Add to `~/.config/i3/config` (remove existing `bar {` block first):

```bash
exec_always --no-startup-id python3 ~/bottom-bar-dock/main.py
```

Reload: `i3-msg reload`
