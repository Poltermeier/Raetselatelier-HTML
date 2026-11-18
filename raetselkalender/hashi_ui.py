"""Grid-aligned islands and direct mouse input for parallel bridges."""
import math


def bridge_segments(a, b, count, radius=22):
    if count not in (1, 2, 3):
        return []
    x1, y1 = a
    x2, y2 = b
    offsets = {1: (0,), 2: (-3, 3), 3: (-5, 0, 5)}[count]
    lines = []
    for offset in offsets:
        inset = math.sqrt(radius*radius-offset*offset)
        if y1 == y2:
            lines.append((x1+inset, y1+offset, x2-inset, y2+offset))
        else:
            lines.append((x1+offset, y1+inset, x2+offset, y2-inset))
    return lines


class HashiUI:
    def render_hashi(self):
        view = self.puzzle.view
        size = view["size"]
        step, margin = (52, 34) if size >= 10 else (64, 42)
        self.hashi_xy = lambda key: (margin+int(key.split(',')[1])*step, margin+int(key.split(',')[0])*step)
        self.hashi_directions = {}
        self.hashi_hover_key = None
        end = margin+(size-1)*step
        for i in range(size):
            pos = margin+i*step
            self.canvas.create_line(margin, pos, end, pos, fill="#c3d6e2", width=1.5, tags=("hashi-grid",))
            self.canvas.create_line(pos, margin, pos, end, fill="#c3d6e2", width=1.5, tags=("hashi-grid",))
        for key, a, b in view["edges"]:
            self.register_click_value(key)
        for key, total in view["islands"]:
            x, y = self.hashi_xy(key)
            self.canvas.create_oval(x-22, y-22, x+22, y+22, fill="#fffef9", outline="#233a32", width=2.5,
                                    tags=("hashi-island", f"hashi-island:{key}"))
            self.canvas.create_text(x, y, text=str(total), font=("Helvetica", 15, "bold"), fill="#233a32",
                                    tags=("hashi-island", f"hashi-number:{key}"))
        self.canvas.create_text(20, end+32, text="Brücken per Klick: 0, 1, 2, 3; danach 2, 1, 0.", anchor="nw",
                                fill="#233a32", font=("Helvetica", 11, "bold"))
        self.canvas.configure(scrollregion=(0, 0, end+margin, end+60))
        self.canvas.bind("<Button-1>", self.click_hashi)
        self.canvas.bind("<Motion>", self.hover_hashi)
        self.canvas.bind("<Leave>", self.clear_hashi_hover)

    def clear_hashi_hover(self, event=None):
        self.hashi_hover_key = None
        self.canvas.delete("hashi-hover")
        self.canvas.configure(cursor="")

    def hashi_edge_at(self, x, y):
        candidates = []
        for key, a, b in self.puzzle.view["edges"]:
            x1, y1 = self.hashi_xy(a)
            x2, y2 = self.hashi_xy(b)
            if y1 == y2 and x1+28 <= x <= x2-28:
                distance = abs(y-y1)
            elif x1 == x2 and y1+28 <= y <= y2-28:
                distance = abs(x-x1)
            else:
                continue
            if distance <= 12:
                candidates.append((distance, key))
        candidates.sort()
        # A crossing of two possible paths does not select either path. Move
        # towards one island so that the intended connection is unambiguous.
        if not candidates or len(candidates) > 1 and abs(candidates[0][0]-candidates[1][0]) < 2:
            return None
        return candidates[0][1]

    def hover_hashi(self, event):
        if self.showing_solution or self.busy:
            self.clear_hashi_hover()
            return
        key = self.hashi_edge_at(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if key == getattr(self, 'hashi_hover_key', None):
            return
        self.clear_hashi_hover()
        self.hashi_hover_key = key
        self.canvas.configure(cursor="hand2" if key else "")
        if key:
            _, a, b = next(edge for edge in self.puzzle.view["edges"] if edge[0] == key)
            for line in bridge_segments(self.hashi_xy(a), self.hashi_xy(b), 1):
                self.canvas.create_line(*line, fill="#d9e8ed", width=13, tags=("hashi-hover",))
            self.canvas.tag_lower("hashi-hover", "hashi-island")
            if self.canvas.find_withtag("hashi-bridge"):
                self.canvas.tag_lower("hashi-hover", "hashi-bridge")

    def click_hashi(self, event):
        if self.showing_solution or self.busy:
            return
        key = self.hashi_edge_at(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if key is None:
            return
        if self.note_mode:
            if self.vars[key].get() in ("1", "2", "3"):
                return
            self.note_vars[key].set("" if self.note_vars[key].get() else "x")
            return
        count = int(self.vars[key].get() or 0)
        direction = self.hashi_directions.get(key, 1)
        if count == 3:
            direction = -1
        elif count == 0:
            direction = 1
        self.hashi_directions[key] = direction
        self.updating = True
        self.note_vars[key].set("")
        self.vars[key].set(str(count+direction) if count+direction else "")
        self.updating = False
        self.on_change()

    def paint_hashi(self):
        self.canvas.delete("hashi-bridge")
        self.canvas.delete("hashi-cross")
        for key, a, b in self.puzzle.view["edges"]:
            text = self.vars[key].get()
            count = int(text) if text in ("1", "2", "3") else 0
            for line in bridge_segments(self.hashi_xy(a), self.hashi_xy(b), count):
                self.canvas.create_line(*line, fill="#233a32", width=2.5,
                                        tags=("hashi-bridge", f"hashi-bridge:{key}"))
            if not count and self.note_vars[key].get() and not self.showing_solution:
                x1, y1 = self.hashi_xy(a)
                x2, y2 = self.hashi_xy(b)
                x, y = (x1+x2)/2, (y1+y2)/2
                for dy in (-7, 7):
                    self.canvas.create_line(x-7, y-dy, x+7, y+dy, fill="#8b9491", width=2,
                                            tags=("hashi-cross", f"hashi-cross:{key}"))
        self.canvas.tag_lower("hashi-bridge", "hashi-island")
