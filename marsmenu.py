# -*- coding: utf-8 -*-
"""Меню в стиле «Кода Марса»: пергамент в тёмной рамке с заклёпками, у пунктов — лампочки.

Повторяет нужную часть tk.Menu, поэтому общая логика строит меню как прежде. Меню открывается у курсора
или под кнопкой и не уходит за край экрана: если места мало, открывается вверх или влево.
Подменю встаёт вплотную к своей строке «▶», а у края экрана — слева от меню."""
import math
import tkinter as tk
import tkinter.font as tkfont

import kod_marsa as km

EDGE, INK, MUTED, HOVER, RIVET = "#2A231C", "#2A241D", "#8C8172", "#D2BE97", "#6E604E"


class MarsMenu:
    def __init__(self, app, parent=None, columns=1):
        self.app, self.parent, self.columns = app, parent, columns
        self.items, self.top, self.child, self.cells = [], None, None, []
        self._hl, self.mark = None, None
        self.x = self.y = self.W = self.H = 0

    # ---------------------------------------------------------------- как у tk.Menu
    def add_command(self, label="", command=None, state="normal", accelerator="", **_):
        self.items.append({"kind": "cmd", "label": label, "command": command, "state": state, "acc": accelerator})

    def add_checkbutton(self, label="", variable=None, command=None, state="normal", **_):
        self.items.append({"kind": "check", "label": label, "var": variable, "command": command, "state": state})

    def add_radiobutton(self, label="", value=None, variable=None, command=None, state="normal", **_):
        self.items.append({"kind": "radio", "label": label, "value": value, "var": variable, "command": command,
                           "state": state})

    def add_separator(self, **_):
        self.items.append({"kind": "sep"})

    def add_cascade(self, label="", menu=None, state="normal", **_):
        self.items.append({"kind": "cascade", "label": label, "menu": menu, "state": state})

    def delete(self, *_):
        self.items = []

    def tk_popup(self, x, y, entry=None):
        """Контекстное меню: у курсора (положение берём у Windows, оно точное)."""
        cx, cy = km.cursor_xy(self.app.root)
        self.post(cx, cy, alt_x=cx, alt_y=cy)

    def grab_release(self):
        pass

    def unpost(self):
        self.close_all()

    # ---------------------------------------------------------------- рисование
    def _lamp(self, it):
        if it.get("state") == "disabled":
            return "off"
        if it["kind"] == "check":
            return "red" if it["var"] is not None and it["var"].get() else "off"
        if it["kind"] == "radio":
            return "red" if it["var"] is not None and it["var"].get() == it["value"] else "off"
        if self.mark and it["label"].startswith(self.mark + " "):
            return "red"
        return "orange"

    def post(self, x, y, alt_x=None, alt_y=None):
        """x, y — левый верхний угол. Если не помещается: вправо → открыть влево до alt_x,
        вниз → открыть вверх до alt_y."""
        app = self.app
        kp, root = app.kp, app.root
        font = (app.fam["cond"], -kp(17), app.cond_weight)
        small = (app.fam["cond"], -kp(14), app.cond_weight)
        fm, fs = tkfont.Font(root=root, font=font), tkfont.Font(root=root, font=small)
        pad, row, sep, lamp_w, gap = kp(12), kp(31), kp(11), kp(30), kp(10)
        arrow = kp(22) if any(it["kind"] == "cascade" for it in self.items) else 0
        per = math.ceil(len(self.items) / self.columns) if self.columns > 1 else len(self.items)
        cols = [list(range(c * per, min(len(self.items), (c + 1) * per))) for c in range(self.columns)]
        widths, heights = [], []
        for col in cols:
            tw = [fm.measure(self.items[i]["label"]) + (fs.measure(self.items[i].get("acc", "")) + kp(18)
                  if self.items[i].get("acc") else 0) for i in col if self.items[i]["kind"] != "sep"]
            widths.append(lamp_w + kp(6) + max(tw + [kp(60)]) + arrow + kp(6))
            heights.append(sum(sep if self.items[i]["kind"] == "sep" else row for i in col))
        W = pad * 2 + sum(widths) + gap * (len(cols) - 1)
        H = pad * 2 + max(heights + [row])
        wx, wy, ww, wh = app._work_area()
        if x + W > wx + ww:
            x = (alt_x if alt_x is not None else wx + ww) - W
        if y + H > wy + wh:
            y = (alt_y if alt_y is not None else wy + wh) - H
        x, y = max(wx, min(x, wx + ww - W)), max(wy, min(y, wy + wh - H))
        self.x, self.y, self.W, self.H = x, y, W, H
        master = self.parent.top if self.parent is not None and self.parent.top is not None else root
        top = self.top = tk.Toplevel(master)
        top.overrideredirect(True)
        top.configure(bg=EDGE)
        try:
            top.attributes("-topmost", True)
        except tk.TclError:
            pass
        cv = self.cv = tk.Canvas(top, width=W, height=H, bd=0, highlightthickness=0, bg="#E6D9BC")
        cv.pack()
        self._paper = app._menu_paper(W, H)
        cv.create_image(0, 0, image=self._paper, anchor="nw")
        b = kp(3)
        cv.create_rectangle(b // 2, b // 2, W - b // 2 - 1, H - b // 2 - 1, outline=EDGE, width=b)
        cv.create_rectangle(b + kp(2), b + kp(2), W - b - kp(3), H - b - kp(3), outline="#9C8B70", width=1)
        r = kp(3)
        for cx, cy in ((kp(8), kp(8)), (W - kp(8), kp(8)), (kp(8), H - kp(8)), (W - kp(8), H - kp(8))):
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RIVET, outline=EDGE)
        self.cells, cx0 = [], pad
        for col, cw in zip(cols, widths):
            yy = pad
            for i in col:
                it = self.items[i]
                if it["kind"] == "sep":
                    cv.create_line(cx0, yy + sep // 2, cx0 + cw, yy + sep // 2, fill="#7A6A55", width=max(1, kp(1)))
                    yy += sep
                    continue
                on = it.get("state") != "disabled"
                self.cells.append((i, cx0, yy, cx0 + cw, yy + row))
                cv.create_image(cx0 + lamp_w // 2, yy + row // 2, image=app._lamp_img(self._lamp(it), 0.42), tags=("fg",))
                cv.create_text(cx0 + lamp_w + kp(6), yy + row // 2, text=it["label"], anchor="w", font=font,
                               fill=INK if on else MUTED, tags=("fg",))
                if it.get("acc"):
                    cv.create_text(cx0 + cw - arrow, yy + row // 2, text=it["acc"], anchor="e", font=small,
                                   fill=MUTED, tags=("fg",))
                if it["kind"] == "cascade":
                    cv.create_text(cx0 + cw, yy + row // 2, text="▶", anchor="e", font=small, fill=INK, tags=("fg",))
                yy += row
            cx0 += cw + gap
        top.geometry(f"{W}x{H}+{x}+{y}")
        cv.bind("<Motion>", self._motion)
        cv.bind("<Leave>", lambda e: self.child is None and self._highlight(None))
        cv.bind("<ButtonRelease-1>", self._release)
        top.bind("<Escape>", lambda e: self.close_all())
        if self.parent is None:
            top.bind("<ButtonPress-1>", self._outside, add="+")
            top.bind("<FocusOut>", lambda e: root.after(120, self._check_focus))
            top.after(10, self._grab)

    def _grab(self):
        try:
            self.top.grab_set()
            self.top.focus_force()
        except tk.TclError:
            pass

    def _cell_at(self, x, y):
        for cell in self.cells:
            if cell[1] <= x < cell[3] and cell[2] <= y < cell[4]:
                return cell
        return None

    def _highlight(self, cell):
        cv = self.cv
        cv.delete("hl")
        self._hl = cell[0] if cell else None
        if cell and self.items[cell[0]].get("state") != "disabled":
            cv.create_rectangle(cell[1] - self.app.kp(4), cell[2] + 1, cell[3] + self.app.kp(4), cell[4] - 1,
                                fill=HOVER, outline="", tags=("hl",))
            cv.tag_raise("fg")

    def _motion(self, e):
        cell = self._cell_at(e.x, e.y)
        if (cell[0] if cell else None) == self._hl:
            return
        self._highlight(cell)
        if self.child is not None:
            self.child.close()
            self.child = None
        it = self.items[cell[0]] if cell else None
        if it and it["kind"] == "cascade" and it.get("state") != "disabled":
            sub = it["menu"]
            if sub is not None and sub.items:
                sub.parent, self.child = self, sub
                pad = self.app.kp(12)
                sub.post(self.x + self.W - self.app.kp(4), self.y + cell[2] - pad,
                         alt_x=self.x + self.app.kp(4), alt_y=self.y + cell[4] + pad)

    def _release(self, e):
        cell = self._cell_at(e.x, e.y)
        if not cell:
            return
        it = self.items[cell[0]]
        if it.get("state") == "disabled" or it["kind"] == "cascade":
            return
        if it["kind"] == "check" and it["var"] is not None:
            it["var"].set(not it["var"].get())
        elif it["kind"] == "radio" and it["var"] is not None:
            it["var"].set(it["value"])
        command = it.get("command")
        self.close_all()
        if command:
            self.app.root.after(10, command)

    def _inside(self, x, y):
        m = self
        while m is not None:
            if m.top is not None and m.x <= x < m.x + m.W and m.y <= y < m.y + m.H:
                return True
            m = m.child
        return False

    def _outside(self, e):
        if not self._inside(*km.cursor_xy(self.app.root)):
            self.close_all()

    def _check_focus(self):
        try:
            f = self.app.root.focus_get()
        except (tk.TclError, KeyError):
            f = None
        tops, m = [], self
        while m is not None:
            if m.top is not None:
                tops.append(str(m.top))
            m = m.child
        if f is None or not any(str(f).startswith(t) for t in tops):
            self.close_all()

    # ---------------------------------------------------------------- закрытие
    def close(self):
        if self.child is not None:
            self.child.close()
            self.child = None
        if self.top is not None:
            try:
                self.top.grab_release()
                self.top.destroy()
            except tk.TclError:
                pass
            self.top = None

    def close_all(self):
        m = self
        while m.parent is not None and m.parent.top is not None:
            m = m.parent
        m.close()


def paper_for(skin, rect, size):
    """Кусок бумаги со шкуры окна под фон меню."""
    from PIL import Image, ImageTk

    return ImageTk.PhotoImage(skin.crop(rect).resize(size, Image.LANCZOS))
