"""Calendar camping board with trees, clickable tents and bottom/right counts."""

INK = "#233a32"


class CampingUI:
    def render_camping(self):
        view = self.puzzle.view
        self.camping_step, self.camping_margin = 54, 28
        self.camping_xy = lambda key: (28+(int(key.split(',')[1])+.5)*54, 28+(int(key.split(',')[0])+.5)*54)
        trees = set(view["trees"])
        for r in range(7):
            for c in range(7):
                key = f"{r},{c}"
                x, y = self.camping_xy(key)
                self.canvas.create_rectangle(x-27,y-27,x+27,y+27,fill="#fffef9",outline="#aebdb1",
                                             tags=("camping-cell",f"camping-cell:{key}"))
                if key in trees:
                    self.canvas.create_line(x,y+5,x,y+18,fill="#79562f",width=4,tags=("camping-tree",))
                    self.canvas.create_oval(x-15,y-17,x+15,y+12,fill="#5f8a66",outline="#3f6746",width=2,
                                            tags=("camping-tree",))
                else:
                    self.register_click_value(key)
        for r, hint in enumerate(view["row_hints"]):
            self.canvas.create_text(28+7*54+23,28+(r+.5)*54,text=str(hint[0]),fill=INK,
                                    font=("Helvetica",13,"bold"),tags=("camping-row-hint",))
        for c, hint in enumerate(view["col_hints"]):
            self.canvas.create_text(28+(c+.5)*54,28+7*54+23,text=str(hint[0]),fill=INK,
                                    font=("Helvetica",13,"bold"),tags=("camping-col-hint",))
        self.canvas.create_text(28,28+7*54+56,text="Klicken: Zelt setzen / entfernen. Notizen: Wiese durchstreichen.",
                                anchor="nw",fill=INK,font=("Helvetica",11),width=470)
        self.canvas.configure(scrollregion=(0,0,520,510),cursor="hand2")
        self.canvas.bind("<Button-1>",self.click_camping)

    def click_camping(self, event):
        x,y = self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        r,c = int((y-28)//54),int((x-28)//54)
        self.toggle_click_cell(f"{r},{c}")

    def paint_camping(self):
        self.canvas.delete("camping-mark")
        for key,var in self.vars.items():
            x,y = self.camping_xy(key)
            self.canvas.itemconfigure(f"camping-cell:{key}",fill="#fffef9")
            if var.get() == "1":
                tags=("camping-mark","camping-tent",f"camping-tent:{key}")
                self.canvas.create_polygon(x,y-18,x-21,y+18,x+21,y+18,fill="#e6bd74",outline="#80552f",width=2,tags=tags)
                self.canvas.create_polygon(x,y-7,x-8,y+18,x+8,y+18,fill="#80552f",outline="#80552f",tags=tags)
            elif self.note_vars[key].get() and not self.showing_solution:
                tags=("camping-mark","camping-cross",f"camping-cross:{key}")
                self.canvas.create_line(x-15,y-15,x+15,y+15,fill="#8b9491",width=2,tags=tags)
                self.canvas.create_line(x+15,y-15,x-15,y+15,fill="#8b9491",width=2,tags=tags)
