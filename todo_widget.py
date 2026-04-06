#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
할일 위젯 - 포스트잇 스타일 데스크탑 투두 위젯
의존성: pip install pystray Pillow
빌드:  pyinstaller --onefile --noconsole --name 할일위젯 todo_widget.py
"""

import tkinter as tk
import json, os, sys, threading, copy
from datetime import date

# ── 선택적 의존성 ────────────────────────────────────────────
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
    },
    "blue": {
        "name": "파랑",
        "bg": "#E3F2FD", "header": "#1565C0", "header_fg": "#FFFFFF",
        "fg": "#1A237E", "done_fg": "#9E9E9E", "input_bg": "#FAFAFA",
        "btn_bg": "#1565C0", "btn_fg": "#FFFFFF", "sep": "#90CAF9",
    },
    "green": {
        "name": "초록",
        "bg": "#E8F5E9", "header": "#2E7D32", "header_fg": "#FFFFFF",
        "fg": "#1B5E20", "done_fg": "#9E9E9E", "input_bg": "#FAFAFA",
        "btn_bg": "#2E7D32", "btn_fg": "#FFFFFF", "sep": "#A5D6A7",
    },
    "pink": {
        "name": "분홍",
        "bg": "#FCE4EC", "header": "#AD1457", "header_fg": "#FFFFFF",
        "fg": "#880E4F", "done_fg": "#9E9E9E", "input_bg": "#FFF5F8",
        "btn_bg": "#AD1457", "btn_fg": "#FFFFFF", "sep": "#F48FB1",
    },
    "dark": {
        "name": "다크",
        "bg": "#2D2D2D", "header": "#1A1A1A", "header_fg": "#EEEEEE",
        "fg": "#DDDDDD", "done_fg": "#666666", "input_bg": "#3D3D3D",
        "btn_bg": "#444444", "btn_fg": "#DDDDDD", "sep": "#444444",
    },
}

DEFAULT_DATA = {
    "window":       {"x": 100, "y": 100, "width": 280, "height": 420},
    "theme":        "yellow",
    "always_on_top": True,
    "opacity":      0.95,
    "startup":      False,
    "todos":        [],
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
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            cmd = (f'"{sys.executable}"' if getattr(sys, 'frozen', False)
                   else f'"{sys.executable}" "{os.path.abspath(__file__)}"')
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"레지스트리 오류: {e}")

# ══════════════════════════════════════════════════════════════
#  트레이 아이콘 이미지 생성
# ══════════════════════════════════════════════════════════════
def make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 62, 62], fill="#F9A825")   # 포스트잇 배경
    d.rectangle([2, 2, 62, 16], fill="#E8A010")   # 상단 어두운 띠
    for y in [24, 32, 40, 48, 56]:                # 줄 표시
        d.rectangle([10, y, 54, y + 3], fill="#5D4037")
    return img

# ══════════════════════════════════════════════════════════════
#  날짜 뱃지 헬퍼
# ══════════════════════════════════════════════════════════════
def date_badge(created: str) -> str:
    today = date.today().isoformat()
    if created == today:
        return ""
    try:
        diff = (date.today() - date.fromisoformat(created)).days
        if diff == 1:
            return " (어제)"
        return f" ({diff}일 전)"
    except Exception:
        return ""

# ══════════════════════════════════════════════════════════════
#  메인 위젯
# ══════════════════════════════════════════════════════════════
class TodoWidget:
    def __init__(self):
        self.data    = load_data()
        self.todos   = self.data["todos"]
        self.next_id = max((t["id"] for t in self.todos), default=0) + 1
        self.tray    = None
        self.list_win = None      # ListWindow 인스턴스

        # 드래그 / 리사이즈 임시값
        self._dx = self._dy = 0
        self._rsx = self._rsy = self._rsw = self._rsh = 0

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)      # 기본 테두리 제거
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._apply_state()
        self._build()

        if TRAY_OK:
            self._start_tray()
        else:
            # 트레이 없으면 닫기 버튼은 진짜 종료
            print("⚠  pip install pystray Pillow 로 트레이 기능 활성화 가능")

        self.root.mainloop()

    # ── 현재 테마 ────────────────────────────────────────────
    @property
    def t(self):
        return THEMES.get(self.data.get("theme", "yellow"), THEMES["yellow"])

    # ── 창 상태 적용 ─────────────────────────────────────────
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

        days = ["월", "화", "수", "목", "금", "토", "일"]
        d = date.today()
        today_str = d.strftime(f"%Y.%m.%d ({days[d.weekday()]})")

        self.title_lbl = tk.Label(
            self.hdr, text=f"📋 {today_str}",
            bg=t["header"], fg=t["header_fg"],
            font=("맑은 고딕", 9, "bold")
        )
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

        self.canvas = tk.Canvas(mid, bg=t["bg"], highlightthickness=0, bd=0)
        self.vsb = tk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._sf_id, width=e.width))
        self.canvas.bind("<MouseWheel>", self._scroll)
        self.sf.bind("<MouseWheel>",     self._scroll)

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
        self.entry = tk.Entry(
            inp, textvariable=self.entry_var,
            bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"],
            relief="flat", font=("맑은 고딕", 9), bd=4
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 2), ipady=3)
        self.entry.bind("<Return>", lambda e: self.add_todo())

        add_btn = tk.Label(inp, text=" + ", bg=t["btn_bg"], fg=t["btn_fg"],
                           font=("맑은 고딕", 13, "bold"), cursor="hand2")
        add_btn.pack(side="right", padx=(2, 6), pady=1)
        add_btn.bind("<Button-1>", lambda e: self.add_todo())

        # ── 리사이즈 그립 ────────────────────────────────────
        grip = tk.Label(self.root, text="◢", bg=t["bg"], fg=t["done_fg"],
                        font=("맑은 고딕", 8), cursor="size_nw_se")
        grip.pack(side="right", anchor="se")
        grip.bind("<ButtonPress-1>",   self._rs_start)
        grip.bind("<B1-Motion>",       self._rs_move)
        grip.bind("<ButtonRelease-1>", lambda e: self._do_save())

        self.refresh()

    def _hbtn(self, parent, text, cmd):
        lb = tk.Label(parent, text=text, bg=self.t["header"], fg=self.t["header_fg"],
                      font=("맑은 고딕", 10), cursor="hand2", padx=4)
        lb.pack(side="left")
        lb.bind("<Button-1>", lambda e: cmd())
        return lb

    # ══════════════════════════════════════════════════════════
    #  드래그 / 리사이즈
    # ══════════════════════════════════════════════════════════
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _rs_start(self, e):
        self._rsx, self._rsy = e.x_root, e.y_root
        self._rsw = self.root.winfo_width()
        self._rsh = self.root.winfo_height()

    def _rs_move(self, e):
        w = max(220, self._rsw + (e.x_root - self._rsx))
        h = max(300, self._rsh + (e.y_root - self._rsy))
        self.root.geometry(f"{w}x{h}")

    def _scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ══════════════════════════════════════════════════════════
    #  할일 CRUD
    # ══════════════════════════════════════════════════════════
    def add_todo(self):
        text = self.entry_var.get().strip()
        if not text:
            return
        todo = {
            "id": self.next_id,
            "text": text,
            "done": False,
            "created_date": date.today().isoformat(),
        }
        self.next_id += 1
        self.todos.append(todo)
        self.entry_var.set("")
        self._do_save()
        self.refresh()
        self._sync_list()

    def toggle(self, todo):
        todo["done"] = not todo["done"]
        self._do_save()
        self.refresh()
        self._sync_list()

    def delete(self, todo):
        if todo in self.todos:
            self.todos.remove(todo)
        self._do_save()
        self.refresh()
        self._sync_list()

    def clear_done(self):
        self.todos[:] = [t for t in self.todos if not t["done"]]
        self._do_save()
        self.refresh()
        self._sync_list()

    def _do_save(self):
        self.data["window"] = {
            "x":      self.root.winfo_x(),
            "y":      self.root.winfo_y(),
            "width":  self.root.winfo_width(),
            "height": self.root.winfo_height(),
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

        today = date.today().isoformat()
        if not self.todos:
            tk.Label(self.sf, text="오늘 할일을 추가해보세요 ✨",
                     bg=t["bg"], fg=t["done_fg"],
                     font=("맑은 고딕", 9), wraplength=220).pack(pady=24)
        else:
            for td in self.todos:
                self._render_item(td, today)

        done  = sum(1 for td in self.todos if td["done"])
        total = len(self.todos)
        self.stat_lbl.config(text=f"{done}/{total} 완료")

        self.sf.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_item(self, td, today):
        t    = self.t
        done = td["done"]
        row  = tk.Frame(self.sf, bg=t["bg"])
        row.pack(fill="x", padx=4, pady=1)

        # 체크박스
        chk = tk.Label(row, text="☑" if done else "☐",
                       bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                       font=("맑은 고딕", 11), cursor="hand2")
        chk.pack(side="left", padx=(2, 2))
        chk.bind("<Button-1>", lambda e, td=td: self.toggle(td))

        # 텍스트
        badge   = date_badge(td.get("created_date", today))
        display = td["text"] + badge
        fg      = t["done_fg"] if done else t["fg"]
        fnt     = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)

        lbl = tk.Label(row, text=display, bg=t["bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2", wraplength=175, justify="left")
        lbl.pack(side="left", fill="x", expand=True)
        lbl.bind("<Button-1>",        lambda e, td=td: self.toggle(td))
        lbl.bind("<Double-Button-1>", lambda e, td=td, l=lbl, r=row: self._inline_edit(td, l, r))

        # 삭제 ×
        x_lbl = tk.Label(row, text="×", bg=t["bg"], fg=t["done_fg"],
                         font=("맑은 고딕", 11), cursor="hand2")
        x_lbl.pack(side="right", padx=2)
        x_lbl.bind("<Button-1>", lambda e, td=td: self.delete(td))

    def _inline_edit(self, td, lbl, row):
        lbl.pack_forget()
        t   = self.t
        var = tk.StringVar(value=td["text"])
        ent = tk.Entry(row, textvariable=var, bg=t["input_bg"], fg=t["fg"],
                       insertbackground=t["fg"], relief="flat",
                       font=("맑은 고딕", 9), bd=2)
        ent.pack(side="left", fill="x", expand=True)
        ent.focus_set()
        ent.select_range(0, "end")

        def commit(e=None):
            txt = var.get().strip()
            if txt:
                td["text"] = txt
            self._do_save()
            self.refresh()

        def cancel(e=None):
            self.refresh()

        ent.bind("<Return>",   commit)
        ent.bind("<Escape>",   cancel)
        ent.bind("<FocusOut>", commit)

    # ══════════════════════════════════════════════════════════
    #  창 관리
    # ══════════════════════════════════════════════════════════
    def hide(self):
        self._do_save()
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self):
        self._do_save()
        if self.tray:
            self.tray.stop()
        self.root.after(0, self.root.destroy)

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

        # 투명도 서브메뉴
        op_m = tk.Menu(m, tearoff=0, bg=t["bg"], fg=t["fg"])
        cur_op = self.data.get("opacity", 0.95)
        for val, label in [(0.75, "75%"), (0.85, "85%"), (0.95, "95%"), (1.0, "100%")]:
            mark = "✓ " if abs(cur_op - val) < 0.01 else "  "
            op_m.add_command(label=f"{mark}{label}",
                             command=lambda v=val: self._set_opacity(v))
        m.add_cascade(label="투명도", menu=op_m)

        # 테마 서브메뉴
        th_m = tk.Menu(m, tearoff=0, bg=t["bg"], fg=t["fg"])
        cur_th = self.data.get("theme", "yellow")
        for key, info in THEMES.items():
            mark = "✓ " if key == cur_th else "  "
            th_m.add_command(label=f"{mark}{info['name']}",
                             command=lambda k=key: self._set_theme(k))
        m.add_cascade(label="테마 색상", menu=th_m)

        m.add_separator()
        su = self.data.get("startup", False)
        m.add_command(label=f"{'✓' if su else '  '} 윈도우 시작 시 자동 실행",
                      command=self._toggle_startup)

        m.add_separator()
        m.add_command(label="전체 목록 보기", command=self.open_list)
        m.add_separator()
        m.add_command(label="완전 종료", command=self.quit_app)

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
        # 열린 목록 창 닫기
        if self.list_win:
            try:
                if self.list_win.win.winfo_exists():
                    self.list_win.win.destroy()
            except Exception:
                pass
            self.list_win = None
        # UI 재구성
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=self.t["bg"])
        self._apply_state()
        self._build()

    def _toggle_startup(self):
        self.data["startup"] = not self.data.get("startup", False)
        set_startup(self.data["startup"])
        self._do_save()

    # ══════════════════════════════════════════════════════════
    #  시스템 트레이
    # ══════════════════════════════════════════════════════════
    def _start_tray(self):
        def setup(icon):
            icon.visible = True

        menu = pystray.Menu(
            pystray.MenuItem("할일위젯 열기",    lambda: self.root.after(0, self.show), default=True),
            pystray.MenuItem("전체 목록 보기",   lambda: self.root.after(0, self.open_list)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("완전 종료",        lambda: self.root.after(0, self.quit_app)),
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
#  전체 목록 창 (관리 화면)
# ══════════════════════════════════════════════════════════════
class ListWindow:
    def __init__(self, app: TodoWidget):
        self.app        = app
        self.filter_mode = "all"   # all | undone | done
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

    # ── UI ─────────────────────────────────────────────────
    def _build(self):
        t = self.app.t

        # 헤더
        hdr = tk.Frame(self.win, bg=t["header"], height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋 전체 할일 관리",
                 bg=t["header"], fg=t["header_fg"],
                 font=("맑은 고딕", 11, "bold")).pack(side="left", padx=12, pady=8)

        # 필터 + 검색 바
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

        # 구분선
        tk.Frame(self.win, bg=t["header"], height=1).pack(fill="x")

        # 목록
        lf = tk.Frame(self.win, bg=t["bg"])
        lf.pack(fill="both", expand=True, padx=8, pady=4)

        self.canvas = tk.Canvas(lf, bg=t["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(lf, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.sf = tk.Frame(self.canvas, bg=t["bg"])
        self._sf_id = self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.sf.bind("<Configure>",
                     lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._sf_id, width=e.width))
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # 상태바
        sb = tk.Frame(self.win, bg=t["bg"], pady=4)
        sb.pack(fill="x", padx=10)
        self.stat_lbl = tk.Label(sb, text="", bg=t["bg"], fg=t["done_fg"],
                                  font=("맑은 고딕", 8))
        self.stat_lbl.pack(side="left")
        tk.Button(sb, text="완료 항목 전체 삭제", command=self._clear_done,
                  relief="flat", cursor="hand2", bg=t["btn_bg"], fg=t["btn_fg"],
                  font=("맑은 고딕", 8), padx=8, pady=3, bd=0).pack(side="right")

        self.refresh()

    # ── 필터 ────────────────────────────────────────────────
    def _set_filter(self, mode):
        self.filter_mode = mode
        self._update_filter_btns()
        self.refresh()

    def _update_filter_btns(self):
        t = self.app.t
        for mode, btn in self.filter_btns.items():
            if mode == self.filter_mode:
                btn.config(bg=t["header"], fg=t["header_fg"])
            else:
                btn.config(bg=t["bg"], fg=t["fg"])

    # ── 목록 새로고침 ────────────────────────────────────────
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
            text=f"총 {total}개  |  미완료 {total - done}개  |  완료 {done}개"
        )

    def _row(self, td, today):
        t    = self.app.t
        done = td["done"]

        row = tk.Frame(self.sf, bg=t["bg"])
        row.pack(fill="x", padx=4, pady=2)

        # 체크박스
        chk = tk.Label(row, text="☑" if done else "☐",
                       bg=t["bg"], fg=t["done_fg"] if done else t["fg"],
                       font=("맑은 고딕", 11), cursor="hand2")
        chk.pack(side="left")
        chk.bind("<Button-1>", lambda e, td=td: self._toggle(td))

        # 날짜 뱃지
        created = td.get("created_date", today)
        if created == today:
            badge_txt = "오늘"
        else:
            try:
                diff = (date.today() - date.fromisoformat(created)).days
                badge_txt = "어제" if diff == 1 else f"{diff}일 전"
            except Exception:
                badge_txt = ""

        # 텍스트
        fnt = ("맑은 고딕", 9, "overstrike") if done else ("맑은 고딕", 9)
        fg  = t["done_fg"] if done else t["fg"]
        lbl = tk.Label(row, text=td["text"], bg=t["bg"], fg=fg, font=fnt,
                       anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=6)
        lbl.bind("<Button-1>", lambda e, td=td: self._toggle(td))

        tk.Label(row, text=badge_txt, bg=t["bg"], fg=t["done_fg"],
                 font=("맑은 고딕", 7), width=7).pack(side="left")

        del_lbl = tk.Label(row, text="삭제", bg=t["bg"], fg=t["done_fg"],
                           font=("맑은 고딕", 8), cursor="hand2")
        del_lbl.pack(side="right", padx=6)
        del_lbl.bind("<Button-1>", lambda e, td=td: self._delete(td))

        # 구분선
        tk.Frame(self.sf, bg=t["sep"], height=1).pack(fill="x", padx=4)

    # ── 액션 ────────────────────────────────────────────────
    def _toggle(self, td):
        td["done"] = not td["done"]
        self.app._do_save()
        self.refresh()
        self.app.refresh()

    def _delete(self, td):
        if td in self.app.todos:
            self.app.todos.remove(td)
        self.app._do_save()
        self.refresh()
        self.app.refresh()

    def _clear_done(self):
        self.app.todos[:] = [td for td in self.app.todos if not td["done"]]
        self.app._do_save()
        self.refresh()
        self.app.refresh()


# ══════════════════════════════════════════════════════════════
#  진입점
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    TodoWidget()
