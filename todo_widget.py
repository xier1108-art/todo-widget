#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
할일 위젯 - 토스 스타일 데스크탑 투두 위젯
의존성: pip install pystray Pillow
빌드:  pyinstaller --onefile --noconsole --name 할일위젯 todo_widget.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json, os, sys, threading, copy, shutil
from datetime import date

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_OK = True
except ImportError:
    TRAY_OK = False

try:
    import winreg
    REG_OK = True
except ImportError:
    REG_OK = False

APP_NAME = "할일위젯"
REG_KEY  = "TodoWidget"

def _data_path():
    base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "todos.json")

DATA_PATH = _data_path()

# ══════════════════════════════════════════════════════════════
#  테마 팔레트 (토스 스타일 기반)
# ══════════════════════════════════════════════════════════════
THEMES = {
    "blue": {
        "name": "블루 (기본)",
        "bg":         "#F0F4FA",
        "header":     "#0064FF",
        "header_fg":  "#FFFFFF",
        "fg":         "#191F28",
        "done_fg":    "#B0B8C1",
        "input_bg":   "#FFFFFF",
        "btn_bg":     "#0064FF",
        "btn_fg":     "#FFFFFF",
        "card_bg":    "#FFFFFF",
        "sep":        "#DDE3EE",
        "drag_over":  "#D6E8FF",
        "stat_fg":    "#6B7684",
    },
    "yellow": {
        "name": "노랑",
        "bg":         "#FFFCF0",
        "header":     "#F0A500",
        "header_fg":  "#1C1100",
        "fg":         "#1C1C1E",
        "done_fg":    "#C8BFA0",
        "input_bg":   "#FFFFFF",
        "btn_bg":     "#F0A500",
        "btn_fg":     "#1C1100",
        "card_bg":    "#FFFFFF",
        "sep":        "#F5E6B8",
        "drag_over":  "#FFF0B0",
        "stat_fg":    "#7A6A40",
    },
    "green": {
        "name": "초록",
        "bg":         "#F2FAF4",
        "header":     "#00A651",
        "header_fg":  "#FFFFFF",
        "fg":         "#0D2318",
        "done_fg":    "#9ABEA6",
        "input_bg":   "#FFFFFF",
        "btn_bg":     "#00A651",
        "btn_fg":     "#FFFFFF",
        "card_bg":    "#FFFFFF",
        "sep":        "#C0E4CC",
        "drag_over":  "#D8F5E2",
        "stat_fg":    "#3A7A52",
    },
    "pink": {
        "name": "분홍",
        "bg":         "#FFF5F8",
        "header":     "#FF3B7A",
        "header_fg":  "#FFFFFF",
        "fg":         "#1C0A12",
        "done_fg":    "#D4A8B8",
        "input_bg":   "#FFFFFF",
        "btn_bg":     "#FF3B7A",
        "btn_fg":     "#FFFFFF",
        "card_bg":    "#FFFFFF",
        "sep":        "#FFD0E4",
        "drag_over":  "#FFE0EE",
        "stat_fg":    "#8A3A58",
    },
    "dark": {
        "name": "다크",
        "bg":         "#18181B",
        "header":     "#09090B",
        "header_fg":  "#F4F4F5",
        "fg":         "#F4F4F5",
        "done_fg":    "#52525B",
        "input_bg":   "#27272A",
        "btn_bg":     "#3F3F46",
        "btn_fg":     "#F4F4F5",
        "card_bg":    "#27272A",
        "sep":        "#3F3F46",
        "drag_over":  "#2D2D32",
        "stat_fg":    "#71717A",
    },
}

DEFAULT_DATA = {
    "window":        {"x": 100, "y": 100, "width": 300, "height": 440},
    "theme":         "blue",
    "always_on_top": True,
    "opacity":       0.97,
    "startup":       False,
    "todos":         [],
}

# ══════════════════════════════════════════════════════════════
#  데이터 I/O
# ══════════════════════════════════════════════════════════════
def load_data():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            for k, v in DEFAULT_DATA.items():
                d.setdefault(k, v)
            return d
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_DATA)

def save_data(d):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════
#  Windows 레지스트리 (시작프로그램)
# ══════════════════════════════════════════════════════════════
def set_startup(enable: bool):
    if not REG_OK:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if enable:
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            else:
                exe_dir = os.path.dirname(sys.executable)
                pythonw = os.path.join(exe_dir, "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                cmd = f'"{pythonw}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, REG_KEY, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, REG_KEY)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass

def get_startup() -> bool:
    if not REG_OK:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, REG_KEY)
            result = True
        except FileNotFoundError:
            result = False
        winreg.CloseKey(key)
        return result
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════
#  트레이 아이콘
# ══════════════════════════════════════════════════════════════
def make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=10, fill="#0064FF")
    for y in [20, 30, 40, 50]:
        d.rectangle([12, y, 52, y + 4], fill="#FFFFFF")
    return img

# ══════════════════════════════════════════════════════════════
#  메인 위젯
# ══════════════════════════════════════════════════════════════
class TodoWidget:
    def __init__(self):
        self.data     = load_data()
        self.data["startup"] = get_startup()
        self.todos    = self.data["todos"]
        self.next_id  = max((t["id"] for t in self.todos), default=0) + 1
        self.tray     = None
        self.list_win = None

        self._dx = self._dy = 0
        self._rsx = self._rsy = self._rsw = self._rsh = 0
        self._resize_type    = None
        self._drag_td        = None
        self._drag_orig_y    = 0
        self._drag_orig_idx  = 0
        self._drag_rows      = []
        self._text_labels    = []

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._apply_state()
        self._build()

        if TRAY_OK:
            self._start_tray()

        self.root.mainloop()

    @property
    def t(self):
        return THEMES.get(self.data.get("theme", "blue"), THEMES["blue"])

    def _apply_state(self):
        w = self.data["window"]
        self.root.geometry(f"{w['width']}x{w['height']}+{w['x']}+{w['y']}")
        self.root.minsize(240, 320)
        self.root.configure(bg=self.t["bg"])
        self.root.wm_attributes('-topmost', self.data.get("always_on_top", True))
        self.root.wm_attributes('-alpha',   self.data.get("opacity", 0.97))

    # ══════════════════════════════════════════════════════════
    #  UI 구성
    # ══════════════════════════════════════════════════════════
    def _build(self):
        t = self.t

        # ── 헤더 ─────────────────────────────────────────────
        self.hdr = tk.Frame(self.root, bg=t["header"], height=44)
        self.hdr.pack(fill="x")
        self.hdr.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.hdr, bg=t["header"], fg=t["header_fg"],
            text="할 일", font=("맑은 고딕", 12, "bold"))
        self.title_lbl.pack(side="left", padx=12)

        btn_f = tk.Frame(self.hdr, bg=t["header"])
        btn_f.pack(side="right", padx=6)
        self._hbtn(btn_f, "─", self.hide)
        self._hbtn(btn_f, "×", self.hide if TRAY_OK else self.quit_app)

        days = ["월","화","수","목","금","토","일"]
        d = date.today()
        tk.Label(self.hdr, bg=t["header"], fg=t["header_fg"],
                 text=d.strftime(f"%m.%d ({days[d.weekday()]})"),
                 font=("맑은 고딕", 9)).pack(side="right", padx=2)

        for w in [self.hdr, self.title_lbl]:
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)
        self.hdr.bind("<Button-3>", lambda e: self._ctx_menu(e.x_root, e.y_root))

        # ── 할일 스크롤 영역 ─────────────────────────────────
        mid = tk.Frame(self.root, bg=t["bg"])
        mid.pack(fill="both", expand=True)

        # 우측 리사이즈 스트립(6px) → 스크롤바 → 캔버스 순으로 pack
        # 빈 Frame collapse 방지: 내부에 투명 Canvas 1px 삽입
        r_edge = tk.Frame(mid, bg=t["header"], cursor="size_we")
        r_edge.pack(side="right", fill="y")
        tk.Canvas(r_edge, bg=t["header"], width=6, highlightthickness=0, bd=0
                  ).pack(fill="both", expand=True)
        r_edge.bind("<ButtonPress-1>",   self._rs_r_press)
        r_edge.bind("<B1-Motion>",       self._rs_r_move)
        r_edge.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.vsb = tk.Scrollbar(mid, orient="vertical", width=11)
        self.vsb.pack(side="right", fill="y")

        self.canvas = tk.Canvas(mid, bg=t["bg"], highlightthickness=0, bd=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")

        # scrollregion: sf Configure 이벤트 width/height로 직접 설정 (bbox 오프셋 버그 제거)
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(
                         scrollregion=(0, 0, e.width, e.height)))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_scroll(self.canvas)
        self._bind_scroll(self.sf)

        # ── 상태바 ───────────────────────────────────────────
        sb = tk.Frame(self.root, bg=t["bg"], pady=4)
        sb.pack(fill="x", padx=10)

        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["stat_fg"],
                                 font=("맑은 고딕", 8))
        self.stat_lbl.pack(side="left")

        for txt, cmd in [("완료삭제", self.clear_done), ("목록", self.open_list)]:
            lb = tk.Label(sb, text=txt, bg=t["bg"], fg=t["stat_fg"],
                          font=("맑은 고딕", 8), cursor="hand2")
            lb.pack(side="right", padx=4)
            lb.bind("<Button-1>", lambda e, c=cmd: c())

        # ── 구분선 ───────────────────────────────────────────
        tk.Frame(self.root, bg=t["sep"], height=1).pack(fill="x")

        # ── 입력 영역 ────────────────────────────────────────
        inp = tk.Frame(self.root, bg=t["bg"], pady=8)
        inp.pack(fill="x")

        # 입력창 테두리 효과
        ent_border = tk.Frame(inp, bg=t["sep"])
        ent_border.pack(side="left", fill="x", expand=True, padx=(10, 4))
        ent_inner = tk.Frame(ent_border, bg=t["input_bg"])
        ent_inner.pack(fill="x", padx=1, pady=1)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(ent_inner, textvariable=self.entry_var,
                              bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"],
                              relief="flat", font=("맑은 고딕", 9), bd=0)
        self.entry.pack(fill="x", ipady=6, padx=8)
        self.entry.bind("<Return>", lambda e: self.add_todo())

        add_btn = tk.Label(inp, text="+", bg=t["btn_bg"], fg=t["btn_fg"],
                           font=("맑은 고딕", 14, "bold"), cursor="hand2",
                           width=3, pady=4)
        add_btn.pack(side="right", padx=(0, 10))
        add_btn.bind("<Button-1>", lambda e: self.add_todo())

        # ── 하단 리사이즈 스트립 ─────────────────────────────
        foot = tk.Frame(self.root, bg=t["header"], height=10, cursor="sb_v_double_arrow")
        foot.pack(fill="x")
        foot.pack_propagate(False)

        # 코너 그립 (◢) — 대각 리사이즈
        grip = tk.Label(foot, text="◢", bg=t["header"], fg=t["header_fg"],
                        font=("맑은 고딕", 7), cursor="size_nw_se")
        grip.pack(side="right", padx=3)
        grip.bind("<ButtonPress-1>",   self._rs_corner_press)
        grip.bind("<B1-Motion>",       self._rs_corner_move)
        grip.bind("<ButtonRelease-1>", lambda e: self._do_save())

        # foot 나머지 영역 → 하단 엣지 리사이즈
        foot.bind("<ButtonPress-1>",   self._rs_b_press)
        foot.bind("<B1-Motion>",       self._rs_b_move)
        foot.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.refresh()

    def _hbtn(self, parent, text, cmd):
        lb = tk.Label(parent, text=text, bg=self.t["header"], fg=self.t["header_fg"],
                      font=("맑은 고딕", 10), cursor="hand2", padx=5)
        lb.pack(side="left")
        lb.bind("<Button-1>", lambda e: cmd())
        return lb

    # ── 스크롤 ───────────────────────────────────────────────
    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>", self._scroll)

    def _bind_scroll_recursive(self, widget):
        self._bind_scroll(widget)
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def _scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._sf_id, width=e.width)
        if hasattr(self, '_wl_job'):
            try: self.root.after_cancel(self._wl_job)
            except Exception: pass
        cw = e.width
        self._wl_job = self.root.after(80, lambda: self._apply_wraplength(cw))

    def _apply_wraplength(self, cw):
        wl = max(80, cw - 82)
        for lbl in self._text_labels:
            try: lbl.config(wraplength=wl)
            except Exception: pass

    # ── 창 드래그 ────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── 창 리사이즈 (우측 / 하단 / 대각) ─────────────────────
    def _snap(self):
        self._rsx = self.root.winfo_pointerx()
        self._rsy = self.root.winfo_pointery()
        self._rsw = self.root.winfo_width()
        self._rsh = self.root.winfo_height()

    def _rs_r_press(self, e):
        self._snap()

    def _rs_r_move(self, e):
        w = max(240, self._rsw + (e.x_root - self._rsx))
        self.root.geometry(f"{w}x{self._rsh}")

    def _rs_b_press(self, e):
        self._snap()

    def _rs_b_move(self, e):
        h = max(320, self._rsh + (e.y_root - self._rsy))
        self.root.geometry(f"{self._rsw}x{h}")

    def _rs_corner_press(self, e):
        self._snap()

    def _rs_corner_move(self, e):
        w = max(240, self._rsw + (e.x_root - self._rsx))
        h = max(320, self._rsh + (e.y_root - self._rsy))
        self.root.geometry(f"{w}x{h}")

    # ══════════════════════════════════════════════════════════
    #  할일 CRUD
    # ══════════════════════════════════════════════════════════
    def add_todo(self):
        text = self.entry_var.get().strip()
        if not text:
            return
        self.todos.append({
            "id": self.next_id, "text": text,
            "done": False, "created_date": date.today().isoformat(),
        })
        self.next_id += 1
        self.entry_var.set("")
        self._do_save(); self.refresh(); self._sync_list()

    def toggle(self, todo):
        todo["done"] = not todo["done"]
        self._do_save(); self.refresh(); self._sync_list()

    def delete(self, todo):
        if todo in self.todos:
            self.todos.remove(todo)
        self._do_save(); self.refresh(); self._sync_list()

    def clear_done(self):
        self.todos[:] = [t for t in self.todos if not t["done"]]
        self._do_save(); self.refresh(); self._sync_list()

    def _do_save(self):
        self.data["window"] = {
            "x": self.root.winfo_x(), "y": self.root.winfo_y(),
            "width": self.root.winfo_width(), "height": self.root.winfo_height(),
        }
        self.data["todos"] = self.todos
        save_data(self.data)

    def _sync_list(self):
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists():
                    self.list_win.refresh()
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════
    #  목록 렌더링
    # ══════════════════════════════════════════════════════════
    def refresh(self):
        t = self.t
        for w in self.sf.winfo_children():
            w.destroy()
        self._drag_rows.clear()
        self._text_labels.clear()

        if not self.todos:
            tk.Label(self.sf, text="할 일을 추가해보세요",
                     bg=t["bg"], fg=t["done_fg"],
                     font=("맑은 고딕", 9)).pack(pady=32)
        else:
            for td in self.todos:
                self._render_item(td)

        done = sum(1 for td in self.todos if td["done"])
        total = len(self.todos)
        self.stat_lbl.config(
            text=f"완료 {done} / {total}" if total else "")

        # scrollregion은 sf Configure 이벤트에서 자동 갱신됨
        self.sf.update_idletasks()

    def _render_item(self, td):
        t    = self.t
        done = td["done"]

        # 카드 외곽 (sep = 테두리)
        card = tk.Frame(self.sf, bg=t["sep"])
        card.pack(fill="x", padx=8, pady=3)

        # 카드 내부 (card_bg = 흰색)
        row = tk.Frame(card, bg=t["card_bg"], pady=6)
        row.pack(fill="x", padx=1, pady=1)

        # ≡ 드래그 핸들
        dh = tk.Label(row, text="≡", bg=t["card_bg"], fg=t["done_fg"],
                      font=("맑은 고딕", 10), cursor="fleur", width=2)
        dh.pack(side="left", padx=(4, 0))
        dh.bind("<ButtonPress-1>",   lambda e, td=td, r=row: self._item_drag_start(e, td, r))
        dh.bind("<B1-Motion>",       self._item_drag_move)
        dh.bind("<ButtonRelease-1>", self._item_drag_end)

        # 체크박스
        ck_sym = "●" if done else "○"
        ck_fg  = t["btn_bg"] if done else t["sep"]
        chk = tk.Label(row, text=ck_sym, bg=t["card_bg"],
                       fg=ck_fg, font=("맑은 고딕", 12), cursor="hand2")
        chk.pack(side="left", padx=(2, 4))
        chk.bind("<Button-1>", lambda e, td=td: self.toggle(td))

        # 오른쪽 버튼 (먼저 pack)
        x_lbl = tk.Label(row, text="✕", bg=t["card_bg"], fg=t["done_fg"],
                         font=("맑은 고딕", 9), cursor="hand2")
        x_lbl.pack(side="right", padx=(2, 6))
        x_lbl.bind("<Button-1>", lambda e, td=td: self.delete(td))

        edit_lbl = tk.Label(row, text="✎", bg=t["card_bg"], fg=t["done_fg"],
                            font=("맑은 고딕", 10), cursor="hand2")
        edit_lbl.pack(side="right", padx=2)
        edit_lbl.bind("<Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        # 텍스트
        cw = self.canvas.winfo_width()
        if cw < 10:
            cw = self.data["window"]["width"] - 17
        wl = max(80, cw - 82)
        fg  = t["done_fg"] if done else t["fg"]
        fnt = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)
        lbl = tk.Label(row, text=td["text"], bg=t["card_bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2", wraplength=wl, justify="left")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 2))
        lbl.bind("<Button-1>",        lambda e, td=td: self.toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))
        self._text_labels.append(lbl)

        self._bind_scroll_recursive(row)
        self._bind_scroll_recursive(card)
        self._drag_rows.append((row, td))

    def _inline_edit(self, td, row):
        for w in row.winfo_children():
            w.destroy()
        t    = self.t
        done = td["done"]

        tk.Label(row, text="≡", bg=t["card_bg"], fg=t["done_fg"],
                 font=("맑은 고딕", 10), width=2).pack(side="left", padx=(4, 0))

        ck_sym = "●" if done else "○"
        ck_fg  = t["btn_bg"] if done else t["sep"]
        tk.Label(row, text=ck_sym, bg=t["card_bg"], fg=ck_fg,
                 font=("맑은 고딕", 12)).pack(side="left", padx=(2, 4))

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt: td["text"] = txt
            self._do_save(); self.refresh(); self._sync_list()

        def cancel(e=None):
            self.refresh()

        cancel_lbl = tk.Label(row, text="✗", bg=t["card_bg"], fg="#EF4444",
                              font=("맑은 고딕", 11, "bold"), cursor="hand2")
        cancel_lbl.pack(side="right", padx=(2, 6))
        cancel_lbl.bind("<Button-1>", lambda e: cancel())

        ok_lbl = tk.Label(row, text="✓", bg=t["card_bg"], fg="#22C55E",
                          font=("맑은 고딕", 11, "bold"), cursor="hand2")
        ok_lbl.pack(side="right", padx=2)
        ok_lbl.bind("<Button-1>", lambda e: commit())

        ent = tk.Entry(row, textvariable=var, bg=t["input_bg"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=("맑은 고딕", 9), bd=0,
                       highlightthickness=1, highlightbackground=t["sep"],
                       highlightcolor=t["btn_bg"])
        ent.pack(side="left", fill="x", expand=True, padx=2, ipady=3)
        ent.focus_set()
        ent.select_range(0, "end")
        ent.bind("<Return>", commit)
        ent.bind("<Escape>", cancel)

        self._bind_scroll_recursive(row)

    # ══════════════════════════════════════════════════════════
    #  드래그 정렬
    # ══════════════════════════════════════════════════════════
    def _item_drag_start(self, e, td, row):
        self._drag_td       = td
        self._drag_orig_y   = e.y_root
        self._drag_orig_idx = self.todos.index(td)
        row.config(bg=self.t["drag_over"])
        row.master.config(bg=self.t["drag_over"])

    def _item_drag_move(self, e):
        if self._drag_td is None:
            return
        dy     = e.y_root - self._drag_orig_y
        target = max(0, min(len(self._drag_rows) - 1,
                            self._drag_orig_idx + round(dy / 36)))
        t = self.t
        for i, (rw, _) in enumerate(self._drag_rows):
            rw.config(bg=t["drag_over"] if i == target else t["card_bg"])
            rw.master.config(bg=t["drag_over"] if i == target else t["sep"])

    def _item_drag_end(self, e):
        if self._drag_td is None:
            return
        dy     = e.y_root - self._drag_orig_y
        orig   = self._drag_orig_idx
        target = max(0, min(len(self.todos) - 1, orig + round(dy / 36)))
        td = self.todos.pop(orig)
        self.todos.insert(target, td)
        self._drag_td = None
        self._do_save(); self.refresh(); self._sync_list()

    # ══════════════════════════════════════════════════════════
    #  창 관리
    # ══════════════════════════════════════════════════════════
    def hide(self):
        self._do_save(); self.root.withdraw()

    def show(self):
        self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def quit_app(self):
        self._do_save()
        if self.tray:
            self.tray.stop()
        self.root.after(0, self.root.destroy)

    # ══════════════════════════════════════════════════════════
    #  백업 / 불러오기
    # ══════════════════════════════════════════════════════════
    def backup(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="할일 백업 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"todos_backup_{date.today().isoformat()}.json",
        )
        if path:
            try:
                shutil.copy2(DATA_PATH, path)
                messagebox.showinfo("백업 완료", f"저장됨:\n{path}", parent=self.root)
            except Exception as ex:
                messagebox.showerror("오류", str(ex), parent=self.root)

    def restore(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="할일 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "todos" not in d:
                messagebox.showerror("오류", "올바른 백업 파일이 아닙니다.", parent=self.root)
                return
            for k, v in DEFAULT_DATA.items():
                d.setdefault(k, v)
            self.data  = d
            self.todos = d["todos"]
            self.next_id = max((t["id"] for t in self.todos), default=0) + 1
            save_data(self.data)
            self.refresh(); self._sync_list()
            messagebox.showinfo("완료", f"{len(self.todos)}개 항목을 불러왔습니다.", parent=self.root)
        except Exception as ex:
            messagebox.showerror("오류", str(ex), parent=self.root)

    # ══════════════════════════════════════════════════════════
    #  우클릭 메뉴
    # ══════════════════════════════════════════════════════════
    def _ctx_menu(self, x, y):
        t = self.t
        m = tk.Menu(self.root, tearoff=0, bg=t["card_bg"], fg=t["fg"],
                    activebackground=t["header"], activeforeground=t["header_fg"],
                    relief="flat", bd=1)

        aot = self.data.get("always_on_top", True)
        m.add_command(label=f"{'✓' if aot else '  '} 항상 위에 표시",
                      command=self._toggle_aot)

        op_m = tk.Menu(m, tearoff=0, bg=t["card_bg"], fg=t["fg"],
                       activebackground=t["header"], activeforeground=t["header_fg"])
        cur_op = self.data.get("opacity", 0.97)
        for val, label in [(0.75, "75%"), (0.85, "85%"), (0.95, "95%"), (1.0, "100%")]:
            mark = "✓ " if abs(cur_op - val) < 0.02 else "  "
            op_m.add_command(label=f"{mark}{label}",
                             command=lambda v=val: self._set_opacity(v))
        m.add_cascade(label="투명도", menu=op_m)

        th_m = tk.Menu(m, tearoff=0, bg=t["card_bg"], fg=t["fg"],
                       activebackground=t["header"], activeforeground=t["header_fg"])
        cur_th = self.data.get("theme", "blue")
        for key, info in THEMES.items():
            mark = "✓ " if key == cur_th else "  "
            th_m.add_command(label=f"{mark}{info['name']}",
                             command=lambda k=key: self._set_theme(k))
        m.add_cascade(label="테마 색상", menu=th_m)

        m.add_separator()
        su = get_startup()
        m.add_command(label=f"{'✓' if su else '  '} 윈도우 시작 시 자동 실행",
                      command=self._toggle_startup)

        m.add_separator()
        m.add_command(label="전체 목록 보기",      command=self.open_list)
        m.add_command(label="백업 (내보내기)",     command=self.backup)
        m.add_command(label="불러오기 (가져오기)", command=self.restore)
        m.add_separator()
        m.add_command(label="완전 종료",           command=self.quit_app)

        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def _toggle_aot(self):
        self.data["always_on_top"] = not self.data.get("always_on_top", True)
        self.root.wm_attributes('-topmost', self.data["always_on_top"])
        self._do_save()

    def _set_opacity(self, val):
        self.data["opacity"] = val
        self.root.wm_attributes('-alpha', val)
        self._do_save()

    def _set_theme(self, key):
        self.data["theme"] = key
        self._do_save()
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists():
                    self.list_win.win.destroy()
            except Exception:
                pass
            self.list_win = None
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=self.t["bg"])
        self._apply_state()
        self._build()

    def _toggle_startup(self):
        current = get_startup()
        set_startup(not current)
        self.data["startup"] = not current
        self._do_save()

    # ══════════════════════════════════════════════════════════
    #  시스템 트레이
    # ══════════════════════════════════════════════════════════
    def _start_tray(self):
        def setup(icon):
            icon.visible = True

        def aot_text(item):
            on = self.data.get("always_on_top", True)
            return ("✅ 항상 위에 표시 [켜짐]" if on else "⬛ 항상 위에 표시 [꺼짐]")

        def startup_text(item):
            on = get_startup()
            return ("✅ 윈도우 시작 시 자동 실행 [켜짐]" if on else "⬛ 윈도우 시작 시 자동 실행 [꺼짐]")

        menu = pystray.Menu(
            pystray.MenuItem("📋 할일위젯 열기",
                             lambda: self.root.after(0, self.show), default=True),
            pystray.MenuItem("📂 전체 목록 보기",
                             lambda: self.root.after(0, self.open_list)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(aot_text,
                             lambda: self.root.after(0, self._toggle_aot)),
            pystray.MenuItem(startup_text,
                             lambda: self.root.after(0, self._toggle_startup)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("💾 백업 (내보내기)",
                             lambda: self.root.after(0, self.backup)),
            pystray.MenuItem("📥 불러오기 (가져오기)",
                             lambda: self.root.after(0, self.restore)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 완전 종료",
                             lambda: self.root.after(0, self.quit_app)),
        )

        try:
            icon_img = make_tray_icon()
        except Exception:
            icon_img = Image.new("RGB", (64, 64), "#0064FF")

        self.tray = pystray.Icon(APP_NAME, icon_img, APP_NAME, menu=menu)
        threading.Thread(target=lambda: self.tray.run(setup), daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  전체 목록 창
    # ══════════════════════════════════════════════════════════
    def open_list(self):
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists():
                    self.list_win.win.lift()
                    self.list_win.win.focus_force()
                    return
            except Exception:
                pass
        self.list_win = ListWindow(self)


# ══════════════════════════════════════════════════════════════
#  전체 목록 창
# ══════════════════════════════════════════════════════════════
class ListWindow:
    def __init__(self, app: TodoWidget):
        self.app         = app
        self.filter_mode = "all"
        self.search_var  = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh())

        t = app.t
        self.win = tk.Toplevel(app.root)
        self.win.title("전체 할일 관리")
        self.win.geometry("460x540")
        self.win.configure(bg=t["bg"])
        self.win.wm_attributes('-topmost', app.data.get("always_on_top", True))
        self.win.resizable(True, True)
        self._build()
        self.win.focus_force()

    def _build(self):
        t = self.app.t

        # 헤더
        hdr = tk.Frame(self.win, bg=t["header"], height=48)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="전체 할일 관리",
                 bg=t["header"], fg=t["header_fg"],
                 font=("맑은 고딕", 12, "bold")).pack(side="left", padx=16, pady=10)

        # 필터 + 검색 바
        bar = tk.Frame(self.win, bg=t["bg"], pady=8)
        bar.pack(fill="x", padx=12)

        self.filter_btns = {}
        filter_frame = tk.Frame(bar, bg=t["bg"])
        filter_frame.pack(side="left")
        for label, mode in [("전체", "all"), ("미완료", "undone"), ("완료", "done")]:
            btn = tk.Label(filter_frame, text=label,
                           font=("맑은 고딕", 9), cursor="hand2",
                           padx=10, pady=4, relief="flat")
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda e, m=mode: self._set_filter(m))
            self.filter_btns[mode] = btn

        # 검색창
        se_border = tk.Frame(bar, bg=t["sep"])
        se_border.pack(side="right", padx=0)
        se_inner = tk.Frame(se_border, bg=t["input_bg"])
        se_inner.pack(fill="x", padx=1, pady=1)
        tk.Label(se_inner, text="🔍", bg=t["input_bg"], fg=t["stat_fg"],
                 font=("맑은 고딕", 9)).pack(side="left", padx=(6, 2))
        se = tk.Entry(se_inner, textvariable=self.search_var,
                      bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"],
                      relief="flat", font=("맑은 고딕", 9), bd=0, width=12)
        se.pack(side="left", ipady=4, padx=(0, 6))

        self._update_filter_btns()
        tk.Frame(self.win, bg=t["sep"], height=1).pack(fill="x")

        # 목록 스크롤
        lf = tk.Frame(self.win, bg=t["bg"])
        lf.pack(fill="both", expand=True, padx=0, pady=0)

        self.vsb = tk.Scrollbar(lf, orient="vertical", width=11)
        self.vsb.pack(side="right", fill="y")
        self.canvas = tk.Canvas(lf, bg=t["bg"], highlightthickness=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)

        scroll_cb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        self.canvas.bind("<MouseWheel>", scroll_cb)

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")

        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(
                         scrollregion=(0, 0, e.width, e.height)))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._sf_id, width=e.width))
        self.sf.bind("<MouseWheel>", scroll_cb)

        # 하단 상태바
        sb = tk.Frame(self.win, bg=t["bg"], pady=6)
        sb.pack(fill="x", padx=12)
        tk.Frame(self.win, bg=t["sep"], height=1).pack(fill="x", before=sb)

        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["stat_fg"],
                                 font=("맑은 고딕", 8))
        self.stat_lbl.pack(side="left")
        clr_btn = tk.Label(sb, text="완료 항목 삭제", cursor="hand2",
                           bg=t["btn_bg"], fg=t["btn_fg"],
                           font=("맑은 고딕", 8), padx=8, pady=3)
        clr_btn.pack(side="right")
        clr_btn.bind("<Button-1>", lambda e: self._clear_done())

        self.refresh()

    def _set_filter(self, mode):
        self.filter_mode = mode; self._update_filter_btns(); self.refresh()

    def _update_filter_btns(self):
        t = self.app.t
        for mode, btn in self.filter_btns.items():
            active = mode == self.filter_mode
            btn.config(bg=t["header"] if active else t["bg"],
                       fg=t["header_fg"] if active else t["fg"])

    def refresh(self):
        t = self.app.t
        for w in self.sf.winfo_children():
            w.destroy()

        kw    = self.search_var.get().strip().lower()
        today = date.today().isoformat()
        items = [
            td for td in self.app.todos
            if (self.filter_mode == "all" or
                (self.filter_mode == "undone" and not td["done"]) or
                (self.filter_mode == "done"   and     td["done"]))
            and (not kw or kw in td["text"].lower())
        ]

        if not items:
            tk.Label(self.sf, text="항목이 없습니다.", bg=t["bg"],
                     fg=t["done_fg"], font=("맑은 고딕", 9)).pack(pady=24)
        else:
            for td in items:
                self._row(td, today)

        total = len(self.app.todos)
        done  = sum(1 for td in self.app.todos if td["done"])
        self.stat_lbl.config(
            text=f"총 {total}개  ·  미완료 {total-done}개  ·  완료 {done}개")

    def _row(self, td, today):
        t    = self.app.t
        done = td["done"]

        card = tk.Frame(self.sf, bg=t["sep"])
        card.pack(fill="x", padx=10, pady=3)
        row  = tk.Frame(card, bg=t["card_bg"], pady=6)
        row.pack(fill="x", padx=1, pady=1)

        ck_sym = "●" if done else "○"
        ck_fg  = t["btn_bg"] if done else t["sep"]
        chk = tk.Label(row, text=ck_sym, bg=t["card_bg"], fg=ck_fg,
                       font=("맑은 고딕", 12), cursor="hand2")
        chk.pack(side="left", padx=(8, 4))
        chk.bind("<Button-1>", lambda e, td=td: self._toggle(td))

        # 날짜 뱃지
        created = td.get("created_date", today)
        if created == today:
            badge = "오늘"
        else:
            try:
                diff = (date.today() - date.fromisoformat(created)).days
                badge = "어제" if diff == 1 else f"{diff}일 전"
            except Exception:
                badge = ""

        del_lbl = tk.Label(row, text="삭제", bg=t["card_bg"], fg=t["done_fg"],
                           font=("맑은 고딕", 8), cursor="hand2")
        del_lbl.pack(side="right", padx=(2, 8))
        del_lbl.bind("<Button-1>", lambda e, td=td: self._delete(td))

        edit_lbl = tk.Label(row, text="✎", bg=t["card_bg"], fg=t["done_fg"],
                            font=("맑은 고딕", 10), cursor="hand2")
        edit_lbl.pack(side="right", padx=2)
        edit_lbl.bind("<Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        if badge:
            tk.Label(row, text=badge, bg=t["card_bg"], fg=t["done_fg"],
                     font=("맑은 고딕", 7), width=6).pack(side="right", padx=2)

        fnt = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)
        fg  = t["done_fg"] if done else t["fg"]
        lbl = tk.Label(row, text=td["text"], bg=t["card_bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=4)
        lbl.bind("<Button-1>",        lambda e, td=td: self._toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        scroll_cb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        for w in [row, card] + list(row.winfo_children()):
            w.bind("<MouseWheel>", scroll_cb)

    def _inline_edit(self, td, row):
        for w in row.winfo_children():
            w.destroy()
        t    = self.app.t
        done = td["done"]

        ck_sym = "●" if done else "○"
        ck_fg  = t["btn_bg"] if done else t["sep"]
        tk.Label(row, text=ck_sym, bg=t["card_bg"], fg=ck_fg,
                 font=("맑은 고딕", 12)).pack(side="left", padx=(8, 4))

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt: td["text"] = txt
            self.app._do_save(); self.refresh(); self.app.refresh()

        def cancel(e=None):
            self.refresh()

        cancel_lbl = tk.Label(row, text="✗", bg=t["card_bg"], fg="#EF4444",
                              font=("맑은 고딕", 11, "bold"), cursor="hand2")
        cancel_lbl.pack(side="right", padx=(2, 8))
        cancel_lbl.bind("<Button-1>", lambda e: cancel())

        ok_lbl = tk.Label(row, text="✓", bg=t["card_bg"], fg="#22C55E",
                          font=("맑은 고딕", 11, "bold"), cursor="hand2")
        ok_lbl.pack(side="right", padx=2)
        ok_lbl.bind("<Button-1>", lambda e: commit())

        ent = tk.Entry(row, textvariable=var, bg=t["input_bg"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=("맑은 고딕", 9), bd=0,
                       highlightthickness=1, highlightbackground=t["sep"],
                       highlightcolor=t["btn_bg"])
        ent.pack(side="left", fill="x", expand=True, padx=6, ipady=3)
        ent.focus_set(); ent.select_range(0, "end")
        ent.bind("<Return>", commit); ent.bind("<Escape>", cancel)

        scroll_cb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        for w in row.winfo_children():
            w.bind("<MouseWheel>", scroll_cb)

    def _toggle(self, td):
        td["done"] = not td["done"]
        self.app._do_save(); self.refresh(); self.app.refresh()

    def _delete(self, td):
        if td in self.app.todos:
            self.app.todos.remove(td)
        self.app._do_save(); self.refresh(); self.app.refresh()

    def _clear_done(self):
        self.app.todos[:] = [td for td in self.app.todos if not td["done"]]
        self.app._do_save(); self.refresh(); self.app.refresh()


# ══════════════════════════════════════════════════════════════
#  진입점
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    TodoWidget()
