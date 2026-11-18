"""Interactive rectangle borders, kept separate from numeric cell input."""
import math
import tkinter as tk


class RectangleUI:
    def render_rectangles(self):
        view = self.puzzle.view
        rows, cols = view["rows"], view["cols"]
        self.borders = set()
        self.border_items = {}
        self.vars = {k: tk.StringVar() for k in self.puzzle.editable}
        step, left, top = 52, 28, 28
        self.canvas.create_rectangle(left, top, left+cols*step, top+rows*step,
                                     fill="#fffef9", outline="#233a32", width=3)
        for r in range(rows):
            for c in range(1, cols):
                self.add_border(("v", r, c), left+c*step, top+r*step, left+c*step, top+(r+1)*step)
        for r in range(1, rows):
            for c in range(cols):
                self.add_border(("h", r, c), left+c*step, top+r*step, left+(c+1)*step, top+r*step)
        for key, r, c, value in view["clues"]:
            self.canvas.create_text(left+(c+.5)*step, top+(r+.5)*step, text=str(value),
                fill="#233a32", font=("Helvetica", 17, "bold"))
        self.canvas.bind("<Button-1>", self.click_rectangle_edge)
        self.canvas.bind("<B1-Motion>", self.drag_rectangle_edge)
        self.canvas.bind("<ButtonRelease-1>", self.finish_rectangle_drag)
        self.canvas.create_text(left, top+rows*step+26, text="Rechteck aufziehen: Parzelle umranden. Einzelklick: Kante umschalten.",
            anchor="nw", fill="#63736a", font=("Helvetica", 11), width=cols*step)
        self.canvas.configure(scrollregion=(0, 0, left+cols*step+28, top+rows*step+70))

    def add_border(self, edge, x1, y1, x2, y2):
        line = self.canvas.create_line(x1, y1, x2, y2, width=1, fill="#d1d8cf")
        self.border_items[edge] = line

    def rectangle_edge_at(self, x, y, preferred_axis=None):
        x, y = x-28, y-28
        rows, cols = self.puzzle.view["rows"], self.puzzle.view["cols"]
        if not (0 <= x < cols*52 and 0 <= y < rows*52):
            return None
        vertical, horizontal = round(x/52), round(y/52)
        options = []
        if 0 < vertical < cols:
            options.append((abs(x-vertical*52), ("v", int(y//52), vertical)))
        if 0 < horizontal < rows:
            options.append((abs(y-horizontal*52), ("h", horizontal, int(x//52))))
        if not options:
            return None
        options.sort(key=lambda item: (item[0], item[1][0] != preferred_axis))
        if preferred_axis is None and len(options) == 2 and all(item[0] < .001 for item in options):
            return None
        if options[0][0] > 10:
            return None
        return options[0][1]

    def click_rectangle_edge(self, event):
        if self.showing_solution or self.busy:
            return
        self.finish_rectangle_drag()
        x,y = self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        rows,cols = self.puzzle.view["rows"],self.puzzle.view["cols"]
        if not (28 <= x <= 28+cols*52 and 28 <= y <= 28+rows*52):
            return
        self.border_drag_active = True
        self.rectangle_drag_start = (x,y)
        self.rectangle_drag_moved = False
        self.rectangle_drag_rect = None
        self.rectangle_click_edge = self.rectangle_edge_at(x,y)

    def selection_rectangle(self, x, y):
        """Cover the cells touched by the marquee in any dragging direction."""
        start_x,start_y = self.rectangle_drag_start
        rows,cols = self.puzzle.view["rows"],self.puzzle.view["cols"]
        def units(value):
            value = (value-28)/52
            nearest = round(value)
            return nearest if abs(value-nearest)*52 < 3 else value
        c1 = max(0,min(cols-1,math.floor(units(min(x,start_x)))))
        r1 = max(0,min(rows-1,math.floor(units(min(y,start_y)))))
        c2 = max(c1+1,min(cols,math.ceil(units(max(x,start_x)))))
        r2 = max(r1+1,min(rows,math.ceil(units(max(y,start_y)))))
        return r1,c1,r2-r1,c2-c1

    def drag_rectangle_edge(self, event):
        if not self.border_drag_active or self.showing_solution or self.busy:
            return
        x,y = self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        start_x,start_y = self.rectangle_drag_start
        if not self.rectangle_drag_moved and max(abs(x-start_x),abs(y-start_y)) < 5:
            return
        self.rectangle_drag_moved = True
        rect = self.selection_rectangle(x,y)
        self.rectangle_drag_rect = rect
        r,c,h,w = rect
        coords = (28+c*52,28+r*52,28+(c+w)*52,28+(r+h)*52)
        if self.canvas.find_withtag("rectangle-preview"):
            self.canvas.coords("rectangle-preview",*coords)
        else:
            self.canvas.create_rectangle(*coords,fill="#a9d2c0",stipple="gray25",outline="#27644c",
                                         width=2.5,dash=(5,3),tags=("rectangle-preview",))
            self.canvas.tag_lower("rectangle-preview",next(iter(self.border_items.values())))

    def rectangle_frame(self, rect):
        r,c,h,w = rect
        rows,cols = self.puzzle.view["rows"],self.puzzle.view["cols"]
        frame = {("v",rr,cc) for rr in range(r,r+h) for cc in (c,c+w) if 0 < cc < cols}
        frame |= {("h",rr,cc) for rr in (r,r+h) for cc in range(c,c+w) if 0 < rr < rows}
        inside = {("v",rr,cc) for rr in range(r,r+h) for cc in range(c+1,c+w)}
        inside |= {("h",rr,cc) for rr in range(r+1,r+h) for cc in range(c,c+w)}
        return frame,inside

    def finish_rectangle_drag(self, event=None):
        if not getattr(self,"border_drag_active",False):
            return
        if event is not None:
            self.drag_rectangle_edge(event)
        self.border_drag_active = False
        self.canvas.delete("rectangle-preview")
        if event is None or self.showing_solution or self.busy:
            return  # Escape, Undo and switching views cancel an unfinished box.
        if self.rectangle_drag_moved and self.rectangle_drag_rect is not None:
            frame,inside = self.rectangle_frame(self.rectangle_drag_rect)
            self.borders.difference_update(inside)
            self.borders.update(frame)
            self.refresh_borders()
            self.on_rectangle_change()
        elif self.rectangle_click_edge is not None:
            self.toggle_border(self.rectangle_click_edge)

    def toggle_border(self, edge):
        if self.showing_solution or self.busy:
            return
        self.borders.symmetric_difference_update({edge})
        self.refresh_borders()
        self.on_rectangle_change()

    def refresh_borders(self):
        for edge, item in self.border_items.items():
            self.canvas.itemconfigure(item, width=4 if edge in self.borders else 1,
                                      fill="#233a32" if edge in self.borders else "#d1d8cf")

    def rectangle_components(self):
        rows, cols = self.puzzle.view["rows"], self.puzzle.view["cols"]
        remaining = {(r, c) for r in range(rows) for c in range(cols)}
        regions = []
        while remaining:
            todo = [min(remaining)]
            region = set(todo)
            remaining.difference_update(region)
            while todo:
                r, c = todo.pop()
                for rr, cc, edge in ((r-1, c, ("h", r, c)), (r+1, c, ("h", r+1, c)),
                                     (r, c-1, ("v", r, c)), (r, c+1, ("v", r, c+1))):
                    if (rr, cc) in remaining and edge not in self.borders:
                        region.add((rr, cc))
                        remaining.remove((rr, cc))
                        todo.append((rr, cc))
            regions.append(region)
        return regions

    def on_rectangle_change(self):
        self.record_history()
        view = self.puzzle.view
        values = {}
        structural = True
        wrong = 0
        components = self.rectangle_components()
        owners = {point: i for i, region in enumerate(components) for point in region}
        stray = sum(owners[r, c-1] == owners[r, c] if axis == "v" else owners[r-1, c] == owners[r, c]
                    for axis, r, c in self.borders)
        for region in components:
            r, c = min(rr for rr, cc in region), min(cc for rr, cc in region)
            h, w = max(rr for rr, cc in region)-r+1, max(cc for rr, cc in region)-c+1
            clues = [(key, value) for key, rr, cc, value in view["clues"] if (rr, cc) in region]
            if h*w != len(region) or len(clues) != 1:
                structural = False
                continue
            key, value = clues[0]
            measured=h*w if view.get('rectangle_rule')=='area' else h+w
            if measured != value:
                wrong += 1
                continue
            rect = (r, c, h, w)
            options = [tuple(option) for option in view["candidates"][key]]
            if rect in options:
                values[key] = options.index(rect)
            else:
                wrong += 1
        for key, var in self.vars.items():
            var.set(str(values[key]) if key in values else "")
        if self.showing_solution:
            return
        if structural and stray:
            self.show_error_count(stray+wrong)
        elif structural and wrong:
            self.show_error_count(wrong)
        elif structural and self.puzzle.check(values)[0] == "correct":
            self.show_success()
        else:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text=f"{len(values)} von {len(self.vars)} Parzellen gültig · zeichne die fehlenden Grenzen ein.", foreground="#63736a")

    def solution_borders(self):
        owner = {}
        view = self.puzzle.view
        for key, index in self.puzzle.solution.items():
            r, c, h, w = view["candidates"][key][index]
            for rr in range(r, r+h):
                for cc in range(c, c+w):
                    owner[rr, cc] = key
        return ({("v", r, c) for r in range(view["rows"]) for c in range(1, view["cols"])
                 if owner[r, c] != owner[r, c-1]}
                | {("h", r, c) for r in range(1, view["rows"]) for c in range(view["cols"])
                   if owner[r, c] != owner[r-1, c]})

    def toggle_rectangle_solution(self):
        self.showing_solution = not self.showing_solution
        if self.showing_solution:
            self.saved_borders = self.borders.copy()
            self.borders = self.solution_borders()
            self.solution_button.configure(text="Zurück zu meinen Eingaben")
            self.reset_button.configure(state="disabled")
            self.status.configure(text="Lösungsansicht · deine eingezeichneten Grenzen bleiben erhalten.", foreground="#233a32")
        else:
            self.borders = self.saved_borders.copy()
            self.solution_button.configure(text="Lösung ansehen")
            self.reset_button.configure(state="normal")
        self.refresh_borders()
        self.on_rectangle_change()
