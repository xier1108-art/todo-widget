#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
할일 위젯 v1.6 — 모던 카드 UI
의존성: pip install pystray Pillow
빌드:  pyinstaller --onefile --noconsole --icon=icon.ico --name 할일위젯 todo_widget.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json, os, sys, threading, copy, shutil
from datetime import date

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
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
FONT     = "맑은 고딕"     # 한글 기본 모던 폰트 (Windows 7+, SIL OFL-free)
CARD_R   = 16              # 카드 모서리 반경 (px)

def _data_path():
    base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "todos.json")

DATA_PATH = _data_path()

# ──────────────────────────────────────────────
#  테마
# ──────────────────────────────────────────────
THEMES = {
    "blue": {
        "name": "블루 (기본)",
        "bg":       "#EEF2F8",
        "header":   "#1A56DB",
        "hdr_fg":   "#FFFFFF",
        "fg":       "#111827",
        "muted":    "#9CA3AF",
        "card":     "#FFFFFF",
        "border":   "#E2E8F0",
        "accent":   "#1A56DB",
        "done_fg":  "#D1D5DB",
        "inp":      "#FFFFFF",
        "btn":      "#1A56DB",
        "btn_fg":   "#FFFFFF",
        "drag":     "#DBEAFE",
    },
    "yellow": {
        "name": "노랑",
        "bg":       "#FEFCE8",
        "header":   "#D97706",
        "hdr_fg":   "#FFFFFF",
        "fg":       "#1C1917",
        "muted":    "#A8A29E",
        "card":     "#FFFFFF",
        "border":   "#FDE68A",
        "accent":   "#D97706",
        "done_fg":  "#D6D3D1",
        "inp":      "#FFFFFF",
        "btn":      "#D97706",
        "btn_fg":   "#FFFFFF",
        "drag":     "#FEF3C7",
    },
    "green": {
        "name": "초록",
        "bg":       "#F0FDF4",
        "header":   "#16A34A",
        "hdr_fg":   "#FFFFFF",
        "fg":       "#14532D",
        "muted":    "#86EFAC",
        "card":     "#FFFFFF",
        "border":   "#BBF7D0",
        "accent":   "#16A34A",
        "done_fg":  "#D1FAE5",
        "inp":      "#FFFFFF",
        "btn":      "#16A34A",
        "btn_fg":   "#FFFFFF",
        "drag":     "#DCFCE7",
    },
    "pink": {
        "name": "분홍",
        "bg":       "#FFF1F2",
        "header":   "#E11D48",
        "hdr_fg":   "#FFFFFF",
        "fg":       "#4C0519",
        "muted":    "#FDA4AF",
        "card":     "#FFFFFF",
        "border":   "#FECDD3",
        "accent":   "#E11D48",
        "done_fg":  "#FFE4E6",
        "inp":      "#FFFFFF",
        "btn":      "#E11D48",
        "btn_fg":   "#FFFFFF",
        "drag":     "#FFE4E6",
    },
    "dark": {
        "name": "다크",
        "bg":       "#0F172A",
        "header":   "#1E293B",
        "hdr_fg":   "#F1F5F9",
        "fg":       "#F1F5F9",
        "muted":    "#475569",
        "card":     "#1E293B",
        "border":   "#334155",
        "accent":   "#3B82F6",
        "done_fg":  "#334155",
        "inp":      "#0F172A",
        "btn":      "#3B82F6",
        "btn_fg":   "#FFFFFF",
        "drag":     "#1E3A5F",
    },
}

DEFAULT_DATA = {
    "window":        {"x": 100, "y": 100, "width": 300, "height": 460},
    "theme":         "blue",
    "always_on_top": True,
    "opacity":       0.97,
    "startup":       False,
    "todos":         [],
}

# ──────────────────────────────────────────────
#  둥근 모서리 카드 그리기
# ──────────────────────────────────────────────
def _draw_rounded(canvas, x1, y1, x2, y2, r, fill, outline, tag="card"):
    """Canvas 위에 둥근 직사각형을 그린다 (border + fill 2중 레이어)."""
    canvas.delete(tag)
    d = r * 2
    for color, (ox1, oy1, ox2, oy2), radius in [
        (outline, (x1, y1, x2, y2), r),
        (fill,    (x1+1, y1+1, x2-1, y2-1), max(1, r-1)),
    ]:
        rd = radius * 2
        kw = dict(fill=color, outline=color, tags=tag)
        fx1, fy1, fx2, fy2 = ox1, oy1, ox2, oy2
        canvas.create_arc(fx1,    fy1,    fx1+rd, fy1+rd, start=90,  extent=90, style="pieslice", **kw)
        canvas.create_arc(fx2-rd, fy1,    fx2,    fy1+rd, start=0,   extent=90, style="pieslice", **kw)
        canvas.create_arc(fx2-rd, fy2-rd, fx2,    fy2,    start=270, extent=90, style="pieslice", **kw)
        canvas.create_arc(fx1,    fy2-rd, fx1+rd, fy2,    start=180, extent=90, style="pieslice", **kw)
        canvas.create_rectangle(fx1+radius, fy1, fx2-radius, fy2, **kw)
        canvas.create_rectangle(fx1, fy1+radius, fx2, fy2-radius, **kw)

# ──────────────────────────────────────────────
#  데이터 I/O
# ──────────────────────────────────────────────
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

# ──────────────────────────────────────────────
#  레지스트리 (시작프로그램)
# ──────────────────────────────────────────────
def set_startup(enable: bool):
    if not REG_OK: return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if enable:
            cmd = (f'"{sys.executable}"' if getattr(sys, 'frozen', False)
                   else f'"{_pythonw()}" "{os.path.abspath(__file__)}"')
            winreg.SetValueEx(key, REG_KEY, 0, winreg.REG_SZ, cmd)
        else:
            try: winreg.DeleteValue(key, REG_KEY)
            except FileNotFoundError: pass
        winreg.CloseKey(key)
    except Exception: pass

def _pythonw():
    d = os.path.dirname(sys.executable)
    p = os.path.join(d, "pythonw.exe")
    return p if os.path.exists(p) else sys.executable

def get_startup() -> bool:
    if not REG_OK: return False
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run",
                           0, winreg.KEY_READ)
        try:    winreg.QueryValueEx(k, REG_KEY); r = True
        except: r = False
        winreg.CloseKey(k); return r
    except: return False

# ──────────────────────────────────────────────
#  아이콘 이미지 생성
# ──────────────────────────────────────────────
def make_tray_icon():
    S = 64
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, S-2, S-2], radius=14, fill="#1A56DB")
    # 체크마크
    d.line([(16, 34), (26, 44), (48, 20)], fill="#FFFFFF", width=5)
    return img

def make_app_icon():
    """EXE 빌드용 아이콘 (여러 사이즈)"""
    sizes = [16, 32, 48, 64, 128, 256]
    imgs = []
    for S in sizes:
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        r = max(2, S // 6)
        d.rounded_rectangle([1, 1, S-1, S-1], radius=r, fill="#1A56DB")
        lw = max(1, S // 16)
        p1 = (S * 0.25, S * 0.52)
        p2 = (S * 0.42, S * 0.70)
        p3 = (S * 0.75, S * 0.32)
        d.line([p1, p2, p3], fill="#FFFFFF", width=lw * 2)
        imgs.append(img)
    return imgs

def save_app_icon(path="icon.ico"):
    imgs = make_app_icon()
    imgs[0].save(path, format="ICO",
                 append_images=imgs[1:],
                 sizes=[(i.width, i.height) for i in imgs])

# ──────────────────────────────────────────────
#  메인 위젯
# ──────────────────────────────────────────────
class TodoWidget:
    def __init__(self):
        self.data    = load_data()
        self.data["startup"] = get_startup()
        self.todos   = self.data["todos"]
        self.next_id = max((t["id"] for t in self.todos), default=0) + 1
        self.tray    = None
        self.list_win = None

        self._dx = self._dy = 0
        self._rsx = self._rsy = self._rsw = self._rsh = 0
        self._drag_td = self._drag_orig_y = self._drag_orig_idx = None
        self._drag_rows:   list = []
        self._text_labels:  list = []
        self._card_cvs:     list = []   # Canvas refs for rounded cards
        self._card_redraws: list = []   # immediate redraw callbacks (flash 방지)

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
        self.root.minsize(260, 340)
        self.root.configure(bg=self.t["bg"])
        self.root.wm_attributes('-topmost', self.data.get("always_on_top", True))
        self.root.wm_attributes('-alpha',   self.data.get("opacity", 0.97))

    # ──────────────────────────────────────────
    #  UI 빌드
    # ──────────────────────────────────────────
    def _build(self):
        t = self.t

        # ── 헤더 ──────────────────────────────
        hdr = tk.Frame(self.root, bg=t["header"], height=50)
        hdr.pack(fill="x"); hdr.pack_propagate(False)

        self.hdr = hdr
        left = tk.Frame(hdr, bg=t["header"])
        left.pack(side="left", padx=14, pady=0, fill="y")

        tk.Label(left, text="할 일", bg=t["header"], fg=t["hdr_fg"],
                 font=(FONT, 13, "bold")).pack(side="left", pady=0)

        self.badge_lbl = tk.Label(left, text="", bg=t["accent"], fg="#FFFFFF",
                                  font=(FONT, 7, "bold"), padx=4, pady=1)

        right = tk.Frame(hdr, bg=t["header"])
        right.pack(side="right", padx=8, fill="y")

        days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        d = date.today()
        tk.Label(right, text=d.strftime(f"%b %d, {days[d.weekday()]}"),
                 bg=t["header"], fg=t["hdr_fg"],
                 font=(FONT, 8), pady=0).pack(side="left", padx=(0, 8))

        for sym, cmd in [("─", self.hide),
                         ("×", self.hide if TRAY_OK else self.quit_app)]:
            lb = tk.Label(right, text=sym, bg=t["header"], fg=t["hdr_fg"],
                          font=(FONT, 11), cursor="hand2", padx=4)
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, c=cmd: c())

        for w in (hdr, left):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)
        hdr.bind("<Button-3>", lambda e: self._ctx_menu(e.x_root, e.y_root))

        # ── 스크롤 영역 ───────────────────────
        mid = tk.Frame(self.root, bg=t["bg"])
        mid.pack(fill="both", expand=True)

        # 우측 리사이즈 핸들 (6px) — 내부 Canvas로 collapse 방지 + 이벤트 바인딩
        r_edge = tk.Frame(mid, bg=t["header"], cursor="size_we")
        r_edge.pack(side="right", fill="y")
        r_cv = tk.Canvas(r_edge, bg=t["header"], width=6,
                         highlightthickness=0, bd=0, cursor="size_we")
        r_cv.pack(fill="both", expand=True)
        for w in (r_edge, r_cv):
            w.bind("<ButtonPress-1>",   self._rs_r_press)
            w.bind("<B1-Motion>",       self._rs_r_move)
            w.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.vsb = tk.Scrollbar(mid, orient="vertical", width=10,
                                troughcolor=t["bg"], bg=t["border"],
                                activebackground=t["muted"], relief="flat", bd=0)
        self.vsb.pack(side="right", fill="y")

        self.canvas = tk.Canvas(mid, bg=t["bg"], highlightthickness=0, bd=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")

        # scrollregion: sf Configure 이벤트 e.width/e.height 직접 사용 (bbox 오프셋 제거)
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(
                         scrollregion=(0, 0, e.width, e.height)))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_scroll(self.canvas)
        self._bind_scroll(self.sf)

        # ── 상태바 ────────────────────────────
        sb = tk.Frame(self.root, bg=t["bg"])
        sb.pack(fill="x", padx=12, pady=(4, 2))
        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["muted"],
                                 font=(FONT, 8))
        self.stat_lbl.pack(side="left")
        for txt, cmd in [("완료 삭제", self.clear_done), ("전체 목록", self.open_list)]:
            lb = tk.Label(sb, text=txt, bg=t["bg"], fg=t["muted"],
                          font=(FONT, 8), cursor="hand2")
            lb.pack(side="right", padx=6)
            lb.bind("<Button-1>", lambda e, c=cmd: c())

        # 구분선
        tk.Frame(self.root, bg=t["border"], height=1).pack(fill="x")

        # ── 입력 영역 ─────────────────────────
        inp = tk.Frame(self.root, bg=t["bg"], pady=8)
        inp.pack(fill="x")

        # 입력창 — rounded border 효과
        eb = tk.Frame(inp, bg=t["border"])
        eb.pack(side="left", fill="x", expand=True, padx=(10, 4))
        ei = tk.Frame(eb, bg=t["inp"])
        ei.pack(fill="x", padx=1, pady=1)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(ei, textvariable=self.entry_var,
                              bg=t["inp"], fg=t["fg"],
                              insertbackground=t["fg"],
                              relief="flat", font=(FONT, 10), bd=0)
        self.entry.pack(fill="x", ipady=7, padx=10)
        self.entry.bind("<Return>", lambda e: self.add_todo())

        add_btn = tk.Label(inp, text="+", bg=t["btn"], fg=t["btn_fg"],
                           font=(FONT, 16, "bold"), cursor="hand2",
                           width=3, pady=3)
        add_btn.pack(side="right", padx=(0, 10))
        add_btn.bind("<Button-1>", lambda e: self.add_todo())

        # ── 하단 리사이즈 스트립 ──────────────
        foot = tk.Frame(self.root, bg=t["header"], height=10,
                        cursor="sb_v_double_arrow")
        foot.pack(fill="x")
        foot.pack_propagate(False)

        grip = tk.Label(foot, text="◢", bg=t["header"], fg=t["hdr_fg"],
                        font=(FONT, 7), cursor="size_nw_se")
        grip.pack(side="right", padx=4)
        grip.bind("<ButtonPress-1>",   self._rs_corner_press)
        grip.bind("<B1-Motion>",       self._rs_corner_move)
        grip.bind("<ButtonRelease-1>", lambda e: self._do_save())

        foot.bind("<ButtonPress-1>",   self._rs_b_press)
        foot.bind("<B1-Motion>",       self._rs_b_move)
        foot.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.refresh()

    # ──────────────────────────────────────────
    #  스크롤
    # ──────────────────────────────────────────
    def _bind_scroll(self, w):
        w.bind("<MouseWheel>", self._scroll)

    def _bind_scroll_recursive(self, w):
        self._bind_scroll(w)
        for c in w.winfo_children():
            self._bind_scroll_recursive(c)

    def _scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._sf_id, width=e.width)
        # 카드 Canvas 너비 + rounded rect 재렌더
        for fn in self._card_redraws:
            try: fn()
            except Exception: pass
        # wraplength 디바운스
        if hasattr(self, '_wl_job'):
            try: self.root.after_cancel(self._wl_job)
            except: pass
        cw = e.width
        self._wl_job = self.root.after(80, lambda: self._apply_wl(cw))

    def _apply_wl(self, cw):
        wl = max(80, cw - 90)
        for lbl in self._text_labels:
            try: lbl.config(wraplength=wl)
            except: pass

    # ──────────────────────────────────────────
    #  창 드래그
    # ──────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")

    # ──────────────────────────────────────────
    #  창 리사이즈
    # ──────────────────────────────────────────
    def _snap(self):
        self._rsx = self.root.winfo_pointerx()
        self._rsy = self.root.winfo_pointery()
        self._rsw = self.root.winfo_width()
        self._rsh = self.root.winfo_height()

    def _rs_r_press(self, e):       self._snap()
    def _rs_r_move(self, e):
        w = max(260, self._rsw + e.x_root - self._rsx)
        self.root.geometry(f"{w}x{self._rsh}")

    def _rs_b_press(self, e):       self._snap()
    def _rs_b_move(self, e):
        h = max(340, self._rsh + e.y_root - self._rsy)
        self.root.geometry(f"{self._rsw}x{h}")

    def _rs_corner_press(self, e):  self._snap()
    def _rs_corner_move(self, e):
        w = max(260, self._rsw + e.x_root - self._rsx)
        h = max(340, self._rsh + e.y_root - self._rsy)
        self.root.geometry(f"{w}x{h}")

    # ──────────────────────────────────────────
    #  CRUD
    # ──────────────────────────────────────────
    def add_todo(self):
        text = self.entry_var.get().strip()
        if not text: return
        self.todos.append({"id": self.next_id, "text": text,
                           "done": False, "created_date": date.today().isoformat()})
        self.next_id += 1
        self.entry_var.set("")
        self._do_save(); self.refresh(); self._sync_list()

    def toggle(self, td):
        td["done"] = not td["done"]
        self._do_save(); self.refresh(); self._sync_list()

    def delete(self, td):
        if td in self.todos: self.todos.remove(td)
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
            except: pass

    # ──────────────────────────────────────────
    #  렌더링
    # ──────────────────────────────────────────
    def refresh(self):
        t = self.t
        for w in self.sf.winfo_children():
            w.destroy()
        self._drag_rows.clear()
        self._text_labels.clear()
        self._card_cvs.clear()
        self._card_redraws.clear()

        if not self.todos:
            tk.Label(self.sf, text="할 일을 추가해보세요",
                     bg=t["bg"], fg=t["muted"],
                     font=(FONT, 10)).pack(pady=40)
        else:
            for td in self.todos:
                self._render_item(td)

        done  = sum(1 for td in self.todos if td["done"])
        total = len(self.todos)
        self.stat_lbl.config(
            text=f"{done} / {total} 완료" if total else "")
        # 배지
        if total:
            undone = total - done
            self.badge_lbl.config(text=str(undone) if undone else "✓")
            self.badge_lbl.pack(side="left", padx=6)
        else:
            self.badge_lbl.pack_forget()

        self.sf.update_idletasks()
        # 모든 카드를 즉시 재렌더 (flash 방지)
        for fn in self._card_redraws:
            fn()

    def _render_item(self, td):
        t    = self.t
        done = td["done"]
        PAD  = 4

        # 부모 캔버스 너비를 미리 계산 → height=1 지연 없이 즉시 렌더
        parent_w = self.canvas.winfo_width()
        if parent_w <= 1:
            parent_w = self.data["window"]["width"]
        card_w = max(100, parent_w - 16)   # padx=8 양쪽

        # ── 카드 Canvas (둥근 모서리) ──────────
        cv = tk.Canvas(self.sf, bg=t["bg"], highlightthickness=0,
                       bd=0, height=52, width=card_w)
        cv.pack(fill="x", padx=8, pady=4)

        row = tk.Frame(cv, bg=t["card"], pady=10)
        win_id = cv.create_window(PAD, PAD, window=row, anchor="nw",
                                  width=card_w - PAD * 2)

        def _redraw(e=None):
            cw = cv.winfo_width()
            if cw <= 1: cw = card_w          # 미리 계산한 너비로 폴백
            row.update_idletasks()
            ch = row.winfo_reqheight()
            if ch <= 1: cv.after(30, _redraw); return
            th = ch + PAD * 2
            cv.config(height=th)
            cv.itemconfig(win_id, width=cw - PAD * 2)
            _draw_rounded(cv, 0, 0, cw, th, CARD_R, t["card"], t["border"])
            cv.tag_lower("card")

        cv.bind("<Configure>", lambda e: _redraw())
        row.bind("<Configure>", lambda e: _redraw())
        cv.bind("<MouseWheel>", self._scroll)

        self._card_cvs.append((cv, win_id))
        self._card_redraws.append(_redraw)

        # ── 드래그 핸들 ───────────────────────
        dh = tk.Label(row, text="⠿", bg=t["card"], fg=t["muted"],
                      font=(FONT, 11), cursor="fleur")
        dh.pack(side="left", padx=(8, 2))
        dh.bind("<ButtonPress-1>",   lambda e, r=row: self._item_drag_start(e, td, r))
        dh.bind("<B1-Motion>",       self._item_drag_move)
        dh.bind("<ButtonRelease-1>", self._item_drag_end)

        # ── 체크박스 ──────────────────────────
        ck_color = t["accent"] if done else t["border"]
        ck_text  = "●" if done else "○"
        chk = tk.Label(row, text=ck_text, bg=t["card"],
                       fg=ck_color, font=(FONT, 14), cursor="hand2")
        chk.pack(side="left", padx=(2, 6))
        chk.bind("<Button-1>", lambda e: self.toggle(td))

        # ── 우측 버튼 (먼저 pack) ─────────────
        del_lb = tk.Label(row, text="✕", bg=t["card"], fg=t["muted"],
                          font=(FONT, 9), cursor="hand2")
        del_lb.pack(side="right", padx=(0, 10))
        del_lb.bind("<Button-1>", lambda e: self.delete(td))

        edt_lb = tk.Label(row, text="✎", bg=t["card"], fg=t["muted"],
                          font=(FONT, 10), cursor="hand2")
        edt_lb.pack(side="right", padx=(0, 2))
        edt_lb.bind("<Button-1>", lambda e, r=row: self._inline_edit(td, r))

        # ── 텍스트 ────────────────────────────
        cw = self.canvas.winfo_width()
        if cw < 10: cw = self.data["window"]["width"] - 16
        wl  = max(80, cw - 90)
        fg  = t["done_fg"] if done else t["fg"]
        fnt = (FONT, 10, "overstrike") if done else (FONT, 10)
        lbl = tk.Label(row, text=td["text"], bg=t["card"], fg=fg,
                       font=fnt, anchor="w", cursor="hand2",
                       wraplength=wl, justify="left")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 4))
        lbl.bind("<Button-1>",        lambda e: self.toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, r=row: self._inline_edit(td, r))
        self._text_labels.append(lbl)

        self._bind_scroll_recursive(row)
        self._drag_rows.append((row, cv, td))

    def _inline_edit(self, td, row):
        for w in row.winfo_children(): w.destroy()
        t    = self.t
        done = td["done"]

        tk.Label(row, text="⠿", bg=t["card"], fg=t["muted"],
                 font=(FONT, 11)).pack(side="left", padx=(8, 2))

        ck_color = t["accent"] if done else t["border"]
        tk.Label(row, text="●" if done else "○", bg=t["card"],
                 fg=ck_color, font=(FONT, 14)).pack(side="left", padx=(2, 6))

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt: td["text"] = txt
            self._do_save(); self.refresh(); self._sync_list()

        def cancel(e=None): self.refresh()

        cl = tk.Label(row, text="✗", bg=t["card"], fg="#EF4444",
                      font=(FONT, 12, "bold"), cursor="hand2")
        cl.pack(side="right", padx=(0, 10))
        cl.bind("<Button-1>", lambda e: cancel())

        ok = tk.Label(row, text="✓", bg=t["card"], fg="#22C55E",
                      font=(FONT, 12, "bold"), cursor="hand2")
        ok.pack(side="right", padx=(0, 4))
        ok.bind("<Button-1>", lambda e: commit())

        ent = tk.Entry(row, textvariable=var, bg=t["inp"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=(FONT, 10), bd=0,
                       highlightthickness=1,
                       highlightbackground=t["border"],
                       highlightcolor=t["accent"])
        ent.pack(side="left", fill="x", expand=True, padx=4, ipady=4)
        ent.focus_set(); ent.select_range(0, "end")
        ent.bind("<Return>", commit); ent.bind("<Escape>", cancel)
        self._bind_scroll_recursive(row)

    # ──────────────────────────────────────────
    #  드래그 정렬
    # ──────────────────────────────────────────
    def _item_drag_start(self, e, td, row):
        self._drag_td       = td
        self._drag_orig_y   = e.y_root
        self._drag_orig_idx = self.todos.index(td)
        t = self.t
        row.config(bg=t["drag"])
        # card canvas border highlight
        for i, (rw, cv, _) in enumerate(self._drag_rows):
            if rw is row:
                _draw_rounded(cv, 0, 0, cv.winfo_width(), cv.winfo_height(),
                              CARD_R, t["drag"], t["accent"])
                break

    def _item_drag_move(self, e):
        if not self._drag_td: return
        dy     = e.y_root - self._drag_orig_y
        target = max(0, min(len(self._drag_rows) - 1,
                            self._drag_orig_idx + round(dy / 40)))
        t = self.t
        for i, (rw, cv, _) in enumerate(self._drag_rows):
            active = i == target
            rw.config(bg=t["drag"] if active else t["card"])

    def _item_drag_end(self, e):
        if not self._drag_td: return
        dy     = e.y_root - self._drag_orig_y
        orig   = self._drag_orig_idx
        target = max(0, min(len(self.todos) - 1, orig + round(dy / 40)))
        td = self.todos.pop(orig)
        self.todos.insert(target, td)
        self._drag_td = None
        self._do_save(); self.refresh(); self._sync_list()

    # ──────────────────────────────────────────
    #  창 관리
    # ──────────────────────────────────────────
    def hide(self):     self._do_save(); self.root.withdraw()
    def show(self):     self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def quit_app(self):
        self._do_save()
        if self.tray: self.tray.stop()
        self.root.after(0, self.root.destroy)

    # ──────────────────────────────────────────
    #  백업 / 불러오기
    # ──────────────────────────────────────────
    def backup(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="할일 백업 저장",
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"todos_backup_{date.today().isoformat()}.json")
        if path:
            try:
                shutil.copy2(DATA_PATH, path)
                messagebox.showinfo("백업 완료", f"저장됨:\n{path}", parent=self.root)
            except Exception as ex:
                messagebox.showerror("오류", str(ex), parent=self.root)

    def restore(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="할일 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "todos" not in d:
                messagebox.showerror("오류", "올바른 백업 파일이 아닙니다.", parent=self.root)
                return
            for k, v in DEFAULT_DATA.items(): d.setdefault(k, v)
            self.data = d; self.todos = d["todos"]
            self.next_id = max((t["id"] for t in self.todos), default=0) + 1
            save_data(self.data)
            self.refresh(); self._sync_list()
            messagebox.showinfo("완료", f"{len(self.todos)}개 항목을 불러왔습니다.",
                                parent=self.root)
        except Exception as ex:
            messagebox.showerror("오류", str(ex), parent=self.root)

    # ──────────────────────────────────────────
    #  우클릭 메뉴
    # ──────────────────────────────────────────
    def _ctx_menu(self, x, y):
        t = self.t
        m = tk.Menu(self.root, tearoff=0,
                    bg=t["card"], fg=t["fg"],
                    activebackground=t["accent"], activeforeground=t["btn_fg"],
                    relief="flat", bd=1, font=(FONT, 9))

        aot = self.data.get("always_on_top", True)
        m.add_command(label=f"{'✓' if aot else '  '} 항상 위에 표시",
                      command=self._toggle_aot)

        op_m = tk.Menu(m, tearoff=0, bg=t["card"], fg=t["fg"],
                       activebackground=t["accent"], activeforeground=t["btn_fg"],
                       font=(FONT, 9))
        cur_op = self.data.get("opacity", 0.97)
        for val, label in [(0.75,"75%"),(0.85,"85%"),(0.95,"95%"),(1.0,"100%")]:
            op_m.add_command(label=f"{'✓' if abs(cur_op-val)<0.02 else '  '} {label}",
                             command=lambda v=val: self._set_opacity(v))
        m.add_cascade(label="투명도", menu=op_m)

        th_m = tk.Menu(m, tearoff=0, bg=t["card"], fg=t["fg"],
                       activebackground=t["accent"], activeforeground=t["btn_fg"],
                       font=(FONT, 9))
        cur_th = self.data.get("theme", "blue")
        for key, info in THEMES.items():
            th_m.add_command(label=f"{'✓' if key==cur_th else '  '} {info['name']}",
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
        try:    m.tk_popup(x, y)
        finally: m.grab_release()

    def _toggle_aot(self):
        self.data["always_on_top"] = not self.data.get("always_on_top", True)
        self.root.wm_attributes('-topmost', self.data["always_on_top"])
        self._do_save()

    def _set_opacity(self, val):
        self.data["opacity"] = val
        self.root.wm_attributes('-alpha', val)
        self._do_save()

    def _set_theme(self, key):
        self.data["theme"] = key; self._do_save()
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists(): self.list_win.win.destroy()
            except: pass
            self.list_win = None
        for w in self.root.winfo_children(): w.destroy()
        self.root.configure(bg=self.t["bg"])
        self._apply_state(); self._build()

    def _toggle_startup(self):
        cur = get_startup(); set_startup(not cur)
        self.data["startup"] = not cur; self._do_save()

    # ──────────────────────────────────────────
    #  시스템 트레이
    # ──────────────────────────────────────────
    def _start_tray(self):
        def aot_text(item):
            return ("✅ 항상 위에 표시 [켜짐]"
                    if self.data.get("always_on_top", True)
                    else "⬛ 항상 위에 표시 [꺼짐]")

        def su_text(item):
            return ("✅ 윈도우 시작 시 자동 실행 [켜짐]"
                    if get_startup()
                    else "⬛ 윈도우 시작 시 자동 실행 [꺼짐]")

        menu = pystray.Menu(
            pystray.MenuItem("📋 할일위젯 열기",
                             lambda: self.root.after(0, self.show), default=True),
            pystray.MenuItem("📂 전체 목록 보기",
                             lambda: self.root.after(0, self.open_list)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(aot_text, lambda: self.root.after(0, self._toggle_aot)),
            pystray.MenuItem(su_text,  lambda: self.root.after(0, self._toggle_startup)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("💾 백업 (내보내기)",
                             lambda: self.root.after(0, self.backup)),
            pystray.MenuItem("📥 불러오기 (가져오기)",
                             lambda: self.root.after(0, self.restore)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 완전 종료",
                             lambda: self.root.after(0, self.quit_app)),
        )
        try:   icon_img = make_tray_icon()
        except: icon_img = Image.new("RGB", (64, 64), "#1A56DB")

        self.tray = pystray.Icon(APP_NAME, icon_img, APP_NAME, menu=menu)
        threading.Thread(target=lambda: self.tray.run(lambda i: setattr(i, 'visible', True)),
                         daemon=True).start()

    # ──────────────────────────────────────────
    #  전체 목록 창
    # ──────────────────────────────────────────
    def open_list(self):
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists():
                    self.list_win.win.lift(); self.list_win.win.focus_force(); return
            except: pass
        self.list_win = ListWindow(self)


# ──────────────────────────────────────────────
#  전체 목록 창
# ──────────────────────────────────────────────
class ListWindow:
    def __init__(self, app: TodoWidget):
        self.app            = app
        self.filter_mode    = "all"
        self.search_var     = tk.StringVar()
        self._list_redraws: list = []
        self.search_var.trace("w", lambda *a: self.refresh())

        t = app.t
        self.win = tk.Toplevel(app.root)
        self.win.title("전체 할일 관리")
        self.win.geometry("480x560")
        self.win.configure(bg=t["bg"])
        self.win.wm_attributes('-topmost', app.data.get("always_on_top", True))
        self.win.resizable(True, True)
        self._build()
        self.win.focus_force()

    def _build(self):
        t = self.app.t

        # 헤더
        hdr = tk.Frame(self.win, bg=t["header"], height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="전체 할일 관리",
                 bg=t["header"], fg=t["hdr_fg"],
                 font=(FONT, 13, "bold")).pack(side="left", padx=16, pady=12)

        # 필터 + 검색
        bar = tk.Frame(self.win, bg=t["bg"], pady=10)
        bar.pack(fill="x", padx=12)

        self.filter_btns = {}
        ff = tk.Frame(bar, bg=t["bg"])
        ff.pack(side="left")
        for lbl, mode in [("전체","all"),("미완료","undone"),("완료","done")]:
            btn = tk.Label(ff, text=lbl, font=(FONT, 9), cursor="hand2",
                           padx=12, pady=4)
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda e, m=mode: self._set_filter(m))
            self.filter_btns[mode] = btn

        sb_f = tk.Frame(bar, bg=t["border"])
        sb_f.pack(side="right")
        sb_i = tk.Frame(sb_f, bg=t["inp"])
        sb_i.pack(fill="x", padx=1, pady=1)
        tk.Label(sb_i, text="🔍", bg=t["inp"], fg=t["muted"],
                 font=(FONT, 9)).pack(side="left", padx=(8, 2))
        se = tk.Entry(sb_i, textvariable=self.search_var,
                      bg=t["inp"], fg=t["fg"], insertbackground=t["fg"],
                      relief="flat", font=(FONT, 9), bd=0, width=14)
        se.pack(side="left", ipady=5, padx=(0, 8))
        self._update_filter_btns()

        tk.Frame(self.win, bg=t["border"], height=1).pack(fill="x")

        # 스크롤 목록
        lf = tk.Frame(self.win, bg=t["bg"])
        lf.pack(fill="both", expand=True)

        self.vsb = tk.Scrollbar(lf, orient="vertical", width=10,
                                troughcolor=t["bg"], bg=t["border"],
                                relief="flat", bd=0)
        self.vsb.pack(side="right", fill="y")
        self.canvas = tk.Canvas(lf, bg=t["bg"], highlightthickness=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)

        scb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        self.canvas.bind("<MouseWheel>", scb)

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")

        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(
                         scrollregion=(0, 0, e.width, e.height)))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._sf_id, width=e.width))
        self.sf.bind("<MouseWheel>", scb)

        # 하단 상태바
        tk.Frame(self.win, bg=t["border"], height=1).pack(fill="x")
        sb = tk.Frame(self.win, bg=t["bg"], pady=8)
        sb.pack(fill="x", padx=12)
        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["muted"],
                                 font=(FONT, 8))
        self.stat_lbl.pack(side="left")
        clr = tk.Label(sb, text="완료 항목 삭제", cursor="hand2",
                       bg=t["btn"], fg=t["btn_fg"],
                       font=(FONT, 8), padx=10, pady=4)
        clr.pack(side="right")
        clr.bind("<Button-1>", lambda e: self._clear_done())

        self.refresh()

    def _set_filter(self, mode):
        self.filter_mode = mode; self._update_filter_btns(); self.refresh()

    def _update_filter_btns(self):
        t = self.app.t
        for mode, btn in self.filter_btns.items():
            active = mode == self.filter_mode
            btn.config(bg=t["accent"] if active else t["bg"],
                       fg=t["btn_fg"] if active else t["fg"])

    def refresh(self):
        t = self.app.t
        for w in self.sf.winfo_children(): w.destroy()
        self._list_redraws.clear()

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
                     fg=t["muted"], font=(FONT, 10)).pack(pady=30)
        else:
            for td in items: self._row(td, today)

        total = len(self.app.todos)
        done  = sum(1 for td in self.app.todos if td["done"])
        self.stat_lbl.config(
            text=f"총 {total}개  ·  미완료 {total-done}개  ·  완료 {done}개")
        self.sf.update_idletasks()
        for fn in self._list_redraws:
            fn()

    def _row(self, td, today):
        t    = self.app.t
        done = td["done"]
        PAD  = 4

        # 부모 캔버스 너비 미리 계산
        parent_w = self.canvas.winfo_width()
        if parent_w <= 1:
            parent_w = 460
        card_w = max(100, parent_w - 20)   # padx=10 양쪽

        cv = tk.Canvas(self.sf, bg=t["bg"], highlightthickness=0,
                       bd=0, height=52, width=card_w)
        cv.pack(fill="x", padx=10, pady=4)
        row = tk.Frame(cv, bg=t["card"], pady=10)
        win_id = cv.create_window(PAD, PAD, window=row, anchor="nw",
                                  width=card_w - PAD * 2)

        def _redraw(e=None):
            cw = cv.winfo_width()
            if cw <= 1: cw = card_w
            row.update_idletasks()
            ch = row.winfo_reqheight()
            if ch <= 1: cv.after(30, _redraw); return
            th = ch + PAD * 2
            cv.config(height=th)
            cv.itemconfig(win_id, width=cw - PAD * 2)
            _draw_rounded(cv, 0, 0, cw, th, CARD_R, t["card"], t["border"])
            cv.tag_lower("card")

        cv.bind("<Configure>", lambda e: _redraw())
        row.bind("<Configure>", lambda e: _redraw())

        scb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        cv.bind("<MouseWheel>", scb)

        # 체크박스
        ck_color = t["accent"] if done else t["border"]
        chk = tk.Label(row, text="●" if done else "○", bg=t["card"],
                       fg=ck_color, font=(FONT, 14), cursor="hand2")
        chk.pack(side="left", padx=(10, 6))
        chk.bind("<Button-1>", lambda e, td=td: self._toggle(td))

        # 날짜 뱃지
        created = td.get("created_date", today)
        if created != today:
            try:
                diff = (date.today() - date.fromisoformat(created)).days
                badge = "어제" if diff == 1 else f"{diff}일 전"
            except: badge = ""
            if badge:
                tk.Label(row, text=badge, bg=t["card"], fg=t["muted"],
                         font=(FONT, 7), width=6).pack(side="right", padx=(0, 4))

        del_lb = tk.Label(row, text="✕", bg=t["card"], fg=t["muted"],
                          font=(FONT, 9), cursor="hand2")
        del_lb.pack(side="right", padx=(0, 10))
        del_lb.bind("<Button-1>", lambda e, td=td: self._delete(td))

        edt_lb = tk.Label(row, text="✎", bg=t["card"], fg=t["muted"],
                          font=(FONT, 10), cursor="hand2")
        edt_lb.pack(side="right", padx=(0, 2))
        edt_lb.bind("<Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        fg  = t["done_fg"] if done else t["fg"]
        fnt = (FONT, 10, "overstrike") if done else (FONT, 10)
        lbl = tk.Label(row, text=td["text"], bg=t["card"], fg=fg,
                       font=fnt, anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 4))
        lbl.bind("<Button-1>",        lambda e, td=td: self._toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        for w in [row, cv] + list(row.winfo_children()):
            w.bind("<MouseWheel>", scb)
        self._list_redraws.append(_redraw)

    def _inline_edit(self, td, row):
        for w in row.winfo_children(): w.destroy()
        t    = self.app.t
        done = td["done"]

        ck_color = t["accent"] if done else t["border"]
        tk.Label(row, text="●" if done else "○", bg=t["card"],
                 fg=ck_color, font=(FONT, 14)).pack(side="left", padx=(10, 6))

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt: td["text"] = txt
            self.app._do_save(); self.refresh(); self.app.refresh()

        def cancel(e=None): self.refresh()

        cl = tk.Label(row, text="✗", bg=t["card"], fg="#EF4444",
                      font=(FONT, 12, "bold"), cursor="hand2")
        cl.pack(side="right", padx=(0, 10))
        cl.bind("<Button-1>", lambda e: cancel())

        ok = tk.Label(row, text="✓", bg=t["card"], fg="#22C55E",
                      font=(FONT, 12, "bold"), cursor="hand2")
        ok.pack(side="right", padx=(0, 4))
        ok.bind("<Button-1>", lambda e: commit())

        ent = tk.Entry(row, textvariable=var, bg=t["inp"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=(FONT, 10), bd=0,
                       highlightthickness=1, highlightbackground=t["border"],
                       highlightcolor=t["accent"])
        ent.pack(side="left", fill="x", expand=True, padx=6, ipady=4)
        ent.focus_set(); ent.select_range(0, "end")
        ent.bind("<Return>", commit); ent.bind("<Escape>", cancel)

        scb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        for w in row.winfo_children(): w.bind("<MouseWheel>", scb)

    def _toggle(self, td):
        td["done"] = not td["done"]
        self.app._do_save(); self.refresh(); self.app.refresh()

    def _delete(self, td):
        if td in self.app.todos: self.app.todos.remove(td)
        self.app._do_save(); self.refresh(); self.app.refresh()

    def _clear_done(self):
        self.app.todos[:] = [td for td in self.app.todos if not td["done"]]
        self.app._do_save(); self.refresh(); self.app.refresh()


# ──────────────────────────────────────────────
#  진입점
# ──────────────────────────────────────────────
if __name__ == "__main__":
    TodoWidget()
