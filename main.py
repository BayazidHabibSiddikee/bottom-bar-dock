#!/usr/bin/env python3
"""Standalone bottom bar dock — replaces i3bar."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from bottom_bar import BottomBar


def main():
    W, H = 1920, 32
    if len(sys.argv) > 1:
        try:
            parts = sys.argv[1].lower().replace("x", " ").split()
            W, H = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
    
    app = QApplication(sys.argv)
    screen_h = app.primaryScreen().geometry().height()
    bar = BottomBar()
    bar.setWindowFlags(Qt.FramelessWindowHint)
    bar.setAttribute(Qt.WA_X11NetWmWindowTypeDock)
    bar.setFixedSize(W, H)
    bar.move(0, screen_h - H)
    bar.setWindowTitle("sworddeck-bar")
    bar.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
