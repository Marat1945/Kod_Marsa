# -*- coding: utf-8 -*-
"""Доработка «шкуры» после make_skin.py (запускать сразу после него):
1) в строке «Азбука Морзе» две целые таблички с лампами — звук (лампа + динамик) и «Сохранить Morse.mp3»;
2) в шапке левее телеграфной ленты две таблички «назад» и «вперёд»; лента стала короче."""
import json
import os

from PIL import Image, ImageDraw, ImageFilter

T = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(os.path.dirname(T), "assets")
mock = Image.open(os.path.join(T, "mockup.png")).convert("RGB")
skin = Image.open(os.path.join(A, "skin.jpg")).convert("RGB")
clean = Image.open(os.path.join(A, "skin_clean.jpg")).convert("RGB")
off = Image.open(os.path.join(A, "lamp_off.png")).convert("RGBA")


def circle_crop(img, cx, cy, r):
    c = img.crop((cx - r, cy - r, cx + r, cy + r)).convert("RGBA")
    a = Image.new("L", c.size, 0)
    ImageDraw.Draw(a).ellipse((1, 1, 2 * r - 1, 2 * r - 1), fill=255)
    c.putalpha(a.filter(ImageFilter.GaussianBlur(1.0)))
    return c


def three_slice(src, cap, mid_box, w, h):
    """Табличка нужной ширины: края с винтами не растягиваются."""
    src = src.resize((src.width, h), Image.LANCZOS) if src.height != h else src
    right = src.crop((src.width - cap, 0, src.width, h))
    left = right.transpose(Image.FLIP_LEFT_RIGHT)
    mid = src.crop((mid_box[0], 0, mid_box[1], h)).resize((w - 2 * cap, h), Image.LANCZOS)
    out = Image.new("RGB", (w, h))
    out.paste(left, (0, 0))
    out.paste(mid, (cap, 0))
    out.paste(right, (w - cap, 0))
    return out


speaker = circle_crop(mock, 923, 551, 16)
gap = clean.crop((1052, 524, 1064, 579))                 # металл между табличками
beige = clean.crop((899, 527, 1051, 576))                # целая табличка, надпись стёрта
dark = clean.crop((1376, 34, 1494, 86))                  # тёмная табличка шапки («Справка»), надпись стёрта
lamp = off.resize((30, 30), Image.LANCZOS)
plates = {"snd": (864, 527, 934, 576), "mp3": (940, 527, 1054, 576)}
nav = {"back": (474, 38, 532, 82), "fwd": (536, 38, 594, 82)}
for img in (skin, clean):
    for x in range(858, 1058, gap.width):
        img.paste(gap.crop((0, 0, min(gap.width, 1058 - x), gap.height)), (x, 524))
    for name, (x0, y0, x1, y1) in plates.items():
        img.paste(three_slice(beige, 16, (56, 136), x1 - x0, y1 - y0), (x0, y0))
    img.paste(lamp, (884 - 15, 551 - 15), lamp)
    img.paste(lamp, (958 - 15, 551 - 15), lamp)
    img.paste(speaker, (914 - 16, 551 - 16), speaker)
    for x0, y0, x1, y1 in nav.values():
        img.paste(three_slice(dark, 18, (26, 80), x1 - x0, y1 - y0), (x0, y0))
skin.save(os.path.join(A, "skin.jpg"), quality=92)
clean.save(os.path.join(A, "skin_clean.jpg"), quality=92)
tape = Image.open(os.path.join(A, "tape.png")).convert("RGBA")
tape.resize((422, tape.height), Image.LANCZOS).save(os.path.join(A, "tape.png"))
meta_path = os.path.join(A, "skin.json")
with open(meta_path, encoding="utf-8") as fh:
    meta = json.load(fh)
meta["tape"] = [602, 46, 1024, 74]
meta["nav"] = {k: list(v) for k, v in nav.items()}
meta["plates"] = {k: list(v) for k, v in plates.items()}
meta["lamps"].update(snd=[884, 551], mp3=[958, 551])
with open(meta_path, "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False)
print("шкура доработана: таблички звука и MP3, «назад»/«вперёд», лента")
