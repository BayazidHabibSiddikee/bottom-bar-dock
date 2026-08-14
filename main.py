#!/usr/bin/env python3
"""Standalone bottom bar dock — replaces i3bar."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from bottom_bar import BottomBar

if __name__ == "__main__":
    app = QApplication(sys.argv)
    bar = BottomBar()
    bar.setWindowFlags(Qt.FramelessWindowHint)
    bar.setAttribute(Qt.WA_X11NetWmWindowTypeDock)
    bar.setFixedSize(1920, 32)
    bar.move(0, 1080 - 32)
    bar.setWindowTitle("sworddeck-bar")
    bar.show()
    sys.exit(app.exec())
