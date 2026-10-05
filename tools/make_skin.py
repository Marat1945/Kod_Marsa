# -*- coding: utf-8 -*-
"""Сборка «шкуры» окна из макета mockup2.png (numpy + opencv, только для разработчика)."""
import json, math, os
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFilter
A = "/home/claude/kod-marsa-exe/assets"
src = cv2.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockup.png"))
rng = np.random.default_rng(1945)
LABELS = {"title": ((222, 30, 472, 88), "light"), "help": ((1388, 44, 1462, 76), "light"),
          "msg_plate": ((52, 124, 206, 152), "dark"), "clear_all": ((500, 124, 622, 152), "light"),
          "b32_plate": ((704, 121, 924, 152), "dark"), "copy1": ((1074, 128, 1152, 150), "light"),
          "paste": ((1216, 128, 1278, 150), "light"), "morse_plate": ((690, 534, 850, 566), "dark"),
          "morse_save": ((950, 533, 1042, 571), "dark"), "copy_morse": ((1072, 536, 1164, 564), "light"),
          "morse_settings": ((1190, 533, 1300, 571), "dark"), "key_plate": ((48, 678, 138, 707), "dark"),
          "rb_list": ((212, 681, 322, 705), "light"), "rb_phrase": ((394, 681, 490, 705), "light"),
          "encrypt": ((112, 838, 292, 886), "light"), "decrypt": ((428, 838, 614, 886), "dark"),
          "shift_note": ((36, 620, 600, 645), "light"), "sstv_save": ((1420, 693, 1578, 721), "dark"),
          "save_qr": ((1344, 797, 1433, 825), "dark"), "copy_qr": ((1452, 797, 1549, 825), "dark"),
          "open_qr": ((1566, 797, 1649, 825), "dark"), "form_png": ((1346, 847, 1489, 897), "dark"),
          "form_doc": ((1504, 847, 1649, 897), "dark")}
DYNAMIC = {"tagline": ((540, 40, 1030, 80), "light"), "lang": ((1280, 44, 1354, 76), "light"),
           "combo_text": ((46, 732, 330, 762), "dark"), "note": ((36, 768, 600, 816), "light"),
           "sstv": ((1384, 742, 1508, 773), "light"), "sstv_mode": ((1548, 742, 1626, 774), "dark"),
           "qr": ((1404, 438, 1596, 634), "all"), "qr_caption": ((1450, 637, 1560, 665), "dark"),
           "text_msg": ((40, 176, 626, 600), "dark"), "text_b32": ((684, 176, 1300, 486), "dark"),
           "text_morse": ((684, 592, 1300, 900), "dark")}

def mask_for(img, box, kind):
    x0, y0, x1, y1 = box
    m = np.zeros(img.shape[:2], np.uint8)
    if kind == "all":
        m[y0:y1, x0:x1] = 255
        return m
    lum = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(np.float32)
    med = float(np.median(lum))
    sub = (lum < med - 38) if kind == "dark" else (lum > med + 38)
    if y1 - y0 > 150:
        for cy in (0, sub.shape[0] - 18):
            for cx in (0, sub.shape[1] - 18):
                sub[cy:cy + 18, cx:cx + 18] = False
    m[y0:y1, x0:x1] = sub.astype(np.uint8) * 255
    return cv2.dilate(m, np.ones((5, 5), np.uint8))

def clean(img, regions):
    m = np.zeros(img.shape[:2], np.uint8)
    for box, kind in regions:
        m |= mask_for(img, box, kind)
    out = cv2.inpaint(img, m, 5, cv2.INPAINT_TELEA).astype(np.float32)
    sel = m > 0
    out[sel] = np.clip(out[sel] + rng.normal(0, 4.0, out.shape)[sel], 0, 255)
    return out.astype(np.uint8)

skin = clean(src, DYNAMIC.values())
skin_clean = clean(skin, LABELS.values())
cv2.imwrite(f"{A}/skin.jpg", skin, [cv2.IMWRITE_JPEG_QUALITY, 92])
cv2.imwrite(f"{A}/skin_clean.jpg", skin_clean, [cv2.IMWRITE_JPEG_QUALITY, 92])

def lit_center(cx, cy, w=30):
    sub = src[cy - w:cy + w, cx - w:cx + w].astype(int)
    m = (sub[..., 2] > 200) & (sub[..., 1] > 90) & (sub[..., 0] < 150)
    ys, xs = np.nonzero(m)
    return [int(xs.mean()) + cx - w, int(ys.mean()) + cy - w] if len(xs) > 8 else [cx, cy]

def knob_center(cx, cy, w=30):
    g = cv2.medianBlur(cv2.cvtColor(src[cy - w:cy + w, cx - w:cx + w], cv2.COLOR_BGR2GRAY), 3)
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, 1, 20, param1=80, param2=14, minRadius=8, maxRadius=22)
    if c is None:
        return [cx, cy]
    x, y, _ = min(c[0], key=lambda q: (q[0] - w) ** 2 + (q[1] - w) ** 2)
    return [int(x) + cx - w, int(y) + cy - w]

lamps = {n: lit_center(*p) for n, p in {"rb_list": (189, 691), "morse": (879, 550), "encrypt": (78, 861),
                                         "decrypt": (385, 861), "sstv": (1364, 757)}.items()}
lamps.update({n: knob_center(*p) for n, p in {"rb_phrase": (370, 691), "copy1": (1052, 138), "paste": (1194, 138),
                                               "speaker": (927, 550)}.items()})

def sprite(c, size=46, rad=20):
    x, y = c
    crop = cv2.cvtColor(skin[y - size // 2:y + size // 2, x - size // 2:x + size // 2], cv2.COLOR_BGR2RGB)
    a = np.zeros((size, size), np.float32)
    cv2.circle(a, (size // 2, size // 2), rad - 3, 1.0, -1)
    a = cv2.GaussianBlur(a, (0, 0), 2.2)
    return Image.fromarray(np.dstack([crop, (a * 255).astype(np.uint8)]), "RGBA")
sprite(lamps["rb_list"]).save(f"{A}/lamp_red.png")
sprite(lamps["morse"]).save(f"{A}/lamp_orange.png")
sprite(lamps["rb_phrase"], rad=19).save(f"{A}/lamp_off.png")

def animate(region, guess, ymax, tip_hint, name, ring_rgb, spacing, reach):
    """Кадры: поверхность планеты вращается, от вершины вышки расходятся волны."""
    x0, y0, x1, y1 = region
    art = skin[y0:y1, x0:x1].astype(np.float32)
    b, g, r = art[..., 0], art[..., 1], art[..., 2]
    lum = 0.114 * b + 0.587 * g + 0.299 * r
    H, W = lum.shape
    yy, xx = np.mgrid[0:H, 0:W]
    tower = (lum < 50) & ((r - g) < 30)
    gcx, gcy, gR = guess[0] - x0, guess[1] - y0, guess[2]
    sm = cv2.GaussianBlur(lum, (0, 0), 1.2)
    pts = []
    for x in range(W):  # край диска: самый резкий переход «небо → планета» рядом с приближением
        if abs(x - gcx) >= gR * 0.97:
            continue
        yg = gcy - math.sqrt(gR * gR - (x - gcx) ** 2)
        lo_, hi_ = int(max(2, yg - 14)), int(min(H - 3, yg + 14))
        if hi_ <= lo_ or tower[lo_:hi_, x].any():
            continue
        grad = sm[lo_ + 2:hi_ + 2, x] - sm[lo_ - 2:hi_ - 2, x]
        pts.append((x, lo_ + int(np.argmax(grad))))
    pts = np.array(pts, np.float64)
    Mx = np.c_[pts[:, 0], pts[:, 1], np.ones(len(pts))]
    D, E, F = np.linalg.lstsq(Mx, -(pts[:, 0] ** 2 + pts[:, 1] ** 2), rcond=None)[0]
    cx, cy = -D / 2, -E / 2
    R = math.sqrt(max(1.0, cx * cx + cy * cy - F))
    if abs(R - gR) > gR * 0.35:  # подгонка не удалась — берём приближение
        cx, cy, R = gcx, gcy, gR
    planet = ((xx - cx) ** 2 + (yy - cy) ** 2 < (R - 1.5) ** 2) & (yy < ymax - y0)
    dx, dy = (xx - cx) / R, (yy - cy) / R
    keep = ~cv2.dilate(tower.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    inside = planet & keep
    planet = planet.astype(np.uint8)
    z = np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))
    lon = np.degrees(np.arctan2(dx, z))
    lat = np.degrees(np.arcsin(np.clip(-dy, -1, 1)))
    wgt = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 6) + 1e-3
    shade = np.clip(cv2.GaussianBlur(lum * inside, (0, 0), 6) / wgt, 20, 255)
    albedo = art / shade[..., None]
    lat_min = float(lat[inside].min()) if inside.any() else 0.0
    NLAT, NLON = 96, 720  # бесшовная поверхность в цветах самой планеты: пятна и кратеры
    deep = inside & (z > 0.4)
    alb = albedo[deep] if deep.sum() > 50 else albedo[inside]
    order = np.argsort(alb.mean(axis=1))
    dark, light = alb[order[int(len(order) * 0.12)]], alb[order[int(len(order) * 0.88)]]
    g2 = np.random.default_rng(7)
    acc = np.zeros((NLAT, NLON * 3), np.float32)
    for cols, amp in ((6, 1.0), (12, 0.55), (24, 0.3), (48, 0.16), (96, 0.08)):
        rows = max(3, int(cols * NLAT / NLON * 2) + 2)
        coarse = g2.random((rows, cols)).astype(np.float32)
        acc += amp * cv2.resize(np.tile(coarse, (1, 3)), (NLON * 3, NLAT), interpolation=cv2.INTER_CUBIC)
    crater = np.zeros_like(acc)
    for _ in range(80):
        x_, y_, rr = int(g2.integers(0, NLON)), int(g2.integers(0, NLAT)), int(g2.integers(2, 11))
        for off in (0, NLON, 2 * NLON):
            cv2.circle(crater, (x_ + off, y_), rr, -0.45, -1, cv2.LINE_AA)
            cv2.circle(crater, (x_ + off, y_ - 1), rr, 0.18, 1, cv2.LINE_AA)
    acc = (acc + cv2.GaussianBlur(crater, (0, 0), 0.8))[:, NLON:2 * NLON]
    acc = (acc - acc.min()) / (np.ptp(acc) + 1e-6)
    tex = (dark[None, None, :] + (light - dark)[None, None, :] * acc[..., None]).astype(np.float32)
    mapy = np.clip((lat - lat_min) / max(1e-3, 90 - lat_min) * NLAT - 0.5, 0, NLAT - 1).astype(np.float32)
    tx, ty = tip_hint
    win = lum[max(0, ty - y0 - 14):ty - y0 + 14, max(0, tx - x0 - 14):tx - x0 + 14]
    if win.size:
        py, px = np.unravel_index(np.argmax(win), win.shape)
        tx, ty = tx - 14 + px if tx - x0 >= 14 else x0 + px, ty - 14 + py if ty - y0 >= 14 else y0 + py
    sky = (~(planet > 0)) & (lum < 110)
    soft = np.zeros((H, W), np.float32)
    cv2.rectangle(soft, (6, 6), (W - 7, H - 7), 1.0, -1)
    soft = cv2.GaussianBlur(soft, (0, 0), 4) * sky
    frames = []
    for f in range(48):
        ph = 360.0 * f / 48
        mapx = (((lon + ph + 180) / 360 * NLON) % NLON).astype(np.float32)
        new = art.copy()
        samp = cv2.remap(tex, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        alpha = (np.clip((z - 0.22) / 0.22, 0, 1) * inside)[..., None]  # край с ореолом остаётся нарисованным
        new = art * (1 - alpha) + np.clip(samp * shade[..., None], 0, 255) * alpha
        rings = np.zeros((H * 2, W * 2), np.float32)
        for k in range(5):
            rad = ((f % 24) / 24.0 + k) * spacing
            a = max(0.0, 1.0 - rad / reach)
            if rad > 2:
                cv2.circle(rings, (int((tx - x0) * 2), int((ty - y0) * 2)), int(rad * 2), a, 3, cv2.LINE_AA)
        rings = cv2.GaussianBlur(cv2.resize(rings, (W, H), interpolation=cv2.INTER_AREA), (0, 0), 0.7) * soft
        col = np.array(ring_rgb[::-1], np.float32)
        new = new * (1 - rings[..., None] * 0.8) + col * rings[..., None] * 0.8
        frames.append(np.clip(new, 0, 255).astype(np.uint8))
    cv2.imwrite(f"{A}/{name}.jpg", np.vstack(frames), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"region": list(region), "tip": [int(tx), int(ty)], "planet": [round(cx + x0, 1), round(cy + y0, 1), round(R, 1)]}

icon = animate((107, 14, 201, 98), (153, 81, 35), 80, (153, 25), "icon_frames", (255, 170, 90), 9, 40)
poster = animate((1356, 112, 1644, 428), (1500, 508, 200), 430, (1496, 276), "poster_frames", (255, 205, 150), 22, 130)

tx0, ty0, tx1, ty1 = 548, 46, 1022, 74
tw, th = tx1 - tx0, ty1 - ty0
tape = Image.new("RGBA", (tw, th + 4), (0, 0, 0, 0))
top = [(0, 3)] + [(x, 3 + int(rng.integers(-1, 2))) for x in range(6, tw - 6, 6)] + [(tw - 1, 3)]
bot = [(tw - 1, th - 1)] + [(x, th - 1 + int(rng.integers(-1, 2))) for x in range(tw - 6, 6, -6)] + [(0, th - 1)]
shadow = Image.new("RGBA", tape.size, (0, 0, 0, 0))
ImageDraw.Draw(shadow).polygon([(x, y + 3) for x, y in top + bot], fill=(0, 0, 0, 130))
tape.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2)))
ImageDraw.Draw(tape).polygon(top + bot, fill=(232, 222, 198, 255))
arr = np.array(tape).astype(np.int16)
sel = arr[..., 3] == 255
noise = rng.normal(0, 6, arr.shape[:2]).astype(np.int16)
for c in range(3):
    arr[..., c][sel] = np.clip(arr[..., c][sel] + noise[sel], 0, 255)
Image.fromarray(arr.astype(np.uint8), "RGBA").save(f"{A}/tape.png")
json.dump({"lamps": lamps, "icon": icon, "poster": poster, "tape": [tx0, ty0, tx1, ty1],
           "labels": {k: v[0] for k, v in LABELS.items()}, "dynamic": {k: v[0] for k, v in DYNAMIC.items()}},
          open(f"{A}/skin.json", "w"), ensure_ascii=False)
print("лампы:", lamps); print("иконка:", icon); print("плакат:", poster)
