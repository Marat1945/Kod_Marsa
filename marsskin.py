# -*- coding: utf-8 -*-
"""«Код Марса» — окно по макету: металлическая панель радиостанции.

Вся логика (шифрование, Морзе, SSTV, MP3, бланки, история) берётся из kod_marsa.App.
Здесь только внешний вид: картинка-«шкура» по макету, настоящие поля и кнопки поверх неё,
лампы, ротор ключей и анимации: вращается Марс на значке и на плакате, от вышек расходятся
волны, девиз печатается на телеграфной ленте, мерцает красная лампа, вспыхивает звезда.
Окно открывается на весь экран и растягивается за любой край пропорционально."""
import json
import math
import random
import sys
import time
import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageStat, ImageTk

import kod_marsa as km
import marscore as core
import marsi18n as i18n
import marsmenu
from marsi18n import T

W0, H0, FRAMES = 1672, 941, 48
INK, CREAM, NOTE_FG = "#2A241D", "#EFE4CE", "#D8CCB4"
WIN = sys.platform == "win32"
ASSETS = ("skin.jpg", "skin_clean.jpg", "skin.json", "icon_frames.jpg", "poster_frames.jpg", "lamp_red.png",
          "lamp_orange.png", "lamp_off.png", "tape.png", "guide_ru.jpg", "guide_uk.jpg", "guide_pl.jpg", "guide_en.jpg")
TEXT = {"msg": (48, 182, 618, 594), "b32": (686, 182, 1296, 446), "status": (690, 450, 1294, 482),
        "morse": (686, 600, 1296, 894)}
QR_CARD = (1350, 426, 1648, 668)
COMBO = (40, 726, 590, 767)
ROTOR = (46, 729, 126, 764)
NOTE = (40, 772, 600, 820)
TOP_LAMP, STAR, MENU_GLOW = (1192, 60), (1495, 124), (55, 56)
EDGE = 8
HOT = {
    "menu": (25, 21, 86, 92), "lang": (1205, 34, 1366, 86), "help": (1374, 34, 1493, 86),
    "min": (1525, 38, 1560, 78), "max": (1563, 38, 1601, 78), "close": (1604, 38, 1645, 78),
    "back": (474, 38, 532, 82), "fwd": (536, 38, 594, 82),
    "clear_all": (490, 118, 631, 158), "copy1": (1036, 120, 1162, 160), "paste": (1176, 120, 1292, 160),
    "rb_list": (166, 672, 334, 712), "rb_phrase": (345, 672, 497, 712), "combo": (128, 726, 626, 767),
    "encrypt": (34, 824, 316, 901), "decrypt": (344, 824, 631, 901), "sound": (864, 527, 934, 576),
    "morse_save": (940, 527, 1054, 576), "copy_morse": (1065, 528, 1171, 571), "morse_settings": (1186, 528, 1303, 574),
    "sstv_save": (1338, 687, 1653, 726), "sstv": (1338, 733, 1530, 783), "sstv_mode": (1541, 733, 1653, 783),
    "save_qr": (1338, 790, 1437, 832), "copy_qr": (1447, 790, 1552, 832), "open_qr": (1561, 790, 1653, 832),
    "form_png": (1338, 842, 1493, 901), "form_doc": (1498, 842, 1653, 901), "note": NOTE,
}
CURSORS = {"w": "size_we", "e": "size_we", "n": "size_ns", "s": "size_ns", "nw": "size_nw_se", "se": "size_nw_se",
           "ne": "size_ne_sw", "sw": "size_ne_sw"} if WIN else {}


def TK(prefix):
    """Перевод длинной строки по её началу."""
    return T(next((k for k in i18n.TR if k.startswith(prefix)), prefix))


def _labels():
    """Надписи для других языков: (текст, цвет, высота шрифта, шрифт)."""
    def U(s):
        return T(s).upper()
    return {
        "title": (U("Код Марса"), CREAM, 46, "cond"), "help": (T("Справка"), CREAM, 17, "cond"),
        "msg_plate": (U("Сообщение"), INK, 24, "cond"), "clear_all": (U("Очистить всё"), CREAM, 15, "cond"),
        "b32_plate": (U("Шифровка Base32").replace("BASE32", "Base32"), INK, 24, "cond"),
        "copy1": (U("Копировать"), CREAM, 13, "cond"), "paste": (U("Вставить"), CREAM, 13, "cond"),
        "morse_plate": (U("Азбука Морзе"), INK, 24, "cond"), "copy_morse": (U("Копировать"), CREAM, 14, "cond"),
        "morse_settings": (U("Настройка\nазбуки Морзе"), INK, 12, "cond"), "key_plate": (U("Ключ"), INK, 24, "cond"),
        "rb_list": (T("Выбрать ключ"), CREAM, 16, "cond"), "rb_phrase": (T("Ключ-фраза"), CREAM, 16, "cond"),
        "encrypt": (U("Зашифровать"), CREAM, 28, "cond"), "decrypt": (U("Расшифровать"), INK, 28, "cond"),
        "shift_note": (TK("Shift+Enter"), NOTE_FG, 13, "sans"), "sstv_save": (T("Сохранить SSTV.mp3"), INK, 16, "cond"),
        "save_qr": (T("Сохранить QR"), INK, 14, "cond"), "copy_qr": (T("Копировать QR"), INK, 14, "cond"),
        "open_qr": (T("Открыть QR"), INK, 14, "cond"), "form_png": (T("Бланк шифровки\npng"), INK, 14, "cond"),
        "form_doc": (T("Бланк шифровки\ndoc"), INK, 14, "cond"),
    }


class Proxy:
    """Вместо кнопки: общая логика вызывает .configure(), окно рисует это на панели."""

    def __init__(self, app, name):
        self.app, self.name = app, name

    def configure(self, **kw):
        self.app._proxy(self.name, kw)

    config = configure


class KeyBox:
    """Вместо выпадающего списка: хранит номер ключа, рисует название в поле и цифры на роторе."""

    def __init__(self, app, idx):
        self.app, self.idx = app, idx

    def current(self, idx=None):
        if idx is None:
            return self.idx
        self.idx = idx
        self.app._draw_combo()

    def selection_clear(self):
        pass


class SkinApp(km.App):
    def __init__(self, root):
        self._maxed, self._k_normal, self._win_xy = True, None, None
        self._anim_job = self._skin_k = self._guide_win = self._band = self._resize = None
        self._over_qr, self._rotor_dir, self._edge = False, 0, None
        super().__init__(root)
        if WIN:  # обычное окно без системной рамки: значок на панели задач остаётся
            try:
                root.attributes("-alpha", 0.0)
            except tk.TclError:
                pass
        else:
            root.overrideredirect(True)
        root.bind("<Alt-F4>", lambda e: self._on_close())
        root.bind("<Control-KeyPress>", self._qr_keys, add="+")

    # ------------------------------------------------------------------ размеры и шрифты
    def _work_area(self):
        return km.work_area(self.root)

    def _layout(self):
        wx, wy, ww, wh = self._work_area()
        if self._maxed:  # на весь экран: картинка вписана, по краям — продолжение рамки
            self.k = min(ww / W0, wh / H0)
            self.CW, self.CH, self.win = ww, wh, (wx, wy)
        else:
            if self._k_normal is None:
                self._k_normal = 0.88 * min(1.0, (ww - 24) / W0, (wh - 16) / H0)
            self.k = self._k_normal
            self.CW, self.CH = round(W0 * self.k), round(H0 * self.k)
            if self._win_xy is None:
                self._win_xy = (wx + (ww - self.CW) // 2, wy + (wh - self.CH) // 2)
            self.win = self._win_xy
        self.W, self.H = round(W0 * self.k), round(H0 * self.k)
        self.ox, self.oy = (self.CW - self.W) // 2, (self.CH - self.H) // 2

    def _make_fonts(self):
        super()._make_fonts()
        self._layout()
        fams = {f.lower(): f for f in tkfont.families(self.root)}

        def pick(*names):
            return next((fams[n.lower()] for n in names if n.lower() in fams), names[-1])

        self.fam = {"cond": pick("Bahnschrift SemiBold Condensed", "Bahnschrift Condensed", "Arial Narrow",
                                 "DejaVu Sans Condensed", "Liberation Sans Narrow", "Arial"),
                    "type": pick("Courier New", "Nimbus Mono PS", "FreeMono", "DejaVu Sans Mono"),
                    "mono": pick("Consolas", "DejaVu Sans Mono", "Courier New"),
                    "sans": pick("Segoe UI", "DejaVu Sans", "Arial")}
        self.cond_weight = "normal" if "Bahnschrift" in self.fam["cond"] else "bold"

    def kp(self, v):
        return max(1, int(round(v * self.k)))

    def font(self, kind, size, weight=None):
        return (self.fam[kind], -self.kp(size), weight or (self.cond_weight if kind == "cond" else "normal"))

    def _r(self, rect):
        """Координаты макета → координаты окна (с учётом масштаба и полей по краям)."""
        return tuple(int(round(v * self.k)) + (self.ox if i % 2 == 0 else self.oy) for i, v in enumerate(rect))

    def _rs(self, rect):
        return tuple(int(round(v * self.k)) for v in rect)

    # ------------------------------------------------------------------ картинки
    def _skin_images(self):
        if self._skin_k == self.k:
            return
        k = self.k

        def load(name, mode="RGB"):
            return Image.open(km.resource("assets", name)).convert(mode)

        def rs(im, w, h):
            return im.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)

        with open(km.resource("assets", "skin.json"), encoding="utf-8") as fh:
            self.meta = json.load(fh)
        self._skin = {"ru": rs(load("skin.jpg"), self.W, self.H), "clean": rs(load("skin_clean.jpg"), self.W, self.H)}

        def frames(name, region):
            strip = load(name)
            fw, fh = strip.width, strip.height // FRAMES
            x0, y0, x1, y1 = region
            return [ImageTk.PhotoImage(rs(strip.crop((0, i * fh, fw, (i + 1) * fh)), (x1 - x0) * k, (y1 - y0) * k))
                    for i in range(FRAMES)]

        self._icon_frames = frames("icon_frames.jpg", self.meta["icon"]["region"])
        self._poster_frames = frames("poster_frames.jpg", self.meta["poster"]["region"])
        self._lamp_src = {n: load(f"lamp_{n}.png", "RGBA") for n in ("red", "orange", "off")}
        tape = load("tape.png", "RGBA")
        tx0, _, tx1, _ = self.meta["tape"]
        self._tape_photo = ImageTk.PhotoImage(rs(tape, (tx1 - tx0) * k, tape.height * k))
        med = ImageStat.Stat(self._skin["ru"].crop(self._rs((200, 300, 450, 500)))).median
        self.paper = "#%02x%02x%02x" % tuple(med[:3])
        med = ImageStat.Stat(self._skin["ru"].crop(self._rs((250, 738, 450, 756)))).median
        self.field_bg = "#%02x%02x%02x" % tuple(med[:3])
        self._lamp_cache, self._halo_cache, self._ov_cache = {}, {}, {}
        blank = ImageTk.PhotoImage(Image.new("RGBA", (2, 2), (0, 0, 0, 0)))
        self._snd_frames = [blank] + [self._halo((255, 170, 40), 30, 0.35 + 0.5 * (0.5 + 0.5 * math.sin(2 * math.pi * i / 13)))
                                      for i in range(13)]
        self._rotor_imgs = self._make_rotor_images()
        self._skin_k = k

    def _compose(self, skin):
        """Картинка окна: шкура по центру, по краям — зеркальное продолжение её рамки."""
        if skin.size == (self.CW, self.CH):
            return skin
        out = Image.new("RGB", (self.CW, self.CH), (20, 17, 14))
        out.paste(skin, (self.ox, self.oy))
        rw = self.CW - self.ox - skin.width
        if self.ox > 0:
            out.paste(skin.crop((0, 0, self.ox, skin.height)).transpose(Image.FLIP_LEFT_RIGHT), (0, self.oy))
        if rw > 0:
            out.paste(skin.crop((skin.width - rw, 0, skin.width, skin.height)).transpose(Image.FLIP_LEFT_RIGHT),
                      (self.ox + skin.width, self.oy))
        bh = self.CH - self.oy - skin.height
        if self.oy > 0:
            out.paste(out.crop((0, self.oy, self.CW, 2 * self.oy)).transpose(Image.FLIP_TOP_BOTTOM), (0, 0))
        if bh > 0:
            band = out.crop((0, self.oy + skin.height - bh, self.CW, self.oy + skin.height))
            out.paste(band.transpose(Image.FLIP_TOP_BOTTOM), (0, self.oy + skin.height))
        return out

    def _halo(self, rgb, radius, alpha):
        key = (rgb, radius, round(alpha, 2))
        if key not in self._halo_cache:
            r = self.kp(radius)
            s = 2 * r
            a = Image.new("L", (s, s), 0)
            ImageDraw.Draw(a).ellipse((r * 0.45, r * 0.45, s - r * 0.45, s - r * 0.45), fill=int(255 * alpha))
            im = Image.new("RGBA", (s, s), rgb + (0,))
            im.putalpha(a.filter(ImageFilter.GaussianBlur(r * 0.32)))
            self._halo_cache[key] = ImageTk.PhotoImage(im)
        return self._halo_cache[key]

    def _glint(self, level):
        key = ("glint", level)
        if key not in self._halo_cache:
            r = self.kp(34)
            s, w = 2 * r, max(1, self.kp(2))
            a = Image.new("L", (s, s), 0)
            d = ImageDraw.Draw(a)
            d.ellipse((r * 0.62, r * 0.62, s - r * 0.62, s - r * 0.62), fill=255)
            d.line((r, r * 0.12, r, s - r * 0.12), fill=210, width=w)
            d.line((r * 0.12, r, s - r * 0.12, r), fill=210, width=w)
            a = a.filter(ImageFilter.GaussianBlur(self.kp(3))).point(lambda v: int(v * level))
            im = Image.new("RGBA", (s, s), (255, 214, 170, 0))
            im.putalpha(a)
            self._halo_cache[key] = ImageTk.PhotoImage(im)
        return self._halo_cache[key]

    def _lamp_img(self, kind, factor=1.0, bright=1.0):
        key = (kind, factor, bright)
        if key not in self._lamp_cache:
            src = self._lamp_src[kind]
            s = max(4, int(round(src.width * factor * self.k)))
            im = src.resize((s, s), Image.LANCZOS)
            if bright != 1.0:
                rgb = ImageEnhance.Brightness(im.convert("RGB")).enhance(bright)
                rgb.putalpha(im.getchannel("A"))
                im = rgb
            self._lamp_cache[key] = ImageTk.PhotoImage(im)
        return self._lamp_cache[key]

    def _make_rotor_images(self):
        """Ротор: корпус, два барабана с цифрами и рифлёное колёсико."""
        x0, y0, x1, y1 = self._rs(ROTOR)
        W, H = x1 - x0, y1 - y0
        body = Image.new("RGB", (W, H), (24, 20, 17))
        d = ImageDraw.Draw(body)
        for y in range(H):
            c = int(46 - 26 * abs(y - H / 2) / (H / 2))
            d.line((0, y, W, y), fill=(c, c - 5, c - 9))
        d.rectangle((0, 0, W - 1, H - 1), outline=(96, 84, 70))
        d.rectangle((1, 1, W - 2, H - 2), outline=(16, 13, 11))
        dw, dh = self.kp(25), H - self.kp(6)
        drum = Image.new("RGB", (dw, dh))
        dd = ImageDraw.Draw(drum)
        for y in range(dh):
            t = abs(y - dh / 2) / (dh / 2)
            c = int(42 - 34 * t * t)
            dd.line((0, y, dw, y), fill=(c, c, c - 2))
        dd.line((0, dh // 2, dw, dh // 2), fill=(70, 66, 60))
        wheel = Image.new("RGB", (self.kp(13), H - self.kp(4)), (40, 36, 32))
        wd = ImageDraw.Draw(wheel)
        for x in range(0, wheel.width, max(2, self.kp(3))):
            wd.line((x, 0, x, wheel.height), fill=(120, 112, 100))
        for y in range(wheel.height):
            t = abs(y - wheel.height / 2) / (wheel.height / 2)
            wd.line((0, y, 1, y), fill=(int(90 - 60 * t),) * 3)
        return {"body": ImageTk.PhotoImage(body), "drum": ImageTk.PhotoImage(drum), "wheel": ImageTk.PhotoImage(wheel),
                "size": (W, H), "dw": dw, "dh": dh}

    # ------------------------------------------------------------------ окно
    def _build(self):
        r = self.root
        self._stop_anim()
        old = getattr(self, "cv", None)
        self._placeholders = {}
        self._skin_images()
        m = self.meta
        r.title(T("Код Марса"))
        r.configure(bg="#14110E")
        try:
            if WIN:
                r.iconbitmap(default=km.resource("assets", "icon.ico"))
            else:
                r.iconphoto(True, self._icon_photo)
        except tk.TclError:
            pass
        x, y = self.win
        r.geometry(f"{self.CW}x{self.CH}+{x}+{y}")
        r.resizable(False, False)
        cv = self.cv = tk.Canvas(r, width=self.CW, height=self.CH, bd=0, highlightthickness=0, bg="#14110E")
        self._bg_item = cv.create_image(0, 0, anchor="nw")
        self._set_background()
        self._icon_item = cv.create_image(*self._r(m["icon"]["region"][:2]), image=self._icon_frames[0], anchor="nw")
        self._poster_item = cv.create_image(*self._r(m["poster"]["region"][:2]), image=self._poster_frames[0],
                                            anchor="nw")
        self._glint_item = cv.create_image(*self._r(STAR), tags=("lamp",))
        self._menu_glow = cv.create_image(*self._r(MENU_GLOW), tags=("lamp",))
        tx0, ty0, _, ty1 = self._r(m["tape"])
        cv.create_image(tx0, ty0, image=self._tape_photo, anchor="nw")
        self._tape_text = cv.create_text(tx0 + self.kp(11), (ty0 + ty1) // 2 + 1, anchor="w", text="",
                                         fill="#2B2219", font=self.font("type", 17, "bold"))
        self._nav = {}
        for name in ("back", "fwd"):  # ◀ назад и ▶ вперёд по операциям этого сеанса
            x0, y0, x1, y1 = self._r(m["nav"][name])
            cx, cy, s, d = (x0 + x1) // 2, (y0 + y1) // 2, self.kp(9), (-1 if name == "back" else 1)
            pts = (cx - d * s * 0.6, cy - s, cx + d * s * 0.9, cy, cx - d * s * 0.6, cy + s)
            self._nav[name] = cv.create_polygon(*pts, fill="#5C5248", outline="#14110E", tags=("lamp",))
        self.lamp_xy = {n: self._r(xy) for n, xy in m["lamps"].items()}
        self.lamp_xy["top"] = self._r(TOP_LAMP)
        self._top_halo = cv.create_image(*self.lamp_xy["top"], image=self._halo((255, 60, 30), 26, 0.7), tags=("lamp",))
        cv.create_image(*self.lamp_xy["top"], image=self._lamp_img("red", 0.55), tags=("lamp",))
        self._lamp_items = {}
        self._snd_item = cv.create_image(*self.lamp_xy["snd"], image=self._snd_frames[0], tags=("lamp",))
        self._snd_bulb = cv.create_image(*self.lamp_xy["snd"], tags=("lamp",))
        # поля
        self.msg = self._paper(TEXT["msg"], self.font("type", 17), "word")
        self.b32 = self._paper(TEXT["b32"], self.font("mono", 16), "char")
        self.morse = self._paper(TEXT["morse"], self.font("mono", 16, "bold"), "word")
        hl = "#EDB49C"  # передача: прозвучавшее — красным с подчёркиванием, текущий знак — фоном
        self.b32.tag_configure("sent", foreground="#B3160C", underline=True)
        self.b32.tag_configure("sending", foreground="#B3160C", background=hl, underline=True)
        self.morse.tag_configure("played", foreground="#B3160C", underline=True)
        self.morse.tag_configure("current", background=hl)
        x0, y0, x1, y1 = self._r(TEXT["status"])
        self.status = tk.Label(cv, text="", bg=self.paper, fg="#6B6052", font=self.font("sans", 13), anchor="w")
        cv.create_window(x0, y0, window=self.status, anchor="nw", width=x1 - x0, height=y1 - y0)
        x0, y0, x1, y1 = self._r(QR_CARD)
        self._qr_size = (x1 - x0, y1 - y0)
        self._card_photo = ImageTk.PhotoImage(self._bg.crop((x0, y0, x1, y1)))
        self.qr_cv = tk.Canvas(cv, width=x1 - x0, height=y1 - y0, bd=0, highlightthickness=0, bg=self.paper)
        cv.create_window(x0, y0, window=self.qr_cv, anchor="nw")
        self.qr_cv.bind("<Button-3>", self._qr_menu)
        self.qr_cv.bind("<Enter>", lambda e: setattr(self, "_over_qr", True))
        self.qr_cv.bind("<Leave>", lambda e: setattr(self, "_over_qr", False))
        # ключ: ротор, название, фраза
        self.mode, self.phrase, self.hex_var = tk.StringVar(value="list"), tk.StringVar(), tk.StringVar()
        x0, y0, x1, y1 = self._r(COMBO)
        self.phrase_entry = tk.Entry(cv, textvariable=self.phrase, bg=self.field_bg, fg=INK, insertbackground=INK,
                                     relief="flat", bd=0, highlightthickness=0, font=self.font("type", 17))
        self._entry_win = cv.create_window(x0 + self.kp(10), y0 + self.kp(5), window=self.phrase_entry, anchor="nw",
                                           width=x1 - x0 - self.kp(16), height=y1 - y0 - self.kp(10), state="hidden")
        self.phrase.trace_add("write", lambda *_: self.root.after_idle(self._phrase_changed))
        self.phrase_entry.bind("<Return>", self.encrypt)
        ri = self._rotor_imgs
        self.rotor = tk.Canvas(cv, width=ri["size"][0], height=ri["size"][1], bd=0, highlightthickness=0,
                               bg="#18140F", cursor="sb_v_double_arrow")
        self._rotor_win = cv.create_window(*self._r(ROTOR)[:2], window=self.rotor, anchor="nw")
        self.rotor.create_image(0, 0, image=ri["body"], anchor="nw")
        self._drums = []
        for i in range(2):
            dx = self.kp(5) + i * (ri["dw"] + self.kp(3))
            self.rotor.create_image(dx, self.kp(3), image=ri["drum"], anchor="nw")
            self._drums.append((dx + ri["dw"] // 2, self.kp(3) + ri["dh"] // 2))
        self.rotor.create_image(ri["size"][0] - self.kp(4), self.kp(2), image=ri["wheel"], anchor="ne")
        self._rolling = {}
        self._drum_items = [self.rotor.create_text(*c, text="", fill="#F3EBDD", font=self.font("cond", 24, "bold"))
                            for c in self._drums]
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.rotor.bind(seq, self._on_wheel)
            cv.bind(seq, self._on_wheel)
        self.rotor.bind("<Button-1>", lambda e: self._rotor_step(-1 if e.y < self.rotor.winfo_height() // 2 else 1))
        self.combo = KeyBox(self, getattr(getattr(self, "combo", None), "idx", self.auto_idx))
        # кнопки, которые общая логика перерисовывает сама
        self.sound_btn, self.sstv_btn, self.sstv_mode_btn = Proxy(self, "sound"), Proxy(self, "sstv"), Proxy(self, "sstv_mode")
        self.open_btn, self.lang_btn, self.menu_btn, self.help_btn = (Proxy(self, n) for n in ("open_qr", "lang", "menu", "help"))
        self._sstv_text, self._sstv_on, self._mode_text = T("Передать SSTV"), False, T("Модель SSTV")
        self.cmds = {
            "menu": self._main_menu, "lang": self._lang_menu, "help": self._help_menu, "min": self._minimize,
            "max": self._toggle_max, "close": self._on_close, "back": self.history_back, "fwd": self.history_forward,
            "clear_all": self.clear_all,
            "copy1": lambda: (self._flash("copy1"), self._copy(self.b32_get(), T("Шифровка скопирована"))),
            "paste": lambda: (self._flash("paste"), self.paste_cipher()),
            "rb_list": lambda: self._set_mode("list"), "rb_phrase": lambda: self._set_mode("phrase"),
            "combo": self._combo_open, "encrypt": lambda: (self._flash("encrypt", 1.1), self.encrypt()),
            "decrypt": lambda: (self._flash("decrypt", 1.1), self.decrypt_manual()), "sound": self.toggle_sound,
            "morse_save": lambda: (self._flash("mp3", 0.62, "orange"), self.save_morse_mp3()),
            "copy_morse": lambda: self._copy(self.morse_get(), T("Морзянка скопирована")),
            "morse_settings": self.show_morse_settings, "sstv_save": self.save_sstv_mp3, "sstv": self._sstv_click,
            "sstv_mode": self._sstv_menu, "save_qr": self.save_qr, "copy_qr": self.copy_qr, "open_qr": self._open_menu,
            "form_png": self.form_png, "form_doc": self.form_docx,
            "note": lambda: self.hex_var.get() and self._copy(self.hex_var.get(), T("HEX-ключ скопирован")),
        }
        self.hots = [(n, self._r(HOT[n])) for n in self.cmds]
        self._hover_name = self._pressed = self._drag = None
        cv.bind("<Motion>", self._on_motion)
        cv.bind("<Leave>", lambda e: self._hover(None))
        cv.bind("<ButtonPress-1>", self._on_press)
        cv.bind("<B1-Motion>", self._on_drag)
        cv.bind("<ButtonRelease-1>", self._on_release)
        cv.bind("<Double-Button-1>", self._on_double)
        for w, text in self._ph_texts().items():
            self._placeholder(w, text)
            self._placeholders[w][0].configure(font=self.font("type", 15), fg="#8C8172")
        for w in (self.msg, self.b32, self.morse, self.phrase_entry):
            w.bind("<Control-KeyPress>", self._qr_keys, add="+")
        self._draw_labels()
        self._draw_combo()
        self._sstv_buttons()
        self._on_mode()
        self._update_nav()
        self._bind_widgets()
        self._setup_dnd()
        self._schedule_qr_redraw()
        self._start_anim()
        cv.place(x=0, y=0)
        if old is not None:  # старое окно убираем только когда новое готово — без мигания
            old.destroy()
        if WIN and r.state() != "withdrawn":
            r.after(30, lambda: self._frameless(move=True))

    def _set_background(self):
        self._bg = self._compose(self._skin["ru" if i18n.lang() == "ru" else "clean"])
        self._bg_photo = ImageTk.PhotoImage(self._bg)
        self.cv.itemconfigure(self._bg_item, image=self._bg_photo)
        self._ov_cache = {}

    def _ph_texts(self):
        return {self.msg: T("Напишите сообщение и нажмите Enter. Расшифрованный текст тоже появляется здесь."),
                self.b32: TK("Здесь появится шифровка"), self.morse: TK("Морзянка появится"),
                self.phrase_entry: T("Введите ключ-фразу")}

    def _paper(self, rect, font, wrap):
        x0, y0, x1, y1 = self._r(rect)
        box, t = self._textbox(self.cv, font, wrap)
        box.configure(bg=self.paper)
        t.configure(bg=self.paper, fg=INK, insertbackground=INK, highlightthickness=0, padx=self.kp(6),
                    pady=self.kp(4), selectbackground="#E8B6A6", inactiveselectbackground="#E8B6A6")
        self.cv.create_window(x0, y0, window=box, anchor="nw", width=x1 - x0, height=y1 - y0)
        return t

    def _label(self, box, text, color, size, kind, tag="lab", anchor="center"):
        x0, y0, x1, y1 = self._r(box)
        lines = text.split("\n")
        weight = self.cond_weight if kind == "cond" else "normal"
        while size > 7:
            f = tkfont.Font(root=self.root, family=self.fam[kind], size=-self.kp(size), weight=weight)
            if max(f.measure(s) for s in lines) <= x1 - x0 - self.kp(2) and f.metrics("linespace") * len(lines) <= y1 - y0 + self.kp(6):
                break
            size -= 1
        x = x0 if anchor == "w" else (x0 + x1) // 2
        return self.cv.create_text(x, (y0 + y1) // 2, text=text, fill=color, font=self.font(kind, size),
                                   justify="left" if anchor == "w" else "center", anchor=anchor, tags=(tag,))

    def _draw_labels(self):
        """Все надписи, зависящие от языка (меняются на месте, без пересборки окна)."""
        cv, m = self.cv, self.meta
        cv.delete("lab")
        if i18n.lang() != "ru":
            for name, (text, color, size, kind) in _labels().items():
                self._label(m["labels"][name], text, color, size, kind, anchor="w" if name == "shift_note" else "center")
        lx0, ly0, lx1, ly1 = m["dynamic"]["lang"]
        self._label((lx0, ly0, lx1 + 8, ly1), T("Язык") + " ▾", CREAM, 18, "cond")
        self._label((975, 530, 1051, 573), T("Сохранить\nMorse.mp3"), INK, 13, "cond")
        self._tape_full = T("шифрование • передача • безопасность").upper()
        tx0, _, tx1, _ = self._r(m["tape"])
        size = 17
        while size > 9:
            f = tkfont.Font(root=self.root, family=self.fam["type"], size=-self.kp(size), weight="bold")
            if f.measure(self._tape_full) <= tx1 - tx0 - self.kp(24):
                break
            size -= 1
        cv.itemconfigure(self._tape_text, text="", font=self.font("type", size, "bold"))
        self._tape = {"phase": "type", "n": 0, "wait": 6}
        cv.tag_raise("lamp")

    def set_language(self, code):
        """Смена языка на месте: окно не пересобирается, поэтому ничего не мигает."""
        if code == i18n.lang():
            return
        self.stop_sound()
        self.stop_sstv()
        i18n.set_lang(code)
        self.prefs["lang"] = code
        self._save_prefs()
        self.root.title(T("Код Марса"))
        self._set_background()
        self._overlay(None, 1)
        self._hover_name = None
        self._draw_labels()
        for w, text in self._ph_texts().items():
            self._placeholders[w][0].configure(text=text)
        self._sstv_text, self._mode_text = T("Передать SSTV"), T("Модель SSTV")
        self._sstv_buttons()
        self._draw_note()
        self._draw_combo()
        self._set_status("")
        self._schedule_qr_redraw()
        for w in (self._help_win, self._settings_win, self._guide_win):
            try:
                if w is not None and w.winfo_exists():
                    w.destroy()
            except tk.TclError:
                pass
        self._help_win = self._settings_win = self._guide_win = None

    # ------------------------------------------------------------------ рисуемые части
    def _draw_combo(self):
        cv = getattr(self, "cv", None)
        if cv is None or not hasattr(self, "mode"):
            return
        cv.delete("combo")
        x0, y0, x1, y1 = self._r(COMBO)
        cv.create_text(self._r(ROTOR)[2] + self.kp(16), (y0 + y1) // 2, text=self._key_name(self.combo.current()),
                       anchor="w", fill=INK, font=self.font("type", 18), tags=("combo",),
                       state="hidden" if self.mode.get() == "phrase" else "normal")
        self._draw_rotor()

    def _rotor_chars(self, idx):
        if idx == 0:
            return "", self._key_name(0)[:1].upper()
        s = str(idx)
        return ("", s) if len(s) == 1 else (s[0], s[1])

    def _draw_rotor(self):
        """Цифры на барабанах; при прокрутке барабан проворачивается (быстрая прокрутка не сбивает счёт)."""
        new = self._rotor_chars(self.combo.current())
        d, self._rotor_dir = self._rotor_dir, 0
        for i in range(2):
            self._snap_drum(i)
            item = self._drum_items[i]
            if self.rotor.itemcget(item, "text") == new[i]:
                continue
            if not d:
                self.rotor.itemconfigure(item, text=new[i])
                continue
            cx, cy = self._drums[i]
            fresh = self.rotor.create_text(cx, cy + d * self._rotor_imgs["dh"], text=new[i], fill="#F3EBDD",
                                           font=self.font("cond", 24, "bold"))
            self._rolling[i] = {"old": item, "fresh": fresh, "step": 0, "d": d, "job": None}
            self._roll(i)

    def _roll(self, i):
        r = self._rolling.get(i)
        if not r:
            return
        try:
            dy = -r["d"] * self._rotor_imgs["dh"] / 5
            self.rotor.move(r["old"], 0, dy)
            self.rotor.move(r["fresh"], 0, dy)
        except tk.TclError:
            self._rolling.pop(i, None)
            return
        r["step"] += 1
        if r["step"] < 5:
            r["job"] = self.root.after(22, lambda: self._roll(i))
        else:
            self._snap_drum(i)

    def _snap_drum(self, i):
        r = self._rolling.pop(i, None)
        if not r:
            return
        try:
            if r["job"]:
                self.root.after_cancel(r["job"])
            self.rotor.delete(r["old"])
            self.rotor.coords(r["fresh"], *self._drums[i])
            self._drum_items[i] = r["fresh"]
        except tk.TclError:
            pass

    def _rotor_step(self, d):
        if self.mode.get() == "phrase":
            return
        self._rotor_dir = d
        self.combo.current((self.combo.current() + d) % len(core.BUILTIN_KEYS))

    def _on_wheel(self, e):
        if e.widget is self.cv:
            x0, y0, x1, y1 = self._r((40, 726, 626, 767))
            if not (x0 <= e.x < x1 and y0 <= e.y < y1):
                return
        up = getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4
        self._rotor_step(-1 if up else 1)
        return "break"

    def _draw_note(self):
        cv = self.cv
        cv.delete("note")
        x0, y0, x1, _ = self._r(NOTE)
        if self.mode.get() == "phrase":
            text = T("HEX-ключ:") + " " + self.hex_var.get() + "\n" + T("Щёлкните по строке HEX, чтобы скопировать ключ.")
            font = self.font("mono", 12)
        else:
            text, font = TK("Автокод"), self.font("sans", 13)
        cv.create_text(x0, y0, text=text, anchor="nw", width=x1 - x0, fill=NOTE_FG, font=font, tags=("note",))

    def _draw_sstv(self):
        cv = getattr(self, "cv", None)
        if cv is None:
            return
        cv.delete("sstvtxt")
        d = self.meta["dynamic"]
        on = self._sstv_on or self._sstv_active
        self._label(d["sstv"], self._sstv_text.upper(), CREAM if on else "#C7A39A", 21, "cond", tag="sstvtxt")
        self._label(d["sstv_mode"], self._mode_text, INK, 17, "cond", tag="sstvtxt")

    def _proxy(self, name, kw):
        if name == "sound" and "image" in kw:
            self.cv.itemconfigure(self._snd_item, image=kw["image"])
            lit = kw["image"] is not self._snd_frames[0]
            self.cv.itemconfigure(self._snd_bulb, image=self._lamp_img("orange", 0.62) if lit else "")
        elif name == "sstv":
            self._sstv_text = kw.get("text", self._sstv_text)
            if "state" in kw:
                self._sstv_on = kw["state"] != "disabled"
            self._draw_sstv()
        elif name == "sstv_mode" and "text" in kw:
            self._mode_text = kw["text"].replace("▾", "").strip()
            self._draw_sstv()

    def _set_lamp(self, name, kind, factor=1.0):
        if name in self._lamp_items:
            self.cv.delete(self._lamp_items.pop(name))
        if kind:
            self._lamp_items[name] = self.cv.create_image(*self.lamp_xy[name], image=self._lamp_img(kind, factor),
                                                          tags=("lamp",))

    def _flash(self, name, factor=0.78, kind="red", ms=None):
        """Лампа загорается после нажатия."""
        cv, xy = self.cv, self.lamp_xy[name]
        steady = name in ("copy1", "paste", "mp3")
        glow = (255, 160, 40) if kind == "orange" else (255, 80, 30)
        items = [cv.create_image(*xy, image=self._halo(glow, 30, 0.75), tags=("lamp",)),
                 cv.create_image(*xy, image=self._lamp_img(kind, factor, 1.0 if steady else 1.3), tags=("lamp",))]
        self.root.after(ms or (1200 if steady else 500), lambda: [cv.delete(i) for i in items])

    def _phrase_changed(self):
        try:
            self._update_hex()
            self._draw_note()
        except tk.TclError:
            pass

    def _set_mode(self, mode):
        self.mode.set(mode)
        self._on_mode()

    def _on_mode(self):
        phrase = self.mode.get() == "phrase"
        if not phrase:
            self.phrase.set("")
        self.cv.itemconfigure(self._entry_win, state="normal" if phrase else "hidden")
        self.cv.itemconfigure(self._rotor_win, state="hidden" if phrase else "normal")
        self.cv.itemconfigure("combo", state="hidden" if phrase else "normal")
        self._set_lamp("rb_list", "off" if phrase else None, 1.15)
        self._set_lamp("rb_phrase", "red" if phrase else None)
        self._draw_note()
        if phrase:
            self.phrase_entry.focus_set()

    def _update_nav(self):
        nav = getattr(self, "_nav", None)
        if not nav:
            return
        for name, ok in (("back", self.hpos > 0), ("fwd", self.hpos < len(self.history) - 1)):
            self.cv.itemconfigure(nav[name], fill="#FFE9C0" if ok else "#5C5248")

    def _sstv_click(self):
        if not self.sstv_mode:
            self.toast(T("Сначала выберите модель SSTV"), error=True)
            return
        self._flash("sstv", 1.0)
        self.toggle_sstv()

    def _redraw_qr(self):
        self._redraw_job = None
        cv = self.qr_cv
        try:
            w, h = self._qr_size
            cv.delete("all")
        except tk.TclError:
            return
        self._qr_box = None
        cv.create_image(0, 0, image=self._card_photo, anchor="nw")
        if self.qr_mat is not None:
            cap = self.kp(24)  # QR на всю карточку, подпись под ним
            size = min(w - self.kp(16), h - cap - self.kp(12))
            self._qr_photo = ImageTk.PhotoImage(core.qr_image(self.qr_mat, 1).resize((size, size), Image.NEAREST))
            qx, qy = (w - size) // 2, self.kp(8)
            cv.create_image(qx, qy, image=self._qr_photo, anchor="nw")
            self._qr_box = (qx, qy, qx + size, qy + size)
            cv.create_text(w // 2, qy + size + cap // 2 + self.kp(1), text=T("Ключ: {key}", key=self._key_label(self.cipher_kid)),
                           width=w - self.kp(30), font=self.font("type", 14), fill=INK)
        else:
            text = self._err(self.qr_err) if self.qr_err else T(
                "Здесь появится QR-код.\nЧтобы расшифровать картинку с QR, перетащите её в окно или нажмите «Открыть QR».")
            cv.create_text(w // 2, h // 2, text=text, width=w - self.kp(52), justify="center", font=self.font("sans", 13),
                           fill="#B00000" if self.qr_err else "#6E6253")
        self._sstv_overlay()

    # ------------------------------------------------------------------ меню
    def _menu(self, parent=None):
        m = marsmenu.MarsMenu(self, parent if isinstance(parent, marsmenu.MarsMenu) else None)
        m.mark, self._mark_next = getattr(self, "_mark_next", None), None
        return m

    def _menu_paper(self, w, h):
        return marsmenu.paper_for(self._skin["clean"], self._rs((60, 200, 600, 580)), (w, h))

    def _sstv_menu(self):
        self._mark_next = self.sstv_mode  # выбранная модель горит красной лампой
        super()._sstv_menu()

    def _popup_under(self, menu, widget):
        if isinstance(widget, Proxy):
            x0, y0, x1, y1 = self._r(HOT[widget.name])
            sx, sy = km.screen_xy(self.cv)
            if isinstance(menu, marsmenu.MarsMenu):
                menu.post(sx + x0, sy + y1, alt_x=sx + x1, alt_y=sy + y0)
            else:
                menu.tk_popup(sx + x0, sy + y1)
        else:
            super()._popup_under(menu, widget)

    def _help_menu(self):
        m = self._menu()
        m.add_command(label=T("Справка"), command=self.show_help)
        m.add_command(label=T("Руководство пользователя"), command=self.show_guide)
        self._popup_under(m, self.help_btn)

    def _main_menu(self):
        m = self._menu()
        m.add_command(label=T("Назад (Alt+←)"), command=self.history_back,
                      state="normal" if self.hpos > 0 else "disabled")
        m.add_command(label=T("Вперёд (Alt+→)"), command=self.history_forward,
                      state="normal" if self.hpos < len(self.history) - 1 else "disabled")
        m.add_separator()
        m.add_command(label=T("Поделиться: показывать в меню"), state="disabled")
        self._menu_vars = []
        for key, name in km.SHARE_APPS:
            var = tk.BooleanVar(value=self.prefs["share"].get(key, True))
            self._menu_vars.append(var)
            m.add_checkbutton(label=name, variable=var, command=lambda k=key, v=var: self._toggle_share(k, v.get()))
        m.add_separator()
        m.add_command(label=T("Открыть папку «Код Марса»"), command=lambda: km.open_folder(km.output_dir()))
        m.add_command(label=T("Справка"), command=self.show_help)
        m.add_command(label=T("Руководство пользователя"), command=self.show_guide)
        self._popup_under(m, self.menu_btn)

    def _combo_open(self):
        """Все ключи сразу — четыре столбца, выбранный горит красной лампой."""
        if self.mode.get() == "phrase":
            return
        m = marsmenu.MarsMenu(self, columns=4)
        var = tk.IntVar(value=self.combo.current())
        for i in range(len(core.BUILTIN_KEYS)):
            m.add_radiobutton(label=self._key_name(i), value=i, variable=var,
                              command=lambda: self.combo.current(var.get()))
        x0, y0, x1, y1 = self._r((40, 726, 626, 767))
        sx, sy = km.screen_xy(self.cv)
        m.post(sx + x0, sy + y1, alt_x=sx + x1, alt_y=sy + y0)

    # ------------------------------------------------------------------ мышь
    def _hit(self, x, y):
        for name, (x0, y0, x1, y1) in self.hots:
            if x0 <= x < x1 and y0 <= y < y1:
                if name == "note" and self.mode.get() != "phrase":
                    continue
                return name
        return None

    def _overlay(self, name, factor):
        cv = self.cv
        cv.delete("ov")
        if name in (None, "note"):
            return
        rect = dict(self.hots)[name]
        key = (name, factor)
        if key not in self._ov_cache:
            self._ov_cache[key] = ImageTk.PhotoImage(ImageEnhance.Brightness(self._bg.crop(rect)).enhance(factor))
        cv.create_image(rect[0], rect[1], image=self._ov_cache[key], anchor="nw", tags=("ov",))
        for tag in ("lab", "dyn", "combo", "note", "sstvtxt", "lamp"):
            cv.tag_raise(tag)

    def _hover(self, name):
        if name != self._hover_name:
            self._hover_name = name
            self._overlay(name, 1.13)
            glow = self._halo((255, 214, 120), 52, 0.6) if name == "menu" else ""
            self.cv.itemconfigure(self._menu_glow, image=glow)  # «≡» мягко светится жёлтым
        self.cv.configure(cursor="hand2" if name else "")

    def _edge_at(self, x, y):
        e = self.kp(EDGE)
        v = "n" if y < e else "s" if y >= self.CH - e else ""
        h = "w" if x < e else "e" if x >= self.CW - e else ""
        return (v + h) or None

    def _on_motion(self, e):
        if self._pressed or self._resize:
            return
        self._edge = self._edge_at(e.x, e.y)
        if self._edge:
            self._hover(None)
            self.cv.configure(cursor=CURSORS.get(self._edge, "fleur"))
            return
        self._hover(self._hit(e.x, e.y))

    def _on_press(self, e):
        if self._edge:
            self._start_resize(e)
            return
        self._pressed = self._hit(e.x, e.y)
        if self._pressed:
            self._overlay(self._pressed, 0.82)
        elif e.y < self._r((0, 0, 0, 100))[3] and not self._maxed:
            if WIN:  # окно тащит сама Windows, как за обычный заголовок
                try:
                    import ctypes
                    u = ctypes.windll.user32
                    u.ReleaseCapture()
                    u.SendMessageW(self._hwnd(), 0x00A1, 2, 0)
                    return
                except Exception:
                    pass
            self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _on_drag(self, e):
        if self._resize:
            self._resize_move(e)
        elif self._drag:
            self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _on_release(self, e):
        if self._resize:
            self._finish_resize()
            return
        name, self._pressed, self._drag = self._pressed, None, None
        self._hover_name = None
        self._overlay(None, 1)
        if name and self._hit(e.x, e.y) == name:
            self.cmds[name]()
        if getattr(self, "cv", None) is not None and self.cv.winfo_exists():
            self._hover(self._hit(e.x, e.y))

    def _on_double(self, e):
        if e.y < self._r((0, 0, 0, 100))[3] and not self._hit(e.x, e.y) and not self._edge:
            self._toggle_max()

    def _qr_keys(self, e):
        """Курсор над QR-кодом: Ctrl+C копирует QR, Ctrl+V берёт QR из буфера обмена."""
        if not self._over_qr:
            return None
        if e.keycode == 67 or e.keysym in ("c", "C", "Cyrillic_es", "Cyrillic_ES"):
            self.copy_qr()
            return "break"
        if e.keycode == 86 or e.keysym in ("v", "V", "Cyrillic_em", "Cyrillic_EM"):
            self.qr_from_clipboard()
            return "break"
        return None

    # ------------------------------------------------------------------ размер окна
    def _hwnd(self):
        import ctypes
        return ctypes.windll.user32.GetParent(self.root.winfo_id())

    def _win_rect(self):
        if WIN:
            try:
                import ctypes
                from ctypes import wintypes
                r = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(self._hwnd(), ctypes.byref(r))
                return r.left, r.top, r.right - r.left, r.bottom - r.top
            except Exception:
                pass
        return self.root.winfo_x(), self.root.winfo_y(), self.CW, self.CH

    def _start_resize(self, e):
        x, y, w, h = self._win_rect()
        self._resize = (self._edge, e.x_root, e.y_root, x, y, w, h, None)
        band = self._band = tk.Toplevel(self.root)
        band.overrideredirect(True)
        band.configure(bg="#E2B653")
        try:
            band.attributes("-alpha", 0.3)
            band.attributes("-topmost", True)
        except tk.TclError:
            pass
        band.geometry(f"{w}x{h}+{x}+{y}")

    def _resize_move(self, e):
        """Тянем за край или угол — окно меняется строго пропорционально."""
        edge, sx, sy, x, y, w, h, _ = self._resize
        dx, dy = e.x_root - sx, e.y_root - sy
        nw = w + (dx if "e" in edge else -dx if "w" in edge else 0)
        nh = h + (dy if "s" in edge else -dy if "n" in edge else 0)
        k0 = min(w / W0, h / H0)
        k = (nh / h * k0) if edge in ("n", "s") else (nw / w * k0) if edge in ("e", "w") else max(nw / w, nh / h) * k0
        _, _, ww, wh = self._work_area()
        k = max(0.5, min(k, ww / W0, wh / H0))
        cw, ch = round(W0 * k), round(H0 * k)
        nx = x + w - cw if "w" in edge else x
        ny = y + h - ch if "n" in edge else y
        self._resize = (edge, sx, sy, x, y, w, h, (k, nx, ny))
        self._band.geometry(f"{cw}x{ch}+{nx}+{ny}")

    def _finish_resize(self):
        target = self._resize[7]
        self._resize = None
        if self._band is not None:
            self._band.destroy()
            self._band = None
        if target:
            k, x, y = target
            self._maxed, self._k_normal, self._win_xy = False, k, (x, y)
            self._rebuild_view()

    def _toggle_max(self):
        if not self._maxed:
            x, y, _, _ = self._win_rect()
            self._win_xy = (x, y)
        self._maxed = not self._maxed
        self._rebuild_view()

    def _rebuild_view(self):
        """Новый масштаб: окно собирается заново поверх старого, потом старое убирается."""
        st = (self.msg_get(), self.b32_get(), self.morse_get(), self.mode.get(), self.phrase.get(),
              self.combo.current(), self._morse_src, self.status.cget("text"), self._status_err)
        self.stop_sound()
        self.stop_sstv()
        self._make_fonts()
        self._build()
        msg, b32, mrs, mode, phrase, idx, src, status, err = st
        self.mode.set(mode)
        self._on_mode()
        self.phrase.set(phrase)
        self.combo.current(idx)
        self._set(self.msg, msg)
        self._set_b32(b32)
        self._set_morse(mrs, src=src)
        self._set_status(status, error=err)
        self._update_drag_source()
        self._schedule_qr_redraw()

    def after_show(self):
        """Под Windows убираем системную рамку, но окно остаётся обычным: значок на панели задач,
        Alt+Tab, сворачивание и разворачивание щелчком по значку."""
        if not WIN:
            return
        self._frameless(move=True)
        self.root.after(80, lambda: self.root.attributes("-alpha", 1.0))
        self.root.bind("<Map>", lambda e: e.widget is self.root and self.root.after(40, self._frameless), add="+")

    def _frameless(self, move=False):
        if not WIN:
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            hwnd = self._hwnd()
            if not hwnd:
                return
            st = u.GetWindowLongW(hwnd, -16)
            new = (st & ~(0x00C00000 | 0x00040000 | 0x00010000)) | 0x00080000 | 0x00020000
            if new != st:
                u.SetWindowLongW(hwnd, -16, new)
            ex = u.GetWindowLongW(hwnd, -20)
            u.SetWindowLongW(hwnd, -20, (ex & ~0x00000080) | 0x00040000)
            x, y = self.win
            flags = 0x0004 | 0x0010 | 0x0020 | (0 if move else 0x0002)
            u.SetWindowPos(hwnd, 0, x, y, self.CW, self.CH, flags)
        except Exception:  # оформление важнее рамки
            pass

    def _minimize(self):
        r = self.root
        if WIN:
            r.iconify()
            return
        r.overrideredirect(False)
        r.iconify()

        def back(_e=None):
            if r.state() == "normal":
                r.unbind("<Map>")
                r.overrideredirect(True)

        r.bind("<Map>", back)

    # ------------------------------------------------------------------ анимации
    def _start_anim(self):
        self._tick = self._frame = 0
        self._glint_i, self._next_glint = None, time.time() + random.uniform(4, 8)
        self._anim()

    def _stop_anim(self):
        if self._anim_job:
            try:
                self.root.after_cancel(self._anim_job)
            except tk.TclError:
                pass
        self._anim_job = None

    def _anim(self):
        self._anim_job = None
        cv = getattr(self, "cv", None)
        if cv is None or not cv.winfo_exists():
            return
        self._tick += 1
        if self._tick % 3 == 0:  # Марс поворачивается, волны идут от вышек, лампа мерцает
            self._frame = (self._frame + 1) % FRAMES
            cv.itemconfigure(self._icon_item, image=self._icon_frames[self._frame])
            cv.itemconfigure(self._poster_item, image=self._poster_frames[self._frame])
            cv.itemconfigure(self._top_halo, image=self._halo((255, 60, 30), 26, random.choice((0.55, 0.64, 0.72, 0.8, 0.88))))
        self._tape_step()
        now = time.time()
        if self._glint_i is None and now >= self._next_glint:
            self._glint_i = 0
        if self._glint_i is not None:  # звезда вспыхивает раз в 10–15 секунд
            n = 40
            lvl = math.sin(math.pi * self._glint_i / n)
            cv.itemconfigure(self._glint_item, image=self._glint(round(max(0.1, lvl), 1)) if lvl > 0.05 else "")
            self._glint_i += 1
            if self._glint_i > n:
                self._glint_i, self._next_glint = None, now + random.uniform(10, 15)
                cv.itemconfigure(self._glint_item, image="")
        self._anim_job = self.root.after(40, self._anim)

    def _tape_step(self):
        """Девиз печатается на ленте по букве, потом стирается и печатается снова."""
        s, full = self._tape, self._tape_full
        if s["wait"] > 0:
            s["wait"] -= 1
            return
        if s["phase"] == "type":
            s["n"] += 1
            self.cv.itemconfigure(self._tape_text, text=full[:s["n"]])
            s["wait"] = 0 if full[s["n"] - 1:s["n"]] == " " else 1
            if s["n"] >= len(full):
                s["phase"], s["wait"] = "erase", 62
        else:
            s["n"] -= 1
            gone = len(full) - s["n"]
            self.cv.itemconfigure(self._tape_text, text=" " * gone + full[gone:])
            if s["n"] <= 0:
                s["phase"], s["wait"], s["n"] = "type", 18, 0

    def _on_close(self):
        self._stop_anim()
        super()._on_close()
