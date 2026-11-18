"""Resizable board presentation with stable logical coordinates for puzzle input."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from weakref import WeakSet


class BoardCanvas(tk.Canvas):
    """Scale drawings, text and entry windows without rebuilding puzzle state.

    Drawing/query coordinates are logical board units. Pointer events remain
    screen pixels; canvasx/canvasy convert them back for all hit testing.
    """
    SCALED = {"width", "height", "font", "arrowshape", "dash"}

    def __init__(self, master, **kwargs):
        self.zoom = 1.0
        self.logical_region = (0, 0, 1, 1)
        self.base_options = {}
        self.font_widgets = WeakSet()
        self.font_cache = {}
        self.image_factories = {}
        super().__init__(master, **kwargs)

    def zoom_font(self, font):
        key = (str(font), self.zoom)
        if key not in self.font_cache:
            data = tkfont.Font(self, font=font).actual()
            size = data["size"]
            scaled = max(1, round(abs(size)*self.zoom)) * (-1 if size < 0 else 1)
            result = (data["family"], scaled, data["weight"], data["slant"])
            if data["underline"]:
                result += ("underline",)
            if data["overstrike"]:
                result += ("overstrike",)
            self.font_cache[key] = result
        return self.font_cache[key]

    def scaled_options(self, options):
        result = dict(options)
        for key in ("width", "height"):
            if key in result:
                result[key] = float(result[key])*self.zoom
        if "font" in result:
            result["font"] = self.zoom_font(result["font"])
        for key in ("arrowshape", "dash"):
            if key in result and result[key]:
                values = self.tk.splitlist(result[key])
                result[key] = tuple(max(1, round(float(v)*self.zoom)) for v in values)
        return result

    def _create(self, itemType, args, kw):
        options = dict(kw)
        if itemType in ("line", "rectangle", "oval", "polygon"):
            options.setdefault("width", 1)
        if itemType == "text":
            options.setdefault("font", "TkDefaultFont")
        coords = tuple(float(v)*self.zoom for v in tk._flatten(args))
        item = super()._create(itemType, coords, self.scaled_options(options))
        self.base_options[item] = {k:v for k,v in options.items() if k in self.SCALED}
        return item

    def create_scaled_image(self,x,y,*,size,factory,**kwargs):
        image=factory(size*self.zoom)
        item=self.create_image(x,y,image=image,**kwargs)
        self.image_factories[item]=(size,factory)
        return item

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if "scrollregion" in kwargs:
            self.logical_region = tuple(float(v) for v in self.tk.splitlist(kwargs["scrollregion"]))
            kwargs["scrollregion"] = tuple(v*self.zoom for v in self.logical_region)
        return super().configure(cnf, **kwargs)

    config = configure

    def cget(self, key):
        if key == "scrollregion":
            return " ".join(map(str, self.logical_region))
        return super().cget(key)

    def coords(self, *args):
        if len(args) > 1:
            return super().coords(args[0], *(float(v)*self.zoom for v in tk._flatten(args[1:])))
        return [v/self.zoom for v in super().coords(*args)]

    def bbox(self, *args):
        result = super().bbox(*args)
        return tuple(v/self.zoom for v in result) if result else None

    def canvasx(self, screenx, gridspacing=None):
        value = super().canvasx(screenx)/self.zoom
        return round(value/gridspacing)*gridspacing if gridspacing else value

    def canvasy(self, screeny, gridspacing=None):
        value = super().canvasy(screeny)/self.zoom
        return round(value/gridspacing)*gridspacing if gridspacing else value

    def itemconfigure(self, tagOrId, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if kwargs:
            for item in self.find_withtag(tagOrId):
                self.base_options.setdefault(item, {}).update({k:v for k,v in kwargs.items() if k in self.SCALED})
            return super().itemconfigure(tagOrId, **self.scaled_options(kwargs))
        return super().itemconfigure(tagOrId, cnf)

    itemconfig = itemconfigure

    def itemcget(self, tagOrId, option):
        items = self.find_withtag(tagOrId)
        if items and option in self.base_options.get(items[0], {}):
            value = self.base_options[items[0]][option]
            if option == "font":
                return value
            return " ".join(map(str,value)) if isinstance(value,(tuple,list)) else str(value)
        return super().itemcget(tagOrId, option)

    def delete(self, *args):
        for tag in args:
            for item in self.find_withtag(tag):
                self.base_options.pop(item, None)
                self.image_factories.pop(item,None)
        super().delete(*args)

    def set_zoom(self, zoom):
        if abs(zoom-self.zoom) < .001:
            return False
        old_x, old_y = self.xview()[0], self.yview()[0]
        ratio = zoom/self.zoom
        self.tk.call(self._w, "scale", "all", 0, 0, ratio, ratio)
        self.zoom = zoom
        for item, options in self.base_options.items():
            if options:
                super().itemconfigure(item, **self.scaled_options(options))
        for item,(size,factory) in self.image_factories.items():
            super().itemconfigure(item,image=factory(size*zoom))
        for widget in tuple(self.font_widgets):
            if widget.winfo_exists():
                widget.rescale_font()
        super().configure(scrollregion=tuple(v*zoom for v in self.logical_region))
        self.xview_moveto(old_x)
        self.yview_moveto(old_y)
        return True


class ScaledFontWidget:
    def __init__(self, master, **kwargs):
        self.scaling_canvas = master if isinstance(master, BoardCanvas) else master.scaling_canvas
        self.base_font = kwargs.get("font", "TkDefaultFont")
        kwargs["font"] = self.scaling_canvas.zoom_font(self.base_font)
        super().__init__(master, **kwargs)
        self.scaling_canvas.font_widgets.add(self)

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        if "font" in kwargs:
            self.base_font = kwargs["font"]
            kwargs["font"] = self.scaling_canvas.zoom_font(self.base_font)
        return super().configure(cnf, **kwargs)

    config = configure

    def cget(self, key):
        return self.base_font if key == "font" else super().cget(key)

    def rescale_font(self):
        super().configure(font=self.scaling_canvas.zoom_font(self.base_font))


class BoardEntry(ScaledFontWidget, tk.Entry):
    pass


class BoardCombobox(ScaledFontWidget, ttk.Combobox):
    pass


class BoardNoteLabel(ScaledFontWidget, tk.Label):
    pass
