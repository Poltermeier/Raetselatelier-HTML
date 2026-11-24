"""Browser implementations of the Tk operations used by the atelier."""
import json
import math
import re
from itertools import count
from types import SimpleNamespace

from js import atelierEmit, atelierTimer, atelierCancelTimer

_ids = count(1)
_widgets = {}
_timers = {}
_dirty_canvases = set()
_operations = []
_focus = None
_root = None


def send(operation, *args):
    _operations.append([operation, *args])


def flush():
    for canvas in list(_dirty_canvases):
        if canvas.exists:
            send("draw", canvas.id, list(canvas.items.values()))
    _dirty_canvases.clear()
    if _operations:
        atelierEmit(json.dumps(_operations, ensure_ascii=False, default=json_default))
        _operations.clear()


def _flatten(values):
    for value in values:
        if isinstance(value, (tuple, list)):
            yield from _flatten(value)
        else:
            yield value


def splitlist(value):
    return value.split() if isinstance(value, str) else tuple(value)


class Variable:
    cast = str

    def __init__(self, master=None, value=None):
        self.value = self.cast() if value is None else self.cast(value)
        self.callbacks = []
        self.widgets = set()

    def get(self):
        return self.value

    def set(self, value):
        self.value = self.cast(value)
        for widget in tuple(self.widgets):
            widget.send_value()
        for callback in tuple(self.callbacks):
            callback(None, None, "write")

    def trace_add(self, mode, callback):
        self.callbacks.append(callback)


class StringVar(Variable):
    pass


class IntVar(Variable):
    cast = int


class DoubleVar(Variable):
    cast = float


class BooleanVar(Variable):
    cast = bool


def encode(value):
    if isinstance(value, Widget):
        return value.id
    if isinstance(value, PhotoImage):
        return value.descriptor()
    return value


def options_for_browser(options):
    return {key: encode(value) for key, value in options.items() if key not in {
        "command", "textvariable", "variable", "validatecommand", "yscrollcommand", "xscrollcommand"
    }}


class Widget:
    kind = "Frame"
    widget_class = None

    def __init__(self, master=None, **options):
        self.master = master
        self.tk = self
        self.id = next(_ids)
        self._w = str(self.id)
        self.children = []
        self.bindings = {}
        self.options = {"state": "normal", "justify": "left", "bg": "#fffef9",
                        "borderwidth": 0, "highlightthickness": 0, "wraplength": 0}
        self.exists = True
        self.variable = None
        self.geometry_data = {}
        self.protocols = {}
        self.value = ""
        self.selection = (0, 0)
        _widgets[self.id] = self
        if master is not None:
            master.children.append(self)
        send("create", self.id, self.kind, master.id if master else None)
        self.configure(**options)

    def __str__(self):
        return self._w

    def configure(self, cnf=None, **options):
        if cnf:
            options = {**cnf, **options}
        self.options.update(options)
        if "textvariable" in options or "variable" in options:
            if self.variable is not None:
                self.variable.widgets.discard(self)
            self.variable = options.get("textvariable", options.get("variable"))
            if self.variable is not None:
                self.variable.widgets.add(self)
        if options:
            send("options", self.id, options_for_browser(options))
        if self.variable is not None and {"textvariable", "variable", "values"} & options.keys():
            self.send_value()

    config = configure

    def cget(self, key):
        return self.options.get(key, "")

    def pack(self, **options):
        send("pack", self.id, options_for_browser(options))

    def pack_forget(self):
        send("hide", self.id)

    def pack_propagate(self, value):
        send("propagate", self.id, value)

    def place(self, **options):
        send("place", self.id, options_for_browser(options))

    place_configure = place

    def place_forget(self):
        send("hide", self.id)

    def bind(self, sequence, callback, add=None):
        if add == "+":
            self.bindings.setdefault(sequence, []).append(callback)
        else:
            self.bindings[sequence] = [callback]
        send("bind", self.id, sequence, True)

    def unbind(self, sequence):
        if sequence in self.bindings:
            del self.bindings[sequence]
            send("bind", self.id, sequence, False)

    def dispatch(self, sequence, event):
        for callback in tuple(self.bindings.get(sequence, ())):
            if callback(event) == "break":
                return "break"

    def destroy(self):
        if not self.exists:
            return
        for child in list(self.children):
            child.destroy()
        if self.variable is not None:
            self.variable.widgets.discard(self)
        if self.master is not None:
            self.master.children.remove(self)
        self.exists = False
        del _widgets[self.id]
        send("destroy", self.id)

    def focus_set(self):
        global _focus
        _focus = self
        send("focus", self.id)

    def focus_get(self):
        return _focus if _focus is not None and _focus.exists else None

    def winfo_exists(self):
        return self.exists

    def winfo_width(self):
        return self.geometry_data.get("width", self.options.get("width", 1))

    def winfo_height(self):
        return self.geometry_data.get("height", self.options.get("height", 1))

    def winfo_x(self):
        return self.geometry_data.get("x", 0) - (self.master.scroll[0] if isinstance(self.master, Canvas) else 0)

    def winfo_y(self):
        return self.geometry_data.get("y", 0) - (self.master.scroll[1] if isinstance(self.master, Canvas) else 0)

    winfo_rootx = winfo_x
    winfo_rooty = winfo_y

    def winfo_reqwidth(self):
        return max(1, self.winfo_width())

    def winfo_reqheight(self):
        return max(1, self.winfo_height())

    def winfo_class(self):
        return self.widget_class or self.kind

    def register(self, callback):
        return callback

    def update_idletasks(self):
        pass

    def lift(self):
        send("raise", self.id)

    def after(self, delay, callback):
        job = next(_ids)
        _timers[job] = callback
        atelierTimer(job, delay)
        return job

    def after_idle(self, callback):
        return self.after(0, callback)

    def after_cancel(self, job):
        _timers.pop(job, None)
        atelierCancelTimer(job)

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def title(self, title):
        send("title", self.id, title)

    def geometry(self, geometry):
        pass

    def minsize(self, width, height):
        pass

    def transient(self, parent):
        pass

    def call(self, *args):
        if args[0] == "raise":
            send("raise", int(args[1]))
        elif args[1] == "scale":
            self.scale_items(args[-2], args[-1])

    splitlist = staticmethod(splitlist)

    def send_value(self):
        send("value", self.id, self.get(), getattr(self, "input_revision", None))

    def get(self):
        return self.variable.get() if self.variable is not None else self.value

    def set_value(self, value):
        if self.variable is not None:
            self.variable.set(value)
        else:
            self.value = value
            self.send_value()

    def selection_range(self, start, end):
        end = len(str(self.get())) if end == "end" else end
        self.selection = (start, end)
        send("selection", self.id, start, end)

    def selection_present(self):
        return self.selection[0] != self.selection[1]

    def icursor(self, index):
        if not self.selection_present():
            index = len(str(self.get())) if index == "end" else index
            self.selection_range(index, index)


class Tk(Widget):
    kind = "Root"

    def __init__(self):
        global _root
        super().__init__()
        _root = self


class Toplevel(Widget):
    kind = "Toplevel"


class Frame(Widget):
    pass


class Label(Widget):
    kind = "Label"


class Button(Widget):
    kind = "Button"


class Entry(Widget):
    kind = "Entry"

    def delete(self, first, last=None):
        value = str(self.get())
        stop = len(value) if last == "end" else first + 1 if last is None else last
        self.set_value(value[:first] + value[stop:])

    def insert(self, index, value):
        old = str(self.get())
        index = len(old) if index == "end" else index
        self.set_value(old[:index] + value + old[index:])

    def accept_input(self, value):
        validator = self.cget("validatecommand")
        if self.cget("validate") == "key" and validator and not validator[0](value):
            self.send_value()
            return
        if value != self.get():
            self.set_value(value)


class Combobox(Widget):
    kind = "Combobox"
    widget_class = "TCombobox"

    def current(self, index=None):
        values = self.cget("values")
        if index is not None:
            self.set_value(values[index])
            return
        try:
            return [str(value) for value in values].index(str(self.get()))
        except ValueError:
            return -1

    def set(self, value):
        self.set_value(value)


class Checkbutton(Widget):
    kind = "Checkbutton"


class Scale(Widget):
    kind = "Scale"


class Separator(Widget):
    kind = "Separator"


class Scrollbar(Widget):
    kind = "Scrollbar"

    def set(self, first, last):
        pass


class Progressbar(Widget):
    kind = "Progressbar"

    def start(self, interval=None):
        send("progress", self.id, True)

    def stop(self):
        send("progress", self.id, False)


class Style:
    def __init__(self, root):
        pass

    def theme_use(self, theme):
        pass

    def configure(self, style, **options):
        send("style", style, options)

    def map(self, style, **options):
        pass


ttk = SimpleNamespace(**{cls.__name__: cls for cls in (
    Frame, Label, Button, Entry, Combobox, Checkbutton, Scale, Separator, Scrollbar, Progressbar, Style
)})


class Font:
    def __init__(self, root=None, font=None, *, family="Helvetica", size=10):
        if not isinstance(font, (list, tuple)):
            font = (family, size)
        family, size, *traits = font
        traits = " ".join(traits).split()
        self.data = dict(family=family, size=int(size),
                         weight="bold" if "bold" in traits else "normal",
                         slant="italic" if "italic" in traits else "roman",
                         underline="underline" in traits, overstrike="overstrike" in traits)

    def actual(self):
        return self.data.copy()

    def pixels(self):
        size = self.data["size"]
        return abs(size) * (4 / 3 if size > 0 else 1)

    def measure(self, text):
        narrow = " .,;:!ilI|1'’"
        wide = "MWmw@%ÖÜÄ"
        return sum(.29 if char in narrow else .86 if char in wide else .56 for char in text) * self.pixels()

    def metrics(self, option):
        return round(self.pixels() * 1.19)


font = SimpleNamespace(Font=Font)


class PhotoImage:
    def __init__(self, master=None, width=None, height=None, data=None, format=None):
        self.width = width or 512
        self.height = height or 512
        self.rects = []
        self.source = next(_ids) if data else None
        if data:
            send("image-source", self.source, data.decode("ascii"))

    def put(self, color, to):
        self.rects.append([color, *to])

    def subsample(self, divisor):
        image = PhotoImage(width=math.ceil(self.width / divisor), height=math.ceil(self.height / divisor))
        image.source = self.source
        return image

    def descriptor(self):
        return dict(width=self.width, height=self.height, rects=self.rects, source=self.source)


class Canvas(Widget):
    kind = "Canvas"

    def __init__(self, master, **options):
        self.items = {}
        self.tag_bindings = {}
        self.scroll = (0, 0)
        super().__init__(master, **options)

    def _create(self, kind, coords, options):
        item = next(_ids)
        self.items[item] = [item, kind, list(_flatten(coords)), dict(options)]
        self.changed()
        return item

    def changed(self):
        _dirty_canvases.add(self)

    def create_line(self, *coords, **kw):
        return self._create("line", coords, kw)

    def create_rectangle(self, *coords, **kw):
        return self._create("rectangle", coords, kw)

    def create_oval(self, *coords, **kw):
        return self._create("oval", coords, kw)

    def create_arc(self, *coords, **kw):
        return self._create("arc", coords, kw)

    def create_polygon(self, *coords, **kw):
        return self._create("polygon", coords, kw)

    def create_text(self, *coords, **kw):
        return self._create("text", coords, kw)

    def create_image(self, *coords, **kw):
        return self._create("image", coords, kw)

    def create_window(self, *coords, **kw):
        return self._create("window", coords, kw)

    def find_withtag(self, tag):
        if tag == "all":
            return tuple(self.items)
        if isinstance(tag, int):
            return (tag,) if tag in self.items else ()
        return tuple(item for item, _, _, options in self.items.values() if tag in splitlist(options.get("tags", ())))

    def delete(self, *tags):
        if "all" in tags:
            self.tag_bindings.clear()
        for tag in tags:
            for item in self.find_withtag(tag):
                del self.items[item]
                self.tag_bindings.pop((item, "<Button-1>"), None)
        self.changed()

    def itemconfigure(self, tag, cnf=None, **kw):
        for item in self.find_withtag(tag):
            self.items[item][3].update(cnf or {}, **kw)
        self.changed()

    itemconfig = itemconfigure

    def itemcget(self, tag, option):
        items = self.find_withtag(tag)
        if items:
            return self.items[items[0]][3].get(option, "center" if option == "anchor" else "")
        return ""

    def coords(self, tag, *coords):
        items = self.find_withtag(tag)
        if not items:
            return []
        if coords:
            self.items[items[0]][2] = list(_flatten(coords))
            self.changed()
        return self.items[items[0]][2].copy()

    def bbox(self, *tags):
        boxes = []
        for tag in tags:
            for item in self.find_withtag(tag):
                _, kind, coords, options = self.items[item]
                xs, ys = coords[::2], coords[1::2]
                if kind in {"text", "image", "window"}:
                    width, height = options.get("width", 0), options.get("height", 0)
                    if kind == "text":
                        label_font = Font(font=options.get("font"))
                        lines = str(options.get("text", "")).split("\n")
                        lengths = [label_font.measure(line) for line in lines]
                        height = label_font.metrics("linespace") * sum(max(1, math.ceil(size / width)) if width else 1 for size in lengths)
                        width = min(max(lengths), width) if width else max(lengths)
                    elif kind == "image":
                        width, height = options["image"].width, options["image"].height
                    anchor = options.get("anchor", "center")
                    left = xs[0] - (0 if "w" in anchor else width if anchor in ("e", "ne", "se") else width / 2)
                    top = ys[0] - (0 if anchor in ("n", "ne", "nw") else height if "s" in anchor else height / 2)
                    xs, ys = [left, left + width], [top, top + height]
                boxes.append((min(xs), min(ys), max(xs), max(ys)))
        if boxes:
            return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes))
        return None

    def move(self, tag, dx, dy):
        for item in self.find_withtag(tag):
            self.items[item][2] = [value + (dx if i % 2 == 0 else dy) for i, value in enumerate(self.items[item][2])]
        self.changed()

    def scale_items(self, x, y):
        for item in self.items.values():
            item[2] = [value * (x if i % 2 == 0 else y) for i, value in enumerate(item[2])]
        self.changed()

    def restack(self, tag, relative, above):
        selected = set(self.find_withtag(tag))
        rest = [item for item in self.items if item not in selected]
        targets = [rest.index(item) for item in self.find_withtag(relative) if item in rest] if relative else []
        index = (max(targets) + 1 if above else min(targets)) if targets else len(rest) if above else 0
        rest[index:index] = [item for item in self.items if item in selected]
        self.items = {item: self.items[item] for item in rest}
        self.changed()

    def tag_raise(self, tag, relative=None):
        self.restack(tag, relative, True)

    def tag_lower(self, tag, relative=None):
        self.restack(tag, relative, False)

    def tag_bind(self, tag, sequence, callback):
        self.tag_bindings[tag, sequence] = callback
        send("bind", self.id, sequence, True)

    def dispatch(self, sequence, event):
        x, y = event.x + self.scroll[0], event.y + self.scroll[1]
        if sequence == "<Button-1>" and self.tag_bindings:
            for item in reversed(self.items):
                _, kind, _, options = self.items[item]
                if kind == "window" or options.get("state") == "hidden":
                    continue
                box = Canvas.bbox(self, item)
                if box and box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                    for tag in (*splitlist(options.get("tags", ())), item):
                        callback = self.tag_bindings.get((tag, sequence))
                        if callback:
                            if callback(event) == "break":
                                return "break"
                            return super().dispatch(sequence, event)
        return super().dispatch(sequence, event)

    def canvasx(self, screenx, gridspacing=None):
        return screenx + self.scroll[0]

    def canvasy(self, screeny, gridspacing=None):
        return screeny + self.scroll[1]

    def view(self, axis):
        region = self.options.get("scrollregion")
        if not region:
            return (0, 1)
        extent = max(1, region[axis + 2])
        return (self.scroll[axis] / extent, min(1, (self.scroll[axis] + (self.winfo_width() if axis == 0 else self.winfo_height())) / extent))

    def xview(self):
        return self.view(0)

    def yview(self):
        return self.view(1)

    def xview_moveto(self, value):
        send("scroll", self.id, 0, value)

    def yview_moveto(self, value):
        send("scroll", self.id, 1, value)


class Menu(Widget):
    kind = "Menu"

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.commands = []

    def add_command(self, label, command):
        send("menu_item", self.id, len(self.commands), label)
        self.commands.append(command)

    def tk_popup(self, x, y):
        send("menu_open", self.id, x, y)


class MessageBox:
    @staticmethod
    def showerror(title, message, **kw):
        send("dialog", title, message, None)

    showinfo = showerror

    @staticmethod
    def askyesno(*args, **kw):
        return True  # The web App requests confirmation before calling reset.


messagebox = MessageBox()
filedialog = SimpleNamespace()


def handle_event(payload):
    global _focus
    event = json.loads(payload)
    kind = event["kind"]
    if kind == "timer":
        callback = _timers.pop(event["id"], None)
        if callback:
            callback()
        return
    widget = _widgets.get(event["id"])
    if widget is None:
        return
    if kind == "confirm":
        callback = _timers.pop(event["token"], None)
        if callback and event["confirmed"]:
            callback()
        return
    if kind == "menu":
        widget.commands[event["index"]]()
        widget.destroy()
        return
    if kind == "close":
        callback = widget.protocols.get("WM_DELETE_WINDOW", widget.destroy)
        callback()
        return
    if "geometry" in event:
        widget.geometry_data.update(event["geometry"])
    if "scroll" in event:
        widget.scroll = event["scroll"]
    if "selection" in event:
        widget.selection = event["selection"]
    if kind == "input":
        if widget.cget("state") == "normal":
            widget.input_revision = event["revision"]
            try:
                widget.accept_input(event["value"])
            finally:
                widget.input_revision = None
        return
    if kind == "change":
        if widget.cget("state") == "disabled":
            return
        widget.set_value(event["value"])
        command = widget.cget("command")
        if command:
            if isinstance(widget, Scale):
                command(event["value"])
            else:
                command()
        if isinstance(widget, Combobox):
            widget.dispatch("<<ComboboxSelected>>", SimpleNamespace(widget=widget))
        return
    if kind == "command":
        command = widget.cget("command")
        if widget.cget("state") != "disabled" and command:
            command()
        return
    sequence = event["sequence"]
    if sequence == "<FocusIn>":
        _focus = widget
    elif sequence == "<FocusOut>" and _focus is widget:
        _focus = None
    attributes = {k: event[k] for k in ("x", "y", "x_root", "y_root", "width", "height", "keysym", "char", "state") if k in event}
    attributes.setdefault("x", 0)
    attributes.setdefault("y", 0)
    attributes.setdefault("state", 0)
    details = SimpleNamespace(widget=widget, **attributes)
    stopped = widget.dispatch(sequence, details)
    if kind == "key" and widget is not _root and stopped != "break":
        _root.dispatch(sequence, details)


def confirm(root, title, message, callback):
    token = next(_ids)
    _timers[token] = callback
    send("dialog", title, message, [root.id, token])


def wire_dispatch(payload):
    try:
        handle_event(payload)
    finally:
        flush()


def json_default(value):
    return encode(value)
