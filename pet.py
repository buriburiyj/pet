import json
import pathlib
import subprocess
import sys
import time

from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF, QPointF
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

        # Space-change fly-in animation state
        self._flying = False
        self._fly_t = 0.0
        self._fly_start = QPointF()
        self._fly_target = QPointF()

        self.resize(self.size_px, self.size_px)
        _x, _y = int(s.get("x", 600)), int(s.get("y", 400))
        _g = QApplication.primaryScreen().availableGeometry()
        _x = max(_g.left(), min(_x, _g.right() - self.width()))
        _y = max(_g.top(), min(_y, _g.bottom() - self.height()))
        self.move(_x, _y)
        self.fx, self.fy = float(_x), float(_y)

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

    def fly_in(self):
        """Start fly-in animation from below-screen to current position."""
        if self._flying:
            return
        self._flying = True
        self._fly_t = 0.0
        screen = QApplication.primaryScreen()
        sh = screen.size().height() if screen else 1080
        self._fly_start = QPointF(self.fx, self.fy + sh + 100)
        self._fly_target = QPointF(self.fx, self.fy)
        self._fly_timer = QTimer(self)
        self._fly_timer.timeout.connect(self._fly_tick)
        self._fly_timer.start(16)

    def _fly_tick(self):
        self._fly_t += 1
        dt = self._fly_t / 20.0
        if dt >= 1.0:
            self._fly_t = 20
            self._fly_timer.stop()
            self._flying = False
            return
        # ease-out cubic
        t = 1.0 - (1.0 - dt) ** 3
        self.fx = self._fly_start.x() + (self._fly_target.x() - self._fly_start.x()) * t
        self.fy = self._fly_start.y() + (self._fly_target.y() - self._fly_start.y()) * t
        self.move(round(self.fx), round(self.fy))
        self.update()

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

    def keyPressEvent(self, e):

        try:

            nvk = int(e.nativeVirtualKey())

        except Exception:

            nvk = -1

        t, k = e.text(), None

        if t in ("f", "F", "\u3139") or nvk == 3:

            k = "f"

        elif t in ("q", "Q", "\u3142") or nvk == 12:

            k = "q"

        elif t in ("+", "=") or nvk in (24, 69):

            k = "+"

        elif t == "-" or nvk in (27, 78):

            k = "-"

        elif t == "0" or nvk in (29, 82):

            k = "0"

        if k == "f":

            self.following = not self.following

            print("따라오기:", self.following)

        elif k == "q":

            self.close()

        elif k in ("+", "-", "0"):

            cur = getattr(self, "size_px", 160)

            n = {"+": cur + 16, "-": cur - 16, "0": 160}[k]

            n = max(64, min(480, n))

            if hasattr(self, "apply_size"):

                self.apply_size(n)

            else:

                self.size_px = n

                self.resize(n, n)

            print("크기:", n)


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
    for nw in NSApp.windows():
        nw.setCollectionBehavior_(1 << 0 | 1 << 8)
        nw.setLevel_(25)
pet = Pet(sys.argv[1] if len(sys.argv) > 1 else None)
pet.show()
pet.raise_()
pet.activateWindow()

def _on_space_change(noti, pet_instance=pet):
    """Called when the active space changes – trigger fly-in animation."""
    pet_instance.fly_in()

try:
    from AppKit import NSWorkspace
    _center = NSWorkspace.sharedWorkspace().notificationCenter()
    _center.addObserverForName_object_queueUsingBlock_(
        "NSWorkspaceActiveSpaceDidChangeNotification", None, None, _on_space_change)
except Exception as e:
    print("스페이스 변경 감지 설정 실패:", e)

from PyQt6.QtCore import QTimer as _T
_T.singleShot(300, all_spaces)
_keep = _T()
_keep.timeout.connect(all_spaces)
_keep.start(1500)

# ==== 데스크톱 전환 연출 ====
try:
    import math as _m, time as _tm
    from PyQt6.QtGui import QCursor as _QCursor
    from Foundation import NSObject as _NSObject
    from AppKit import NSWorkspace as _NSWorkspace

    _FLY_MS = 650.0
    _fly = {"on": False, "t0": 0.0, "sx": 0.0, "sy": 0.0, "tx": 0.0, "ty": 0.0}

    def _start_fly():
        scr = (pet.screen() or QApplication.primaryScreen()).geometry()
        w, h = pet.width(), pet.height()
        if pet.following:
            c = _QCursor.pos()
            tx, ty = c.x() - w / 2, c.y() - h / 2
        else:
            tx, ty = pet.fx, pet.fy
        if tx + w / 2 > scr.center().x():
            sx = scr.left() - w * 0.6
        else:
            sx = scr.right() + w * 0.6
        _fly.update(on=True, t0=_tm.monotonic(), sx=sx, sy=ty + 70, tx=tx, ty=ty)
        pet.fx, pet.fy = sx, ty + 70

    def _fly_step():
        if not _fly["on"]:
            return
        if pet.following:
            c = _QCursor.pos()
            _fly["tx"] = c.x() - pet.width() / 2
            _fly["ty"] = c.y() - pet.height() / 2
        t = (_tm.monotonic() - _fly["t0"]) * 1000.0 / _FLY_MS
        if t >= 1.0:
            pet.fx, pet.fy = _fly["tx"], _fly["ty"]
            _fly["on"] = False
            return
        e = 1 - (1 - t) ** 3
        pet.fx = _fly["sx"] + (_fly["tx"] - _fly["sx"]) * e
        pet.fy = _fly["sy"] + (_fly["ty"] - _fly["sy"]) * e - _m.sin(_m.pi * t) * 26

    _ftimer = QTimer(pet)
    _ftimer.timeout.connect(_fly_step)
    _ftimer.start(16)

    class _SpaceWatch(_NSObject):
        def spaceChanged_(self, noti):
            print("전환 감지")
            _start_fly()

    _sw = _SpaceWatch.alloc().init()
    _NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
        _sw, b"spaceChanged:", "NSWorkspaceActiveSpaceDidChangeNotification", None)
    print("전환 감지 등록됨")
except Exception as _e:
    print("전환 연출 실패:", _e)


# ==== 장난 동작 ====
try:
    import math as _mm, random as _rd, time as _tt
    _mis = {"kind": None, "t0": 0.0, "next": _tt.monotonic() + 4.0,
            "bx": 0.0, "by": 0.0}

    def _mis_step():
        now = _tt.monotonic()
        if _mis["kind"] is None:
            if pet.following or getattr(pet, "_flying", False) or now < _mis["next"]:
                return
            _mis["kind"] = _rd.choice(["hop", "hop", "wiggle"])
            _mis["t0"] = now
            _mis["bx"], _mis["by"] = pet.fx, pet.fy
            return
        t = now - _mis["t0"]
        if _mis["kind"] == "hop":
            if t > 1.0:
                pet.fx, pet.fy = _mis["bx"], _mis["by"]
                pet.move(round(pet.fx), round(pet.fy))
                _mis["kind"] = None
                _mis["next"] = now + _rd.uniform(5, 10)
                return
            h = abs(_mm.sin(_mm.pi * t * 2)) * 18
            pet.fy = _mis["by"] - h
            pet.move(round(pet.fx), round(pet.fy))
        else:
            if t > 0.8:
                pet.fx, pet.fy = _mis["bx"], _mis["by"]
                pet.move(round(pet.fx), round(pet.fy))
                _mis["kind"] = None
                _mis["next"] = now + _rd.uniform(5, 10)
                return
            pet.fx = _mis["bx"] + _mm.sin(t * 22) * 5
            pet.move(round(pet.fx), round(pet.fy))

    _mtimer = QTimer(pet)
    _mtimer.timeout.connect(_mis_step)
    _mtimer.start(16)
    print("장난 동작 등록됨")
except Exception as _e:
    print("장난 동작 실패:", _e)

sys.exit(app.exec())
