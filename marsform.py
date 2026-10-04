# -*- coding: utf-8 -*-
"""
Бланк «ШИФРОВКА» для «Кода Марса».

* PNG — по картинке на лист: QR-код, номер вида 041026/001, дата, ключ,
  шифровка группами по 5 знаков с номером над каждой группой.
* Word (.docx) — те же листы; номер, дата, ключ, шифровка и пустые поля
  бланка можно править. Промежутки между группами сделаны разрядкой,
  а не пробелами, поэтому скопированная шифровка идёт без пробелов.
"""
from __future__ import annotations

import datetime as _dt
import io
import math
import zipfile
from xml.sax.saxutils import escape

import marscore as core

FORM_W, FORM_H = 2528, 3416
QR_BOX = (68, 1666, 632, 2229)
KEY_FIELD = (72, 2342, 590)          # x, середина по высоте, правый край
NUMBER = (1765, 450, 2440, 92)       # x, линия строки, правый край, высота цифр (знак № — 119 px)
FILED = (1135, 586)                  # «Подана»
TEXT_AREA = (790, 800, 2400, 2960)
PAGE_NO = (2470, 3390)
INK = (28, 32, 52)
INK_SOFT = (118, 122, 140)

PER_LINE = 7
LINES_PER_PAGE = 16
PER_PAGE = PER_LINE * LINES_PER_PAGE
GROUP_PX, NUM_PX = 52, 24
PITCH = NUM_PX + 8 + GROUP_PX + 36


def groups_of(b32):
    s = core.normalize_b32(b32)
    return [s[i:i + 5] for i in range(0, len(s), 5)]


def paginate(groups):
    return [groups[i:i + PER_PAGE] for i in range(0, len(groups), PER_PAGE)] or [[]]


def form_number(when, seq):
    """041026/001 — дата отправки и порядковый номер бланка."""
    return f"{when:%d%m%y}/{seq:03d}"


def file_stem(number):
    return "Шифровка " + number.replace("/", "-")


def footer_lines(on_page, total, page, pages):
    if pages == 1:
        return [f"Всего групп: {total}"]
    lines = [f"Групп на странице: {on_page}"]
    if page == pages - 1:
        lines.append(f"Всего групп: {total}")
    return lines


def _font(size):
    from PIL import ImageFont

    for name in ("courbd.ttf", "cour.ttf", "consolab.ttf", "DejaVuSansMono-Bold.ttf",
                 "LiberationMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def base_image(form_path, b32):
    """Чистый бланк с QR-кодом в квадрате."""
    from PIL import Image, ImageDraw

    img = Image.open(form_path).convert("RGB")
    x0, y0, x1, y1 = QR_BOX
    inner = min(x1 - x0, y1 - y0) - 44
    try:
        m = core.qr_matrix(core.normalize_b32(b32), border=2)
        q = core.qr_image(m, max(1, inner // len(m))).convert("RGB")
        img.paste(q, (x0 + (x1 - x0 - q.width) // 2, y0 + (y1 - y0 - q.height) // 2))
    except core.MarsError:
        ImageDraw.Draw(img).text(((x0 + x1) // 2, (y0 + y1) // 2), "QR не\nпомещается", font=_font(40),
                                 fill=INK, anchor="mm", align="center")
    return img


def _number_mask(number):
    """Номер шифровки чуть ниже знака №; если не влезает по ширине — сжимается."""
    from PIL import Image, ImageDraw

    x, _, right, height = NUMBER
    probe = _font(150)
    box = probe.getbbox("0123456789", anchor="ls")
    size = max(20, round(150 * height / max(1, box[3] - box[1])))
    font = _font(size)
    asc, desc = font.getmetrics()
    mask = Image.new("L", (int(math.ceil(font.getlength(number))) + 4, asc + desc), 0)
    ImageDraw.Draw(mask).text((0, asc), number, font=font, fill=255, anchor="ls")
    if mask.width > right - x:
        mask = mask.resize((right - x, mask.height), Image.LANCZOS)
    return mask, asc


def key_text(key_label):
    return f"Ключ: {key_label}"


def _draw_header(img, number, key_label, when):
    from PIL import Image, ImageDraw

    d = ImageDraw.Draw(img)
    mask, asc = _number_mask(number)
    img.paste(Image.new("RGB", mask.size, INK), (NUMBER[0], NUMBER[1] - asc), mask)
    d.text(FILED, when.strftime("%d.%m.%Y %H:%M"), font=_font(42), fill=INK, anchor="ls")
    kx, ky, kright = KEY_FIELD
    label, size = key_text(key_label), 40
    font = _font(size)
    while font.getlength(label) > kright - kx and size > 20:
        size -= 2
        font = _font(size)
    while font.getlength(label) > kright - kx and len(label) > 8:
        label = label[:-2] + "…"
    d.text((kx, ky), label, font=font, fill=INK, anchor="lm")


def render_png_pages(form_path, b32, key_label, number, when=None):
    """Список картинок-листов бланка."""
    from PIL import ImageDraw

    when = when or _dt.datetime.now()
    groups = groups_of(b32)
    pages = paginate(groups)
    head = base_image(form_path, b32)
    _draw_header(head, number, key_label, when)
    gfont, nfont, ffont = _font(GROUP_PX), _font(NUM_PX), _font(40)
    x0, y0, x1, _ = TEXT_AREA
    gw = gfont.getlength("MMMMM")
    gap = (x1 - x0 - PER_LINE * gw) / (PER_LINE - 1)   # выравнивание по ширине поля
    out = []
    for p, page in enumerate(pages):
        img = head.copy()
        d = ImageDraw.Draw(img)
        y = y0
        for li in range(0, len(page), PER_LINE):
            for ci, g in enumerate(page[li:li + PER_LINE]):
                gx = x0 + ci * (gw + gap)
                d.text((gx + gw / 2, y), str(p * PER_PAGE + li + ci + 1), font=nfont, fill=INK_SOFT, anchor="mt")
                d.text((gx, y + NUM_PX + 8), g, font=gfont, fill=INK)
            y += PITCH
        y += 10
        for line in footer_lines(len(page), len(groups), p, len(pages)):
            d.text((x0, y), line, font=ffont, fill=INK)
            y += 56
        if len(pages) > 1:
            d.text(PAGE_NO, str(p + 1), font=_font(60), fill=INK, anchor="rs")
        out.append(img)
    return out


# ---------------------------------------------------------------------------
# Word (.docx), собирается вручную: никаких дополнительных библиотек
# ---------------------------------------------------------------------------
PAGE_W_TW, PAGE_H_TW = 11906, 16838            # A4 в twips
TW = PAGE_W_TW / FORM_W                        # twips на пиксель бланка
OFF_Y = round((PAGE_H_TW - FORM_H * TW) / 2)   # бланк по центру листа
FONT = "Courier New"
INK_HEX = "1C2034"
ASC, LINE_H, ADV, DIGIT_H = 0.8325, 1.1328, 0.6001, 0.615   # метрики Courier New в долях кегля
CIPHER_PT = 14

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _x(px):
    return round(px * TW)


def _y(px):
    return OFF_Y + round(px * TW)


def _rpr(half_pt, spacing=None, scale=None):
    s = (f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/>'
         f'<w:b/><w:bCs/><w:color w:val="{INK_HEX}"/>')
    if spacing:
        s += f'<w:spacing w:val="{spacing}"/>'
    if scale and scale != 100:
        s += f'<w:w w:val="{scale}"/>'
    s += f'<w:sz w:val="{half_pt}"/><w:szCs w:val="{half_pt}"/>'
    return f"<w:rPr>{s}</w:rPr>"


def _run(text, half_pt, spacing=None, scale=None):
    return f'<w:r>{_rpr(half_pt, spacing, scale)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _frame(x0, x1, top_tw, height_tw, paragraphs):
    """Рамка с фиксированным местом на листе; paragraphs: [(выравнивание, строка_tw, до_tw, runs, кегль)]."""
    fp = (f'<w:framePr w:w="{_x(x1) - _x(x0)}" w:h="{height_tw}" w:hRule="exact" w:wrap="around" '
          f'w:hAnchor="page" w:vAnchor="page" w:x="{_x(x0)}" w:y="{top_tw}"/>')
    return "".join(
        f'<w:p><w:pPr>{fp}<w:spacing w:before="{before}" w:after="0" w:line="{line}" w:lineRule="exact"/>'
        f'<w:jc w:val="{jc}"/>{_rpr(half)}</w:pPr>{runs}</w:p>'
        for jc, line, before, runs, half in paragraphs)


def _field(x0, x1, base_px, pt, text="", jc="left", scale=None):
    """Однострочное поле: текст стоит на линии base_px бланка."""
    half = int(round(pt * 2))
    line = round(LINE_H * pt * 20)
    top = _y(base_px) - round(ASC * pt * 20)
    return _frame(x0, x1, top, line, [(jc, line, 0, _run(text, half, scale=scale) if text else "", half)])


def _cipher_frame(page_groups, footer):
    x0, y0, x1, y1 = TEXT_AREA
    half = CIPHER_PT * 2
    adv = ADV * CIPHER_PT * 20
    width = _x(x1) - _x(x0)
    gap = int((width - adv / 2 - PER_LINE * 5 * adv) // (PER_LINE - 1))
    runs = []
    for k, g in enumerate(page_groups):
        line_end = k % PER_LINE == PER_LINE - 1 or k == len(page_groups) - 1
        if len(g) > 1:
            runs.append(_run(g[:-1], half))
        runs.append(_run(g[-1], half, spacing=None if line_end else gap))
    paragraphs = [("left", 480, 0, "".join(runs), half)]
    for i, line in enumerate(footer):
        paragraphs.append(("left", 300, 240 if i == 0 else 0, _run(line, 22), 22))
    return _frame(x0, x1, _y(y0), _y(y1) - _y(y0), paragraphs)


def _number_field(number):
    x, base, right, height = NUMBER
    pt = round(height * TW / 20 / DIGIT_H)
    natural = len(number) * ADV * pt * 20
    scale = max(50, min(100, int(100 * (_x(right) - _x(x)) / natural)))
    return _field(x, right, base, pt, number, scale=scale)


def _key_field(key_label):
    kx, ky, kright = KEY_FIELD
    label = key_text(key_label)
    pt = max(6.0, min(10.0, (_x(kright) - _x(kx)) / (len(label) * ADV * 20)))
    pt = math.floor(pt * 2) / 2
    return _field(kx, kright, ky + 11, pt, label)


def _page_xml(page_groups, total, p, pages, number, key_label, when):
    parts = [
        _number_field(number),
        _field(1125, 1735, FILED[1], 10, when.strftime("%d.%m.%Y %H:%M")),
        _key_field(key_label),
        _cipher_frame(page_groups, footer_lines(len(page_groups), total, p, pages)),
        # пустые поля бланка для записи от руки в Word
        _field(330, 925, 600, 10), _field(1950, 2415, 600, 10), _field(830, 2415, 682, 10),
        _field(1100, 1740, 3090, 10), _field(1370, 1740, 3192, 10),
    ]
    if pages > 1:
        parts.append(_field(2250, PAGE_NO[0], PAGE_NO[1], 16, str(p + 1), jc="right"))
    return "".join(parts)


def _header_xml(cx, cy):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:hdr xmlns:w="{NS_W}" xmlns:r="{NS_R}" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr><w:r><w:drawing>'
        '<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="0" behindDoc="1" '
        'locked="1" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="page"><wp:posOffset>{OFF_Y * 635}</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
        '<wp:docPr id="1" name="Бланк шифровки"/><wp:cNvGraphicFramePr>'
        '<a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
        '<pic:nvPicPr><pic:cNvPr id="1" name="blank.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="rIdBg"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:anchor></w:drawing></w:r></w:p></w:hdr>')


def build_docx(form_path, b32, key_label, number, target, when=None):
    """Документ Word с листами бланка (target — путь или файловый объект)."""
    when = when or _dt.datetime.now()
    groups = groups_of(b32)
    pages = paginate(groups)
    bg = io.BytesIO()
    base_image(form_path, b32).save(bg, "PNG", optimize=True)
    page_break = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    body = page_break.join(_page_xml(pg, len(groups), p, len(pages), number, key_label, when)
                           for p, pg in enumerate(pages))
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS_W}" xmlns:r="{NS_R}"><w:body>{body}'
        '<w:sectPr><w:headerReference w:type="default" r:id="rIdHdr"/>'
        f'<w:pgSz w:w="{PAGE_W_TW}" w:h="{PAGE_H_TW}"/>'
        '<w:pgMar w:top="567" w:right="567" w:bottom="567" w:left="567" w:header="0" w:footer="0" w:gutter="0"/>'
        '</w:sectPr></w:body></w:document>')
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:styles xmlns:w="{NS_W}"><w:docDefaults><w:rPrDefault><w:rPr>'
        f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/>'
        '<w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="ru-RU"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
    settings = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:settings xmlns:w="{NS_W}"><w:zoom w:percent="100"/><w:defaultTabStop w:val="708"/>'
        '<w:characterSpacingControl w:val="doNotCompress"/><w:compat><w:compatSetting '
        'w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
        '</w:compat></w:settings>')
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
        '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>')
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        f'<Relationship Id="rId3" Type="{rel}/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>')
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdStyles" Type="{rel}/styles" Target="styles.xml"/>'
        f'<Relationship Id="rIdSettings" Type="{rel}/settings" Target="settings.xml"/>'
        f'<Relationship Id="rIdHdr" Type="{rel}/header" Target="header1.xml"/>'
        '</Relationships>')
    header_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdBg" Type="{rel}/image" Target="media/blank.png"/></Relationships>')
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>Шифровка {escape(number)}</dc:title><dc:creator>Код Марса</dc:creator>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{when:%Y-%m-%dT%H:%M:%S}Z</dcterms:created>'
        '</cp:coreProperties>')
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>Код Марса</Application></Properties>')
    cx = PAGE_W_TW * 635
    cy = round(FORM_H * TW) * 635
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/settings.xml", settings)
        z.writestr("word/header1.xml", _header_xml(cx, cy))
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/_rels/header1.xml.rels", header_rels)
        z.writestr("word/media/blank.png", bg.getvalue())
