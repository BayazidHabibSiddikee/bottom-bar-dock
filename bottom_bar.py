"""bottom_bar.py — always-visible dock bar (replaces i3bar)

Left:  clickable workspace buttons
Mid:   time · CPU · RAM · disk · net speed · active window
Right: wifi SSID + IP · volume · battery · uptime
"""
import os, json, getpass, subprocess
from datetime import datetime

USER_TAG = f"[{getpass.getuser().upper()}]"
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics

CYAN  = QColor(97, 175, 239)    # One Dark blue
GREEN = QColor(152, 195, 121)   # One Dark green
AMBER = QColor(229, 192, 123)   # One Dark yellow
RED   = QColor(224, 108, 117)   # One Dark red
DIM   = QColor(62, 68, 81)      # One Dark dark gray
WHITE = QColor(171, 178, 191)   # One Dark foreground
BG    = QColor(40, 44, 52, 255) # One Dark bg
WS_BG = QColor(62, 68, 81, 255) # One Dark dark gray for workspace bg


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
    # diff /proc/net/dev between refresh ticks (no blocking subprocess)
    try:
        rx = tx = 0
        for line in open("/proc/net/dev").readlines()[2:]:
            name, data = line.split(":", 1)
            if name.strip() == "lo":
                continue
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
    if not title:
        return "▣ none"
    title = f"▣ {title}"
    return (title[:45] + "…") if len(title) > 45 else title


def _uptime():
    try:
        secs = float(open("/proc/uptime").read().split()[0])
        return f"↑ {int(secs//3600)}h {int((secs%3600)//60)}m"
    except Exception:
        return "↑ ?"


_NET_ICONS = {
    "wifi": "📶", "ethernet": "🔌",
    "gsm": "📡", "cdma": "📡", "wimax": "📡",  # mobile broadband / modem
}


def _network():
    """Active connection name + type, via nmcli — works for wifi, wired
    ethernet, and mobile broadband/USB modem connections alike (not just
    wifi), so the bar is accurate regardless of how the box is online."""
    name, icon = "—", "🌐"
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"],
            timeout=1, text=True)
        best = None
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) < 3:
                continue
            dtype, state, conn = parts[0], parts[1], parts[2]
            if state == "connected" and conn and conn != "--":
                best = (dtype, conn)
                if dtype == "wifi":
                    break   # prefer wifi if several devices are up at once
        if best:
            dtype, conn = best
            name = conn
            icon = _NET_ICONS.get(dtype, "🌐")
    except Exception:
        # nmcli not available — fall back to a plain wifi SSID check
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"], timeout=1,
                                           text=True).strip()
            if ssid:
                name, icon = ssid, "📶"
        except Exception:
            pass
    ip = "?"
    try:
        for line in subprocess.check_output(
                ["ip", "-4", "-o", "addr", "show", "scope", "global"],
                timeout=1, text=True).splitlines():
            ip = line.split()[3].split("/")[0]
            break
    except Exception:
        pass
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


class BottomBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._stats = {}
        self._ws = []
        self._ws_rects = []   # (x0, x1, name) for click handling
        self._win_rect = None          # (x0, x1) of the current-window button
        self._hover_win = False        # mouse over the current-window button
        self.setMouseTracking(True)    # so we can highlight the button on hover

        t = QTimer(self); t.timeout.connect(self._refresh); t.start(2000)
        tw = QTimer(self); tw.timeout.connect(self._refresh_ws); tw.start(500)
        QTimer.singleShot(100, self._refresh)

    def _refresh(self):
        bat_pct, bat_txt = _battery()
        self._stats = {
            "cpu": _cpu(), "mem": _mem_pct(), "disk": _disk_pct(),
            "net": _net(), "uptime": _uptime(),
            "wifi": _network(), "bat": bat_txt, "bat_pct": bat_pct,
            "vol": _volume(), "win": _active_window(),
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
        # Current-window button (far-left): open the window switcher.
        if self._win_rect and self._win_rect[0] <= x <= self._win_rect[1]:
            subprocess.Popen(["rofi", "-show", "window"],
                             start_new_session=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return
        # Workspace buttons
        for x0, x1, name in self._ws_rects:
            if x0 <= x <= x1:
                subprocess.Popen(["i3-msg", "workspace", name],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return

    def mouseMoveEvent(self, e):
        x = int(e.position().x())
        hov = bool(self._win_rect) and (self._win_rect[0] <= x <= self._win_rect[1])
        if hov != self._hover_win:
            self._hover_win = hov
            self.update()

    def leaveEvent(self, e):
        if self._hover_win:
            self._hover_win = False
            self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), BG)

        f = QFont("JetBrains Mono", 10, QFont.Bold)
        p.setFont(f)
        fm = QFontMetrics(f)
        y = H - (H - fm.ascent()) // 2 - 2

        # Workspaces start at the left edge. The active-window button now lives
        # in the center of the bar (rendered below after the stats).
        x = 6

        # ── Workspaces (clickable) ───────────────────────────────────
        self._ws_rects = []
        for name, focused, urgent in self._ws:
            tw = fm.horizontalAdvance(name)
            bw = tw + 14
            if focused:
                p.fillRect(x, 3, bw, H - 6, WS_BG)
                p.setPen(CYAN)
            elif urgent:
                p.setPen(RED)
            else:
                p.setPen(DIM)
            p.drawText(x + 7, y, name)
            self._ws_rects.append((x, x + bw, name))
            x += bw + 2
        x += 8

        # ── Stats ────────────────────────────────────────────────────
        now = datetime.now()
        s = self._stats
        cpu = s.get("cpu", 0); mem = s.get("mem", 0); disk = s.get("disk", 0)

        def cpu_color(v):
            return RED if v >= 80 else AMBER if v >= 50 else GREEN

        bat_pct = s.get("bat_pct", 100)
        bat_col = RED if bat_pct <= 20 else AMBER if bat_pct <= 40 else GREEN

        SEP = "  │  "
        parts = [
            (CYAN,           f"{USER_TAG}  {now.strftime('%H:%M:%S  %a %d %b')}"),
            (DIM,            SEP),
            (GREEN,          "⚡ CPU: "),
            (cpu_color(cpu), f"{cpu}%"),
            (DIM,            SEP),
            (GREEN,          "🧠 RAM: "),
            (CYAN,           f"{mem}%"),
            (DIM,            SEP),
            (GREEN,          "💾 /: "),
            (CYAN,           f"{disk}%"),
            (DIM,            SEP),
            (CYAN,           s.get("net", "?")),
            (DIM,            SEP),
        ]
        for color, text in parts:
            p.setPen(color)
            p.drawText(x, y, text)
            x += fm.horizontalAdvance(text)

        # ── Active-window button (center, clickable -> rofi window switcher) ──
        win_label = self._stats.get("win", "▣ none")
        if len(win_label) > 28:
            win_label = win_label[:28] + "…"
        ww = fm.horizontalAdvance(win_label) + 18
        self._win_rect = (x, x + ww)
        p.setPen(Qt.NoPen)
        p.setBrush(WS_BG.lighter(130) if self._hover_win else WS_BG)
        p.drawRoundedRect(x, 3, ww, H - 6, 3, 3)
        p.setPen(CYAN)
        p.drawText(x + 7, y, win_label)
        x += ww + 6

        # ── Right-aligned: wifi · volume · battery · uptime ─────────
        right = [
            (WHITE,   s.get("wifi", "")),
            (CYAN,    s.get("vol", "")),
            (bat_col, s.get("bat", "")),
            (GREEN,   s.get("uptime", "")),
        ]
        right = [(c, t) for c, t in right if t]
        rx = W - 10
        for color, text in reversed(right):
            rx -= fm.horizontalAdvance(text)
            p.setPen(color)
            p.drawText(rx, y, text)
            rx -= fm.horizontalAdvance(SEP)
            if (color, text) != right[0]:
                p.setPen(DIM)
                p.drawText(rx, y, SEP)

        p.end()
