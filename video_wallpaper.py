"""video_wallpaper.py - looping, cover-fit video wallpaper.

Mirrors how the fwm window manager does it ([[wallpaper]] fit = "video"):
a frameless window pinned to the desktop layer (`_NET_WM_WINDOW_TYPE_DESKTOP`)
that plays a video scaled to *cover* the whole screen (preserve aspect ratio
and crop the overflow - no stretching, no letterbox bars).

The video is decoded in-process: the player's QVideoSink delivers each frame,
the current frame is cached as a QImage, and paintEvent draws it with a manual
cover transform. This keeps the wallpaper a single plain widget, so it reliably
stays behind real windows and clips/covers on any compositor.

Usage:
    from video_wallpaper import VideoWallpaper
    wall = VideoWallpaper("/home/sword/Videos/paper10.mp4")  # or None
    wall.show()
"""
import os
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRectF, QUrl
from PySide6.QtGui import QPainter, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink

DEFAULT_WALLPAPER = os.path.expanduser("~/Videos/paper10_720.mp4")


class VideoWallpaper(QWidget):
    """Full-screen looping video wallpaper on the desktop layer."""

    def __init__(self, path=None, screen_index=0, mirror=False, parent=None):
        super().__init__(parent)
        self._path = None
        self._image = None
        self._mirror = mirror
        self._video_w = 0
        self._video_h = 0

        # Pin on top of the desktop background but below every real window.
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnBottomHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_X11NetWmWindowTypeDesktop)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Cover exactly the physical screen we were told to decorate.
        screens = QApplication.screens()
        idx = max(0, min(screen_index, len(screens) - 1))
        geo = screens[idx].geometry()
        self.setGeometry(geo)

        # Audio is muted - this is a wallpaper, not a player.
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.0)

        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        self._sink = QVideoSink(self)              # capture frames in-process
        self._player.setVideoOutput(self._sink)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

        if path:
            self.set_video(path)

    # -- public API ---------------------------------------------------------

    def set_video(self, path):
        """Load a new looping video wallpaper. Replaces the current one."""
        path = os.path.expanduser(path)
        if self._path == path:
            return
        self._path = path
        if not os.path.exists(path):
            print(f"[video_wallpaper] file not found: {path}")
            return
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def path(self):
        return self._path

    def set_mirror(self, on):
        if on != self._mirror:
            self._mirror = on
            self.update()

    # -- media callbacks ----------------------------------------------------

    def _on_frame(self, frame):
        img = frame.toImage()
        if img.isNull():
            return
        # Some backends never emit videoSizeChanged, so take the size from the
        # frame itself to keep cover-fit correct.
        if self._video_w != img.width() or self._video_h != img.height():
            self._video_w, self._video_h = img.width(), img.height()
        self._image = img
        self.update()

    def _on_status(self, status):
        # Loop: when the clip reaches the end, restart from 0.
        if status == QMediaPlayer.EndOfMedia:
            self._player.setPosition(0)
            self._player.play()

    def _on_error(self, error, msg):
        # Surface errors instead of silently dying; keep the bar usable.
        print(f"[video_wallpaper] error {error}: {msg}")

    # -- rendering ----------------------------------------------------------

    def _cover_rect(self):
        """Screen rect to draw so the video covers the screen (crops overflow)."""
        ws, hs = self.width(), self.height()
        iw, ih = self._video_w, self._video_h
        if not iw or not ih:
            return QRectF(0, 0, ws, hs)
        scale = max(ws / iw, hs / ih)
        dw, dh = iw * scale, ih * scale
        dx = (ws - dw) / 2.0
        dy = (hs - dh) / 2.0
        return QRectF(dx, dy, dw, dh)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # Solid black underlay in case bounds are briefly 0 or during load.
        p.fillRect(self.rect(), QColor(0, 0, 0))
        img = self._image
        if img is not None and not img.isNull():
            target = self._cover_rect()
            if self._mirror:
                # Horizontally mirrored ("selfie") wallpaper. Off by default.
                p.save()
                p.translate(target.center().x(), 0)
                p.scale(-1.0, 1.0)
                p.translate(-target.center().x(), 0)
                p.drawImage(target, img)
                p.restore()
            else:
                p.drawImage(target, img)
        p.end()


def run_wallpaper(path=None, screen_index=0, mirror=False):
    """Standalone entry point: app.run() a wallpaper-only process."""
    import sys
    app = QApplication(sys.argv)
    wall = VideoWallpaper(path, screen_index=screen_index, mirror=mirror)
    wall.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Looping video wallpaper")
    parser.add_argument("--wallpaper", default=DEFAULT_WALLPAPER,
                        help="Path to the video (mp4/webm/mkv...). Default: paper10.mp4")
    parser.add_argument("--screen", type=int, default=0,
                        help="Monitor index to cover (default 0)")
    parser.add_argument("--mirror", action="store_true",
                        help="Draw the video horizontally mirrored")
    args = parser.parse_args()
    run_wallpaper(args.wallpaper, args.screen, args.mirror)
