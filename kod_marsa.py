# -*- coding: utf-8 -*-
"""
«Код Марса» для компьютера (Windows).

Перенос Android-приложения «Код Марса» (16.06.2025) в альбомное окно.
Ключи, автокод по дате, ключ-фраза, AES-256 + Base32, морзянка и QR
устроены так же, как на телефоне, поэтому шифровки свободно ходят
между телефонами и компьютерами в обе стороны.
"""
from __future__ import annotations

import datetime as dt
import os
import random
import sys
import tempfile
import time
import tkinter as tk
import traceback
from tkinter import filedialog, ttk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

import marscore as core

try:
    from tkinterdnd2 import COPY, DND_FILES, DND_TEXT, TkinterDnD
    HAS_DND = True
except Exception:  # без перетаскивания программа тоже работает
    HAS_DND = False

IS_WIN = sys.platform == "win32"

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")

# Цвета из оформления Android-версии: космос логотипа, красный Марс иконки,
# светлый фон главного экрана.
C = {
    "space": "#0C0F16",
    "space_text": "#F3EDE2",
    "space_muted": "#A7A2AE",
    "space_hover": "#252A38",
    "paper": "#F4EFE5",
    "card": "#FFFEFA",
    "line": "#DED5C4",
    "ink": "#1F1B16",
    "muted": "#766C60",
    "faint": "#A39888",
    "mars": "#C20000",
    "mars_hover": "#990000",
    "mars_soft": "#F5D8D3",
    "hover": "#EEE6D8",
}

HELP = [
    ("Как зашифровать",
     "Напишите текст в поле «Сообщение» и нажмите Enter или кнопку «Зашифровать». "
     "Справа появятся шифровка Base32, азбука Морзе и QR-код. Shift+Enter переносит строку."),
    ("Как отправить",
     "Скопируйте шифровку и отправьте её текстом. Или нажмите «Копировать QR» и вставьте "
     "картинку в мессенджер сочетанием Ctrl+V. QR-код можно сохранить файлом, перетащить "
     "мышью из окна прямо в чат или папку и напечатать на бланке шифровки."),
    ("Как расшифровать",
     "Вставьте шифровку в поле «Шифровка Base32»: программа расшифрует её сама. Картинку "
     "с QR-кодом можно перетащить в окно, открыть из файла, вставить из буфера обмена "
     "или найти прямо на экране, например в открытом Telegram. Принятую морзянку вставьте "
     "в нижнее поле и нажмите «В шифровку»."),
    ("Ключи",
     "В списке те же 32 ключа, что и в Android-версии: «Универсальный» и «Код 1» – «Код 31». "
     "Каждый день сам выбирается ключ с номером текущего числа. Если сообщение зашифровано "
     "ключом другого дня, программа найдёт нужный ключ и скажет, какой подошёл. "
     "Ключ-фраза превращается в ключ через SHA-256 точно так же, как на телефоне, "
     "поэтому у отправителя и получателя должна быть одна и та же фраза."),
    ("Совместимость",
     "Шифровки полностью совместимы с Android-версией «Код Марса»: сообщение с телефона "
     "расшифровывается на компьютере, а сообщение с компьютера — на телефоне."),
    ("Клавиши",
     "Enter в поле сообщения — зашифровать. Enter в поле шифровки — расшифровать. "
     "Удержание Backspace 2 секунды очищает все поля. Правая кнопка мыши открывает меню "
     "копирования и вставки. F1 — эта справка."),
]


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def enable_dpi_awareness():
    """Чёткие шрифты на экранах с масштабом 125–150 %."""
    if not IS_WIN:
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KodMarsa.Desktop")
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def copy_image_to_clipboard(img, hwnd):
    """Кладёт картинку в буфер обмена Windows (CF_DIB + PNG)."""
    import ctypes
    import io
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalFree.argtypes = [wintypes.HANDLE]

    bmp, png = io.BytesIO(), io.BytesIO()
    img.convert("RGB").save(bmp, "BMP")
    img.convert("RGB").save(png, "PNG")

    def put(fmt, data):
        handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
        if not handle:
            raise MemoryError("не хватило памяти")
        ptr = kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(fmt, handle):
            kernel32.GlobalFree(handle)
            raise OSError("Windows не приняла картинку")

    for _ in range(20):
        if user32.OpenClipboard(hwnd):
            break
        time.sleep(0.05)
    else:
        raise OSError("буфер обмена занят другой программой")
    try:
        user32.EmptyClipboard()
        put(8, bmp.getvalue()[14:])  # CF_DIB: BMP без файлового заголовка
        fmt_png = user32.RegisterClipboardFormatW("PNG")
        if fmt_png:
            put(fmt_png, png.getvalue())
    finally:
        user32.CloseClipboard()


class App:
    def __init__(self, root):
        self.root = root
        self.scale = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
        self.names = core.key_names()
        self.today = dt.date.today()
        self.auto_idx = core.auto_key_index(self.today)
        self.qr_mat = None          # матрица текущего QR-кода
        self.qr_note = None         # почему QR-кода нет
        self.cipher_key = ""        # каким ключом сделана или расшифрована шифровка
        self._b32_prog = ""         # что программа сама записала в поле шифровки
        self._b32_last = ""         # что уже пробовали расшифровать автоматически
        self._b32_job = None
        self._bs_job = None
        self._bs_press_t = 0.0
        self._toast_win = None
        self._toast_job = None
        self._help_win = None
        self._redraw_job = None
        self._drag_on = False
        self._placeholders = {}
        self._art_src = Image.open(resource("assets", "background.jpg")).convert("RGB")
        self._art_cache = {}
        self._make_fonts()
        self._make_style()
        self._build()
        self._bind_keys()
        self._setup_dnd()
        self.root.after(60_000, self._day_tick)

    def px(self, value):
        return int(round(value * self.scale))

    # ------------------------------------------------------------------ вид
    def _make_fonts(self):
        families = set(tkfont.families(self.root))

        def pick(options, size):
            for family, weight in options:
                if family in families:
                    return tkfont.Font(root=self.root, family=family, size=size, weight=weight)
            f = tkfont.nametofont("TkDefaultFont").copy()
            f.configure(size=size)
            return f

        ui = [("Segoe UI", "normal"), ("DejaVu Sans", "normal")]
        mono = [("Consolas", "normal"), ("Cascadia Mono", "normal"),
                ("DejaVu Sans Mono", "normal"), ("Courier New", "normal")]
        self.f_title = pick([("Bahnschrift SemiBold Condensed", "normal"), ("Bahnschrift", "bold"),
                             ("Segoe UI Semibold", "normal"), ("DejaVu Sans Condensed", "bold"),
                             ("DejaVu Sans", "bold")], 19)
        self.f_head = pick([("Bahnschrift SemiBold", "normal"), ("Segoe UI Semibold", "normal"),
                            ("DejaVu Sans", "bold")], 12)
        self.f_btn = pick([("Segoe UI Semibold", "normal"), ("DejaVu Sans", "bold")], 10)
        self.f_body = pick(ui, 10)
        self.f_link = pick(ui, 10)
        self.f_link_hover = pick(ui, 10)
        self.f_link_hover.configure(underline=True)
        self.f_small = pick(ui, 9)
        self.f_text = pick(ui, 11)
        self.f_mono = pick(mono, 11)
        self.f_mono_small = pick(mono, 9)

    def _make_style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Mars.TCombobox", fieldbackground=C["card"], background=C["card"],
                     foreground=C["ink"], arrowcolor=C["ink"], bordercolor=C["line"],
                     lightcolor=C["card"], darkcolor=C["card"], padding=(self.px(8), self.px(5)),
                     arrowsize=self.px(14))
        st.map("Mars.TCombobox",
               fieldbackground=[("readonly", C["card"])], foreground=[("readonly", C["ink"])],
               selectbackground=[("readonly", C["card"])], selectforeground=[("readonly", C["ink"])],
               bordercolor=[("focus", C["mars"])], arrowcolor=[("active", C["mars"])],
               background=[("active", C["hover"])])
        for opt, val in (("background", C["card"]), ("foreground", C["ink"]),
                         ("selectBackground", C["mars"]), ("selectForeground", "#FFFFFF")):
            self.root.option_add(f"*TCombobox*Listbox.{opt}", val)
        self.root.option_add("*TCombobox*Listbox.font", str(self.f_text))
        st.configure("Mars.Vertical.TScrollbar", background=C["line"], troughcolor=C["card"],
                     bordercolor=C["card"], lightcolor=C["line"], darkcolor=C["line"],
                     arrowcolor=C["muted"], gripcount=0)
        st.map("Mars.Vertical.TScrollbar", background=[("active", C["faint"])])

    def _button(self, parent, text, command, kind="secondary"):
        bg, fg, hover, border = {
            "primary": (C["mars"], "#FFFFFF", C["mars_hover"], C["mars"]),
            "secondary": (C["card"], C["ink"], C["hover"], C["line"]),
            "ghost": (C["paper"], C["ink"], C["hover"], C["paper"]),
            "dark": (C["space"], C["space_text"], C["space_hover"], "#3A3F4D"),
        }[kind]
        b = tk.Button(parent, text=text, command=command, font=self.f_btn, bg=bg, fg=fg,
                      activebackground=hover, activeforeground=fg, relief="flat", bd=0,
                      highlightthickness=1, highlightbackground=border,
                      highlightcolor=C["ink"] if kind == "primary" else C["mars"],
                      padx=self.px(14), pady=self.px(6), cursor="hand2")
        b.bind("<Enter>", lambda e: b.configure(bg=hover))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def _link(self, parent, text, command):
        lbl = tk.Label(parent, text=text, font=self.f_link, fg=C["mars"], bg=parent.cget("bg"), cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(fg=C["mars_hover"], font=self.f_link_hover))
        lbl.bind("<Leave>", lambda e: lbl.configure(fg=C["mars"], font=self.f_link))
        return lbl

    def _heading(self, parent, text):
        return tk.Label(parent, text=text, font=self.f_head, fg=C["ink"], bg=parent.cget("bg"))

    def _note(self, parent, text):
        lbl = tk.Label(parent, text=text, font=self.f_small, fg=C["muted"], bg=parent.cget("bg"),
                       justify="left", anchor="w", wraplength=self.px(300))
        lbl.bind("<Configure>", lambda e: lbl.configure(wraplength=max(self.px(120), e.width - 4)))
        return lbl

    def _menu(self):
        return tk.Menu(self.root, tearoff=0, font=self.f_body, bg=C["card"], fg=C["ink"],
                       activebackground=C["mars"], activeforeground="#FFFFFF", bd=1, relief="solid")

    def _textbox(self, parent, font, wrap):
        box = tk.Frame(parent, bg=C["card"])
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        t = tk.Text(box, font=font, wrap=wrap, width=10, height=3, bg=C["card"], fg=C["ink"],
                    insertbackground=C["ink"], selectbackground=C["mars_soft"], selectforeground=C["ink"],
                    inactiveselectbackground=C["mars_soft"], relief="flat", bd=0, highlightthickness=1,
                    highlightbackground=C["line"], highlightcolor=C["mars"], padx=self.px(12),
                    pady=self.px(10), undo=True, maxundo=-1, spacing2=self.px(2))
        sb = ttk.Scrollbar(box, orient="vertical", command=t.yview, style="Mars.Vertical.TScrollbar")

        def on_scroll(first, last):
            if float(first) <= 0.0 and float(last) >= 1.0:
                sb.grid_remove()
            else:
                sb.grid(row=0, column=1, sticky="ns")
            sb.set(first, last)

        t.configure(yscrollcommand=on_scroll)
        t.grid(row=0, column=0, sticky="nsew")

        def on_modified(_e):
            if not t.edit_modified():
                return
            t.edit_modified(False)
            self._refresh_placeholder(t)
            if t is getattr(self, "b32", None):
                self._b32_changed()

        t.bind("<<Modified>>", on_modified, add="+")
        t.bind("<Button-3>", self._text_menu)
        t.bind("<KeyPress-BackSpace>", self._bs_press, add="+")
        t.bind("<KeyRelease-BackSpace>", self._bs_release, add="+")
        return box, t

    def _placeholder(self, widget, text):
        lbl = tk.Label(widget, text=text, font=self.f_body, fg=C["faint"], bg=widget.cget("bg"),
                       justify="left", anchor="nw", cursor="xterm")
        lbl.bind("<Button-1>", lambda e: widget.focus_set())
        if isinstance(widget, tk.Text):
            x, y = int(widget.cget("padx")) + 1, int(widget.cget("pady")) + 1
            place = {"x": x, "y": y}
            lbl.configure(wraplength=self.px(260))
            widget.bind("<Configure>", lambda e: lbl.configure(wraplength=max(60, e.width - 2 * x - 6)), add="+")
            lbl.bind("<Button-3>", lambda e: self._text_menu(e, widget))
        else:
            place = {"x": int(widget.cget("bd")) + 2, "rely": 0.5, "anchor": "w"}
        self._placeholders[widget] = (lbl, place)
        self._refresh_placeholder(widget)

    def _refresh_placeholder(self, widget):
        item = self._placeholders.get(widget)
        if not item:
            return
        lbl, place = item
        empty = widget.get("1.0", "end-1c") == "" if isinstance(widget, tk.Text) else widget.get() == ""
        if empty:
            lbl.place(**place)
        else:
            lbl.place_forget()

    # ------------------------------------------------------------------ окно
    def _build(self):
        r = self.root
        r.title("Код Марса")
        r.configure(bg=C["paper"])
        try:
            if IS_WIN:
                r.iconbitmap(default=resource("assets", "icon.ico"))
        except tk.TclError:
            pass
        try:
            self._icon_photo = ImageTk.PhotoImage(Image.open(resource("assets", "icon.png")))
            r.iconphoto(True, self._icon_photo)
        except Exception:
            pass
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        w, h = min(self.px(1180), sw - self.px(40)), min(self.px(720), sh - self.px(90))
        r.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - self.px(20))}")
        r.minsize(min(self.px(1000), w), min(self.px(600), h))

        self._build_header()
        body = tk.Frame(r, bg=C["paper"])
        body.pack(fill="both", expand=True, padx=self.px(20), pady=(self.px(16), self.px(18)))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_columnconfigure(2, weight=0)
        cols = [tk.Frame(body, bg=C["paper"]) for _ in range(3)]
        gap = self.px(20)
        cols[0].grid(row=0, column=0, sticky="nsew", padx=(0, gap))
        cols[1].grid(row=0, column=1, sticky="nsew", padx=(0, gap))
        cols[2].grid(row=0, column=2, sticky="nsew")
        self._build_message(cols[0])
        self._build_cipher(cols[1])
        self._build_qr(cols[2])

    def _build_header(self):
        self.header = tk.Canvas(self.root, height=self.px(60), bg=C["space"], highlightthickness=0, bd=0)
        self.header.pack(fill="x")
        size = self.px(38)
        icon = Image.open(resource("assets", "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", icon.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=self.px(9), fill=255)
        icon.putalpha(mask)
        self._hdr_icon = ImageTk.PhotoImage(icon)
        self.help_btn = self._button(self.header, "Справка", self.show_help, "dark")
        self.header.bind("<Configure>", lambda e: self._draw_header())

    def _today_text(self):
        return (f"Ключ на сегодня, {self.today.day} {MONTHS[self.today.month - 1]}: "
                f"{self.names[self.auto_idx]}")

    def _draw_header(self):
        cv = self.header
        w, h = max(cv.winfo_width(), 1), max(cv.winfo_height(), 1)
        cv.delete("all")
        rnd = random.Random(1945)
        for _ in range(max(20, w // 12)):
            x, y = rnd.uniform(0, w), rnd.uniform(0, h)
            b = rnd.randint(60, 190)
            s = 2 if rnd.random() < 0.15 else 1
            cv.create_rectangle(x, y, x + s, y + s, fill=f"#{b:02x}{b:02x}{min(255, b + 18):02x}", outline="")
        pad = self.px(20)
        cv.create_image(pad, h // 2, image=self._hdr_icon, anchor="w")
        cv.create_text(pad + self.px(52), h // 2, text="Код Марса", font=self.f_title,
                       fill=C["space_text"], anchor="w")
        cv.create_window(w - pad, h // 2, window=self.help_btn, anchor="e")
        cv.create_text(w - pad - self.help_btn.winfo_reqwidth() - self.px(22), h // 2,
                       text=self._today_text(), font=self.f_body, fill=C["space_muted"], anchor="e")

    def _build_message(self, f):
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)
        top = tk.Frame(f, bg=C["paper"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, self.px(8)))
        self._heading(top, "Сообщение").pack(side="left")
        self._link(top, "Очистить всё", self.clear_all).pack(side="right")
        box, self.msg = self._textbox(f, self.f_text, "word")
        box.grid(row=1, column=0, sticky="nsew")
        self._placeholder(self.msg, "Напишите сообщение и нажмите Enter. "
                                    "Расшифрованный текст тоже появляется здесь.")
        self._note(f, "Shift+Enter переносит строку. Если удерживать Backspace 2 секунды, "
                      "очистятся все поля.").grid(row=2, column=0, sticky="ew", pady=(self.px(6), 0))
        key = tk.Frame(f, bg=C["paper"])
        key.grid(row=3, column=0, sticky="ew", pady=(self.px(16), 0))
        self._build_key(key)
        btns = tk.Frame(f, bg=C["paper"])
        btns.grid(row=4, column=0, sticky="ew", pady=(self.px(18), 0))
        self._button(btns, "Зашифровать", self.encrypt, "primary").pack(side="left")
        self._button(btns, "Расшифровать", self.decrypt_manual).pack(side="left", padx=(self.px(8), 0))

    def _build_key(self, f):
        f.grid_columnconfigure(0, weight=1)
        row = tk.Frame(f, bg=C["paper"])
        row.grid(row=0, column=0, sticky="ew")
        self._heading(row, "Ключ").pack(side="left")
        self.mode = tk.StringVar(value="list")
        for text, value in (("Выбрать ключ", "list"), ("Ключ-фраза", "phrase")):
            tk.Radiobutton(row, text=text, value=value, variable=self.mode, command=self._on_mode,
                           font=self.f_body, bg=C["paper"], fg=C["ink"], activebackground=C["paper"],
                           activeforeground=C["ink"], selectcolor=C["card"], highlightthickness=0,
                           bd=0, cursor="hand2").pack(side="left", padx=(self.px(18), 0))

        self.list_frame = tk.Frame(f, bg=C["paper"])
        self.combo = ttk.Combobox(self.list_frame, state="readonly", style="Mars.TCombobox",
                                  font=self.f_text, values=self._combo_values(), height=17)
        self.combo.current(self.auto_idx)
        self.combo.pack(fill="x")
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.combo.selection_clear())
        self._note(self.list_frame, "Автокод: каждый день выбирается ключ с номером текущего числа, "
                                    "как на телефоне. Если сообщение зашифровано ключом другого дня, "
                                    "программа подберёт ключ сама.").pack(fill="x", pady=(self.px(6), 0))

        self.phrase_frame = tk.Frame(f, bg=C["paper"])
        self.phrase = tk.StringVar()
        self.phrase.trace_add("write", lambda *a: self._update_hex())
        self.phrase_entry = tk.Entry(self.phrase_frame, textvariable=self.phrase, font=self.f_text,
                                     bg=C["card"], fg=C["ink"], insertbackground=C["ink"], relief="flat",
                                     bd=self.px(7), highlightthickness=1, highlightbackground=C["line"],
                                     highlightcolor=C["mars"])
        self.phrase_entry.pack(fill="x")
        self.phrase_entry.bind("<Button-3>", self._text_menu)
        self._placeholder(self.phrase_entry, "Введите ключ-фразу")
        hexrow = tk.Frame(self.phrase_frame, bg=C["paper"])
        hexrow.pack(fill="x", pady=(self.px(6), 0))
        tk.Label(hexrow, text="HEX-ключ:", font=self.f_small, fg=C["muted"], bg=C["paper"]).pack(side="left")
        self.hex_var = tk.StringVar()
        tk.Entry(hexrow, textvariable=self.hex_var, state="readonly", font=self.f_mono_small,
                 readonlybackground=C["paper"], fg=C["ink"], relief="flat", bd=0,
                 highlightthickness=0, width=10).pack(side="left", fill="x", expand=True,
                                                     padx=(self.px(6), self.px(8)))
        self._link(hexrow, "Копировать", lambda: self._copy(self.hex_var.get(), "HEX-ключ скопирован")).pack(side="right")
        self._note(self.phrase_frame, "Ключ вычисляется из фразы через SHA-256 так же, как на телефоне. "
                                      "У получателя должна быть та же фраза.").pack(fill="x", pady=(self.px(4), 0))
        self._on_mode()

    def _build_cipher(self, f):
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=3)
        f.grid_rowconfigure(4, weight=2)
        top = tk.Frame(f, bg=C["paper"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, self.px(8)))
        self._heading(top, "Шифровка Base32").pack(side="left")
        self._link(top, "Вставить", self.paste_cipher).pack(side="right")
        self._link(top, "Копировать", lambda: self._copy(self.b32_get(), "Шифровка скопирована")).pack(
            side="right", padx=(0, self.px(16)))
        box, self.b32 = self._textbox(f, self.f_mono, "char")
        box.grid(row=1, column=0, sticky="nsew")
        self._placeholder(self.b32, "Здесь появится шифровка. Чтобы расшифровать сообщение, "
                                    "вставьте сюда его шифровку: программа расшифрует её сама.")
        self.status = self._note(f, "")
        self.status.grid(row=2, column=0, sticky="ew", pady=(self.px(6), self.px(14)))
        mid = tk.Frame(f, bg=C["paper"])
        mid.grid(row=3, column=0, sticky="ew", pady=(0, self.px(8)))
        self._heading(mid, "Азбука Морзе").pack(side="left")
        self._link(mid, "В шифровку", self.morse_to_cipher).pack(side="right")
        self._link(mid, "Копировать", lambda: self._copy(self.morse_get(), "Морзянка скопирована")).pack(
            side="right", padx=(0, self.px(16)))
        box2, self.morse = self._textbox(f, self.f_mono, "word")
        box2.grid(row=4, column=0, sticky="nsew")
        self._placeholder(self.morse, "Морзянка появится после шифрования. Принятую по радио "
                                      "морзянку вставьте сюда и нажмите «В шифровку».")

    def _build_qr(self, f):
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)
        self.qr_cv = tk.Canvas(f, width=self.px(320), height=self.px(300), bg=C["card"],
                               highlightthickness=1, highlightbackground=C["line"], bd=0)
        self.qr_cv.grid(row=0, column=0, sticky="nsew")
        self.qr_cv.bind("<Configure>", lambda e: self._schedule_qr_redraw())
        self.qr_cv.bind("<Button-3>", self._qr_menu)
        g = tk.Frame(f, bg=C["paper"])
        g.grid(row=1, column=0, sticky="ew", pady=(self.px(12), 0))
        g.grid_columnconfigure(0, weight=1, uniform="q")
        g.grid_columnconfigure(1, weight=1, uniform="q")
        s = self.px(5)
        self._button(g, "Сохранить QR…", self.save_qr).grid(row=0, column=0, sticky="ew", padx=(0, s))
        self._button(g, "Копировать QR", self.copy_qr).grid(row=0, column=1, sticky="ew", padx=(s, 0))
        self.open_btn = self._button(g, "Открыть QR…", self._open_menu)
        self.open_btn.grid(row=1, column=0, sticky="ew", padx=(0, s), pady=(self.px(10), 0))
        self._button(g, "Бланк шифровки…", self.save_form).grid(row=1, column=1, sticky="ew",
                                                                padx=(s, 0), pady=(self.px(10), 0))

    # ------------------------------------------------------------------ QR-холст
    def _schedule_qr_redraw(self):
        if self._redraw_job:
            self.root.after_cancel(self._redraw_job)
        self._redraw_job = self.root.after(40, self._redraw_qr)

    def _art(self, w, h, faded):
        key = (w, h, faded)
        if key not in self._art_cache:
            src = self._art_src
            k = max(w / src.width, h / src.height)
            im = src.resize((max(1, round(src.width * k)), max(1, round(src.height * k))), Image.LANCZOS)
            left, top = (im.width - w) // 2, (im.height - h) // 2
            im = im.crop((left, top, left + w, top + h))
            if faded:
                im = Image.blend(im, Image.new("RGB", im.size, (255, 254, 250)), 0.5)
            if len(self._art_cache) > 4:
                self._art_cache.clear()
            self._art_cache[key] = ImageTk.PhotoImage(im)
        return self._art_cache[key]

    def _redraw_qr(self):
        self._redraw_job = None
        cv = self.qr_cv
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 20 or h < 20:
            return
        cv.delete("all")
        cv.create_image(0, 0, image=self._art(w, h, self.qr_mat is not None), anchor="nw")
        if self.qr_mat is not None:
            n = len(self.qr_mat)
            mod = max(1, min(w - self.px(60), int(h * 0.62)) // n)
            size = n * mod
            self._qr_photo = ImageTk.PhotoImage(core.qr_image(self.qr_mat, mod))
            pad, cap = self.px(12), self.px(30)
            x0, y0 = w // 2 - size // 2 - pad, int(h * 0.43) - size // 2 - pad
            x1, y1 = x0 + size + 2 * pad, y0 + size + 2 * pad + cap
            cv.create_rectangle(x0 + 3, y0 + 4, x1 + 3, y1 + 4, fill="#E6DED0", outline="")
            cv.create_rectangle(x0, y0, x1, y1, fill="#FFFFFF", outline=C["line"])
            cv.create_image(w // 2, y0 + pad + size // 2, image=self._qr_photo)
            cv.create_text(w // 2, y1 - cap // 2 - self.px(2), text=f"Ключ: {self.cipher_key}",
                           font=self.f_small, fill=C["muted"])
        else:
            text = self.qr_note or ("Здесь появится QR-код.\nЧтобы расшифровать картинку с QR, "
                                    "перетащите её в окно или нажмите «Открыть QR…».")
            cv.create_text(w // 2, h - self.px(62), text=text, width=w - self.px(48), justify="center",
                           font=self.f_small, fill=C["mars"] if self.qr_note else C["muted"])

    def _show_qr(self, b32, key_label):
        self.cipher_key = key_label
        try:
            self.qr_mat, self.qr_note = core.qr_matrix(b32), None
        except core.MarsError as e:
            self.qr_mat, self.qr_note = None, str(e)
        self._update_drag_source()
        self._redraw_qr()

    def _qr_export(self):
        return core.qr_image(self.qr_mat, max(4, 640 // len(self.qr_mat)))

    # ------------------------------------------------------------------ поля
    def msg_get(self):
        return self.msg.get("1.0", "end-1c")

    def b32_get(self):
        return self.b32.get("1.0", "end-1c")

    def morse_get(self):
        return self.morse.get("1.0", "end-1c")

    def _set(self, widget, value):
        widget.delete("1.0", "end")
        if value:
            widget.insert("1.0", value)
        self._refresh_placeholder(widget)

    def _set_b32(self, value):
        self._b32_prog = value.strip()
        self._set(self.b32, value)

    def _set_status(self, text, error=False):
        self.status.configure(text=text, fg=C["mars"] if error else C["muted"])

    def _copy(self, text, done):
        if not text.strip():
            self.toast("Поле пустое, копировать нечего", error=True)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.toast(done)

    # ------------------------------------------------------------------ ключи
    def _combo_values(self):
        return [f"{n}   (сегодня)" if i == self.auto_idx else n for i, n in enumerate(self.names)]

    def _on_mode(self):
        if self.mode.get() == "phrase":
            self.list_frame.grid_forget()
            self.phrase_frame.grid(row=1, column=0, sticky="ew", pady=(self.px(8), 0))
            self.phrase_entry.focus_set()
        else:
            self.phrase.set("")  # как на телефоне: фраза стирается при возврате к списку
            self.phrase_frame.grid_forget()
            self.list_frame.grid(row=1, column=0, sticky="ew", pady=(self.px(8), 0))

    def _update_hex(self):
        phrase = self.phrase.get().strip()
        self.hex_var.set(core.phrase_key(phrase).hex() if phrase else "")
        self._refresh_placeholder(self.phrase_entry)

    def _selected_key(self, feedback):
        if self.mode.get() == "phrase":
            phrase = self.phrase.get().strip()
            if not phrase:
                if feedback:
                    self.toast("Введите ключ-фразу или вернитесь к списку ключей", error=True)
                    self.phrase_entry.focus_set()
                return None
            return core.phrase_key(phrase), "ключ-фраза"
        idx = self.combo.current()
        idx = self.auto_idx if idx < 0 else idx
        return core.key_bytes(idx), self.names[idx]

    def _candidates(self):
        """Сначала выбранный ключ, затем ключ дня и остальные ключи списка."""
        seen, out = set(), []

        def add(key, label, primary=False):
            if key not in seen:
                seen.add(key)
                out.append((key, label, primary))

        sel = self._selected_key(feedback=False)
        if sel:
            add(sel[0], sel[1], True)
        for i in [self.auto_idx] + [i for i in range(len(self.names)) if i != self.auto_idx]:
            add(core.key_bytes(i), self.names[i])
        add(core.phrase_key(""), "пустая ключ-фраза")
        return out

    def _day_tick(self):
        today = dt.date.today()
        if today != self.today:
            old = self.auto_idx
            self.today, self.auto_idx = today, core.auto_key_index(today)
            cur = self.combo.current()
            self.combo.configure(values=self._combo_values())
            if cur == old:
                self.combo.current(self.auto_idx)
                if self.mode.get() == "list":
                    self.toast(f"Наступил новый день: выбран ключ «{self.names[self.auto_idx]}»")
            else:
                self.combo.current(cur)
            self._draw_header()
        self.root.after(60_000, self._day_tick)

    # ------------------------------------------------------------------ шифрование
    def encrypt(self, _event=None):
        text = self.msg_get()
        if not text.strip():
            self.toast("Сначала напишите сообщение", error=True)
            self.msg.focus_set()
            return "break"
        sel = self._selected_key(feedback=True)
        if sel is None:
            return "break"
        key, label = sel
        try:
            b32 = core.b32encode(core.encrypt(text, key))
        except Exception as e:
            self.toast(f"Ошибка при шифровании: {e}", error=True)
            return "break"
        self._set_b32(b32)
        self._set(self.morse, core.to_morse(b32))
        self._show_qr(b32, label)
        self._set_status(f"Зашифровано ключом «{label}». В шифровке {len(b32)} знаков.")
        return "break"

    def decrypt_manual(self, _event=None):
        raw = self.b32_get().strip()
        if not raw:
            self.toast("Вставьте шифровку в поле Base32 или откройте QR-код", error=True)
            return "break"
        self._decrypt_and_show(raw, explicit=True)
        return "break"

    def _b32_changed(self):
        if self._b32_job:
            self.root.after_cancel(self._b32_job)
        self._b32_job = self.root.after(350, self._b32_auto)

    def _b32_auto(self):
        """Как на телефоне: вставленная шифровка расшифровывается сама."""
        self._b32_job = None
        raw = self.b32_get().strip()
        if not raw or raw in (self._b32_prog, self._b32_last):
            return
        if core.is_morse(raw) or core.looks_like_b32(raw):
            self._b32_last = raw
            self._decrypt_and_show(raw, explicit=False)

    def _decrypt_and_show(self, raw, explicit):
        if core.is_morse(raw):
            try:
                b32 = core.morse_to_b32(raw)
            except core.MarsError as e:
                return self._fail(str(e), explicit)
            self._set_b32(b32)
        else:
            b32 = core.normalize_b32(raw)
        try:
            text, label, primary = core.decrypt_any(core.b32decode(b32), self._candidates())
        except core.MarsError as e:
            return self._fail(str(e), explicit)
        self._set(self.msg, text)
        self._set(self.morse, core.to_morse(b32))
        self._show_qr(b32, label)
        self._set_status(f"Расшифровано ключом «{label}».")
        if not primary:
            self.toast(f"Расшифровано ключом «{label}»")
        elif explicit:
            self.toast("Успешно расшифровано")
        return True

    def _fail(self, message, explicit):
        self._set_status(message, error=True)
        if explicit:
            self.toast(message, error=True)
        return False

    def _receive_cipher_text(self, text):
        t = text.strip()
        self._set_b32(t)
        self._b32_last = t
        self._decrypt_and_show(t, explicit=True)

    def morse_to_cipher(self):
        raw = self.morse_get().strip()
        if not raw:
            self.toast("Вставьте морзянку в поле «Азбука Морзе»", error=True)
            return
        try:
            b32 = core.morse_to_b32(raw)
        except core.MarsError as e:
            self.toast(str(e), error=True)
            return
        self._set_b32(b32)
        self._b32_last = b32
        self._decrypt_and_show(b32, explicit=True)

    def clear_all(self):
        self._set(self.msg, "")
        self._set(self.morse, "")
        self._set_b32("")
        self.qr_mat = self.qr_note = None
        self.cipher_key = self._b32_last = ""
        self._set_status("")
        self._update_drag_source()
        self._redraw_qr()
        self.msg.focus_set()

    # ------------------------------------------------------------------ получение QR
    def paste_cipher(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        if text.strip():
            self._receive_cipher_text(text)
            return
        img = self._clipboard_image()
        if img is not None:
            self._receive_image(img)
        else:
            self.toast("В буфере обмена нет шифровки", error=True)

    def _clipboard_image(self):
        try:
            from PIL import ImageGrab
            data = ImageGrab.grabclipboard()
        except Exception:
            return None
        if isinstance(data, Image.Image):
            return data
        if isinstance(data, list):
            for path in data:
                try:
                    im = Image.open(path)
                    im.load()
                    return im
                except Exception:
                    continue
        return None

    def _open_menu(self):
        m = self._menu()
        m.add_command(label="Из файла…", command=self.open_qr_file)
        m.add_command(label="Из буфера обмена", command=self.qr_from_clipboard)
        m.add_command(label="Найти на экране", command=self.qr_from_screen)
        b = self.open_btn
        m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def open_qr_file(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Открыть картинку с QR-кодом",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                       ("Текст шифровки", "*.txt"), ("Все файлы", "*.*")])
        if path:
            self.open_path(path)

    def open_path(self, path):
        if os.path.splitext(path)[1].lower() == ".txt":
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError as e:
                self.toast(f"Не удалось открыть файл: {e}", error=True)
                return
            if core.looks_like_b32(text) or core.is_morse(text):
                self._receive_cipher_text(text)
            else:
                self._set(self.msg, text)
            return
        try:
            img = Image.open(path)
            img.load()
        except Exception:
            self.toast("Этот файл не открывается как картинка", error=True)
            return
        self._receive_image(img)

    def _receive_image(self, img):
        try:
            texts = core.read_qr(img)
        except Exception as e:
            self.toast(f"Не удалось прочитать QR-код: {e}", error=True)
            return
        self._receive_qr_texts(texts, "QR-код на картинке не найден")

    def _receive_qr_texts(self, texts, not_found):
        if not texts:
            self.toast(not_found, error=True)
            return
        cipher = core.pick_cipher(texts)
        if cipher is None:
            self.toast("QR-код найден, но в нём не шифровка «Кода Марса»", error=True)
            return
        self._receive_cipher_text(cipher)

    def qr_from_clipboard(self):
        img = self._clipboard_image()
        if img is None:
            self.toast("В буфере обмена нет картинки. Скопируйте QR-код и повторите", error=True)
            return
        self._receive_image(img)

    def qr_from_screen(self):
        self.root.withdraw()
        self.root.after(450, self._grab_screen)

    def _grab_screen(self):
        img = None
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True) if IS_WIN else ImageGrab.grab()
        except Exception:
            img = None
        finally:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        if img is None:
            self.toast("Не удалось сделать снимок экрана", error=True)
            return
        try:
            texts = core.read_qr(img)
        except Exception:
            texts = []
        self._receive_qr_texts(texts, "На экране не найден QR-код. Откройте его крупнее и повторите")

    # ------------------------------------------------------------------ отдача QR
    def _need_qr(self):
        if self.qr_mat is None:
            self.toast(self.qr_note or "QR-кода пока нет: сначала зашифруйте сообщение", error=True)
            return False
        return True

    def _pictures_dir(self):
        base = os.path.join(os.path.expanduser("~"), "Pictures")
        if not os.path.isdir(base):
            base = os.path.expanduser("~")
        folder = os.path.join(base, "KodMars")
        try:
            os.makedirs(folder, exist_ok=True)
            return folder
        except OSError:
            return base

    def save_qr(self):
        if not self._need_qr():
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить QR-код", initialdir=self._pictures_dir(),
            initialfile=dt.datetime.now().strftime("qr_%Y%m%d_%H%M%S.png"), defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return
        try:
            img = self._qr_export()
            if path.lower().endswith((".jpg", ".jpeg")):
                img.convert("RGB").save(path, quality=95)
            else:
                img.save(path)
        except Exception as e:
            self.toast(f"Не удалось сохранить: {e}", error=True)
            return
        self.toast("QR-код сохранён")

    def copy_qr(self):
        if not self._need_qr():
            return
        if not IS_WIN:
            self.toast("Копирование картинки работает в Windows. Используйте «Сохранить QR…»", error=True)
            return
        try:
            copy_image_to_clipboard(self._qr_export(), self.root.winfo_id())
        except Exception as e:
            self.toast(f"Не удалось скопировать картинку: {e}", error=True)
            return
        self.toast("QR-код скопирован. Вставьте его в мессенджер: Ctrl+V")

    def save_form(self):
        raw = self.b32_get().strip()
        b32 = core.normalize_b32(raw) if raw and not core.is_morse(raw) else ""
        if not core.looks_like_b32(b32):
            self.toast("Сначала зашифруйте сообщение: бланк заполняется шифровкой", error=True)
            return
        try:
            img = core.render_form(resource("assets", "form_blank.png"), b32, self.cipher_key or "—")
        except Exception as e:
            self.toast(f"Не удалось подготовить бланк: {e}", error=True)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить бланк шифровки", initialdir=self._pictures_dir(),
            initialfile=dt.datetime.now().strftime("shifrovka_%Y%m%d_%H%M.png"), defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF для печати", "*.pdf"), ("JPEG", "*.jpg")])
        if not path:
            return
        try:
            if path.lower().endswith(".pdf"):
                img.save(path, "PDF", resolution=300.0)
            elif path.lower().endswith((".jpg", ".jpeg")):
                img.save(path, quality=92)
            else:
                img.save(path)
        except Exception as e:
            self.toast(f"Не удалось сохранить: {e}", error=True)
            return
        self.toast("Бланк шифровки сохранён")

    # ------------------------------------------------------------------ перетаскивание
    def _setup_dnd(self):
        if not HAS_DND:
            return
        targets = [(self.root, "cipher"), (self.qr_cv, "cipher"), (self.b32, "cipher"),
                   (self.morse, "cipher"), (self.msg, "message")]
        targets += [(lbl, "message" if w is self.msg else "cipher")
                    for w, (lbl, _) in self._placeholders.items() if isinstance(w, tk.Text)]
        for widget, role in targets:
            try:
                widget.drop_target_register(DND_FILES, DND_TEXT)
                widget.dnd_bind("<<Drop>>", lambda e, r=role: self._on_drop(e, r))
            except Exception:
                pass

    def _on_drop(self, event, role):
        data = event.data or ""
        try:
            items = list(self.root.tk.splitlist(data))
        except tk.TclError:
            items = [data]
        files = [p for p in items if os.path.isfile(p)]
        if files:
            self.root.after(10, lambda: self.open_path(files[0]))
        elif data.strip():
            if role == "message" and not (core.looks_like_b32(data) or core.is_morse(data)):
                self.msg.insert("insert", data)
            else:
                self.root.after(10, lambda: self._receive_cipher_text(data))
        return getattr(event, "action", COPY)

    def _update_drag_source(self):
        """QR-код можно утащить мышью в чат или папку, когда он есть."""
        if not HAS_DND:
            return
        try:
            if self.qr_mat is not None and not self._drag_on:
                self.qr_cv.drag_source_register(1, DND_FILES)
                self.qr_cv.dnd_bind("<<DragInitCmd>>", self._drag_init)
                self._drag_on = True
            elif self.qr_mat is None and self._drag_on:
                self.qr_cv.drag_source_unregister()
                self._drag_on = False
        except Exception:
            self._drag_on = False

    def _drag_init(self, _event):
        if self.qr_mat is None:
            return (COPY, DND_TEXT, self.b32_get() or " ")
        folder = os.path.join(tempfile.gettempdir(), "KodMarsa")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "qr_kod_marsa.png")
        self._qr_export().save(path)
        return (COPY, DND_FILES, (path,))

    # ------------------------------------------------------------------ клавиатура и меню
    def _bind_keys(self):
        self.root.bind_all("<F1>", lambda e: self.show_help())
        if IS_WIN:
            self.root.bind_all("<Control-KeyPress>", self._ctrl_fix, add="+")
        self.msg.bind("<Return>", self.encrypt)
        self.msg.bind("<KP_Enter>", self.encrypt)
        self.msg.bind("<Shift-Return>", self._newline)
        self.b32.bind("<Return>", self.decrypt_manual)
        self.b32.bind("<KP_Enter>", self.decrypt_manual)
        self.b32.bind("<Shift-Return>", lambda e: "break")
        self.morse.bind("<Return>", lambda e: (self.morse_to_cipher(), "break")[1])

    def _newline(self, _event):
        self.msg.insert("insert", "\n")
        self.msg.see("insert")
        return "break"

    def _ctrl_fix(self, event):
        """Ctrl+C/V/X/A/Z при русской и украинской раскладке."""
        if event.keysym.isascii() and len(event.keysym) == 1:
            return None
        action = {67: "<<Copy>>", 86: "<<Paste>>", 88: "<<Cut>>", 65: "<<SelectAll>>",
                  90: "<<Undo>>", 89: "<<Redo>>"}.get(event.keycode)
        if not action:
            return None
        w = event.widget
        if action == "<<SelectAll>>" and isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end-1c")
        else:
            w.event_generate(action)
        return "break"

    def _bs_press(self, _event):
        self._bs_press_t = time.monotonic()
        if self._bs_job is None:
            self._bs_job = self.root.after(2000, self._bs_fire)

    def _bs_release(self, _event):
        released = time.monotonic()
        self.root.after(70, lambda: self._bs_check(released))

    def _bs_check(self, released):
        if self._bs_press_t <= released and self._bs_job is not None:
            self.root.after_cancel(self._bs_job)
            self._bs_job = None

    def _bs_fire(self):
        self._bs_job = None
        self.clear_all()
        self.toast("Все поля очищены")

    def _text_menu(self, event, widget=None):
        w = widget or event.widget
        w.focus_set()
        is_text = isinstance(w, tk.Text)
        try:
            has_sel = bool(w.tag_ranges("sel")) if is_text else w.selection_present()
        except tk.TclError:
            has_sel = False
        get_all = (lambda: w.get("1.0", "end-1c")) if is_text else w.get
        m = self._menu()
        m.add_command(label="Вырезать", command=lambda: w.event_generate("<<Cut>>"),
                      state="normal" if has_sel else "disabled")
        if has_sel:
            m.add_command(label="Копировать", command=lambda: w.event_generate("<<Copy>>"))
        else:
            m.add_command(label="Копировать всё", command=lambda: self._copy(get_all(), "Скопировано"))
        m.add_command(label="Вставить",
                      command=self.paste_cipher if w is self.b32 else (lambda: w.event_generate("<<Paste>>")))
        m.add_separator()
        if is_text:
            m.add_command(label="Выделить всё", command=lambda: w.tag_add("sel", "1.0", "end-1c"))
        clear = (lambda: self._set_b32("")) if w is self.b32 else (
            (lambda: self._set(w, "")) if is_text else (lambda: w.delete(0, "end")))
        m.add_command(label="Очистить поле", command=clear)
        m.tk_popup(event.x_root, event.y_root)

    def _qr_menu(self, event):
        m = self._menu()
        m.add_command(label="Сохранить QR…", command=self.save_qr)
        m.add_command(label="Копировать QR", command=self.copy_qr)
        m.add_separator()
        m.add_command(label="Открыть QR из файла…", command=self.open_qr_file)
        m.add_command(label="Вставить QR из буфера обмена", command=self.qr_from_clipboard)
        m.add_command(label="Найти QR на экране", command=self.qr_from_screen)
        m.add_separator()
        m.add_command(label="Бланк шифровки…", command=self.save_form)
        m.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------------ уведомления и справка
    def toast(self, text, error=False):
        """Короткое уведомление, которое исчезает само, как Toast на телефоне."""
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self._hide_toast()
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(win, text=text, font=self.f_body, fg="#FFFFFF", bg=C["mars"] if error else C["space"],
                 padx=self.px(18), pady=self.px(10), wraplength=self.px(520), justify="center").pack()
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + self.root.winfo_height() - win.winfo_reqheight() - self.px(26)
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        self._toast_win = win
        self._toast_job = self.root.after(3200 if error else 2200, self._hide_toast)

    def _hide_toast(self):
        self._toast_job = None
        if self._toast_win is not None:
            try:
                self._toast_win.destroy()
            except tk.TclError:
                pass
            self._toast_win = None

    def show_help(self):
        if self._help_win is not None and self._help_win.winfo_exists():
            self._help_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("Справка — Код Марса")
        win.configure(bg=C["paper"])
        win.geometry(f"{self.px(640)}x{self.px(560)}")
        t = tk.Text(win, wrap="word", font=self.f_text, bg=C["card"], fg=C["ink"], relief="flat",
                    padx=self.px(22), pady=self.px(16), highlightthickness=0, spacing2=self.px(3))
        t.pack(fill="both", expand=True, padx=self.px(14), pady=self.px(14))
        t.tag_configure("h", font=self.f_head, spacing1=self.px(12), spacing3=self.px(4))
        for i, (title, body) in enumerate(HELP):
            t.insert("end", ("" if i == 0 else "\n") + title + "\n", "h")
            t.insert("end", body + "\n")
        t.insert("end", f"\nВерсия {core.APP_VERSION} для компьютера.", "")
        t.configure(state="disabled")
        win.bind("<Escape>", lambda e: win.destroy())
        self._help_win = win


def show_splash(root, scale, done):
    """Заставка, как на телефоне: логотип на чёрном фоне."""
    try:
        img = Image.open(resource("assets", "logo.jpg")).convert("RGB")
    except Exception:
        done()
        return
    sh = root.winfo_screenheight()
    h = min(int(560 * scale), int(sh * 0.66))
    w = int(h * img.width / img.height)
    photo = ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.configure(bg="black")
    lbl = tk.Label(win, image=photo, bd=0, bg="black")
    lbl.image = photo
    lbl.pack()
    win.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(sh - h) // 2}")
    try:
        win.attributes("-topmost", True)
    except tk.TclError:
        pass
    state = {"done": False}

    def finish(_e=None):
        if state["done"]:
            return
        state["done"] = True
        win.destroy()
        done()

    lbl.bind("<Button-1>", finish)
    root.after(1800, finish)


def run_selftest():
    """KodMarsa.exe --selftest: проверка собранной программы (пишет selftest.log)."""
    lines = [f"Код Марса {core.APP_VERSION}: самопроверка {dt.datetime.now():%d.%m.%Y %H:%M}"]
    ok = True
    try:
        lines += core.selftest()
        for name in ("logo.jpg", "background.jpg", "form_blank.png", "icon.png", "icon.ico"):
            assert os.path.isfile(resource("assets", name)), f"нет файла assets/{name}"
        lines.append("картинки программы: на месте")
        sample = core.b32encode(core.encrypt("проверка бланка", core.key_bytes(1)))
        assert core.render_form(resource("assets", "form_blank.png"), sample, "Код 1").size == (2528, 3416)
        lines.append("бланк шифровки: ок")
        if not HAS_DND:
            raise AssertionError("модуль tkinterdnd2 не попал в сборку")
        import tkinterdnd2
        assert os.path.isdir(os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd")), "нет папки tkdnd"
        lines.append("перетаскивание: библиотека tkdnd на месте")
        try:
            r = TkinterDnD.Tk()
            r.withdraw()
            lines.append(f"перетаскивание: tkdnd {r.TkdndVersion} загружается")
            r.destroy()
        except Exception as e:  # без экрана окно создать нельзя, это не ошибка сборки
            lines.append(f"предупреждение: окно для проверки tkdnd не создано ({e})")
    except Exception as e:
        ok = False
        lines.append(f"ОШИБКА: {e!r}")
        lines.append(traceback.format_exc())
    lines.append("ИТОГ: " + ("всё в порядке" if ok else "есть ошибки"))
    text = "\n".join(lines) + "\n"
    for folder in (app_dir(), tempfile.gettempdir()):
        try:
            with open(os.path.join(folder, "selftest.log"), "w", encoding="utf-8") as fh:
                fh.write(text)
            break
        except OSError:
            continue
    if sys.stdout is not None:
        try:
            print(text)
        except Exception:
            pass
    return 0 if ok else 1


def main():
    global HAS_DND
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    enable_dpi_awareness()
    root = None
    if HAS_DND:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            HAS_DND = False
            root = getattr(tk, "_default_root", None)
    if root is None:
        root = tk.Tk()
    root.withdraw()
    app = App(root)

    def start():
        root.deiconify()
        root.lift()
        root.focus_force()
        app.msg.focus_set()
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args and os.path.isfile(args[0]):  # файл, перетащенный на значок программы
            root.after(300, lambda: app.open_path(args[0]))

    if "--no-splash" in sys.argv:
        start()
    else:
        show_splash(root, app.scale, start)
    root.mainloop()


if __name__ == "__main__":
    main()
