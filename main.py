#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""할일위젯 v5.0.0 — PyQt6 | 카테고리 그룹 · 접기/펼치기 · 드래그 정렬"""

import sys, json, winreg
from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect, QSizePolicy,
    QSizeGrip, QFileDialog, QMessageBox, QDialog, QComboBox, QGridLayout,
)
from PyQt6.QtCore import Qt, QPoint, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QPixmap, QPainter, QPen, QAction, QPalette,
)

# ── 상수 ────────────────────────────────────────────────────────────────────────
APP_NAME   = "할일위젯"
APP_VER    = "5.0.0"
FONT       = "맑은 고딕"
SHADOW_PAD = 14
RADIUS     = 12

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "todos.json"

# ── 색상 스와치 (카테고리 색상 선택용) ────────────────────────────────────────
COLOR_SWATCHES = [
    '#e05252','#e07a52','#e0b452','#a3c252','#52c27a',
    '#52c2b4','#528be0','#8b52e0','#c252b4','#8b5cf6',
    '#3b9e7a','#5a7fa8','#a3844a','#c2526a','#6b7280',
]

# ── 기본 카테고리 ───────────────────────────────────────────────────────────────
DEFAULT_CATS = [
    {"id": "c1", "label": "수색초",  "color": "#e05252"},
    {"id": "c2", "label": "용강초",  "color": "#8b5cf6"},
    {"id": "c3", "label": "갈현초",  "color": "#a3844a"},
    {"id": "c4", "label": "중동초",  "color": "#3b9e7a"},
    {"id": "c5", "label": "기타",    "color": "#5a7fa8"},
]

# ── 테마 ────────────────────────────────────────────────────────────────────────
THEMES = {
    "midnight": dict(
        bg="#141414", header="#181818", card="#1e1e1e",
        border="#282828", border2="#2e2e2e",
        accent="#3b82f6", accent_h="#2563eb",
        fg="#d0d0d0",  muted="#484848", done_fg="#383838",
        input_bg="#1c1c1c",
    ),
    "dark": dict(
        bg="#1e1e1e", header="#151515", card="#272727",
        border="#333333", border2="#3a3a3a",
        accent="#bb86fc", accent_h="#9965e8",
        fg="#dddddd",  muted="#666666", done_fg="#444444",
        input_bg="#222222",
    ),
    "yellow": dict(
        bg="#FFFDE7", header="#F57F17", card="#FFF9C4",
        border="#FFD54F", border2="#FFC107",
        accent="#E65100", accent_h="#BF360C",
        fg="#333333",  muted="#795548", done_fg="#BCAAA4",
        input_bg="#FFF9C4",
    ),
    "blue": dict(
        bg="#E3F2FD", header="#1565C0", card="#BBDEFB",
        border="#90CAF9", border2="#64B5F6",
        accent="#1565C0", accent_h="#0D47A1",
        fg="#212121",  muted="#546E7A", done_fg="#90A4AE",
        input_bg="#BBDEFB",
    ),
    "green": dict(
        bg="#E8F5E9", header="#2E7D32", card="#C8E6C9",
        border="#A5D6A7", border2="#81C784",
        accent="#1B5E20", accent_h="#004D40",
        fg="#212121",  muted="#558B2F", done_fg="#A5D6A7",
        input_bg="#C8E6C9",
    ),
    "pink": dict(
        bg="#FCE4EC", header="#C2185B", card="#F8BBD9",
        border="#F48FB1", border2="#F06292",
        accent="#880E4F", accent_h="#AD1457",
        fg="#212121",  muted="#C2185B", done_fg="#F48FB1",
        input_bg="#F8BBD9",
    ),
}
THEME_NAMES = {
    "midnight": "미드나잇", "dark": "다크", "yellow": "노랑 (포스트잇)",
    "blue": "파랑", "green": "초록", "pink": "분홍",
}

DEFAULT_DATA = {
    "window":     {"x": 100, "y": 100, "width": 460, "height": 640},
    "theme":      "midnight",
    "always_on_top": False,
    "opacity":    1.0,
    "font_size":  13,
    "startup":    False,
    "collapsed":  {},
    "categories": [c.copy() for c in DEFAULT_CATS],
    "todos":      [],
}

# ── 데이터 I/O ──────────────────────────────────────────────────────────────────
def _kw_cat(cats: list) -> dict:
    """카테고리 라벨 키워드 → id 매핑 (마이그레이션용)"""
    label_to_id = {c["label"]: c["id"] for c in cats}
    kw_map: dict[str, str] = {}
    for kw in ["수색초", "용강초", "갈현초", "중동초"]:
        if kw in label_to_id:
            kw_map[kw] = label_to_id[kw]
    return kw_map

def migrate_data(d: dict) -> dict:
    """v4.x → v5.0 포맷 마이그레이션"""
    if "categories" not in d or not d["categories"]:
        d["categories"] = [c.copy() for c in DEFAULT_CATS]
    if "collapsed" not in d:
        d["collapsed"] = {}
    kw_map = _kw_cat(d["categories"])
    etc_id = d["categories"][-1]["id"]
    for i, todo in enumerate(d.get("todos", [])):
        if "cat" not in todo:
            assigned = etc_id
            text = todo.get("text", "")
            for kw, cid in kw_map.items():
                if kw in text:
                    assigned = cid
                    break
            todo["cat"] = assigned
        if "order" not in todo:
            todo["order"] = i
    return d

def load_data() -> dict:
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in DEFAULT_DATA.items():
            if k not in d:
                d[k] = (v.copy() if isinstance(v, (dict, list)) else v)
        for k, v in DEFAULT_DATA["window"].items():
            d["window"].setdefault(k, v)
        return migrate_data(d)
    except Exception:
        return {k: (v.copy() if isinstance(v, (dict, list)) else v)
                for k, v in DEFAULT_DATA.items()}

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save] {e}")

def backup_data(data: dict) -> Path:
    fname = DATA_FILE.parent / f"todos_backup_{date.today().isoformat()}.json"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[backup] {e}")
    return fname

def restore_data(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in DEFAULT_DATA.items():
            if k not in d:
                d[k] = (v.copy() if isinstance(v, (dict, list)) else v)
        return migrate_data(d)
    except Exception as e:
        print(f"[restore] {e}")
        return None

# ── 시작프로그램 ────────────────────────────────────────────────────────────────
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

# ── 트레이 아이콘 ───────────────────────────────────────────────────────────────
def make_tray_icon(accent: str = "#3b82f6") -> QIcon:
    pix = QPixmap(64, 64); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#181818")); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    pen = QPen(QColor(accent), 5.5, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(16, 34, 27, 45); p.drawLine(27, 45, 48, 20)
    p.end()
    return QIcon(pix)


# ── 드래그 핸들 (6점 그리드) ────────────────────────────────────────────────────
class DotGridWidget(QWidget):
    def __init__(self, color: str = "#555", parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(16, 18)

    def setColor(self, c: str):
        self.color = c; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self.color)); p.setPen(Qt.PenStyle.NoPen)
        for cx in [5, 10]:
            for cy in [4, 9, 14]:
                p.drawEllipse(cx - 2, cy - 2, 4, 4)
        p.end()


# ── 커스텀 체크박스 ─────────────────────────────────────────────────────────────
class CheckWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, done: bool, cat_color: str, parent=None):
        super().__init__(parent)
        self.done = done
        self.cat_color = cat_color
        self._hovered = False
        self.setFixedSize(19, 19)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.done:
            fill = QColor(self.cat_color); fill.setAlpha(38)
            border = QColor(self.cat_color); border.setAlpha(110)
            p.setBrush(fill); p.setPen(QPen(border, 1.5))
        elif self._hovered:
            p.setBrush(QColor(255, 255, 255, 8))
            p.setPen(QPen(QColor("#555555"), 1.5))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#363636"), 1.5))
        p.drawEllipse(1, 1, 16, 16)
        if self.done:
            pen = QPen(QColor(self.cat_color), 1.8, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(4, 10, 7, 13); p.drawLine(7, 13, 14, 6)
        p.end()


# ── 카테고리 컬러 닷 ─────────────────────────────────────────────────────────────
class ColorDotWidget(QWidget):
    def __init__(self, color: str, size: int = 8, parent=None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size + 4, size + 4)

    def setColor(self, c: str):
        self._color = c; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self._color)); p.setPen(Qt.PenStyle.NoPen)
        off = (self.width() - self._size) // 2
        p.drawEllipse(off, off, self._size, self._size)
        p.end()


# ── 카테고리 추가/수정 모달 ────────────────────────────────────────────────────
class CategoryModal(QDialog):
    def __init__(self, theme: dict, initial: dict = None, parent=None):
        super().__init__(parent,
                         Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        t = self.t = theme
        self.selected_color = (initial["color"] if initial else COLOR_SWATCHES[0])
        self._result = None

        outer = QWidget(); outer.setObjectName("cmOuter")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50); shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 180))
        outer.setGraphicsEffect(shadow)
        outer.setStyleSheet(
            f"QWidget#cmOuter{{background:{t['card']};border-radius:12px;"
            f"border:1px solid {t['border2']};}}")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.addWidget(outer)

        il = QVBoxLayout(outer)
        il.setContentsMargins(20, 20, 20, 20); il.setSpacing(0)

        # 제목
        title = QLabel("카테고리 수정" if initial else "새 카테고리")
        title.setStyleSheet(f"color:{t['fg']};font-family:'{FONT}';font-size:14px;"
                            f"font-weight:bold;background:transparent;")
        il.addWidget(title); il.addSpacing(16)

        # 이름 입력
        nm_lbl = QLabel("이름")
        nm_lbl.setStyleSheet(f"color:{t['muted']};font-family:'{FONT}';font-size:11px;"
                             f"background:transparent;")
        il.addWidget(nm_lbl); il.addSpacing(6)
        self.name_input = QLineEdit(initial["label"] if initial else "")
        self.name_input.setPlaceholderText("카테고리 이름...")
        self.name_input.setStyleSheet(
            f"QLineEdit{{background:{t['input_bg']};color:{t['fg']};"
            f"border:1px solid {t['border2']};border-radius:7px;"
            f"padding:8px 11px;font-family:'{FONT}';font-size:13px;}}"
            f"QLineEdit:focus{{border-color:{t['accent']};}}")
        il.addWidget(self.name_input); il.addSpacing(14)

        # 색상
        cl_lbl = QLabel("색상")
        cl_lbl.setStyleSheet(f"color:{t['muted']};font-family:'{FONT}';font-size:11px;"
                             f"background:transparent;")
        il.addWidget(cl_lbl); il.addSpacing(8)

        grid_w = QWidget(); grid_w.setStyleSheet("background:transparent;")
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(7)
        self._sw_btns: dict[str, QPushButton] = {}
        for i, c in enumerate(COLOR_SWATCHES):
            btn = QPushButton(); btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._sw_btns[c] = btn
            btn.clicked.connect(lambda _, col=c: self._pick(col))
            grid.addWidget(btn, i // 5, i % 5)
        il.addWidget(grid_w); il.addSpacing(16)
        self._refresh_swatches()

        # 버튼 행
        btn_row = QHBoxLayout(); btn_row.setSpacing(7)
        cancel = QPushButton("취소")
        cancel.setStyleSheet(
            f"QPushButton{{background:{t['border']};color:{t['muted']};"
            f"border:none;border-radius:7px;padding:6px 14px;"
            f"font-family:'{FONT}';font-size:12px;}}"
            f"QPushButton:hover{{background:{t['border2']};color:{t['fg']};}}")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("저장" if initial else "만들기")
        confirm.setStyleSheet(
            f"QPushButton{{background:{t['accent']};color:white;"
            f"border:none;border-radius:7px;padding:6px 14px;"
            f"font-family:'{FONT}';font-size:12px;}}"
            f"QPushButton:hover{{background:{t['accent_h']};}}")
        confirm.clicked.connect(self._confirm)
        btn_row.addWidget(cancel); btn_row.addWidget(confirm)
        il.addLayout(btn_row)

        self.name_input.setFocus()
        self.name_input.returnPressed.connect(self._confirm)

    def _pick(self, c: str):
        self.selected_color = c; self._refresh_swatches()

    def _refresh_swatches(self):
        for c, btn in self._sw_btns.items():
            sel = (c == self.selected_color)
            btn.setStyleSheet(
                f"QPushButton{{background:{c};border-radius:13px;"
                f"border:2.5px solid {'white' if sel else 'transparent'};}}"
                f"QPushButton:hover{{border-color:rgba(255,255,255,0.6);}}")

    def _confirm(self):
        name = self.name_input.text().strip()
        if not name: return
        self._result = {"label": name, "color": self.selected_color}
        self.accept()

    def get_result(self) -> dict | None:
        return self._result


# ── 드래그 전역 이벤트 필터 ────────────────────────────────────────────────────
class DragFilter(QObject):
    def __init__(self, widget):
        super().__init__(widget); self._w = widget

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            self._w._drag_update(event.globalPosition().toPoint()); return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._w._drag_end(event.globalPosition().toPoint())
            QApplication.instance().removeEventFilter(self); return True
        return False


# ── 할일 아이템 위젯 ────────────────────────────────────────────────────────────
class TodoItemWidget(QWidget):
    sig_toggle     = pyqtSignal(int)
    sig_delete     = pyqtSignal(int)
    sig_edit       = pyqtSignal(int, str)
    sig_drag_start = pyqtSignal(int, QPoint)

    def __init__(self, item: dict, cat: dict, theme: dict,
                 font_size: int = 13, parent=None):
        super().__init__(parent)
        self.item = item
        self.cat  = cat
        self.t    = theme
        self.font_size = font_size
        self._editing  = False
        self._drag_above = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._build()

    def _build(self):
        t    = self.t
        done = self.item.get("done", False)
        cc   = self.cat.get("color", t["accent"])

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # 드래그 핸들
        self.drag_handle = DotGridWidget("#444444")
        self.drag_handle.setVisible(False)
        self.drag_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self.drag_handle.mousePressEvent = self._on_drag_press
        root.addWidget(self.drag_handle)

        # 카테고리 컬러 바 (3px)
        self.color_bar = QWidget(); self.color_bar.setFixedWidth(3)
        self.color_bar.setStyleSheet(
            f"background:{'#262626' if done else cc};border-radius:2px;")
        self._bar_wrap = QWidget()
        bwl = QVBoxLayout(self._bar_wrap)
        bwl.setContentsMargins(0, 5, 0, 5); bwl.addWidget(self.color_bar)
        root.addWidget(self._bar_wrap)
        root.addSpacing(7)

        # 체크박스
        self.check = CheckWidget(done, cc)
        self.check.clicked.connect(lambda: self.sig_toggle.emit(self.item["id"]))
        root.addWidget(self.check)
        root.addSpacing(9)

        # 텍스트 영역
        self._text_wrap = QWidget()
        self._text_wrap.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Preferred)
        self._text_wrap.setStyleSheet("background:transparent;")
        tl = QHBoxLayout(self._text_wrap)
        tl.setContentsMargins(0, 8, 0, 8); tl.setSpacing(0)
        self.text_lbl = QLabel(self.item["text"])
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setStyleSheet(
            f"color:{'#383838' if done else t['fg']};"
            f"font-family:'{FONT}';font-size:{self.font_size}px;"
            f"text-decoration:{'line-through' if done else 'none'};"
            f"background:transparent;line-height:150%;")
        tl.addWidget(self.text_lbl)
        root.addWidget(self._text_wrap, 1)

        # 호버 액션 버튼
        self.edit_btn = self._ghost_btn("✎", danger=False)
        self.edit_btn.setVisible(False)
        self.edit_btn.clicked.connect(self._start_edit)

        self.del_btn = self._ghost_btn("×", danger=True)
        self.del_btn.setVisible(False)
        self.del_btn.clicked.connect(lambda: self.sig_delete.emit(self.item["id"]))

        action_wrap = QWidget(); action_wrap.setStyleSheet("background:transparent;")
        al = QHBoxLayout(action_wrap)
        al.setContentsMargins(0, 0, 6, 0); al.setSpacing(2)
        if not done:
            al.addWidget(self.edit_btn)
        al.addWidget(self.del_btn)
        root.addWidget(action_wrap)

        self.setMinimumHeight(36)
        self._style(False)

    def _ghost_btn(self, text: str, danger: bool) -> QPushButton:
        t = self.t
        btn = QPushButton(text); btn.setFixedSize(22, 22); btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hover_bg   = f"rgba(239,68,68,0.1)"  if danger else t["card"]
        hover_fg   = "#ef4444"                if danger else t["fg"]
        btn.setStyleSheet(
            f"QPushButton{{color:{t['muted']};background:transparent;"
            f"border:none;font-size:{'15' if text=='×' else '13'}px;"
            f"border-radius:5px;}}"
            f"QPushButton:hover{{background:{hover_bg};color:{hover_fg};}}")
        return btn

    def _on_drag_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.sig_drag_start.emit(self.item["id"],
                                     e.globalPosition().toPoint())

    # ── 인라인 편집 ───────────────────────────────────────────────────────────
    def _start_edit(self):
        if self._editing: return
        self._editing = True
        t = self.t
        self.text_lbl.hide()
        self._edit = QLineEdit(self.item["text"])
        self._edit.setStyleSheet(
            f"QLineEdit{{background:{t['input_bg']};color:{t['fg']};"
            f"border:1px solid {t['accent']};border-radius:5px;"
            f"padding:3px 7px;font-family:'{FONT}';font-size:{self.font_size}px;}}")
        self._text_wrap.layout().insertWidget(0, self._edit)
        self._edit.setFocus(); self._edit.selectAll()
        self._edit.returnPressed.connect(self._commit)
        self._edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_edit", None):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self._cancel(); return True
            elif event.type() == QEvent.Type.FocusOut:
                if self._editing: self._commit()
        return super().eventFilter(obj, event)

    def _commit(self):
        if not self._editing: return
        self._editing = False
        txt = self._edit.text().strip()
        self._edit.deleteLater(); self.text_lbl.show()
        if txt and txt != self.item["text"]:
            self.sig_edit.emit(self.item["id"], txt)

    def _cancel(self):
        if not self._editing: return
        self._editing = False
        self._edit.deleteLater(); self.text_lbl.show()

    # ── 스타일 ───────────────────────────────────────────────────────────────
    def _style(self, hovered: bool):
        t  = self.t
        bg = "rgba(255,255,255,0.03)" if hovered else "transparent"
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window,
                     QColor(bg) if hovered else QColor(0, 0, 0, 0))
        self.setPalette(pal)

    def enterEvent(self, e):
        self._style(True)
        self.drag_handle.setVisible(True)
        self.edit_btn.setVisible(not self.item.get("done", False))
        self.del_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._style(False)
        if not self._editing:
            self.drag_handle.setVisible(False)
            self.edit_btn.setVisible(False)
            self.del_btn.setVisible(False)
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setPen(Qt.PenStyle.NoPen); p.end()
        # 드래그 삽입선
        if self._drag_above:
            p = QPainter(self)
            pen = QPen(QColor(self.t["accent"]), 2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(4, 1, self.width() - 4, 1)
            p.setBrush(QColor(self.t["accent"])); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(0, -3, 7, 7)
            p.drawEllipse(self.width() - 7, -3, 7, 7)
            p.end()


# ── 카테고리 그룹 위젯 ─────────────────────────────────────────────────────────
class CategoryGroupWidget(QWidget):
    sig_toggle_cat  = pyqtSignal(str)          # cat_id
    sig_edit_cat    = pyqtSignal(str)          # cat_id
    sig_delete_cat  = pyqtSignal(str)          # cat_id
    sig_toggle_task = pyqtSignal(int)
    sig_delete_task = pyqtSignal(int)
    sig_edit_task   = pyqtSignal(int, str)
    sig_drag_start  = pyqtSignal(int, QPoint)  # task_id, global_pos

    def __init__(self, cat: dict, tasks: list, theme: dict,
                 collapsed: bool, font_size: int = 13, parent=None):
        super().__init__(parent)
        self.cat = cat; self.t = theme
        self._item_widgets: list[TodoItemWidget] = []
        self._build(tasks, collapsed, font_size)

    def _build(self, tasks: list, collapsed: bool, font_size: int):
        t = self.t; cc = self.cat["color"]
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── 카테고리 헤더 ────────────────────────────────────────────────────
        self._hdr = QWidget(); self._hdr.setObjectName("catHdr")
        self._hdr.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hdr.setAttribute(Qt.WidgetAttribute.WA_Hover)
        hl = QHBoxLayout(self._hdr)
        hl.setContentsMargins(12, 7, 8, 6); hl.setSpacing(7)

        self._chevron = QLabel("▾" if not collapsed else "▸")
        self._chevron.setStyleSheet(
            f"color:#444444;font-size:10px;background:transparent;")
        self._chevron.setFixedWidth(12)
        hl.addWidget(self._chevron)

        dot = ColorDotWidget(cc, 8)
        hl.addWidget(dot)

        name_lbl = QLabel(self.cat["label"])
        name_lbl.setStyleSheet(
            f"color:{cc};font-family:'{FONT}';font-size:11px;"
            f"font-weight:bold;background:transparent;letter-spacing:0.2px;")
        hl.addWidget(name_lbl, 1)

        self._count_lbl = QLabel(str(len(tasks)))
        self._count_lbl.setStyleSheet(
            f"color:#404040;font-family:'{FONT}';font-size:10px;"
            f"background:{t['card']};border-radius:10px;padding:1px 6px;")
        hl.addWidget(self._count_lbl)

        # 수정/삭제 버튼 (호버 시 표시)
        self._action_wrap = QWidget(); self._action_wrap.setStyleSheet("background:transparent;")
        self._action_wrap.setVisible(False)
        al = QHBoxLayout(self._action_wrap)
        al.setContentsMargins(0, 0, 0, 0); al.setSpacing(2)

        edit_cat_btn = QPushButton("✎"); edit_cat_btn.setFixedSize(22, 22)
        edit_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_cat_btn.setStyleSheet(
            f"QPushButton{{color:#555;background:transparent;border:none;"
            f"font-size:13px;border-radius:5px;}}"
            f"QPushButton:hover{{background:{t['card']};color:{t['fg']};}}")
        edit_cat_btn.clicked.connect(lambda: self.sig_edit_cat.emit(self.cat["id"]))
        al.addWidget(edit_cat_btn)

        del_cat_btn = QPushButton("×"); del_cat_btn.setFixedSize(22, 22)
        del_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_cat_btn.setStyleSheet(
            f"QPushButton{{color:#555;background:transparent;border:none;"
            f"font-size:15px;border-radius:5px;}}"
            f"QPushButton:hover{{background:rgba(239,68,68,0.1);color:#ef4444;}}")
        del_cat_btn.clicked.connect(lambda: self.sig_delete_cat.emit(self.cat["id"]))
        al.addWidget(del_cat_btn)
        hl.addWidget(self._action_wrap)

        self._hdr.mousePressEvent = lambda _: self.sig_toggle_cat.emit(self.cat["id"])
        self._hdr.enterEvent  = lambda _: self._action_wrap.setVisible(True)
        self._hdr.leaveEvent  = lambda _: self._action_wrap.setVisible(False)
        root.addWidget(self._hdr)

        # 구분선
        div = QWidget(); div.setFixedHeight(1)
        div.setStyleSheet(f"background:rgba(255,255,255,0.035);margin:0 14px;")
        root.addWidget(div)

        # ── 아이템 목록 ──────────────────────────────────────────────────────
        self._content = QWidget(); self._content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)

        if not tasks:
            empty = QLabel("할 일 없음")
            empty.setStyleSheet(
                f"color:#333333;font-family:'{FONT}';font-size:12px;"
                f"font-style:italic;background:transparent;padding:8px 14px 10px 36px;")
            cl.addWidget(empty)
        else:
            for task in sorted(tasks, key=lambda x: x.get("order", 0)):
                w = TodoItemWidget(task, self.cat, self.t, font_size)
                w.sig_toggle.connect(self.sig_toggle_task)
                w.sig_delete.connect(self.sig_delete_task)
                w.sig_edit.connect(self.sig_edit_task)
                w.sig_drag_start.connect(self.sig_drag_start)
                cl.addWidget(w)
                self._item_widgets.append(w)

        self._content.setVisible(not collapsed)
        root.addWidget(self._content)

    def set_collapsed(self, collapsed: bool):
        self._content.setVisible(not collapsed)
        self._chevron.setText("▸" if collapsed else "▾")

    def update_count(self, n: int):
        self._count_lbl.setText(str(n))


# ── 메인 윈도우 ────────────────────────────────────────────────────────────────
class TodoWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        self._drag_pos   = None
        self._cat_groups: list[CategoryGroupWidget] = []
        self._dragging_id    = None
        self._drag_insert_at = None
        self._drag_filter    = None
        self._ghost: QWidget | None = None

        self._set_win_flags()
        self._build_ui()
        self._build_tray()
        self.apply_theme(self.data.get("theme", "midnight"), first_run=True)

        # 자동 백업
        auto_bak = DATA_FILE.parent / f"todos_backup_{date.today().isoformat()}.json"
        if not auto_bak.exists() and self.data.get("todos"):
            backup_data(self.data)

        # 위치 복원
        w  = self.data["window"]
        sw = w.get("width", 460); sh = w.get("height", 640)
        self.resize(sw, sh)
        sc = QApplication.primaryScreen().availableGeometry()
        self.move(max(0, min(w.get("x", 100), sc.width()  - sw)),
                  max(0, min(w.get("y", 100), sc.height() - sh)))
        self.setWindowOpacity(self.data.get("opacity", 1.0))

    def _set_win_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.data.get("always_on_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── UI 빌드 ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QWidget(); outer.setObjectName("outerWidget")
        self.setCentralWidget(outer)
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(SHADOW_PAD, SHADOW_PAD, SHADOW_PAD, SHADOW_PAD)

        self.inner = QWidget(); self.inner.setObjectName("innerWidget")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32); shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 165))
        self.inner.setGraphicsEffect(shadow)
        ol.addWidget(self.inner)

        il = QVBoxLayout(self.inner)
        il.setContentsMargins(0, 0, 0, 0); il.setSpacing(0)

        self._hdr = self._make_header(); il.addWidget(self._hdr)

        self.scroll = QScrollArea(); self.scroll.setObjectName("scrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_container = QWidget(); self.list_container.setObjectName("listContainer")
        self._list_lay = QVBoxLayout(self.list_container)
        self._list_lay.setContentsMargins(0, 4, 0, 4); self._list_lay.setSpacing(0)
        self._list_lay.addStretch()
        self.scroll.setWidget(self.list_container)
        il.addWidget(self.scroll, 1)

        self._footer = self._make_footer(); il.addWidget(self._footer)
        self._grip = QSizeGrip(self); self._grip.setFixedSize(16, 16)

    def _make_header(self):
        hdr = QWidget(); hdr.setObjectName("header"); hdr.setFixedHeight(44)
        lay = QHBoxLayout(hdr); lay.setContentsMargins(14, 0, 14, 0); lay.setSpacing(0)

        # 타이틀 아이콘 (파란 박스 + 체크)
        icon_box = QWidget(); icon_box.setFixedSize(20, 20)
        icon_box.setStyleSheet("background:#3b82f6;border-radius:6px;")
        ib_lay = QHBoxLayout(icon_box); ib_lay.setContentsMargins(0, 0, 0, 0)
        chk = QLabel("✓"); chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk.setStyleSheet("color:white;font-size:11px;font-weight:bold;background:transparent;")
        ib_lay.addWidget(chk)
        lay.addWidget(icon_box); lay.addSpacing(8)

        title = QLabel("할 일"); title.setObjectName("hdrTitle")
        lay.addWidget(title); lay.addSpacing(7)

        self.count_badge = QLabel("0"); self.count_badge.setObjectName("countBadge")
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_badge.setFixedHeight(18)
        lay.addWidget(self.count_badge)
        lay.addStretch()

        d = date.today()
        day_s = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d.weekday()]
        date_lbl = QLabel(d.strftime(f"%b %d  {day_s}")); date_lbl.setObjectName("hdrDate")
        lay.addWidget(date_lbl); lay.addSpacing(12)

        # macOS 스타일 윈도우 버튼
        min_btn = QPushButton(); min_btn.setFixedSize(11, 11)
        min_btn.setStyleSheet(
            "QPushButton{background:#f5a623;border-radius:5px;border:none;}"
            "QPushButton:hover{background:#e6961a;}")
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.clicked.connect(self.hide_to_tray); lay.addWidget(min_btn)
        lay.addSpacing(6)

        cls_btn = QPushButton(); cls_btn.setFixedSize(11, 11)
        cls_btn.setStyleSheet(
            "QPushButton{background:#ff5f57;border-radius:5px;border:none;}"
            "QPushButton:hover{background:#e5453d;}")
        cls_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cls_btn.clicked.connect(self.hide_to_tray); lay.addWidget(cls_btn)

        hdr.mousePressEvent   = self._hdr_press
        hdr.mouseMoveEvent    = self._hdr_move
        hdr.mouseReleaseEvent = self._hdr_release
        hdr.setCursor(Qt.CursorShape.SizeAllCursor)
        hdr.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hdr.customContextMenuRequested.connect(
            lambda pos: self._show_settings_menu(hdr.mapToGlobal(pos)))
        return hdr

    def _make_footer(self):
        footer = QWidget(); footer.setObjectName("footer")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(12, 10, 12, 10); fl.setSpacing(9)

        # 진행률 행
        prog_row = QWidget(); prog_row.setStyleSheet("background:transparent;")
        prl = QHBoxLayout(prog_row); prl.setContentsMargins(0, 0, 0, 0); prl.setSpacing(8)

        self.prog_text = QLabel("0 / 0 완료")
        self.prog_text.setObjectName("progText")
        prl.addWidget(self.prog_text)

        # 프로그레스 바
        self._prog_bg = QWidget(); self._prog_bg.setFixedSize(80, 3)
        self._prog_bg.setObjectName("progBg")
        self._prog_fill = QWidget(self._prog_bg)
        self._prog_fill.setGeometry(0, 0, 0, 3)
        self._prog_fill.setObjectName("progFill")
        prl.addWidget(self._prog_bg)
        prl.addStretch()

        self.add_cat_btn = QPushButton("+ 카테고리")
        self.add_cat_btn.setObjectName("footerBtn")
        self.add_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_cat_btn.clicked.connect(self._add_category)
        prl.addWidget(self.add_cat_btn)

        self.clear_done_btn = QPushButton("완료 삭제")
        self.clear_done_btn.setObjectName("footerBtnDanger")
        self.clear_done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_done_btn.clicked.connect(self.clear_done)
        self.clear_done_btn.setVisible(False)
        prl.addWidget(self.clear_done_btn)

        fl.addWidget(prog_row)

        # 입력 행
        input_row = QWidget(); input_row.setStyleSheet("background:transparent;")
        irl = QHBoxLayout(input_row); irl.setContentsMargins(0, 0, 0, 0); irl.setSpacing(7)

        self._input_wrap = QWidget(); self._input_wrap.setObjectName("inputWrap")
        iwl = QHBoxLayout(self._input_wrap)
        iwl.setContentsMargins(0, 0, 0, 0); iwl.setSpacing(0)

        self.cat_select = QComboBox(); self.cat_select.setObjectName("catSelect")
        self.cat_select.setFixedHeight(34)
        self._refresh_cat_select()
        iwl.addWidget(self.cat_select)

        self.input_field = QLineEdit(); self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("할 일을 입력하세요...")
        self.input_field.setFixedHeight(34)
        self.input_field.returnPressed.connect(self.add_todo)
        iwl.addWidget(self.input_field, 1)
        irl.addWidget(self._input_wrap, 1)

        add_btn = QPushButton("+"); add_btn.setObjectName("addBtn")
        add_btn.setFixedSize(34, 34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_todo); irl.addWidget(add_btn)
        fl.addWidget(input_row)
        return footer

    def _refresh_cat_select(self):
        self.cat_select.blockSignals(True)
        self.cat_select.clear()
        for c in self.data.get("categories", []):
            self.cat_select.addItem(c["label"], c["id"])
        self.cat_select.blockSignals(False)

    # ── 트레이 ───────────────────────────────────────────────────────────────
    def _build_tray(self):
        t = THEMES.get(self.data.get("theme", "midnight"), THEMES["midnight"])
        self.tray = QSystemTrayIcon(make_tray_icon(t["accent"]), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self._tray_activated)
        self._rebuild_tray_menu()
        self.tray.show()

    def _rebuild_tray_menu(self):
        self.tray.setContextMenu(self._build_settings_menu())

    def _build_settings_menu(self) -> QMenu:
        menu = QMenu()
        show_act = QAction(f"📋 {APP_NAME} 열기", self)
        show_act.triggered.connect(self.show_window); menu.addAction(show_act)
        menu.addSeparator()

        aot = self.data.get("always_on_top", False)
        aot_act = QAction(("✓ " if aot else "  ") + "항상 위에 표시", self)
        aot_act.triggered.connect(self.toggle_aot); menu.addAction(aot_act)

        op_menu = menu.addMenu("투명도")
        cur_op = int(round(self.data.get("opacity", 1.0) * 100))
        for pct in [75, 85, 95, 100]:
            a = QAction(("✓ " if cur_op == pct else "  ") + f"{pct}%", self)
            a.triggered.connect(lambda _, v=pct/100: self.set_opacity(v))
            op_menu.addAction(a)

        fs_menu = menu.addMenu("글씨 크기")
        cur_fs = self.data.get("font_size", 13)
        for pt in [11, 12, 13, 14, 15]:
            a = QAction(("✓ " if cur_fs == pt else "  ") + f"{pt}pt", self)
            a.triggered.connect(lambda _, s=pt: self.set_font_size(s))
            fs_menu.addAction(a)

        theme_menu = menu.addMenu("테마 색상")
        cur_t = self.data.get("theme", "midnight")
        for key, name in THEME_NAMES.items():
            a = QAction(("✓ " if key == cur_t else "  ") + name, self)
            a.triggered.connect(lambda _, k=key: self.apply_theme(k))
            theme_menu.addAction(a)

        menu.addSeparator()
        su = self.data.get("startup", False)
        su_act = QAction(("✓ " if su else "  ") + "윈도우 시작 시 자동 실행", self)
        su_act.triggered.connect(self.toggle_startup); menu.addAction(su_act)

        menu.addSeparator()
        bak_act = QAction("💾 오늘 날짜로 백업", self)
        bak_act.triggered.connect(self.do_backup); menu.addAction(bak_act)
        rst_act = QAction("📂 백업 파일 불러오기", self)
        rst_act.triggered.connect(self.do_restore); menu.addAction(rst_act)

        menu.addSeparator()
        quit_act = QAction("❌ 완전 종료", self)
        quit_act.triggered.connect(self.quit_app); menu.addAction(quit_act)
        return menu

    def _show_settings_menu(self, gpos: QPoint):
        self._build_settings_menu().exec(gpos)

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.hide_to_tray() if self.isVisible() else self.show_window()

    # ── 테마 적용 ─────────────────────────────────────────────────────────────
    def apply_theme(self, key: str, first_run=False):
        if key not in THEMES: key = "midnight"
        self.data["theme"] = key
        t = THEMES[key]

        self.inner.setStyleSheet(
            f"QWidget#innerWidget{{background:{t['bg']};border-radius:{RADIUS}px;"
            f"border:1px solid {t['border']};}}")
        self._hdr.setStyleSheet(
            f"QWidget#header{{background:{t['header']};"
            f"border-radius:{RADIUS}px {RADIUS}px 0 0;}}")

        self.findChild(QLabel, "hdrTitle").setStyleSheet(
            f"color:#f0f0f0;font-family:'{FONT}';font-size:14px;"
            f"font-weight:bold;background:transparent;letter-spacing:-0.3px;")
        self.count_badge.setStyleSheet(
            f"color:#777777;font-family:'{FONT}';font-size:11px;font-weight:bold;"
            f"background:#222222;border:1px solid #2c2c2c;border-radius:10px;"
            f"padding:2px 7px;")
        self.findChild(QLabel, "hdrDate").setStyleSheet(
            f"color:#484848;font-family:'{FONT}';font-size:11px;background:transparent;")

        self.scroll.setStyleSheet(
            f"QScrollArea#scrollArea{{background:{t['bg']};border:none;}}"
            f"QScrollBar:vertical{{background:transparent;width:4px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:{t['border']};"
            f"border-radius:2px;min-height:20px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}")
        self.list_container.setStyleSheet(
            f"QWidget#listContainer{{background:{t['bg']};}}")

        self._footer.setStyleSheet(
            f"QWidget#footer{{background:{t['header']};"
            f"border-top:1px solid {t['border']};"
            f"border-radius:0 0 {RADIUS}px {RADIUS}px;}}")
        self.prog_text.setStyleSheet(
            f"color:{t['muted']};font-family:'{FONT}';font-size:11px;"
            f"background:transparent;")
        self._prog_bg.setStyleSheet(
            f"QWidget#progBg{{background:{t['card']};border-radius:2px;}}")
        self._prog_fill.setStyleSheet(
            f"background:{t['accent']};border-radius:2px;")

        fbtn_ss = (
            f"QPushButton#footerBtn{{color:{t['muted']};background:transparent;"
            f"border:1px solid {t['border2']};border-radius:5px;padding:3px 8px;"
            f"font-family:'{FONT}';font-size:11px;}}"
            f"QPushButton#footerBtn:hover{{color:{t['fg']};border-color:{t['border']};"
            f"background:{t['card']};}}")
        self.add_cat_btn.setStyleSheet(fbtn_ss)
        self.clear_done_btn.setStyleSheet(
            f"QPushButton#footerBtnDanger{{color:{t['muted']};background:transparent;"
            f"border:1px solid {t['border2']};border-radius:5px;padding:3px 8px;"
            f"font-family:'{FONT}';font-size:11px;}}"
            f"QPushButton#footerBtnDanger:hover{{color:#ef4444;"
            f"border-color:rgba(239,68,68,0.3);background:rgba(239,68,68,0.05);}}")

        self._input_wrap.setStyleSheet(
            f"QWidget#inputWrap{{background:{t['input_bg']};"
            f"border:1px solid {t['border']};border-radius:8px;overflow:hidden;}}"
            f"QWidget#inputWrap:focus-within{{border-color:{t['accent']};}}")
        self.cat_select.setStyleSheet(
            f"QComboBox#catSelect{{background:transparent;border:none;"
            f"border-right:1px solid {t['border2']};color:{t['muted']};"
            f"font-family:'{FONT}';font-size:11px;padding:0 8px;"
            f"min-width:70px;}}"
            f"QComboBox#catSelect::drop-down{{border:none;width:0;}}"
            f"QComboBox#catSelect QAbstractItemView{{background:{t['input_bg']};"
            f"color:{t['fg']};border:1px solid {t['border2']};"
            f"selection-background-color:{t['accent']};}}")
        self.input_field.setStyleSheet(
            f"QLineEdit#inputField{{background:transparent;border:none;"
            f"color:{t['fg']};font-family:'{FONT}';"
            f"font-size:{self.data.get('font_size',13)}px;padding:0 10px;}}"
            f"QLineEdit#inputField::placeholder{{color:{t['border']};}}")
        self.findChild(QPushButton, "addBtn").setStyleSheet(
            f"QPushButton#addBtn{{background:{t['accent']};color:white;"
            f"border:none;border-radius:8px;font-size:20px;font-weight:bold;}}"
            f"QPushButton#addBtn:hover{{background:{t['accent_h']};}}")

        if hasattr(self, "tray"):
            self.tray.setIcon(make_tray_icon(t["accent"]))
            self._rebuild_tray_menu()
        if not first_run:
            save_data(self.data)
        self.render_todos()

    # ── 렌더링 ────────────────────────────────────────────────────────────────
    def render_todos(self):
        t = THEMES.get(self.data["theme"], THEMES["midnight"])
        fs = self.data.get("font_size", 13)

        # 기존 위젯 제거
        for g in self._cat_groups: g.setParent(None); g.deleteLater()
        self._cat_groups.clear()
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        cats  = self.data.get("categories", [])
        todos = self.data.get("todos", [])
        collapsed = self.data.get("collapsed", {})

        for cat in cats:
            cat_tasks = [td for td in todos if td.get("cat") == cat["id"]]
            g = CategoryGroupWidget(cat, cat_tasks, t,
                                    collapsed.get(cat["id"], False), fs)
            g.sig_toggle_cat.connect(self._toggle_collapse)
            g.sig_edit_cat.connect(self._edit_category)
            g.sig_delete_cat.connect(self._delete_category)
            g.sig_toggle_task.connect(self.toggle_item)
            g.sig_delete_task.connect(self.delete_item)
            g.sig_edit_task.connect(self.edit_item)
            g.sig_drag_start.connect(self._drag_start)
            self._list_lay.addWidget(g)
            self._cat_groups.append(g)

        self._list_lay.addStretch()
        self._update_status()

    def _all_item_widgets(self) -> list[TodoItemWidget]:
        """현재 렌더된 모든 TodoItemWidget 반환 (드래그 계산용)"""
        result = []
        for g in self._cat_groups:
            result.extend(g._item_widgets)
        return result

    def _update_status(self):
        todos = self.data.get("todos", [])
        total = len(todos); done = sum(1 for x in todos if x.get("done"))
        pending = total - done
        self.prog_text.setText(f"{done} / {total} 완료")
        self.count_badge.setText(str(pending))
        # 프로그레스 바
        pct = (done / total) if total else 0
        self._prog_fill.setFixedWidth(int(80 * pct))
        self.clear_done_btn.setVisible(done > 0)

    # ── CRUD ─────────────────────────────────────────────────────────────────
    def add_todo(self):
        text = self.input_field.text().strip()
        if not text: return
        cat_id = self.cat_select.currentData()
        if not cat_id: return
        todos = self.data.setdefault("todos", [])
        cat_tasks = [x for x in todos if x.get("cat") == cat_id]
        max_order = max((x.get("order", 0) for x in cat_tasks), default=-1) + 1
        nxt_id = max((x["id"] for x in todos), default=0) + 1
        todos.insert(0, {"id": nxt_id, "text": text, "cat": cat_id,
                         "done": False, "order": max_order,
                         "created_date": date.today().isoformat()})
        self.input_field.clear()
        save_data(self.data); self.render_todos()

    def toggle_item(self, item_id: int):
        for td in self.data.get("todos", []):
            if td["id"] == item_id: td["done"] = not td["done"]; break
        save_data(self.data); self.render_todos()

    def delete_item(self, item_id: int):
        self.data["todos"] = [x for x in self.data.get("todos", [])
                               if x["id"] != item_id]
        save_data(self.data); self.render_todos()

    def edit_item(self, item_id: int, text: str):
        for td in self.data.get("todos", []):
            if td["id"] == item_id: td["text"] = text; break
        save_data(self.data); self.render_todos()

    def clear_done(self):
        self.data["todos"] = [x for x in self.data.get("todos", [])
                               if not x.get("done")]
        save_data(self.data); self.render_todos()

    # ── 카테고리 CRUD ─────────────────────────────────────────────────────────
    def _toggle_collapse(self, cat_id: str):
        c = self.data.setdefault("collapsed", {})
        c[cat_id] = not c.get(cat_id, False)
        save_data(self.data)
        for g in self._cat_groups:
            if g.cat["id"] == cat_id:
                g.set_collapsed(c[cat_id]); break

    def _add_category(self):
        t = THEMES.get(self.data.get("theme", "midnight"), THEMES["midnight"])
        dlg = CategoryModal(t, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            res = dlg.get_result()
            if res:
                new_id = f"cat_{int(date.today().strftime('%Y%m%d%H%M%S'))}"
                self.data.setdefault("categories", []).append(
                    {"id": new_id, **res})
                save_data(self.data)
                self._refresh_cat_select()
                self.render_todos()

    def _edit_category(self, cat_id: str):
        cat = next((c for c in self.data.get("categories", [])
                    if c["id"] == cat_id), None)
        if not cat: return
        t = THEMES.get(self.data.get("theme", "midnight"), THEMES["midnight"])
        dlg = CategoryModal(t, initial=cat, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            res = dlg.get_result()
            if res:
                cat.update(res)
                save_data(self.data)
                self._refresh_cat_select()
                self.render_todos()

    def _delete_category(self, cat_id: str):
        cat = next((c for c in self.data.get("categories", [])
                    if c["id"] == cat_id), None)
        if not cat: return
        cat_tasks = [x for x in self.data.get("todos", [])
                     if x.get("cat") == cat_id]
        if cat_tasks:
            reply = QMessageBox.question(
                self, "카테고리 삭제",
                f"'{cat['label']}' 카테고리와\n할 일 {len(cat_tasks)}개를 삭제할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes: return
        self.data["categories"] = [c for c in self.data.get("categories", [])
                                    if c["id"] != cat_id]
        self.data["todos"] = [x for x in self.data.get("todos", [])
                               if x.get("cat") != cat_id]
        save_data(self.data)
        self._refresh_cat_select()
        self.render_todos()

    # ── 드래그 정렬 ───────────────────────────────────────────────────────────
    def _make_ghost(self, item_id: int) -> QWidget | None:
        item = next((x for x in self.data.get("todos", [])
                     if x["id"] == item_id), None)
        cat = next((c for c in self.data.get("categories", [])
                    if c["id"] == item.get("cat")), None) if item else None
        if not item or not cat: return None
        t = THEMES.get(self.data["theme"], THEMES["midnight"])
        fs = self.data.get("font_size", 13)

        ghost = QWidget(None,
                        Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        ghost.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ghost.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        ghost.setWindowOpacity(0.82)

        lay = QHBoxLayout(ghost); lay.setContentsMargins(8, 6, 10, 6); lay.setSpacing(0)

        bar = QWidget(); bar.setFixedWidth(3)
        bar.setStyleSheet(f"background:{cat['color']};border-radius:2px;")
        bw = QWidget(); bl = QVBoxLayout(bw); bl.setContentsMargins(0,4,0,4); bl.addWidget(bar)
        lay.addWidget(bw); lay.addSpacing(7)

        lbl = QLabel(item["text"])
        lbl.setStyleSheet(f"color:{t['fg']};font-family:'{FONT}';font-size:{fs}px;"
                          f"background:transparent;")
        lbl.setMaximumWidth(self.list_container.width() - 50)
        lay.addWidget(lbl, 1)

        ghost.setStyleSheet(
            f"QWidget{{background:{t['card']};border:1.5px solid {t['accent']};"
            f"border-radius:7px;}}")
        ghost.setFixedWidth(self.list_container.width())
        ghost.adjustSize()
        return ghost

    def _drag_start(self, item_id: int, gpos: QPoint):
        self._dragging_id    = item_id
        self._drag_insert_at = None
        self._ghost = self._make_ghost(item_id)
        if self._ghost:
            self._ghost.move(gpos.x() + 12, gpos.y() - self._ghost.height() // 2)
            self._ghost.show()
        self._drag_filter = DragFilter(self)
        QApplication.instance().installEventFilter(self._drag_filter)

    def _drag_update(self, gpos: QPoint):
        if self._dragging_id is None: return
        if self._ghost:
            self._ghost.move(gpos.x() + 12, gpos.y() - self._ghost.height() // 2)
        insert_idx = self._calc_insert_idx(gpos)
        if insert_idx == self._drag_insert_at: return
        self._drag_insert_at = insert_idx
        for i, w in enumerate(self._all_item_widgets()):
            w._drag_above = (i == insert_idx); w.update()

    def _drag_end(self, gpos: QPoint):
        if self._dragging_id is None: return
        if self._ghost:
            self._ghost.close(); self._ghost.deleteLater(); self._ghost = None
        insert_idx = self._calc_insert_idx(gpos)

        # 드래그 아이템과 타겟이 같은 카테고리인지 확인
        drag_item = next((x for x in self.data.get("todos", [])
                          if x["id"] == self._dragging_id), None)
        all_ws = self._all_item_widgets()
        target_item_id = (all_ws[insert_idx].item["id"]
                          if all_ws and 0 <= insert_idx < len(all_ws) else None)
        target_item = next((x for x in self.data.get("todos", [])
                            if x["id"] == target_item_id), None) if target_item_id else None

        # 같은 카테고리 내에서만 이동
        if (drag_item and target_item
                and drag_item.get("cat") == target_item.get("cat")):
            todos = self.data.get("todos", [])
            from_idx = next((i for i, x in enumerate(todos)
                             if x["id"] == self._dragging_id), None)
            to_idx   = next((i for i, x in enumerate(todos)
                             if x["id"] == target_item_id), None)
            if from_idx is not None and to_idx is not None and from_idx != to_idx:
                item = todos.pop(from_idx)
                if to_idx > from_idx: to_idx -= 1
                todos.insert(to_idx, item)
                # order 재계산
                cat_id = item.get("cat")
                cat_tasks = [x for x in todos if x.get("cat") == cat_id]
                for i, t_item in enumerate(cat_tasks):
                    t_item["order"] = i
                self.data["todos"] = todos
                save_data(self.data)

        for w in self._all_item_widgets():
            w._drag_above = False; w.update()
        self._dragging_id = None; self._drag_insert_at = None; self._drag_filter = None
        self.render_todos()

    def _calc_insert_idx(self, gpos: QPoint) -> int:
        ws = self._all_item_widgets()
        if not ws: return 0
        for i, w in enumerate(ws):
            r = w.rect()
            top = w.mapToGlobal(r.topLeft())
            bot = w.mapToGlobal(r.bottomLeft())
            if gpos.y() < (top.y() + bot.y()) // 2: return i
        return len(ws)

    # ── 창 이동 ───────────────────────────────────────────────────────────────
    def _hdr_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

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

    # ── 창 제어 · 설정 ────────────────────────────────────────────────────────
    def hide_to_tray(self): self.hide()
    def show_window(self):  self.show(); self.raise_(); self.activateWindow()

    def toggle_aot(self):
        aot = not self.data.get("always_on_top", False)
        self.data["always_on_top"] = aot
        vis = self.isVisible(); self._set_win_flags()
        if vis: self.show()
        save_data(self.data); self._rebuild_tray_menu()

    def set_opacity(self, val: float):
        self.data["opacity"] = val
        self.setWindowOpacity(val)
        save_data(self.data); self._rebuild_tray_menu()

    def set_font_size(self, pt: int):
        self.data["font_size"] = pt
        save_data(self.data); self._rebuild_tray_menu(); self.render_todos()

    def toggle_startup(self):
        su = not self.data.get("startup", False)
        self.data["startup"] = su; set_startup(su)
        save_data(self.data); self._rebuild_tray_menu()

    # ── 백업 / 복원 ────────────────────────────────────────────────────────────
    def do_backup(self):
        fname = backup_data(self.data)
        t = THEMES.get(self.data.get("theme", "midnight"), THEMES["midnight"])
        msg = QMessageBox(self)
        msg.setWindowTitle("백업 완료")
        msg.setText(f"백업 저장 완료:\n{fname.name}")
        msg.setStyleSheet(
            f"QMessageBox{{background:{t['card']};color:{t['fg']};}}"
            f"QLabel{{color:{t['fg']};font-family:'{FONT}';font-size:10px;}}"
            f"QPushButton{{background:{t['accent']};color:white;border:none;"
            f"border-radius:4px;padding:4px 12px;font-family:'{FONT}';}}")
        msg.exec()

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "백업 파일 선택", str(DATA_FILE.parent),
            "JSON 파일 (todos_backup_*.json);;모든 JSON (*.json)")
        if not path: return
        new_data = restore_data(Path(path))
        if new_data is None:
            QMessageBox.warning(self, "오류", "파일을 읽을 수 없습니다."); return
        backup_data(self.data)
        new_data["window"] = self.data["window"]
        self.data = new_data; save_data(self.data)
        self._refresh_cat_select()
        self.apply_theme(self.data.get("theme", "midnight"), first_run=True)
        self.render_todos()

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
