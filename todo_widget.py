#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
할일 위젯 - 포스트잇 스타일 데스크탑 투두 위젯
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

# ══════════════════════════════════════════════════════════════
#  상수 / 테마
# ══════════════════════════════════════════════════════════════
APP_NAME = "할일위젯"
REG_KEY  = "TodoWidget"

def _data_path():
    base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "todos.json")

DATA_PATH = _data_path()

THEMES = {
    "yellow": {
        "name": "노랑 (포스트잇)",
        "bg": "#FFF9C4", "header": "#F9A825", "header_fg": "#5D4037",
        "fg": "#333333", "done_fg": "#BBBBBB", "input_bg": "#FFFDE7",
        "btn_bg": "#F0B800", "btn_fg": "#5D4037", "sep": "#F0D040",
        "drag_over": "#FFE57F",
    },
    "blue": {
        "name": "파랑",
        "bg": "#E3F2FD", "header": "#1565C0", "header_fg": "#FFFFFF",
        "fg": "#1A237E", "done_fg": "#9E9E9E", "input_bg": "#FAFAFA",
        "btn_bg": "#1565C0", "btn_fg": "#FFFFFF", "sep": "#90CAF9",
        "drag_over": "#BBDEFB",
    },
    "green": {
        "name": "초록",
        "bg": "#E8F5E9", "header": "#2E7D32", "header_fg": "#FFFFFF",
        "fg": "#1B5E20", "done_fg": "#9E9E9E", "input_bg": "#FAFAFA",
        "btn_bg": "#2E7D32", "btn_fg": "#FFFFFF", "sep": "#A5D6A7",
        "drag_over": "#C8E6C9",
    },
    "pink": {
        "name": "분홍",
        "bg": "#FCE4EC", "header": "#AD1457", "header_fg": "#FFFFFF",
        "fg": "#880E4F", "done_fg": "#9E9E9E", "input_bg": "#FFF5F8",
        "btn_bg": "#AD1457", "btn_fg": "#FFFFFF", "sep": "#F48FB1",
        "drag_over": "#F8BBD0",
    },
    "dark": {
        "name": "다크",
        "bg": "#2D2D2D", "header": "#1A1A1A", "header_fg": "#EEEEEE",
        "fg": "#DDDDDD", "done_fg": "#666666", "input_bg": "#3D3D3D",
        "btn_bg": "#444444", "btn_fg": "#DDDDDD", "sep": "#444444",
        "drag_over": "#3A3A3A",
    },
}

DEFAULT_DATA = {
    "window":        {"x": 100, "y": 100, "width": 280, "height": 420},
    "theme":         "yellow",
    "always_on_top": True,
    "opacity":       0.95,
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
    except Exception as e:
        print(f"레지스트리 오류: {e}")

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
#  트레이 아이콘 이미지
# ══════════════════════════════════════════════════════════════
def make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 62, 62], fill="#F9A825")
    d.rectangle([2, 2, 62, 16], fill="#E8A010")
    for y in [24, 32, 40, 48, 56]:
        d.rectangle([10, y, 54, y + 3], fill="#5D4037")
    return img

# ══════════════════════════════════════════════════════════════
#  날짜 뱃지
# ══════════════════════════════════════════════════════════════
def date_badge(created: str) -> str:
    today = date.today().isoformat()
    if created == today:
        return ""
    try:
        diff = (date.today() - date.fromisoformat(created)).days
        return " (어제)" if diff == 1 else f" ({diff}일 전)"
    except Exception:
        return ""

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
        self._drag_td       = None
        self._drag_orig_y   = 0
        self._drag_orig_idx = 0
        self._drag_rows     = []
        self._text_labels   = []

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
        return THEMES.get(self.data.get("theme", "yellow"), THEMES["yellow"])

    def _apply_state(self):
        w = self.data["window"]
        self.root.geometry(f"{w['width']}x{w['height']}+{w['x']}+{w['y']}")
        self.root.minsize(220, 300)
        self.root.configure(bg=self.t["bg"])
        self.root.wm_attributes('-topmost', self.data.get("always_on_top", True))
        self.root.wm_attributes('-alpha',   self.data.get("opacity", 0.95))

    # ══════════════════════════════════════════════════════════
    #  UI 구성
    # ══════════════════════════════════════════════════════════
    def _build(self):
        t = self.t

        # ── 헤더 ─────────────────────────────────────────────
        self.hdr = tk.Frame(self.root, bg=t["header"], height=36)
        self.hdr.pack(fill="x")
        self.hdr.pack_propagate(False)

        days = ["월","화","수","목","금","토","일"]
        d = date.today()
        self.title_lbl = tk.Label(
            self.hdr, bg=t["header"], fg=t["header_fg"],
            text=f"📋 {d.strftime(f'%Y.%m.%d ({days[d.weekday()]})')}",
            font=("맑은 고딕", 9, "bold"))
        self.title_lbl.pack(side="left", padx=8)

        btn_f = tk.Frame(self.hdr, bg=t["header"])
        btn_f.pack(side="right", padx=2)
        self._hbtn(btn_f, "─", self.hide)
        self._hbtn(btn_f, "×", self.hide if TRAY_OK else self.quit_app)

        for w in [self.hdr, self.title_lbl]:
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)
        self.hdr.bind("<Button-3>", lambda e: self._ctx_menu(e.x_root, e.y_root))

        # ── 할일 스크롤 영역 ─────────────────────────────────
        mid = tk.Frame(self.root, bg=t["bg"])
        mid.pack(fill="both", expand=True)

        self.vsb = tk.Scrollbar(mid, orient="vertical", width=12)
        self.vsb.pack(side="right", fill="y")

        self.canvas = tk.Canvas(mid, bg=t["bg"], highlightthickness=0, bd=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_scroll(self.canvas)
        self._bind_scroll(self.sf)

        # ── 상태바 ───────────────────────────────────────────
        sb = tk.Frame(self.root, bg=t["bg"])
        sb.pack(fill="x", padx=6, pady=(1, 2))

        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["done_fg"],
                                  font=("맑은 고딕", 8))
        self.stat_lbl.pack(side="left")

        for txt, cmd in [("완료삭제", self.clear_done), ("목록", self.open_list)]:
            lb = tk.Label(sb, text=txt, bg=t["bg"], fg=t["done_fg"],
                          font=("맑은 고딕", 8), cursor="hand2")
            lb.pack(side="right", padx=3)
            lb.bind("<Button-1>", lambda e, c=cmd: c())

        # ── 입력 영역 ────────────────────────────────────────
        inp = tk.Frame(self.root, bg=t["header"], pady=4)
        inp.pack(fill="x")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(inp, textvariable=self.entry_var,
                              bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"],
                              relief="flat", font=("맑은 고딕", 9), bd=4)
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 2), ipady=3)
        self.entry.bind("<Return>", lambda e: self.add_todo())

        add_btn = tk.Label(inp, text=" + ", bg=t["btn_bg"], fg=t["btn_fg"],
                           font=("맑은 고딕", 13, "bold"), cursor="hand2")
        add_btn.pack(side="right", padx=(2, 6), pady=1)
        add_btn.bind("<Button-1>", lambda e: self.add_todo())

        # ── 하단 리사이즈 스트립 (코너 그립 포함) ─────────────
        # place 방식 제거 → pack 방식으로 스트립 추가해 UI 짤림 방지
        foot = tk.Frame(self.root, bg=t["header"], height=8)
        foot.pack(fill="x")
        foot.pack_propagate(False)

        grip = tk.Label(foot, text="◢", bg=t["header"], fg=t["header_fg"],
                        font=("맑은 고딕", 7), cursor="size_nw_se")
        grip.pack(side="right", padx=2)
        grip.bind("<ButtonPress-1>",   self._rs_start)
        grip.bind("<B1-Motion>",       self._rs_move)
        grip.bind("<ButtonRelease-1>", lambda e: self._do_save())

        # 스트립 자체는 하단 엣지 리사이즈
        foot.bind("<ButtonPress-1>",   self._rs_b_start)
        foot.bind("<B1-Motion>",       self._rs_b_move)
        foot.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.refresh()

    def _hbtn(self, parent, text, cmd):
        lb = tk.Label(parent, text=text, bg=self.t["header"], fg=self.t["header_fg"],
                      font=("맑은 고딕", 10), cursor="hand2", padx=4)
        lb.pack(side="left")
        lb.bind("<Button-1>", lambda e: cmd())
        return lb

    # ── 스크롤 바인딩 ────────────────────────────────────────
    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>", self._scroll)

    def _bind_scroll_recursive(self, widget):
        self._bind_scroll(widget)
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._sf_id, width=e.width)
        wl = max(80, e.width - 78)
        for lbl in self._text_labels:
            try:
                lbl.config(wraplength=wl)
            except Exception:
                pass

    def _scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── 창 드래그 ────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── 창 리사이즈 ──────────────────────────────────────────
    def _rs_start(self, e):
        self._rsx, self._rsy = e.x_root, e.y_root
        self._rsw = self.root.winfo_width()
        self._rsh = self.root.winfo_height()

    def _rs_move(self, e):
        w = max(220, self._rsw + (e.x_root - self._rsx))
        h = max(300, self._rsh + (e.y_root - self._rsy))
        self.root.geometry(f"{w}x{h}")

    def _rs_b_start(self, e):
        self._rsy = e.y_root
        self._rsw = self.root.winfo_width()
        self._rsh = self.root.winfo_height()

    def _rs_b_move(self, e):
        h = max(300, self._rsh + (e.y_root - self._rsy))
        self.root.geometry(f"{self._rsw}x{h}")

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

        today = date.today().isoformat()
        if not self.todos:
            tk.Label(self.sf, text="오늘 할일을 추가해보세요 ✨",
                     bg=t["bg"], fg=t["done_fg"],
                     font=("맑은 고딕", 9), wraplength=220).pack(pady=24)
        else:
            for td in self.todos:
                self._render_item(td, today)

        done  = sum(1 for td in self.todos if td["done"])
        self.stat_lbl.config(text=f"{done}/{len(self.todos)} 완료")
        self.sf.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_item(self, td, today):
        t    = self.t
        done = td["done"]

        # 카드 테두리 (sep 색으로 1px 보더 효과)
        card = tk.Frame(self.sf, bg=t["sep"])
        card.pack(fill="x", padx=4, pady=2)
        row = tk.Frame(card, bg=t["bg"])
        row.pack(fill="x", padx=1, pady=1)

        # ≡ 드래그 핸들
        dh = tk.Label(row, text="≡", bg=t["bg"], fg=t["done_fg"],
                      font=("맑은 고딕", 9), cursor="fleur")
        dh.pack(side="left", padx=(2, 1))
        dh.bind("<ButtonPress-1>",   lambda e, td=td, r=row: self._item_drag_start(e, td, r))
        dh.bind("<B1-Motion>",       self._item_drag_move)
        dh.bind("<ButtonRelease-1>", self._item_drag_end)

        # ☐ 체크박스
        chk = tk.Label(row, text="☑" if done else "☐",
                       bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                       font=("맑은 고딕", 11), cursor="hand2")
        chk.pack(side="left", padx=(0, 2))
        chk.bind("<Button-1>", lambda e, td=td: self.toggle(td))

        # 오른쪽 버튼들 (먼저 pack해야 텍스트가 남은 공간 채움)
        x_lbl = tk.Label(row, text="×", bg=t["bg"], fg=t["done_fg"],
                         font=("맑은 고딕", 11), cursor="hand2")
        x_lbl.pack(side="right", padx=(1, 2))
        x_lbl.bind("<Button-1>", lambda e, td=td: self.delete(td))

        edit_lbl = tk.Label(row, text="✏", bg=t["bg"], fg=t["done_fg"],
                            font=("맑은 고딕", 9), cursor="hand2")
        edit_lbl.pack(side="right", padx=1)
        edit_lbl.bind("<Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        # 텍스트 레이블 (날짜 뱃지 없음, 동적 wraplength)
        cw = self.canvas.winfo_width()
        if cw < 10:
            cw = self.data["window"]["width"] - 16
        wl = max(80, cw - 78)
        fg  = t["done_fg"] if done else t["fg"]
        fnt = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)
        lbl = tk.Label(row, text=td["text"], bg=t["bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2", wraplength=wl, justify="left")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 2))
        lbl.bind("<Button-1>",        lambda e, td=td: self.toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))
        self._text_labels.append(lbl)

        self._bind_scroll_recursive(row)
        self._bind_scroll_recursive(card)
        self._drag_rows.append((row, td))

    def _inline_edit(self, td, row):
        """행 내 인라인 편집 모드 (팝업 없음)"""
        for w in row.winfo_children():
            w.destroy()

        t    = self.t
        done = td["done"]

        # 드래그 핸들 (비활성)
        tk.Label(row, text="≡", bg=t["bg"], fg=t["done_fg"],
                 font=("맑은 고딕", 9)).pack(side="left", padx=(0, 1))

        # 체크박스 (비활성)
        tk.Label(row, text="☑" if done else "☐",
                 bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                 font=("맑은 고딕", 11)).pack(side="left", padx=(0, 2))

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt:
                td["text"] = txt
            self._do_save(); self.refresh(); self._sync_list()

        def cancel(e=None):
            self.refresh()

        # ✗ 취소 (right, 먼저 pack)
        cancel_lbl = tk.Label(row, text="✗", bg=t["bg"], fg="#E53935",
                              font=("맑은 고딕", 11, "bold"), cursor="hand2")
        cancel_lbl.pack(side="right", padx=1)
        cancel_lbl.bind("<Button-1>", lambda e: cancel())

        # ✓ 확인 (right)
        ok_lbl = tk.Label(row, text="✓", bg=t["bg"], fg="#43A047",
                          font=("맑은 고딕", 11, "bold"), cursor="hand2")
        ok_lbl.pack(side="right", padx=1)
        ok_lbl.bind("<Button-1>", lambda e: commit())

        # 입력창 (나머지 공간)
        ent = tk.Entry(row, textvariable=var, bg=t["input_bg"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=("맑은 고딕", 9), bd=2)
        ent.pack(side="left", fill="x", expand=True, padx=2, ipady=2)
        ent.focus_set()
        ent.select_range(0, "end")
        ent.bind("<Return>", commit)
        ent.bind("<Escape>", cancel)

        self._bind_scroll_recursive(row)

    # ══════════════════════════════════════════════════════════
    #  할일 드래그 정렬
    # ══════════════════════════════════════════════════════════
    def _item_drag_start(self, e, td, row):
        self._drag_td       = td
        self._drag_orig_y   = e.y_root
        self._drag_orig_idx = self.todos.index(td)
        row.config(bg=self.t["drag_over"])
        row.master.config(bg=self.t["drag_over"])  # card border

    def _item_drag_move(self, e):
        if self._drag_td is None:
            return
        dy     = e.y_root - self._drag_orig_y
        target = max(0, min(len(self._drag_rows) - 1,
                            self._drag_orig_idx + round(dy / 30)))
        t = self.t
        for i, (rw, _) in enumerate(self._drag_rows):
            rw.config(bg=t["drag_over"] if i == target else t["bg"])
            rw.master.config(bg=t["drag_over"] if i == target else t["sep"])

    def _item_drag_end(self, e):
        if self._drag_td is None:
            return
        dy     = e.y_root - self._drag_orig_y
        orig   = self._drag_orig_idx
        target = max(0, min(len(self.todos) - 1, orig + round(dy / 26)))
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
    #  우클릭 메뉴 (헤더)
    # ══════════════════════════════════════════════════════════
    def _ctx_menu(self, x, y):
        t = self.t
        m = tk.Menu(self.root, tearoff=0, bg=t["bg"], fg=t["fg"],
                    activebackground=t["header"], activeforeground=t["header_fg"])

        aot = self.data.get("always_on_top", True)
        m.add_command(label=f"{'✓' if aot else '  '} 항상 위에 표시",
                      command=self._toggle_aot)

        op_m = tk.Menu(m, tearoff=0, bg=t["bg"], fg=t["fg"])
        cur_op = self.data.get("opacity", 0.95)
        for val, label in [(0.75, "75%"), (0.85, "85%"), (0.95, "95%"), (1.0, "100%")]:
            mark = "✓ " if abs(cur_op - val) < 0.01 else "  "
            op_m.add_command(label=f"{mark}{label}",
                             command=lambda v=val: self._set_opacity(v))
        m.add_cascade(label="투명도", menu=op_m)

        th_m = tk.Menu(m, tearoff=0, bg=t["bg"], fg=t["fg"])
        cur_th = self.data.get("theme", "yellow")
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
    #  시스템 트레이 (설정 항목 포함)
    # ══════════════════════════════════════════════════════════
    def _start_tray(self):
        def setup(icon):
            icon.visible = True

        # checked 콜백: 현재 상태를 실시간 반영
        def aot_checked(item):
            return self.data.get("always_on_top", True)

        def startup_checked(item):
            return get_startup()

        menu = pystray.Menu(
            pystray.MenuItem("할일위젯 열기",
                             lambda: self.root.after(0, self.show), default=True),
            pystray.MenuItem("전체 목록 보기",
                             lambda: self.root.after(0, self.open_list)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("항상 위에 표시",
                             lambda: self.root.after(0, self._toggle_aot),
                             checked=aot_checked),
            pystray.MenuItem("윈도우 시작 시 자동 실행",
                             lambda: self.root.after(0, self._toggle_startup),
                             checked=startup_checked),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("백업 (내보내기)",
                             lambda: self.root.after(0, self.backup)),
            pystray.MenuItem("불러오기 (가져오기)",
                             lambda: self.root.after(0, self.restore)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("완전 종료",
                             lambda: self.root.after(0, self.quit_app)),
        )

        try:
            icon_img = make_tray_icon()
        except Exception:
            icon_img = Image.new("RGB", (64, 64), "#F9A825")

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
        self.win.title("📋 전체 할일 관리")
        self.win.geometry("440x520")
        self.win.configure(bg=t["bg"])
        self.win.wm_attributes('-topmost', app.data.get("always_on_top", True))
        self.win.resizable(True, True)
        self._build()
        self.win.focus_force()

    def _build(self):
        t = self.app.t

        hdr = tk.Frame(self.win, bg=t["header"], height=42)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📋 전체 할일 관리",
                 bg=t["header"], fg=t["header_fg"],
                 font=("맑은 고딕", 11, "bold")).pack(side="left", padx=12, pady=8)

        bar = tk.Frame(self.win, bg=t["bg"], pady=6)
        bar.pack(fill="x", padx=10)
        self.filter_btns = {}
        for label, mode in [("전체", "all"), ("미완료", "undone"), ("완료", "done")]:
            btn = tk.Label(bar, text=label, font=("맑은 고딕", 9), cursor="hand2",
                           padx=10, pady=3, relief="flat")
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda e, m=mode: self._set_filter(m))
            self.filter_btns[mode] = btn

        se = tk.Entry(bar, textvariable=self.search_var,
                      bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"],
                      relief="flat", font=("맑은 고딕", 9), bd=3)
        se.pack(side="right", padx=4, ipady=3, ipadx=4)
        tk.Label(bar, text="🔍", bg=t["bg"], fg=t["fg"],
                 font=("맑은 고딕", 10)).pack(side="right")
        self._update_filter_btns()

        tk.Frame(self.win, bg=t["header"], height=1).pack(fill="x")

        lf = tk.Frame(self.win, bg=t["bg"])
        lf.pack(fill="both", expand=True, padx=8, pady=4)

        self.vsb = tk.Scrollbar(lf, orient="vertical", width=12)
        self.vsb.pack(side="right", fill="y")
        self.canvas = tk.Canvas(lf, bg=t["bg"], highlightthickness=0,
                                yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.config(command=self.canvas.yview)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._sf_id, width=e.width))
        self.sf.bind("<MouseWheel>",
                     lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        sb = tk.Frame(self.win, bg=t["bg"], pady=4)
        sb.pack(fill="x", padx=10)
        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["done_fg"],
                                  font=("맑은 고딕", 8))
        self.stat_lbl.pack(side="left")
        tk.Button(sb, text="완료 항목 전체 삭제", command=self._clear_done,
                  relief="flat", cursor="hand2", bg=t["btn_bg"], fg=t["btn_fg"],
                  font=("맑은 고딕", 8), padx=8, pady=3, bd=0).pack(side="right")

        self.refresh()

    def _set_filter(self, mode):
        self.filter_mode = mode; self._update_filter_btns(); self.refresh()

    def _update_filter_btns(self):
        t = self.app.t
        for mode, btn in self.filter_btns.items():
            btn.config(bg=t["header"] if mode == self.filter_mode else t["bg"],
                       fg=t["header_fg"] if mode == self.filter_mode else t["fg"])

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
                     fg=t["done_fg"], font=("맑은 고딕", 9)).pack(pady=20)
        else:
            for td in items:
                self._row(td, today)

        total = len(self.app.todos)
        done  = sum(1 for td in self.app.todos if td["done"])
        self.stat_lbl.config(
            text=f"총 {total}개  |  미완료 {total - done}개  |  완료 {done}개")

    def _row(self, td, today):
        t    = self.app.t
        done = td["done"]
        row  = tk.Frame(self.sf, bg=t["bg"])
        row.pack(fill="x", padx=4, pady=2)

        chk = tk.Label(row, text="☑" if done else "☐",
                       bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                       font=("맑은 고딕", 11), cursor="hand2")
        chk.pack(side="left")
        chk.bind("<Button-1>", lambda e, td=td: self._toggle(td))

        created = td.get("created_date", today)
        if created == today:
            badge_txt = "오늘"
        else:
            try:
                diff = (date.today() - date.fromisoformat(created)).days
                badge_txt = "어제" if diff == 1 else f"{diff}일 전"
            except Exception:
                badge_txt = ""

        # 오른쪽 버튼 먼저 pack
        del_lbl = tk.Label(row, text="삭제", bg=t["bg"], fg=t["done_fg"],
                           font=("맑은 고딕", 8), cursor="hand2")
        del_lbl.pack(side="right", padx=4)
        del_lbl.bind("<Button-1>", lambda e, td=td: self._delete(td))

        edit_lbl = tk.Label(row, text="✏", bg=t["bg"], fg=t["done_fg"],
                            font=("맑은 고딕", 8), cursor="hand2")
        edit_lbl.pack(side="right", padx=2)
        edit_lbl.bind("<Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        tk.Label(row, text=badge_txt, bg=t["bg"], fg=t["done_fg"],
                 font=("맑은 고딕", 7), width=7).pack(side="right")

        fnt = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)
        fg  = t["done_fg"] if done else t["fg"]
        lbl = tk.Label(row, text=td["text"], bg=t["bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=6)
        lbl.bind("<Button-1>",        lambda e, td=td: self._toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, r=row: self._inline_edit(td, r))

        scroll_cb = lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        for w in row.winfo_children():
            w.bind("<MouseWheel>", scroll_cb)
        row.bind("<MouseWheel>", scroll_cb)

        tk.Frame(self.sf, bg=t["sep"], height=1).pack(fill="x", padx=4)

    def _inline_edit(self, td, row):
        """목록 창 인라인 편집"""
        for w in row.winfo_children():
            w.destroy()

        t    = self.app.t
        done = td["done"]
        tk.Label(row, text="☑" if done else "☐",
                 bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                 font=("맑은 고딕", 11)).pack(side="left")

        var = tk.StringVar(value=td["text"])

        def commit(e=None):
            txt = var.get().strip()
            if txt:
                td["text"] = txt
            self.app._do_save(); self.refresh(); self.app.refresh()

        def cancel(e=None):
            self.refresh()

        cancel_lbl = tk.Label(row, text="✗", bg=t["bg"], fg="#E53935",
                              font=("맑은 고딕", 11, "bold"), cursor="hand2")
        cancel_lbl.pack(side="right", padx=1)
        cancel_lbl.bind("<Button-1>", lambda e: cancel())

        ok_lbl = tk.Label(row, text="✓", bg=t["bg"], fg="#43A047",
                          font=("맑은 고딕", 11, "bold"), cursor="hand2")
        ok_lbl.pack(side="right", padx=1)
        ok_lbl.bind("<Button-1>", lambda e: commit())

        ent = tk.Entry(row, textvariable=var, bg=t["input_bg"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=("맑은 고딕", 9), bd=2)
        ent.pack(side="left", fill="x", expand=True, padx=6, ipady=2)
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
