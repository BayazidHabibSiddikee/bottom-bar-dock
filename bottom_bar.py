"""bottom_bar.py — always-visible dock bar (replaces i3bar).

Left:  clickable workspace buttons + window switcher
Mid:   time · CPU · RAM · disk · net speed
Right: wifi SSID+IP · volume · battery · uptime · [GLAVA] · [COLOR]
"""
import os, json, getpass, shutil, subprocess
from datetime import datetime

USER_TAG = f"[{getpass.getuser().upper()}]"

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics

CYAN  = QColor(97, 175, 239)
GREEN = QColor(152, 195, 121)
AMBER = QColor(229, 192, 123)
RED   = QColor(224, 108, 117)
DIM   = QColor(62, 68, 81)
WHITE = QColor(171, 178, 191)
BG    = QColor(40, 44, 52, 255)
WS_BG = QColor(62, 68, 81, 255)

GLAVA_PID        = os.path.expanduser("~/.config/animated-wallpaper/glava.pid")
GLAVA_THEME_FILE = os.path.expanduser("~/.config/animated-wallpaper/glava.theme")
GLAVA_THEMES     = ["cyan", "green", "purple", "red", "rainbow", "sunset"]

# Accent color shown in the bar for the active glava theme
_THEME_ACCENTS = {
    "cyan":    QColor(97, 175, 239),    # One Dark blue
    "green":   QColor(0, 255, 136),
    "purple":  QColor(198, 120, 221),
    "red":     QColor(224, 108, 117),
    "rainbow": QColor(255, 200, 50),    # warm gold
    "sunset":  QColor(255, 107, 53),
}

# Hex color pairs written into the glava shader files
_THEME_COLORS = {
    "cyan":    ("#00D4FF", "#00FFC8"),
    "green":   ("#00FF88", "#88FF00"),
    "purple":  ("#c678dd", "#7c3aed"),
    "red":     ("#e06c75", "#ff4444"),
    "rainbow": ("#ff0000", "#0000ff"),
    "sunset":  ("#ff6b35", "#ff006e"),
}

DOCK_H = 32     # height of this bar (glava's clearance above it)
GLAVA_H = 140   # height of the glava visualizer strip


def _bar_accent():
    """Return the bar accent QColor for the current glava theme."""
    try:
        theme = open(GLAVA_THEME_FILE).read().strip()
    except Exception:
        theme = "cyan"
    return _THEME_ACCENTS.get(theme, CYAN)


def _cpu():
    try:
        vals = list(map(int, open("/proc/stat").readline().split()[1:8]))
        idle, total = vals[3], sum(vals)
        if not hasattr(_cpu, "_p"):
            _cpu._p = (total, idle); return 0
        pt, pi = _cpu._p; _cpu._p = (total, idle)
        dt, di = total - pt, idle - pi
        return int(100 * (1 - di / dt)) if dt else 0
    except Exception:
        return 0

def _mem_pct():
    try:
        info = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":", 1)
            info[k.strip()] = int(v.split()[0])
        return int(100 * (info["MemTotal"] - info["MemAvailable"]) / info["MemTotal"])
    except Exception:
        return 0

def _disk_pct():
    try:
        st = os.statvfs("/")
        return int(100 * (1 - st.f_bavail / st.f_blocks))
    except Exception:
        return 0

def _net():
    try:
        rx = tx = 0
        for line in open("/proc/net/dev").readlines()[2:]:
            name, data = line.split(":", 1)
            if name.strip() == "lo": continue
            f = data.split()
            rx += int(f[0]); tx += int(f[8])
        import time
        now = time.monotonic()
        prev = getattr(_net, "_p", None)
        _net._p = (now, rx, tx)
        if prev is None:
            return "↓0 ↑0 KB/s"
        dt = max(0.1, now - prev[0])
        down = max(0, int((rx - prev[1]) / dt / 1024))
        up   = max(0, int((tx - prev[2]) / dt / 1024))
        return f"↓{down} ↑{up} KB/s"
    except Exception:
        return "? KB/s"

def _active_window():
    try:
        title = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowname"],
            timeout=1, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        title = ""
    return f"▣ {title}" if title else "▣ none"

def _uptime():
    try:
        secs = float(open("/proc/uptime").read().split()[0])
        return f"↑ {int(secs//3600)}h {int((secs%3600)//60)}m"
    except Exception:
        return "↑ ?"

_NET_ICONS = {"wifi":"📶","ethernet":"🔌","gsm":"📡","cdma":"📡","wimax":"📡"}

def _network():
    name, icon = "—", "🌐"
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"],
            timeout=1, text=True)
        best = None
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) < 3: continue
            dtype, state, conn = parts[0], parts[1], parts[2]
            if state == "connected" and conn and conn != "--":
                best = (dtype, conn)
                if dtype == "wifi": break
        if best:
            dtype, conn = best
            name = conn
            icon = _NET_ICONS.get(dtype, "🌐")
    except Exception:
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"], timeout=1, text=True).strip()
            if ssid: name, icon = ssid, "📶"
        except Exception: pass
    ip = "?"
    try:
        for line in subprocess.check_output(
                ["ip", "-4", "-o", "addr", "show", "scope", "global"],
                timeout=1, text=True).splitlines():
            ip = line.split()[3].split("/")[0]; break
    except Exception: pass
    return f"{icon} {name}  {ip}"

def _battery():
    try:
        base = "/sys/class/power_supply/BAT0"
        cap = int(open(f"{base}/capacity").read())
        status = open(f"{base}/status").read().strip()
        icon = "⚡" if status == "Charging" else "🔋"
        return cap, f"{icon} {cap}%"
    except Exception:
        return 100, ""

def _volume():
    try:
        out = subprocess.check_output(
            ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
            timeout=1, text=True)
        vol = out.split("%")[0].split("/")[-1].strip()
        mute = "yes" in subprocess.check_output(
            ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
            timeout=1, text=True)
        return f"🔇 {vol}%" if mute else f"🔊 {vol}%"
    except Exception:
        return ""

def _workspaces():
    try:
        return [
            (w["name"], w["focused"], w["urgent"])
            for w in json.loads(subprocess.check_output(
                ["i3-msg", "-t", "get_workspaces"], timeout=1, text=True))
        ]
    except Exception:
        return []


# ── GLava helpers (launch strategy copied from animated-wallpaper/cyberdesk.sh) ──

def _glava_running():
    try:
        pid = int(open(GLAVA_PID).read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        pass
    try:
        return subprocess.run(["pgrep", "-x", "glava"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    except Exception:
        return False

def _screen_size():
    try:
        out = subprocess.check_output(["xrandr", "--current"], timeout=2,
                                      text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "*" in line:
                w, h = line.split()[0].split("x")
                return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080

def _reclass_glava(pid):
    """Re-class the glava window: utility type, always-on-top, sticky,
    and floating under i3 so it renders as a strip instead of tiling."""
    try:
        gid = ""
        for cmd in (
            ["xdotool", "search", "--pid", str(pid), "--class", "GLava"],
            ["xdotool", "search", "--class", "GLava"],
        ):
            try:
                out = subprocess.check_output(cmd, timeout=2, text=True,
                                              stderr=subprocess.DEVNULL).strip()
            except Exception:
                continue
            if out:
                gid = out.splitlines()[0].strip()
                break
        if not gid:
            return
        if shutil.which("xprop"):
            subprocess.run(
                ["xprop", "-id", gid, "-f", "_NET_WM_WINDOW_TYPE", "32a",
                 "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_UTILITY"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(
                ["xprop", "-id", gid, "-f", "_NET_WM_STATE", "32a",
                 "-set", "_NET_WM_STATE",
                 "_NET_WM_STATE_ABOVE,_NET_WM_STATE_SKIP_TASKBAR,"
                 "_NET_WM_STATE_SKIP_PAGER,_NET_WM_STATE_STICKY"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if shutil.which("i3-msg"):
            subprocess.run(
                ["i3-msg", f"[id={gid}] floating enable, sticky enable"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["xdotool", "windowraise", gid],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def _start_glava():
    """Start glava as a bottom visualizer strip just above the dock bar."""
    _apply_theme_full(_read_theme())
    sw, sh = _screen_size()
    gy = max(0, sh - DOCK_H - GLAVA_H)
    args = ["glava", "-m", "graph",
            "-r", f"setgeometry 0 {gy} {sw} {GLAVA_H}"]
    if shutil.which("xwinwrap"):
        # -ov -ni -argb: always-on-top, click-through, transparent.
        cmd = ["xwinwrap", "-ov", "-ni", "-argb",
               "-g", f"{sw}x{GLAVA_H}+0+{gy}", "--"] + args
    else:
        cmd = args
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True)
    except FileNotFoundError:
        return
    os.makedirs(os.path.dirname(GLAVA_PID), exist_ok=True)
    with open(GLAVA_PID, "w") as f:
        f.write(str(proc.pid))
    QTimer.singleShot(700, lambda: _reclass_glava(proc.pid))

def _stop_glava():
    try:
        pid = int(open(GLAVA_PID).read().strip())
        os.kill(pid, 15)
    except Exception:
        pass
    try:
        os.remove(GLAVA_PID)
    except Exception:
        pass
    subprocess.run(["pkill", "-x", "glava"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-x", "xwinwrap"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── GLava theme support ────────────────────────────────────────────────────────

def _read_theme():
    try:
        return open(GLAVA_THEME_FILE).read().strip()
    except Exception:
        return "cyan"

def _write_theme(theme):
    os.makedirs(os.path.dirname(GLAVA_THEME_FILE), exist_ok=True)
    with open(GLAVA_THEME_FILE, "w") as f:
        f.write(theme)

def _apply_theme_full(theme):
    """Apply theme colors to ALL glava shader files (graph, bars, radial, wave)."""
    if theme not in _THEME_COLORS:
        return
    c1, c2 = _THEME_COLORS[theme]
    glsl_files = [
        os.path.expanduser("~/.config/glava/graph.glsl"),
        os.path.expanduser("~/.config/glava/bars.glsl"),
        os.path.expanduser("~/.config/glava/radial.glsl"),
        os.path.expanduser("~/.config/glava/wave.glsl"),
    ]
    import re
    for glsl_file in glsl_files:
        if not os.path.exists(glsl_file):
            continue
        txt = open(glsl_file).read()
        # graph / radial: update mix() gradient colors
        txt = re.sub(
            r'mix\(#[0-9A-Fa-f]{6}, #[0-9A-Fa-f]{6}',
            f'mix({c1}, {c2}',
            txt
        )
        # bars / radial: set solid COLOR macro (gradient, already-solid,
        # and radial's "#define COLOR (#hex * (...))" scaled form)
        if 'bars.glsl' in glsl_file or 'radial.glsl' in glsl_file:
            txt = re.sub(
                r'#define COLOR \(#[0-9A-Fa-f]{6} \* GRADIENT\)',
                f'#define COLOR {c1}',
                txt
            )
            txt = re.sub(
                r'^#define COLOR #[0-9A-Fa-f]{6}$',
                f'#define COLOR {c1}',
                txt,
                flags=re.MULTILINE
            )
            txt = re.sub(
                r'^#define COLOR \(#[0-9A-Fa-f]{6} \* \(',
                f'#define COLOR ({c1} * (',
                txt,
                flags=re.MULTILINE
            )
        # wave: set BASE_COLOR vec4 from first theme color c1
        if 'wave.glsl' in glsl_file:
            r = int(c1[1:3], 16) / 255.0
            g = int(c1[3:5], 16) / 255.0
            b = int(c1[5:7], 16) / 255.0
            txt = re.sub(
                r'#define BASE_COLOR vec4\([^)]+\)',
                f'#define BASE_COLOR vec4({r:.3f}, {g:.3f}, {b:.3f}, 1)',
                txt
            )
        with open(glsl_file, "w") as f:
            f.write(txt)


class BottomBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._stats = {}
        self._ws = []
        self._ws_rects = []
        self._win_rect = None
        self._hover_win = False
        self._hover_glava = False
        self._hover_sw = False
        self._glava_on = _glava_running()
        self._accent = _bar_accent()   # color derived from glava.theme
        self.setMouseTracking(True)

        t = QTimer(self); t.timeout.connect(self._refresh); t.start(2000)
        tw = QTimer(self); tw.timeout.connect(self._refresh_ws); tw.start(1000)
        QTimer.singleShot(100, self._refresh)

    def _refresh(self):
        self._accent = _bar_accent()   # pick up theme file changes
        self._glava_on = _glava_running()
        bat_pct, bat_txt = _battery()
        self._stats = {
            "cpu": _cpu(), "mem": _mem_pct(), "disk": _disk_pct(),
            "net": _net(), "uptime": _uptime(),
            "wifi": _network(), "vol": _volume(),
            "bat": bat_txt, "bat_pct": bat_pct,
            "win": _active_window(),
        }
        self.update()

    def _refresh_ws(self):
        ws = _workspaces()
        win = _active_window()
        if ws != self._ws or win != self._stats.get("win"):
            self._ws = ws
            self._stats["win"] = win
            self.update()

    def mousePressEvent(self, e):
        x = int(e.position().x())
        # Window switcher button
        if self._win_rect and self._win_rect[0] <= x <= self._win_rect[1]:
            subprocess.Popen(["rofi", "-show", "window"],
                             start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        # Workspace buttons
        for x0, x1, name in self._ws_rects:
            if x0 <= x <= x1:
                subprocess.Popen(["i3-msg", "workspace", name],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        # [COLOR] button: cycle glava theme (left-click)
        if self._color_rect and self._color_rect[0] <= x <= self._color_rect[1]:
            self._cycle_glava_theme()
            return
        # [GLAVA] button: left-click toggles, right-click cycles theme
        if self._glava_rect and self._glava_rect[0] <= x <= self._glava_rect[1]:
            if e.button() == Qt.RightButton:
                self._cycle_glava_theme()
            else:
                self._toggle_glava()
            return

    def mouseMoveEvent(self, e):
        x = int(e.position().x())
        hov_win = bool(self._win_rect) and (self._win_rect[0] <= x <= self._win_rect[1])
        if hov_win != self._hover_win:
            self._hover_win = hov_win
            self.update()
        # [GLAVA] button hover
        if self._glava_rect:
            if self._glava_rect[0] <= x <= self._glava_rect[1]:
                if not self._hover_glava:
                    self._hover_glava = True
                    self.update()
            elif self._hover_glava:
                self._hover_glava = False
                self.update()
        # [COLOR] button hover
        if self._color_rect:
            if self._color_rect[0] <= x <= self._color_rect[1]:
                if not self._hover_sw:
                    self._hover_sw = True
                    self.update()
            elif self._hover_sw:
                self._hover_sw = False
                self.update()

    def leaveEvent(self, e):
        if self._hover_win:
            self._hover_win = False; self.update()
        if self._hover_glava:
            self._hover_glava = False; self.update()
        if getattr(self, '_hover_sw', False):
            self._hover_sw = False; self.update()
        super().leaveEvent(e)

    def _toggle_glava(self):
        """Toggle glava on/off via the module-level start/stop helpers."""
        if self._glava_on:
            _stop_glava()
        else:
            _start_glava()
        self._glava_on = _glava_running()
        self._accent = _bar_accent()
        self.update()

    def _cycle_glava_theme(self):
        """Cycle through glava color themes and update all shader files."""
        current = _read_theme()
        try:
            idx = GLAVA_THEMES.index(current)
        except ValueError:
            idx = 0
        next_theme = GLAVA_THEMES[(idx + 1) % len(GLAVA_THEMES)]
        _write_theme(next_theme)
        _apply_theme_full(next_theme)
        # Restart glava if running so the new theme colors take effect.
        if self._glava_on:
            _stop_glava()
            _start_glava()
            self._glava_on = _glava_running()
        self._accent = _bar_accent()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), BG)

        f = QFont("JetBrains Mono", 10, QFont.Bold)
        p.setFont(f)
        fm = QFontMetrics(f)
        y = H - (H - fm.ascent()) // 2 - 2

        x = 6
        # ── Workspaces ────────────────────────────────────────────────
        self._ws_rects = []
        for name, focused, urgent in self._ws:
            tw = fm.horizontalAdvance(name)
            bw = tw + 14
            if focused:
                p.fillRect(x, 3, bw, H - 6, WS_BG)
                p.setPen(self._accent)
            elif urgent:
                p.setPen(RED)
            else:
                p.setPen(DIM)
            p.drawText(x + 7, y, name)
            self._ws_rects.append((x, x + bw, name))
            x += bw + 2
        x += 8

        # ── Stats ─────────────────────────────────────────────────────
        s = self._stats
        cpu = s.get("cpu", 0); mem = s.get("mem", 0); disk = s.get("disk", 0)
        def cpu_color(v): return RED if v >= 80 else AMBER if v >= 50 else GREEN
        bat_pct = s.get("bat_pct", 100)
        bat_col = RED if bat_pct <= 20 else AMBER if bat_pct <= 40 else GREEN
        SEP = "  │  "
        parts = [
            (self._accent,           f"{USER_TAG}  {datetime.now().strftime('%H:%M:%S  %a %d %b')}"),
            (DIM,            SEP),
            (GREEN,          "⚡ CPU: "),
            (cpu_color(cpu), f"{cpu}%"),
            (DIM,            SEP),
            (GREEN,          "🧠 RAM: "),
            (self._accent,           f"{mem}%"),
            (DIM,            SEP),
            (GREEN,          "💾 /: "),
            (self._accent,           f"{disk}%"),
            (DIM,            SEP),
            (self._accent,           s.get("net", "?")),
            (DIM,            SEP),
        ]
        for color, text in parts:
            p.setPen(color)
            p.drawText(x, y, text)
            x += fm.horizontalAdvance(text)

        # ── Active-window button ──────────────────────────────────────
        win_label = s.get("win", "▣ none")
        if len(win_label) > 28: win_label = win_label[:28] + "…"
        ww = fm.horizontalAdvance(win_label) + 18
        self._win_rect = (x, x + ww)
        p.setPen(Qt.NoPen)
        p.setBrush(WS_BG.lighter(130) if self._hover_win else WS_BG)
        p.drawRoundedRect(x, 3, ww, H - 6, 3, 3)
        p.setPen(self._accent)
        p.drawText(x + 7, y, win_label)
        x += ww + 6

        # ── [COLOR] + [GLAVA] buttons: sizes first (right edge) ───────
        # Buttons use a slightly smaller, letter-spaced label font so the
        # controls read distinctly from the stats text.
        bf = QFont("JetBrains Mono", 9, QFont.Bold)
        bf.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        p.setFont(bf)
        bfm = QFontMetrics(bf)
        by = H - (H - bfm.ascent()) // 2 - 2

        col_w = bfm.horizontalAdvance("COLOR") + 8 + 12 + 7 + 6
        gla_w = bfm.horizontalAdvance("GLAVA") + 8 + 7 + 7 + 6
        gap = 8
        color_x = W - 10 - col_w
        glava_x = color_x - gap - gla_w
        self._color_rect = (color_x, color_x + col_w)
        self._glava_rect = (glava_x, glava_x + gla_w)

        # ── Right-aligned stats (stopped before the buttons) ──────────
        right = [
            (WHITE,        s.get("wifi", "")),
            (self._accent, s.get("vol", "")),
            (bat_col,      s.get("bat", "")),
            (GREEN,        s.get("uptime", "")),
        ]
        right = [(c, t) for c, t in right if t]
        rx = glava_x - 14
        for color, text in reversed(right):
            rx -= fm.horizontalAdvance(text)
            p.setPen(color)
            p.drawText(rx, y, text)
            rx -= fm.horizontalAdvance(SEP)
            if (color, text) != right[0]:
                p.setPen(DIM)
                p.drawText(rx, y, SEP)

        # ── [GLAVA] toggle button ─────────────────────────────────────
        on = self._glava_on
        p.setPen(self._accent if on else DIM)
        p.setBrush(WS_BG.lighter(135) if self._hover_glava else WS_BG)
        p.drawRoundedRect(glava_x, 3, gla_w, H - 6, 4, 4)
        dot = 7
        dotx = glava_x + 8
        p.setPen(Qt.NoPen)
        p.setBrush(self._accent if on else QColor(90, 90, 90))
        p.drawEllipse(dotx, (H - dot) // 2, dot, dot)
        p.setPen(self._accent if on else WHITE)
        p.drawText(dotx + dot + 7, by, "GLAVA")

        # ── [COLOR] cycle button ──────────────────────────────────────
        p.setPen(DIM)
        p.setBrush(WS_BG.lighter(135) if self._hover_sw else WS_BG)
        p.drawRoundedRect(color_x, 3, col_w, H - 6, 4, 4)
        sw = 12
        swx = color_x + 8
        p.setPen(Qt.NoPen)
        p.setBrush(self._accent)
        p.drawRoundedRect(swx, (H - sw) // 2, sw, sw, 2, 2)
        p.setPen(WHITE)
        p.drawText(swx + sw + 7, by, "COLOR")

        p.end()
