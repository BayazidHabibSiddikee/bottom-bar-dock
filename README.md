# Bottom Bar Dock

Always-visible i3 dock bar with a live glava spectrum strip, color themes,
night mode, video wallpaper cycling, and per-module glava controls — pure
PySide6, rendered with `QPainter` (no widgets, no HTML).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1  2  3  4 │ SWORD  17:23:45  Sat 17 Aug │ ⚡ CPU: 12% │ 🧠 RAM: 48% │ …
│             │ ▣ firefox │       🔊 35% ⚡ 96% ↑ 3h 12m   🎞 ↻ 🌙 〰 📈 ▮ 🎨 │
└──────────────────────────────────────────────────────────────────────────┘
   ↑ workspaces        ↑ window switcher      ↑ wallpaper restart night
                                                ↑ glava modules ↑ color cycle
```

## Features

- **Workspace buttons** (left): click to switch workspaces via `i3-msg`;
  focused workspace is highlighted with the theme accent, urgent in red.
- **Live stats**: clock + date, CPU/RAM/disk % (green < 50, amber < 80, red ≥ 80),
  network speed, wifi SSID + IP, volume, battery, uptime.
- **Window switcher**: opens `rofi -show window`.
- **Glava visualizer strip**: launches glava as a transparent, click-through,
  always-on-top strip pinned just above the bar (full screen width, 140px tall,
  25 → 15 fps cap, theme-colored).
- **3 glava modules**: wave, graph, bars — one button each; click the *active*
  module to turn glava off.
- **Color themes**: cycle 6 themes (cyan, green, purple, red, rainbow, sunset).
  Theme colors are written into glava's shader files and the bar accent follows.
- **Night mode**: cycles redshift reading levels off → 5000K → 5500K → 6000K.
- **Restart button**: relaunches the bar (survives as a detached process).
- **Video wallpaper**: cycles looping videos from `~/Videos` behind everything,
  via `xwinwrap + mpv` (cover-fit).

## Requirements

- Python 3.8+
- PySide6 — `pip3 install -r requirements.txt`

### System tools (all optional — the bar degrades gracefully if missing)

| Tool | Used for |
|------|----------|
| `i3-msg` | workspace switching |
| `xdotool` | window name, glava window re-class |
| `xprop` | glava window type/state properties |
| `xwinwrap` | transparent wrapper for glava strip + video wallpaper |
| `glava` | the audio spectrum visualizer strip |
| `redshift` | night/reading mode |
| `nmcli` | wifi SSID + IP (falls back to `iwgetid`) |
| `pactl` | volume % / mute state |
| `rofi` | window switcher dialog |
| `mpv` | video wallpaper playback |

Install on Arch: `sudo pacman -S glava xwinwrap xdotool xprop redshift networkmanager libpulse rofi mpv`

## Install & run

```bash
pip3 install -r requirements.txt
python3 main.py            # 1920x32 bar
python3 main.py 2560x32    # custom width x height
```

Add to `~/.config/i3/config` (remove any existing `bar { }` block first):

```
exec_always --no-startup-id python3 ~/bottom-bar-dock/main.py
```

Reload: `i3-msg reload`

## Controls

All buttons are on the right side of the bar:

| Button | Action |
|--------|--------|
| **workspace 1..N** | switch to that workspace (`i3-msg workspace`) |
| **▣ window title** | open `rofi -show window` switcher |
| **🎨 color swatch** | cycle glava theme (cyan → green → purple → red → rainbow → sunset); restarts glava so shaders recolor live |
| **〰 / 📈 / ▮ module icons** | start glava with wave / graph / bars module; clicking the active module toggles glava **off** |
| **🌙 night dot** | cycle reading mode off → 5000K → 5500K → 6000K (`redshift -O`) |
| **↻** | restart the bar |
| **🎞** | cycle to the next video wallpaper in `~/Videos` |

## Color themes

The bar accent and glava's strip colors are driven by a theme file shared with
your animated-wallpaper setup: `~/.config/animated-wallpaper/glava.theme`.

| Theme    | Bar accent | Glava strip colors |
|----------|------------|--------------------|
| `cyan`   | `#61AFEF`  | `#00D4FF → #00FFC8` |
| `green`  | `#00FF88`  | `#00FF88 → #88FF00` |
| `purple` | `#C678DD`  | `#c678dd → #7c3aed` |
| `red`    | `#E06C75`  | `#e06c75 → #ff4444` |
| `rainbow`| `#FFC832` (warm gold) | `#FFC832 → #FF9500` |
| `sunset` | `#FF6B35`  | `#ff6b35 → #ff006e` |

The theme file is re-read on every refresh, so the bar recolors live. Glava's
shader files (`~/.config/glava/graph.glsl`, `bars.glsl`, `radial.glsl`,
`wave.glsl`) are rewritten with the theme colors each time glava starts or the
theme cycles.

## Glava integration

- Launched as `xwinwrap -ov -ni -argb` at `setgeometry 0 (screen_h-172) W 140`,
  then re-classed: `_NET_WM_WINDOW_TYPE_UTILITY`, ABOVE, SKIP_TASKBAR/PAGER,
  STICKY, and floated in i3 — so it renders as a strip, never tiles.
- **`wave` module uses the `wavefix` module dir**: the stock wave shader adds a
  white term (`BASE_COLOR + dist*0.02`) that washes out the theme color, so a
  fixed copy without it is shipped at `~/.config/glava/wavefix/`.
- **Frame cap**: `#request setframerate 15` in `~/.config/glava/rc.glsl`
  (vsync `setswap 1`). Measured: steady 15.00 FPS / UPS.
- State files in `~/.config/animated-wallpaper/`:

| File | Meaning |
|------|---------|
| `glava.theme` | current theme name |
| `glava.mode`  | current module (`wave` / `graph` / `bars`) |
| `glava.pid`   | pid of the running glava (for toggling) |
| `night.temp`  | night-mode level 0–3 |

## Video wallpaper

`~/Videos/*.{mp4,webm,mkv,mov}` sorted alphabetically; the 🎞 button kills the
current `mpv -wid` instance and starts the next video cover-fit
(`--panscan=1.0`, muted, looped). The wallpaper is independent of glava.

## Files

| File | Purpose |
|------|---------|
| `main.py` | entry point; creates the frameless dock window |
| `bottom_bar.py` | the bar: drawing, buttons, stats, glava/night/wallpaper control |
| `video_wallpaper.py` | optional in-process QtMultimedia video wallpaper widget (standalone or library) |
| `pipes_layer.py` | animated "pipes" background texture layer (helper for panel widgets) |
| `requirements.txt` | Python dependencies (PySide6) |