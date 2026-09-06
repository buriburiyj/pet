import json
import pathlib
import subprocess
import sys
import time

from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF
from PyQt6.QtGui import (QCursor, QImage, QKeySequence, QPainter, QPixmap,
                         QShortcut)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

STATE = pathlib.Path(__file__).with_name("state.json")
PROJECT = pathlib.Path.home() / "dev" / "pet"



class Pet(QWidget):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)

        s = self.load()
        self.size_px = s.get("size", 160)
        self._drag = QPoint()
        self.following = False
        self.facing = 1
        self.tick = 0
        self.bob = 0
        self.fx = float(s.get("x", 600))
        self.fy = float(s.get("y", 400))

        self.img = QImage(path) if path else QImage()
        self.flipped = self.img.mirrored(True, False) if not self.img.isNull() else QImage()

        self.resize(self.size_px, self.size_px)
        self.move(s.get("x", 600), s.get("y", 400))

        self.anim = QTimer(self)
        self.anim.timeout.connect(self.beat)
        self.anim.start(16)

        for keys, fn in [
            ("F", self.toggle_follow),
            ("+", lambda: self.apply_size(self.size_px + 32)),
            ("=", lambda: self.apply_size(self.size_px + 32)),
            ("-", lambda: self.apply_size(self.size_px - 32)),
            ("0", lambda: self.apply_size(160)),
            ("Q", self.close),
        ]:
            sc = QShortcut(QKeySequence(keys), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(fn)

    def apply_size(self, px):
        self.size_px = max(64, min(480, px))
        self.resize(self.size_px, self.size_px)
        self.update()

    def toggle_follow(self):
        self.following = not self.following

    def beat(self):
        self.tick += 1
        if self.tick % 5 == 0:
            self.bob = (0, 1, 2, 2, 1, 0, -1, -1)[(self.tick // 5) % 8]

        c = QCursor.pos()
        cx = self.x() + self.size_px / 2
        if abs(c.x() - cx) > 12:
            self.facing = 1 if c.x() > cx else -1

        if self.following:
            tx = c.x() - self.size_px / 2
            ty = c.y() + 24
            self.fx += (tx - self.fx) * 0.12
            self.fy += (ty - self.fy) * 0.12
            self.move(round(self.fx), round(self.fy))
        self.update()

    def paintEvent(self, e):
        if self.img.isNull():
            return
        src = self.flipped if self.facing > 0 else self.img
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        n = src.width()
        k = max(1, self.size_px // n)
        side = n * k
        ox = (self.size_px - side) / 2
        oy = (self.size_px - side) / 2 + self.bob
        p.drawImage(QRectF(ox, oy, side, side), src,
                    QRectF(0, 0, n, src.height()))
        p.end()

    def menu(self, pos):
        m = QMenu(self)
        m.addAction("따라오기 끄기" if self.following else "따라오기 켜기 (F)").triggered.connect(self.toggle_follow)
        m.addAction("크게 (+)").triggered.connect(lambda: self.apply_size(self.size_px + 32))
        m.addAction("작게 (-)").triggered.connect(lambda: self.apply_size(self.size_px - 32))
        m.addAction("기본 크기 (0)").triggered.connect(lambda: self.apply_size(160))
        m.addSeparator()
        m.addAction("opencode 열기").triggered.connect(self.launch)
        m.addSeparator()
        m.addAction("닫기 (Q)").triggered.connect(self.close)
        m.exec(self.mapToGlobal(pos))

    def mousePressEvent(self, e):
        self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._press = e.globalPosition().toPoint()
        self._moved = False
        self._t = time.monotonic()
        self.activateWindow()

    def mouseReleaseEvent(self, e):
        if self.following:
            return
        if getattr(self, "_moved", True):
            return
        if time.monotonic() - getattr(self, "_t", 0) > 0.35:
            return
        self.launch()

    def launch(self):
        cmd = 'cd {} && opencode'.format(PROJECT)
        subprocess.Popen([
            "osascript",
            "-e", 'tell application "Terminal" to do script "{}"'.format(cmd),
            "-e", 'tell application "Terminal" to activate',
        ])

    def mouseMoveEvent(self, e):
        q0 = e.globalPosition().toPoint()
        if hasattr(self, "_press"):
            d = (q0 - self._press)
            if abs(d.x()) + abs(d.y()) > 4:
                self._moved = True
        if not self.following:
            q = q0 - self._drag
            self.move(q)
            self.fx, self.fy = float(q.x()), float(q.y())

    def wheelEvent(self, e):
        d = e.angleDelta().y()
        if d:
            self.apply_size(self.size_px + (16 if d > 0 else -16))

    def mouseDoubleClickEvent(self, e):
        pass

    def load(self):
        try:
            return json.loads(STATE.read_text())
        except Exception:
            return {}

    def closeEvent(self, e):
        STATE.write_text(json.dumps(
            {"size": self.size_px, "x": self.x(), "y": self.y()}))


import socket
_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    _lock.bind(("127.0.0.1", 51737))
except OSError:
    print("이미 실행 중")
    sys.exit(0)

try:
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
except Exception:
    NSApplication = None

app = QApplication(sys.argv)


def all_spaces(w=None):
    try:
        from AppKit import NSApp
    except Exception:
        print("pyobjc 없음")
        return
    n = 0
    for nw in NSApp.windows():
        nw.setCollectionBehavior_(1 << 0 | 1 << 8)
        n += 1
    print("공간 설정한 창 수:", n)
pet = Pet(sys.argv[1] if len(sys.argv) > 1 else None)
pet.show()
pet.raise_()
pet.activateWindow()
from PyQt6.QtCore import QTimer as _T
_T.singleShot(500, all_spaces)
_T.singleShot(2000, all_spaces)
sys.exit(app.exec())
