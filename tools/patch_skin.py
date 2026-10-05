# -*- coding: utf-8 -*-
"""Доработка «шкуры» после make_skin.py: в строке «Азбука Морзе» две отдельные кнопки с лампами —
звук (лампа + динамик) и «Сохранить Morse.mp3» (лампа + надпись, которую рисует программа).
Запускать один раз после make_skin.py."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
skin = Image.open(os.path.join(A, "skin.jpg")).convert("RGB")
clean = Image.open(os.path.join(A, "skin_clean.jpg")).convert("RGB")
off = Image.open(os.path.join(A, "lamp_off.png")).convert("RGBA")


def circle_crop(img, cx, cy, r):
    c = img.crop((cx - r, cy - r, cx + r, cy + r)).convert("RGBA")
    a = Image.new("L", c.size, 0)
    ImageDraw.Draw(a).ellipse((1, 1, 2 * r - 1, 2 * r - 1), fill=255)
    c.putalpha(a.filter(ImageFilter.GaussianBlur(1.2)))
    return c


speaker = circle_crop(skin, 921, 548, 17)      # динамик с прежней таблички
metal = clean.crop((945, 112, 1030, 162))      # металл из строки «Шифровка Base32»
plate = clean.crop((1186, 528, 1303, 574))     # табличка «Настройка» без надписи


def plate_of(width):
    cap = 14
    mid = plate.crop((cap, 0, plate.width - cap, plate.height)).resize((width - 2 * cap, plate.height))
    out = Image.new("RGB", (width, plate.height))
    out.paste(plate.crop((0, 0, cap, plate.height)), (0, 0))
    out.paste(mid, (cap, 0))
    out.paste(plate.crop((plate.width - cap, 0, plate.width, plate.height)), (width - cap, 0))
    return out


lamp = off.resize((30, 30), Image.LANCZOS)
for img, name in ((skin, "skin.jpg"), (clean, "skin_clean.jpg")):
    for x in range(862, 1062, metal.width):
        img.paste(metal.crop((0, 0, min(metal.width, 1062 - x), metal.height)), (x, 526))
    img.paste(plate_of(70), (864, 528))
    img.paste(plate_of(122), (938, 528))
    img.paste(lamp, (882 - 15, 551 - 15), lamp)
    img.paste(lamp, (957 - 15, 551 - 15), lamp)
    img.paste(speaker, (913 - 17, 551 - 17), speaker)
    img.save(os.path.join(A, name), quality=92)
print("строка «Азбука Морзе»: две кнопки с лампами")
