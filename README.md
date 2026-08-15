# Bottom Bar Dock

Minimal i3 dock bar — pure PySide6, no system tool dependencies.

## Features

- **Left**: live clock + date
- **Center**: CPU % (color-coded: green < 50, amber < 80, red ≥ 80) · RAM %
- **Right**: wifi SSID+IP · volume · battery · uptime · 🎵 GLAVA toggle (themable color themes)
- **📽 Video wallpaper**: a looping, cover-fit video behind the bar (fwm-style,
  in-process decode via QtMultimedia, muted, on the desktop layer)

## Video wallpaper

A full-screen looping video is pinned to the desktop layer (below every real
window) and scaled to *cover* the screen — preserving aspect ratio and cropping
the overflow, exactly like fwm's `[[wallpaper]] fit = "video"`. Decoded in-process
through QtMultimedia (no mpv/ffplay dependency); audio is muted.

```bash
# Defaults to ~/Videos/paper10_720.mp4; override with:
python3 main.py --screen 1920x1080 --wallpaper ~/Videos/paper11.mp4
python3 main.py --wallpaper none        # bar only, no wallpaper
python3 main.py --wallpaper ~/x.mp4 --mirror   # mirrored ("selfie") clip

# Wallpaper only (no bar):
python3 video_wallpaper.py --wallpaper ~/Videos/paper10_720.mp4
```

Switching wallpapers at runtime is done by calling `set_video(path)` on the
`video_wallpaper.VideoWallpaper` instance.

## Color themes (bar + GLAVA)

The bar's accent color and GLAVA's strip colors are driven by a theme file
that lives in your animated-wallpaper config (same one your fwm/sword setup
uses): `~/.config/animated-wallpaper/glava.theme`.

| Theme   | Bar accent color | GLAVA `mix()` strip colors |
|---------|------------------|----------------------------|
| `cyan`   | One Dark blue `#61AFEF` | `#00D4FF → #00FFC8` |
| `green`  | `#00FF88` | `#00FF88 → #88FF00` |
| `purple` | `#C678DD` | `#c678dd → #7c3aed` |
| `red`    | `#E06C75` | `#e06c75 → #ff4444` |
| `rainbow` | warm gold `#FFC832` | `#ff0000 → #0000ff` |
| `sunset` | `#FF6B35` | `#ff6b35 → #ff006e` |

Change it by editing one line, then toggle GLAVA to restart with the new colors:

```bash
echo rainbow > ~/.config/animated-wallpaper/glava.theme   # bar accent goes gold
echo cyan   > ~/.config/animated-wallpaper/glava.theme    # back to One Dark blue
# then click the 🎵 GLAVA button to relaunch glava with the new theme
```

**Glava button behavior:**
- **Left-click**: toggles the GLAVA spectrum strip on/off (starts glava with the
  current theme when off, kills it when on). The button label shows the active
  theme while running (e.g. `🎵 RAINBOW`).
- **Right-click** (while running): cycles to the next theme and restarts glava.

The bar re-reads the theme on every refresh, so it recolors live.

## Glava integration

Clicking the button launches glava as a transparent dock window (30px tall, full-width).
Glava uses the `graph` module with only color bands — no bar shapes.

```bash
# Toggle via button in the bar, or CLI:
glava -d -m graph          # start
pkill glava                # stop
```

GLAVA's shader files (`~/.config/glava/graph.glsl`, `bars.glsl`, `radial.glsl`)
are recolored with the theme's `mix()` colors on every start/cycle (see the
Color themes section above).

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
