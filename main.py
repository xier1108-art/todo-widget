#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""할일위젯 v4.2.0 — PyQt6 | 드래그 정렬 · 색상 설정 · 헤더 우클릭 · 백업/복원"""

import sys
import json
import shutil
import winreg
from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect, QSizePolicy,
    QSizeGrip, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QPoint, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QPixmap, QPainter, QPen, QAction, QPalette,
)

# ── 상수 ───────────────────────────────────────────────────────────────────────
APP_NAME   = "할일위젯"
APP_VER    = "4.1.0"
FONT       = "맑은 고딕"
SHADOW_PAD = 14
RADIUS     = 8

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "todos.json"

# ── 테마 ───────────────────────────────────────────────────────────────────────
THEMES = {
    "yellow": dict(
        bg="#FFFDE7", header="#F57F17", card="#FFF9C4",
        border="#FFD54F", accent="#E65100", accent_h="#BF360C",
        fg="#333333",   muted="#795548", done_fg="#BCAAA4",
    ),
    "blue": dict(
        bg="#E3F2FD", header="#1565C0", card="#BBDEFB",
        border="#90CAF9", accent="#1565C0", accent_h="#0D47A1",
        fg="#212121",   muted="#546E7A", done_fg="#90A4AE",
    ),
    "green": dict(
        bg="#E8F5E9", header="#2E7D32", card="#C8E6C9",
        border="#A5D6A7", accent="#1B5E20", accent_h="#004D40",
        fg="#212121",   muted="#558B2F", done_fg="#A5D6A7",
    ),
    "pink": dict(
        bg="#FCE4EC", header="#C2185B", card="#F8BBD9",
        border="#F48FB1", accent="#880E4F", accent_h="#AD1457",
        fg="#212121",   muted="#C2185B", done_fg="#F48FB1",
    ),
    "dark": dict(
        bg="#2D2D2D", header="#1A1A1A", card="#3D3D3D",
        border="#4A4A4A", accent="#BB86FC", accent_h="#9965E8",
        fg="#EEEEEE",   muted="#888888", done_fg="#555555",
    ),
    "midnight": dict(
        bg="#0D1117", header="#161B22", card="#21262D",
        border="#30363D", accent="#58A6FF", accent_h="#388BFD",
        fg="#E6EDF3",   muted="#8B949E", done_fg="#484F58",
    ),
}
THEME_NAMES = {
    "yellow": "노랑 (포스트잇)", "blue": "파랑", "green": "초록",
    "pink": "분홍", "dark": "다크", "midnight": "미드나잇",
}
ITEM_COLORS = [
    None,
    "#FF6B6B", "#FFB347", "#FFD93D", "#6BCB77",
    "#4D96FF", "#C77DFF", "#FF8FAB",
]
DEFAULT_DATA = {
    "window":       {"x": 100, "y": 100, "width": 320, "height": 520},
    "theme":        "yellow",
    "always_on_top": False,
    "opacity":      0.97,
    "font_size":    10,
    "startup":      False,
    "todos":        [],
}

# ── 데이터 I/O ─────────────────────────────────────────────────────────────────
def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in DEFAULT_DATA.items():
            d.setdefault(k, v)
        for k, v in DEFAULT_DATA["window"].items():
            d["window"].setdefault(k, v)
        return d
    except Exception:
        return {k: (v.copy() if isinstance(v, dict) else v)
                for k, v in DEFAULT_DATA.items()}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save] {e}")

def backup_data(data) -> Path:
    """오늘 날짜로 백업 파일 생성. 이미 있으면 덮어씀. 경로 반환."""
    fname = DATA_FILE.parent / f"todos_backup_{date.today().isoformat()}.json"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[backup] {e}")
    return fname

def restore_data(path: Path) -> dict | None:
    """백업 파일에서 데이터 읽기. 실패 시 None."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in DEFAULT_DATA.items():
            d.setdefault(k, v)
        return d
    except Exception as e:
        print(f"[restore] {e}")
        return None

# ── 시작프로그램 ───────────────────────────────────────────────────────────────
def get_startup() -> bool:
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run",
                           0, winreg.KEY_READ)
        winreg.QueryValueEx(k, APP_NAME); winreg.CloseKey(k)
        return True
    except Exception:
        return False

def set_startup(enable: bool):
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
        if enable:
            exe = (f'"{sys.executable}"' if getattr(sys, "frozen", False)
                   else f'"{sys.executable}" "{Path(__file__).resolve()}"')
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, exe)
        else:
            try: winreg.DeleteValue(k, APP_NAME)
            except: pass
        winreg.CloseKey(k)
    except Exception as e:
        print(f"[startup] {e}")

# ── 트레이 아이콘 ──────────────────────────────────────────────────────────────
def make_tray_icon(accent: str = "#58A6FF") -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#161B22")); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    pen = QPen(QColor(accent), 5.5, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(16, 34, 27, 45); p.drawLine(27, 45, 48, 20)
    p.end()
    return QIcon(pix)

# ── 색상 선택 팝업 ─────────────────────────────────────────────────────────────
class ColorPicker(QWidget):
    colorSelected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent,
                         Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        wrap = QHBoxLayout(self); wrap.setContentsMargins(0, 0, 0, 0)
        box  = QWidget(); box.setObjectName("cpBox"); wrap.addWidget(box)
        row  = QHBoxLayout(box); row.setContentsMargins(8, 8, 8, 8); row.setSpacing(6)
        for c in ITEM_COLORS:
            btn = QPushButton(); btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if c is None:
                btn.setStyleSheet("""QPushButton{background:#fff;border-radius:12px;
                    border:2px solid #ccc;color:#aaa;font-size:10px;}
                    QPushButton:hover{border-color:#888;}""")
                btn.setText("✕")
            else:
                btn.setStyleSheet(f"""QPushButton{{background:{c};border-radius:12px;
                    border:2px solid transparent;}}
                    QPushButton:hover{{border-color:white;}}""")
            btn.clicked.connect(lambda _, col=c: self._pick(col))
            row.addWidget(btn)
        box.setStyleSheet("""QWidget#cpBox{background:#2D2D2D;
            border-radius:10px;border:1px solid #444;}""")

    def _pick(self, c):
        self.colorSelected.emit(c); self.close()

    def show_near(self, gpos: QPoint):
        self.adjustSize(); self.move(gpos); self.show()


# ── 드래그 전역 이벤트 필터 ────────────────────────────────────────────────────
class DragFilter(QObject):
    """드래그 도중 전역 마우스 이벤트를 가로채 TodoWidget에 전달"""
    def __init__(self, widget):
        super().__init__(widget)
        self._w = widget

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            self._w._drag_update(event.globalPosition().toPoint())
            return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._w._drag_end(event.globalPosition().toPoint())
            QApplication.instance().removeEventFilter(self)
            return True
        return False


# ── 할일 아이템 위젯 ────────────────────────────────────────────────────────────
class TodoItemWidget(QWidget):
    sig_toggle      = pyqtSignal(int)
    sig_delete      = pyqtSignal(int)
    sig_edit        = pyqtSignal(int, str)
    sig_color       = pyqtSignal(int, object)
    sig_drag_start  = pyqtSignal(int, QPoint)   # item_id, global_pos

    def __init__(self, item: dict, theme: dict, font_size: int = 10, parent=None):
        super().__init__(parent)
        self.item      = item
        self.t         = theme
        self.font_size = font_size
        self._editing  = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._build()

    # ── 빌드 ──────────────────────────────────────────────────────────────────
    def _build(self):
        t    = self.t
        done = self.item.get("done", False)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 8, 0)
        root.setSpacing(0)

        # ① 드래그 핸들 (≡)
        self.drag_handle = QLabel("≡")
        self.drag_handle.setFixedWidth(18)
        self.drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self.drag_handle.setVisible(False)   # 호버 시 표시
        self.drag_handle.mousePressEvent = self._on_drag_press
        root.addWidget(self.drag_handle)

        # ② 컬러 바 (3px 시각적 인디케이터)
        self.color_bar = QWidget()
        self.color_bar.setFixedWidth(3)
        self._refresh_color_bar()
        root.addWidget(self.color_bar)
        root.addSpacing(9)

        # ③ 체크 버튼
        self.check_btn = QPushButton("●" if done else "○")
        self.check_btn.setFixedSize(18, 18)
        self.check_btn.setFlat(True)
        self.check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_btn.clicked.connect(lambda: self.sig_toggle.emit(self.item["id"]))
        root.addWidget(self.check_btn)
        root.addSpacing(7)

        # ④ 텍스트 + 날짜 뱃지
        self._text_wrap = QWidget()
        self._text_wrap.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Preferred)
        tlay = QHBoxLayout(self._text_wrap)
        tlay.setContentsMargins(0, 5, 0, 5); tlay.setSpacing(5)
        self.text_lbl = QLabel(self.item["text"])
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Preferred)
        tlay.addWidget(self.text_lbl)
        badge = self._make_badge()
        if badge:
            tlay.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(self._text_wrap, 1)

        # ⑤ 고스트 버튼 (색상 · 편집 · 삭제) — 호버 시 표시
        self.color_btn = QPushButton("●")   # 색상 선택
        self.color_btn.setFixedSize(22, 22); self.color_btn.setFlat(True)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setVisible(False)
        self.color_btn.clicked.connect(self._on_color_click)

        self.edit_btn = QPushButton("✎")
        self.edit_btn.setFixedSize(22, 22); self.edit_btn.setFlat(True)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setVisible(False)
        self.edit_btn.clicked.connect(self._start_edit)

        self.del_btn = QPushButton("×")
        self.del_btn.setFixedSize(22, 22); self.del_btn.setFlat(True)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setVisible(False)
        self.del_btn.clicked.connect(lambda: self.sig_delete.emit(self.item["id"]))

        root.addWidget(self.color_btn)
        root.addSpacing(1)
        root.addWidget(self.edit_btn)
        root.addSpacing(1)
        root.addWidget(self.del_btn)

        self.setMinimumHeight(38)
        self._style(False)

    # ── 헬퍼 ──────────────────────────────────────────────────────────────────
    def _make_badge(self):
        created = self.item.get("created_date")
        if not created: return None
        try:
            delta = (date.today() - date.fromisoformat(created)).days
            text  = "어제" if delta == 1 else (f"{delta}일 전" if delta > 1 else None)
            if not text: return None
        except Exception: return None
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.t['muted']};font-family:'{FONT}';"
                          f"font-size:8px;background:transparent;")
        return lbl

    def _refresh_color_bar(self):
        c = self.item.get("color")
        self.color_bar.setStyleSheet(f"background:{c};" if c
                                     else "background:transparent;")
        # 색상 버튼도 동기화 (보여질 때)
        if hasattr(self, "color_btn"):
            c2 = c or self.t["muted"]
            self.color_btn.setStyleSheet(
                f"QPushButton{{color:{c2};background:transparent;border:none;"
                f"font-size:12px;border-radius:3px;}}"
                f"QPushButton:hover{{background:{self.t['border']};}}"
            )

    def _on_color_click(self):
        picker = ColorPicker(self)
        picker.colorSelected.connect(
            lambda c: self.sig_color.emit(self.item["id"], c))
        gpos = self.color_btn.mapToGlobal(
            QPoint(self.color_btn.width() // 2,
                   self.color_btn.height() + 2))
        picker.show_near(gpos)

    # ── 드래그 핸들 ────────────────────────────────────────────────────────────
    def _on_drag_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.sig_drag_start.emit(
                self.item["id"],
                event.globalPosition().toPoint()
            )

    # ── 인라인 편집 ────────────────────────────────────────────────────────────
    def _start_edit(self):
        if self._editing: return
        self._editing = True
        t = self.t
        self.text_lbl.hide()
        self._edit_field = QLineEdit(self.item["text"])
        self._edit_field.setStyleSheet(
            f"QLineEdit{{background:{t['card']};color:{t['fg']};"
            f"border:1px solid {t['accent']};border-radius:3px;"
            f"padding:1px 5px;font-family:'{FONT}';font-size:{self.font_size}px;"
            f"selection-background-color:{t['accent']};}}")
        self._text_wrap.layout().insertWidget(0, self._edit_field)
        self._edit_field.setFocus(); self._edit_field.selectAll()
        self._edit_field.returnPressed.connect(self._commit_edit)
        self._edit_field.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_edit_field", None):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self._cancel_edit(); return True
            elif event.type() == QEvent.Type.FocusOut:
                if self._editing: self._commit_edit()
        return super().eventFilter(obj, event)

    def _commit_edit(self):
        if not self._editing: return
        self._editing = False
        new_text = self._edit_field.text().strip()
        self._edit_field.deleteLater(); self.text_lbl.show()
        if new_text and new_text != self.item["text"]:
            self.sig_edit.emit(self.item["id"], new_text)

    def _cancel_edit(self):
        if not self._editing: return
        self._editing = False
        self._edit_field.deleteLater(); self.text_lbl.show()

    # ── 스타일 ─────────────────────────────────────────────────────────────────
    def _style(self, hovered: bool):
        t    = self.t
        done = self.item.get("done", False)
        bg   = t["card"] if hovered else t["bg"]
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        self.setPalette(pal)
        deco = "line-through" if done else "none"
        fg   = t["done_fg"] if done else t["fg"]
        if hasattr(self, "text_lbl"):
            self.text_lbl.setStyleSheet(
                f"color:{fg};font-family:'{FONT}';font-size:{self.font_size}px;"
                f"text-decoration:{deco};background:transparent;")
        if hasattr(self, "check_btn"):
            cc = t["accent"] if done else t["muted"]
            self.check_btn.setStyleSheet(
                f"QPushButton{{color:{cc};background:transparent;border:none;"
                f"font-size:11px;}}QPushButton:hover{{color:{t['accent']};}}")
        if hasattr(self, "drag_handle"):
            self.drag_handle.setStyleSheet(
                f"color:{t['muted']};background:transparent;font-size:14px;")
        ghost = (f"QPushButton{{color:{t['muted']};background:transparent;"
                 f"border:none;font-size:13px;border-radius:3px;}}"
                 f"QPushButton:hover{{color:{t['accent']};"
                 f"background:{t['border']};}}")
        if hasattr(self, "edit_btn"):  self.edit_btn.setStyleSheet(ghost)
        if hasattr(self, "del_btn"):
            self.del_btn.setStyleSheet(
                f"QPushButton{{color:{t['muted']};background:transparent;"
                f"border:none;font-size:15px;border-radius:3px;}}"
                f"QPushButton:hover{{color:#E53935;background:{t['border']};}}")
        self._refresh_color_bar()

    # ── 호버 ───────────────────────────────────────────────────────────────────
    def enterEvent(self, e):
        self._style(True)
        self.drag_handle.setVisible(True)
        self.color_btn.setVisible(True)
        self.edit_btn.setVisible(True)
        self.del_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._style(False)
        if not self._editing:
            self.drag_handle.setVisible(False)
            self.color_btn.setVisible(False)
            self.edit_btn.setVisible(False)
            self.del_btn.setVisible(False)
        super().leaveEvent(e)

    # ── 하단 구분선 ────────────────────────────────────────────────────────────
    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setPen(QColor(self.t["border"]))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        p.end()

    # ── 드래그 오버레이용 하이라이트 ───────────────────────────────────────────
    def set_drag_highlight(self, above: bool, below: bool):
        """드래그 삽입 위치 표시 — 위/아래 강조선"""
        self._drag_above = above
        self._drag_below = below
        self.update()

    def _draw_drag_indicator(self, painter, color):
        painter.setPen(QPen(QColor(color), 2))

    def paintEvent(self, e):      # noqa: F811
        super().paintEvent(e)
        p = QPainter(self)
        t = self.t
        p.setPen(QColor(t["border"]))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        # 드래그 인디케이터
        if getattr(self, "_drag_above", False):
            p.setPen(QPen(QColor(t["accent"]), 2))
            p.drawLine(0, 0, self.width(), 0)
        if getattr(self, "_drag_below", False):
            p.setPen(QPen(QColor(t["accent"]), 2))
            p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        p.end()


# ── 메인 윈도우 ────────────────────────────────────────────────────────────────
class TodoWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data      = load_data()
        self._drag_pos = None
        self._item_widgets: list[TodoItemWidget] = []
        # 드래그 정렬 상태
        self._dragging_id    = None
        self._drag_insert_at = None   # 삽입할 인덱스
        self._drag_filter    = None

        self._set_win_flags()
        self._build_ui()
        self._build_tray()
        self.apply_theme(self.data.get("theme", "yellow"), first_run=True)

        # 하루 1회 자동 백업 (오늘 백업 없을 때만)
        auto_bak = DATA_FILE.parent / f"todos_backup_{date.today().isoformat()}.json"
        if not auto_bak.exists() and self.data.get("todos"):
            backup_data(self.data)

        # 위치 복원 (화면 경계 보정)
        w  = self.data["window"]
        sw = w.get("width", 320); sh = w.get("height", 520)
        self.resize(sw, sh)
        sc = QApplication.primaryScreen().availableGeometry()
        self.move(max(0, min(w.get("x", 100), sc.width()  - sw)),
                  max(0, min(w.get("y", 100), sc.height() - sh)))
        self.setWindowOpacity(self.data.get("opacity", 0.97))

    def _set_win_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.data.get("always_on_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── UI 빌드 ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QWidget(); outer.setObjectName("outerWidget")
        self.setCentralWidget(outer)
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(SHADOW_PAD, SHADOW_PAD, SHADOW_PAD, SHADOW_PAD)

        self.inner = QWidget(); self.inner.setObjectName("innerWidget")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28); shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.inner.setGraphicsEffect(shadow)
        ol.addWidget(self.inner)

        il = QVBoxLayout(self.inner)
        il.setContentsMargins(0, 0, 0, 0); il.setSpacing(0)

        self.accent_strip = QWidget()
        self.accent_strip.setObjectName("accentStrip")
        self.accent_strip.setFixedHeight(3)
        il.addWidget(self.accent_strip)

        self._hdr = self._make_header(); il.addWidget(self._hdr)
        il.addWidget(self._sep())

        self.scroll = QScrollArea()
        self.scroll.setObjectName("scrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_container = QWidget(); self.list_container.setObjectName("listContainer")
        self._list_lay = QVBoxLayout(self.list_container)
        self._list_lay.setContentsMargins(0, 0, 0, 0); self._list_lay.setSpacing(0)
        self._list_lay.addStretch()
        self.scroll.setWidget(self.list_container)
        il.addWidget(self.scroll, 1)

        il.addWidget(self._sep())
        self._status_bar = self._make_status_bar(); il.addWidget(self._status_bar)
        il.addWidget(self._sep())
        self._input_area = self._make_input_area(); il.addWidget(self._input_area)

        self._grip = QSizeGrip(self); self._grip.setFixedSize(16, 16)

    def _sep(self):
        f = QFrame(); f.setObjectName("sep"); f.setFrameShape(QFrame.Shape.HLine)
        f.setFixedHeight(1); return f

    def _make_header(self):
        hdr = QWidget(); hdr.setObjectName("header"); hdr.setFixedHeight(44)
        lay = QHBoxLayout(hdr); lay.setContentsMargins(12, 0, 8, 0); lay.setSpacing(0)

        check_lbl = QLabel("✓"); check_lbl.setObjectName("hdrCheck"); lay.addWidget(check_lbl)
        lay.addSpacing(6)
        title_lbl = QLabel("할 일"); title_lbl.setObjectName("hdrTitle"); lay.addWidget(title_lbl)
        lay.addSpacing(7)
        self.count_badge = QLabel("0"); self.count_badge.setObjectName("countBadge")
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_badge.setFixedSize(24, 17); lay.addWidget(self.count_badge)
        lay.addStretch()

        d = date.today()
        day_s = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d.weekday()]
        date_lbl = QLabel(d.strftime(f"%b %d  {day_s}")); date_lbl.setObjectName("hdrDate")
        lay.addWidget(date_lbl); lay.addSpacing(10)

        min_btn = QPushButton("−"); min_btn.setObjectName("hdrBtn")
        min_btn.setFixedSize(22, 22); min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.clicked.connect(self.hide_to_tray); lay.addWidget(min_btn)
        lay.addSpacing(3)
        close_btn = QPushButton("×"); close_btn.setObjectName("hdrBtnClose")
        close_btn.setFixedSize(22, 22); close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide_to_tray); lay.addWidget(close_btn)

        # 드래그 이동
        hdr.mousePressEvent   = self._hdr_press
        hdr.mouseMoveEvent    = self._hdr_move
        hdr.mouseReleaseEvent = self._hdr_release
        hdr.setCursor(Qt.CursorShape.SizeAllCursor)

        # 우클릭 → 설정 메뉴
        hdr.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hdr.customContextMenuRequested.connect(
            lambda pos: self._show_settings_menu(hdr.mapToGlobal(pos)))

        return hdr

    def _make_status_bar(self):
        bar = QWidget(); bar.setObjectName("statusBar"); bar.setFixedHeight(32)
        lay = QHBoxLayout(bar); lay.setContentsMargins(12, 0, 8, 0)
        self.status_lbl = QLabel("0 / 0 완료"); self.status_lbl.setObjectName("statusLbl")
        lay.addWidget(self.status_lbl); lay.addStretch()
        clear_btn = QPushButton("🗑 완료삭제"); clear_btn.setObjectName("statusBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_done); lay.addWidget(clear_btn)
        return bar

    def _make_input_area(self):
        area = QWidget(); area.setObjectName("inputArea"); area.setFixedHeight(46)
        lay = QHBoxLayout(area); lay.setContentsMargins(10, 7, 8, 7); lay.setSpacing(6)
        self.input_field = QLineEdit(); self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("할일을 입력하세요...")
        self.input_field.returnPressed.connect(self.add_todo); lay.addWidget(self.input_field, 1)
        add_btn = QPushButton("+"); add_btn.setObjectName("addBtn"); add_btn.setFixedSize(30, 30)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_todo); lay.addWidget(add_btn)
        return area

    # ── 트레이 ─────────────────────────────────────────────────────────────────
    def _build_tray(self):
        t = THEMES.get(self.data.get("theme", "yellow"), THEMES["yellow"])
        self.tray = QSystemTrayIcon(make_tray_icon(t["accent"]), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self._tray_activated)
        self._rebuild_tray_menu()
        self.tray.show()

    def _rebuild_tray_menu(self):
        menu = self._build_settings_menu()
        self.tray.setContextMenu(menu)

    def _build_settings_menu(self) -> QMenu:
        """트레이 · 헤더 우클릭 공용 설정 메뉴"""
        menu = QMenu()
        # 열기 (트레이 전용)
        show_act = QAction(f"📋 {APP_NAME} 열기", self)
        show_act.triggered.connect(self.show_window); menu.addAction(show_act)
        menu.addSeparator()

        # 항상 위에
        aot = self.data.get("always_on_top", False)
        aot_act = QAction(("✓ " if aot else "  ") + "항상 위에 표시", self)
        aot_act.triggered.connect(self.toggle_aot); menu.addAction(aot_act)

        # 투명도
        op_menu = menu.addMenu("투명도")
        cur_op  = int(round(self.data.get("opacity", 0.97) * 100))
        for pct in [75, 85, 95, 100]:
            a = QAction(("✓ " if cur_op == pct else "  ") + f"{pct}%", self)
            a.triggered.connect(lambda _, v=pct/100: self.set_opacity(v))
            op_menu.addAction(a)

        # 글씨 크기
        fs_menu  = menu.addMenu("글씨 크기")
        cur_fs   = self.data.get("font_size", 10)
        for pt in [9, 10, 11, 12, 13]:
            a = QAction(("✓ " if cur_fs == pt else "  ") + f"{pt}pt", self)
            a.triggered.connect(lambda _, s=pt: self.set_font_size(s))
            fs_menu.addAction(a)

        # 테마
        theme_menu = menu.addMenu("테마 색상")
        cur_t = self.data.get("theme", "yellow")
        for key, name in THEME_NAMES.items():
            a = QAction(("✓ " if key == cur_t else "  ") + name, self)
            a.triggered.connect(lambda _, k=key: self.apply_theme(k))
            theme_menu.addAction(a)

        menu.addSeparator()
        su = self.data.get("startup", False)
        su_act = QAction(("✓ " if su else "  ") + "윈도우 시작 시 자동 실행", self)
        su_act.triggered.connect(self.toggle_startup); menu.addAction(su_act)

        # 백업 / 복원
        menu.addSeparator()
        bak_act = QAction("💾 오늘 날짜로 백업", self)
        bak_act.triggered.connect(self.do_backup); menu.addAction(bak_act)
        rst_act = QAction("📂 백업 파일 불러오기", self)
        rst_act.triggered.connect(self.do_restore); menu.addAction(rst_act)

        menu.addSeparator()
        quit_act = QAction("❌ 완전 종료", self)
        quit_act.triggered.connect(self.quit_app); menu.addAction(quit_act)
        return menu

    def _show_settings_menu(self, global_pos: QPoint):
        menu = self._build_settings_menu()
        menu.exec(global_pos)

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.hide_to_tray() if self.isVisible() else self.show_window()

    # ── 테마 ───────────────────────────────────────────────────────────────────
    def apply_theme(self, key: str, first_run=False):
        if key not in THEMES: key = "yellow"
        self.data["theme"] = key
        t = THEMES[key]

        self.inner.setStyleSheet(
            f"QWidget#innerWidget{{background:{t['bg']};border-radius:{RADIUS}px;}}")
        self.accent_strip.setStyleSheet(f"background:{t['accent']};")
        self._hdr.setStyleSheet(f"QWidget#header{{background:{t['header']};}}")

        is_dark = key in ("midnight", "dark")
        chk_col = t["accent"] if is_dark else "white"
        self.findChild(QLabel, "hdrCheck").setStyleSheet(
            f"color:{chk_col};font-family:'{FONT}';font-size:14px;"
            f"font-weight:bold;background:transparent;")
        self.findChild(QLabel, "hdrTitle").setStyleSheet(
            f"color:white;font-family:'{FONT}';font-size:13px;"
            f"font-weight:bold;background:transparent;")
        self.count_badge.setStyleSheet(
            f"background:{t['bg']};color:{t['header']};"
            f"font-family:'{FONT}';font-size:9px;font-weight:bold;border-radius:8px;")
        self.findChild(QLabel, "hdrDate").setStyleSheet(
            f"color:rgba(255,255,255,160);font-family:'{FONT}';"
            f"font-size:9px;background:transparent;")

        hbtn = (f"QPushButton{{background:transparent;color:rgba(255,255,255,150);"
                f"border:none;font-size:16px;border-radius:4px;}}"
                f"QPushButton:hover{{background:rgba(255,255,255,20);color:white;}}")
        self.findChild(QPushButton, "hdrBtn").setStyleSheet(hbtn)
        self.findChild(QPushButton, "hdrBtnClose").setStyleSheet(
            f"QPushButton{{background:transparent;color:rgba(255,255,255,150);"
            f"border:none;font-size:16px;border-radius:4px;}}"
            f"QPushButton:hover{{background:#E53935;color:white;}}")

        sep_ss = f"background:{t['border']};border:none;"
        for s in self.findChildren(QFrame, "sep"): s.setStyleSheet(sep_ss)

        self.scroll.setStyleSheet(
            f"QScrollArea#scrollArea{{background:{t['bg']};border:none;}}"
            f"QScrollBar:vertical{{background:transparent;width:4px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:{t['border']};"
            f"border-radius:2px;min-height:20px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}")
        self.list_container.setStyleSheet(
            f"QWidget#listContainer{{background:{t['bg']};}}")

        self._status_bar.setStyleSheet(
            f"QWidget#statusBar{{background:{t['header']};}}")
        self.status_lbl.setStyleSheet(
            f"color:rgba(255,255,255,160);font-family:'{FONT}';"
            f"font-size:9px;background:transparent;")
        self.findChild(QPushButton, "statusBtn").setStyleSheet(
            f"QPushButton{{color:rgba(255,255,255,150);background:transparent;"
            f"border:none;font-family:'{FONT}';font-size:9px;border-radius:3px;"
            f"padding:2px 6px;}}QPushButton:hover{{background:rgba(255,255,255,20);"
            f"color:white;}}")

        self._input_area.setStyleSheet(
            f"QWidget#inputArea{{background:{t['header']};}}")
        fs = self.data.get("font_size", 10)
        self.input_field.setStyleSheet(
            f"QLineEdit#inputField{{background:{t['card']};color:{t['fg']};"
            f"border:1px solid {t['border']};border-radius:5px;padding:4px 8px;"
            f"font-family:'{FONT}';font-size:{fs}px;"
            f"selection-background-color:{t['accent']};}}"
            f"QLineEdit#inputField:focus{{border-color:{t['accent']};}}")
        self.findChild(QPushButton, "addBtn").setStyleSheet(
            f"QPushButton#addBtn{{background:{t['accent']};color:white;"
            f"border:none;border-radius:5px;font-size:18px;font-weight:bold;}}"
            f"QPushButton#addBtn:hover{{background:{t['accent_h']};}}")

        if hasattr(self, "tray"):
            self.tray.setIcon(make_tray_icon(t["accent"]))
            self._rebuild_tray_menu()
        if not first_run: save_data(self.data)
        self.render_todos()

    # ── 렌더링 ─────────────────────────────────────────────────────────────────
    def render_todos(self):
        t = THEMES.get(self.data["theme"], THEMES["yellow"])
        for w in self._item_widgets:
            w.setParent(None); w.deleteLater()
        self._item_widgets.clear()
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        todos = self.data.get("todos", [])
        if not todos:
            self._render_empty(t)
        else:
            fs = self.data.get("font_size", 10)
            for todo in todos:
                w = TodoItemWidget(todo, t, font_size=fs)
                w.sig_toggle.connect(self.toggle_item)
                w.sig_delete.connect(self.delete_item)
                w.sig_edit.connect(self.edit_item)
                w.sig_color.connect(self.color_item)
                w.sig_drag_start.connect(self._drag_start)
                self._list_lay.addWidget(w)
                self._item_widgets.append(w)
            self._list_lay.addStretch()

        self._update_status(t)

    def _render_empty(self, t):
        wrap = QWidget(); wrap.setStyleSheet(f"background:{t['bg']};")
        lay  = QVBoxLayout(wrap)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(0, 48, 0, 48)
        for text, ss in [
            ("✅",  f"font-size:32px;background:transparent;"),
            ("모두 완료!", f"color:{t['fg']};font-family:'{FONT}';font-size:13px;"
                          f"font-weight:bold;background:transparent;"),
            ("아래 입력창으로 할일을 추가하세요",
             f"color:{t['muted']};font-family:'{FONT}';font-size:9px;"
             f"background:transparent;"),
        ]:
            lbl = QLabel(text); lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl.setStyleSheet(ss); lay.addWidget(lbl)
            if text == "✅": lay.addSpacing(10)
            elif "완료!" in text: lay.addSpacing(4)
        self._list_lay.addWidget(wrap); self._list_lay.addStretch()

    def _update_status(self, t):
        todos  = self.data.get("todos", [])
        total  = len(todos)
        done   = sum(1 for x in todos if x.get("done"))
        self.status_lbl.setText(f"{done} / {total} 완료")
        self.count_badge.setText(str(total - done))

    # ── CRUD ───────────────────────────────────────────────────────────────────
    def add_todo(self):
        text = self.input_field.text().strip()
        if not text: return
        todos  = self.data.setdefault("todos", [])
        nxt_id = max((x["id"] for x in todos), default=0) + 1
        todos.append({"id": nxt_id, "text": text, "done": False,
                      "created_date": date.today().isoformat(), "color": None})
        self.input_field.clear(); save_data(self.data); self.render_todos()

    def toggle_item(self, item_id):
        for t in self.data.get("todos", []):
            if t["id"] == item_id: t["done"] = not t["done"]; break
        save_data(self.data); self.render_todos()

    def delete_item(self, item_id):
        self.data["todos"] = [x for x in self.data.get("todos", [])
                               if x["id"] != item_id]
        save_data(self.data); self.render_todos()

    def edit_item(self, item_id, new_text):
        for t in self.data.get("todos", []):
            if t["id"] == item_id: t["text"] = new_text; break
        save_data(self.data); self.render_todos()

    def color_item(self, item_id, color):
        for t in self.data.get("todos", []):
            if t["id"] == item_id: t["color"] = color; break
        save_data(self.data); self.render_todos()

    def clear_done(self):
        self.data["todos"] = [x for x in self.data.get("todos", [])
                               if not x.get("done")]
        save_data(self.data); self.render_todos()

    # ── 드래그 정렬 ────────────────────────────────────────────────────────────
    def _drag_start(self, item_id: int, global_pos: QPoint):
        self._dragging_id    = item_id
        self._drag_insert_at = None
        # 전역 이벤트 필터 설치
        self._drag_filter = DragFilter(self)
        QApplication.instance().installEventFilter(self._drag_filter)

    def _drag_update(self, global_pos: QPoint):
        if self._dragging_id is None: return
        # 커서가 어느 아이템 위에 있는지 계산
        insert_idx = self._calc_insert_idx(global_pos)
        if insert_idx == self._drag_insert_at: return
        self._drag_insert_at = insert_idx
        # 시각적 인디케이터 갱신
        for i, w in enumerate(self._item_widgets):
            w._drag_above = (i == insert_idx)
            w._drag_below = False
            w.update()

    def _drag_end(self, global_pos: QPoint):
        if self._dragging_id is None: return
        insert_idx = self._calc_insert_idx(global_pos)
        # 현재 아이템 인덱스
        todos     = self.data.get("todos", [])
        from_idx  = next((i for i, t in enumerate(todos)
                          if t["id"] == self._dragging_id), None)
        if from_idx is not None and insert_idx is not None:
            item = todos.pop(from_idx)
            # pop 이후 삽입 위치 보정
            if insert_idx > from_idx: insert_idx -= 1
            todos.insert(insert_idx, item)
            self.data["todos"] = todos
            save_data(self.data)
        # 인디케이터 제거 후 재렌더
        for w in self._item_widgets:
            w._drag_above = False; w._drag_below = False
        self._dragging_id    = None
        self._drag_insert_at = None
        self._drag_filter    = None
        self.render_todos()

    def _calc_insert_idx(self, global_pos: QPoint) -> int:
        """global_pos 기준으로 삽입할 인덱스 계산"""
        n = len(self._item_widgets)
        if n == 0: return 0
        for i, w in enumerate(self._item_widgets):
            wr = w.rect()
            top_global = w.mapToGlobal(wr.topLeft())
            bot_global = w.mapToGlobal(wr.bottomLeft())
            mid_y = (top_global.y() + bot_global.y()) // 2
            if global_pos.y() < mid_y:
                return i
        return n

    # ── 창 이동 ────────────────────────────────────────────────────────────────
    def _hdr_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (e.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())

    def _hdr_move(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _hdr_release(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None; self._save_win_pos()

    def _save_win_pos(self):
        g = self.geometry()
        self.data["window"].update({"x": g.x(), "y": g.y(),
                                     "width": g.width(), "height": g.height()})
        save_data(self.data)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._grip.move(self.width()  - self._grip.width()  - 2,
                         self.height() - self._grip.height() - 2)
        self._save_win_pos()

    # ── 창 제어 · 설정 ─────────────────────────────────────────────────────────
    def hide_to_tray(self):   self.hide()
    def show_window(self):
        self.show(); self.raise_(); self.activateWindow()

    def toggle_aot(self):
        aot = not self.data.get("always_on_top", False)
        self.data["always_on_top"] = aot
        vis = self.isVisible()
        self._set_win_flags()
        if vis: self.show()
        save_data(self.data); self._rebuild_tray_menu()

    def set_opacity(self, val):
        self.data["opacity"] = val
        self.setWindowOpacity(val)
        save_data(self.data); self._rebuild_tray_menu()

    def set_font_size(self, pt: int):
        self.data["font_size"] = pt
        save_data(self.data)
        self._rebuild_tray_menu()
        self.render_todos()   # 아이템 재생성으로 글씨 크기 반영

    def toggle_startup(self):
        su = not self.data.get("startup", False)
        self.data["startup"] = su; set_startup(su)
        save_data(self.data); self._rebuild_tray_menu()

    # ── 백업 / 복원 ────────────────────────────────────────────────────────────
    def do_backup(self):
        fname = backup_data(self.data)
        t = THEMES.get(self.data.get("theme","yellow"), THEMES["yellow"])
        msg = QMessageBox(self)
        msg.setWindowTitle("백업 완료")
        msg.setText(f"백업 저장 완료:\n{fname.name}")
        msg.setStyleSheet(
            f"QMessageBox{{background:{t['bg']};color:{t['fg']};}}"
            f"QLabel{{color:{t['fg']};font-family:'{FONT}';font-size:10px;}}"
            f"QPushButton{{background:{t['accent']};color:white;border:none;"
            f"border-radius:4px;padding:4px 12px;font-family:'{FONT}';}}")
        msg.exec()

    def do_restore(self):
        t = THEMES.get(self.data.get("theme","yellow"), THEMES["yellow"])
        path, _ = QFileDialog.getOpenFileName(
            self,
            "백업 파일 선택",
            str(DATA_FILE.parent),
            "JSON 파일 (todos_backup_*.json);;모든 JSON (*.json)",
        )
        if not path:
            return
        new_data = restore_data(Path(path))
        if new_data is None:
            QMessageBox.warning(self, "오류", "파일을 읽을 수 없습니다.")
            return
        # 현재 상태를 임시 백업 후 교체
        backup_data(self.data)
        # 창 위치/크기는 현재 것 유지
        new_data["window"] = self.data["window"]
        self.data = new_data
        save_data(self.data)
        self.apply_theme(self.data.get("theme", "yellow"), first_run=True)
        self.render_todos()
        QMessageBox.information(self, "복원 완료",
            f"불러오기 완료 — 할일 {len(self.data.get('todos',[]))}개")

    def quit_app(self):
        save_data(self.data); self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, e):
        e.ignore(); self.hide_to_tray()


# ── 진입점 ─────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont(FONT, 10))
    widget = TodoWidget()
    widget.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
