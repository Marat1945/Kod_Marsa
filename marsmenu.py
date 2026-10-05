# -*- coding: utf-8 -*-
"""Меню в стиле «Кода Марса»: пергамент в тёмной рамке с заклёпками, у пунктов — лампочки.

Повторяет нужную часть tk.Menu (add_command, add_checkbutton, add_radiobutton, add_separator,
add_cascade, delete, tk_popup), поэтому вся общая логика программы строит меню как прежде."""
import tkinter as tk
import tkinter.font as tkfont

from PIL import ImageTk

EDGE, INK, MUTED, HOVER, RIVET = "#2A231C", "#2A241D", "#8C8172", "#D2BE97", "#6E604E"


class MarsMenu:
    def __init__(self, app, parent=None):
        self.app, self.parent = app, parent
        self.items, self.top, self.child, self.rows = [], None, None, []
        self._hl = None
        self.mark = None

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
        self.post(int(x), int(y))

    def grab_release(self):
        pass

    def unpost(self):
        self.close_all()

    # ---------------------------------------------------------------- рисование
    def _lamp(self, it):
        if it["kind"] == "sep":
            return None
        if it.get("state") == "disabled":
            return "off"
        if it["kind"] == "check":
            return "red" if it["var"] is not None and it["var"].get() else "off"
        if it["kind"] == "radio":
            return "red" if it["var"] is not None and it["var"].get() == it["value"] else "off"
        if self.mark and it["label"].startswith(self.mark + " "):
            return "red"
        return "orange"

    def post(self, x, y):
        app = self.app
        kp = app.kp
        root = app.root
        master = self.parent.top if self.parent is not None and self.parent.top is not None else root
        font = (app.fam["cond"], -kp(17), app.cond_weight)
        small = (app.fam["cond"], -kp(14), app.cond_weight)
        fm, fs = tkfont.Font(root=root, font=font), tkfont.Font(root=root, font=small)
        pad, row, sep, lamp_w = kp(12), kp(31), kp(11), kp(30)
        text_w = max([fm.measure(it["label"]) + (fs.measure(it.get("acc", "")) + kp(18) if it.get("acc") else 0)
                      for it in self.items if it["kind"] != "sep"] + [kp(80)])
        arrow = kp(22) if any(it["kind"] == "cascade" for it in self.items) else 0
        W = pad * 2 + lamp_w + kp(6) + text_w + arrow + kp(6)
        H = pad * 2 + sum(sep if it["kind"] == "sep" else row for it in self.items)
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
        self.rows, y = [], pad
        for i, it in enumerate(self.items):
            if it["kind"] == "sep":
                cv.create_line(pad, y + sep // 2, W - pad, y + sep // 2, fill="#7A6A55", width=max(1, kp(1)))
                y += sep
                continue
            on = it.get("state") != "disabled"
            self.rows.append((i, y, y + row))
            cv.create_image(pad + lamp_w // 2, y + row // 2, image=app._lamp_img(self._lamp(it), 0.42),
                            tags=("fg",))
            cv.create_text(pad + lamp_w + kp(6), y + row // 2, text=it["label"], anchor="w", font=font,
                           fill=INK if on else MUTED, tags=("fg",))
            if it.get("acc"):
                cv.create_text(W - pad - arrow, y + row // 2, text=it["acc"], anchor="e", font=small, fill=MUTED,
                               tags=("fg",))
            if it["kind"] == "cascade":
                cv.create_text(W - pad, y + row // 2, text="▶", anchor="e", font=small, fill=INK, tags=("fg",))
            y += row
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x, y = max(0, min(x, sw - W - 2)), max(0, min(y, sh - H - 2))
        top.geometry(f"{W}x{H}+{x}+{y}")
        self.W = W
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

    def _row_at(self, y):
        for i, y0, y1 in self.rows:
            if y0 <= y < y1:
                return i, y0, y1
        return None

    def _highlight(self, hit):
        cv = self.cv
        cv.delete("hl")
        self._hl = hit[0] if hit else None
        if hit and self.items[hit[0]].get("state") != "disabled":
            cv.create_rectangle(self.app.kp(8), hit[1] + 1, self.W - self.app.kp(8), hit[2] - 1, fill=HOVER,
                                outline="", tags=("hl",))
            cv.tag_raise("fg")

    def _motion(self, e):
        hit = self._row_at(e.y)
        if (hit[0] if hit else None) == self._hl:
            return
        self._highlight(hit)
        if self.child is not None:
            self.child.close()
            self.child = None
        if hit and self.items[hit[0]]["kind"] == "cascade" and self.items[hit[0]].get("state") != "disabled":
            sub = self.items[hit[0]]["menu"]
            if sub is not None and sub.items:
                sub.parent = self
                self.child = sub
                sub.post(self.top.winfo_rootx() + self.W - self.app.kp(6), self.top.winfo_rooty() + hit[1])

    def _release(self, e):
        hit = self._row_at(e.y)
        if not hit:
            return
        it = self.items[hit[0]]
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
            t = m.top
            if t is not None and t.winfo_exists():
                if 0 <= x - t.winfo_rootx() < t.winfo_width() and 0 <= y - t.winfo_rooty() < t.winfo_height():
                    return True
            m = m.child
        return False

    def _outside(self, e):
        if not self._inside(e.x_root, e.y_root):
            self.close_all()

    def _check_focus(self):
        try:
            f = self.app.root.focus_get()
        except (tk.TclError, KeyError):
            f = None
        tops = []
        m = self
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
    from PIL import Image

    crop = skin.crop(rect).resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(crop)
