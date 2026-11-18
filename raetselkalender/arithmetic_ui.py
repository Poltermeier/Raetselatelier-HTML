"""Vector symbols and a prominent final-answer panel for Rechenfreude."""
import math
import re

INK = "#233a32"
MUTED = "#63736a"
ACCENT = "#27644c"
COLORS = {"star": "#b58324", "moon": "#5375a2", "sun": "#c07a21",
          "heart": "#b85162", "diamond": "#8263a0", "triangle": "#5375a2", "pentagon": "#458270"}


class ArithmeticUI:
    def draw_arithmetic_symbol(self, name, x, y, radius=12):
        kind = self.puzzle.view["symbols"][name]
        color = COLORS[kind]
        tags = ("arithmetic-symbol", f"symbol:{kind}")
        if kind == "sun":
            for i in range(8):
                angle = i*math.pi/4
                self.canvas.create_line(x+radius*.75*math.cos(angle), y+radius*.75*math.sin(angle),
                    x+radius*1.12*math.cos(angle), y+radius*1.12*math.sin(angle),
                    fill=color, width=2, tags=tags)
            self.canvas.create_oval(x-radius*.58, y-radius*.58, x+radius*.58, y+radius*.58,
                fill=color, outline=color, tags=tags)
            return
        if kind == "star":
            points = [(x+(radius if i % 2 == 0 else radius*.43)*math.cos(-math.pi/2+i*math.pi/5),
                       y+(radius if i % 2 == 0 else radius*.43)*math.sin(-math.pi/2+i*math.pi/5))
                      for i in range(10)]
        elif kind == "diamond":
            points = [(x, y-radius), (x+radius*.8, y), (x, y+radius), (x-radius*.8, y)]
        elif kind == "triangle":
            points = [(x, y-radius), (x+radius, y+radius*.85), (x-radius, y+radius*.85)]
        elif kind == "pentagon":
            points = [(x+radius*math.cos(-math.pi/2+i*2*math.pi/5),
                       y+radius*math.sin(-math.pi/2+i*2*math.pi/5)) for i in range(5)]
        elif kind == "moon":
            points = [(x+radius*math.cos(math.radians(-60-i*12)),
                       y+radius*math.sin(math.radians(-60-i*12))) for i in range(21)]
            inner_radius = math.hypot(.05, math.sqrt(3)/2)
            start = math.atan2(math.sqrt(3)/2, -.05)
            points += [(x+radius*(.55+inner_radius*math.cos(start+i*(2*math.pi-2*start)/20)),
                        y+radius*inner_radius*math.sin(start+i*(2*math.pi-2*start)/20)) for i in range(21)]
        elif kind == "heart":
            raw = [(math.sin(t)**3, -(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)))
                   for t in (i*2*math.pi/60 for i in range(60))]
            low, high = min(v for u, v in raw), max(v for u, v in raw)
            points = [(x+radius*u, y+radius*(2*(v-low)/(high-low)-1)) for u, v in raw]
        else:
            raise ValueError(f"Unbekanntes Symbol: {kind}")
        self.canvas.create_polygon(*(coord for point in points for coord in point),
            fill=color, outline=color, width=1, tags=tags)

    def draw_symbol_formula(self, text, x, y, step=32):
        for i, token in enumerate(re.findall(r"\w+|[^\w\s]", text)):
            if token in self.puzzle.view["symbols"]:
                self.draw_arithmetic_symbol(token, x+i*step, y)
            else:
                self.canvas.create_text(x+i*step, y, text=token.replace("−", "-"),
                    fill=INK, font=("Helvetica", 17))

    def arithmetic_panel(self, x, y, width, height, *, fill, outline, tag):
        r = 10
        points = (x+r, y, x+width-r, y, x+width, y, x+width, y+r,
                  x+width, y+height-r, x+width, y+height, x+width-r, y+height,
                  x+r, y+height, x, y+height, x, y+height-r, x, y+r, x, y)
        self.canvas.create_polygon(*points, smooth=True, splinesteps=16,
            fill=fill, outline=outline, width=2, tags=(tag,))

    def render_arithmetic(self):
        p, view = self.puzzle, self.puzzle.view
        self.canvas.create_text(28, 24, text="DIE SYMBOLGLEICHUNGEN", anchor="nw", fill=MUTED,
                                font=("Helvetica", 10, "bold"))
        for i, equation in enumerate(view["equations"]):
            self.draw_symbol_formula(equation, 46+(i % 2)*320, 65+(i//2)*48)
        y = 65+((len(view["equations"])+1)//2)*48+16
        self.canvas.create_text(28, y, text="DEINE SYMBOLWERTE", anchor="nw", fill=MUTED,
                                font=("Helvetica", 10, "bold"))
        top = y+24
        for i, name in enumerate(view["symbols"]):
            slot = 620/len(view["symbols"])
            x = 28+i*slot
            self.arithmetic_panel(x, top, slot-10, 85, fill="#fffef9", outline="#d1d8cf", tag="symbol-card")
            self.draw_arithmetic_symbol(name, x+(slot-10)/2, top+23, 14)
            self.add_entry(name, x+(slot-10)/2, top+61, 36)
        final_top = top+108
        self.arithmetic_panel(28, final_top, 620, 156, fill="#edf3e8", outline=ACCENT, tag="final-answer-panel")
        self.canvas.create_text(48, final_top+18, text="DIE SCHLUSSFORMEL", anchor="nw", fill=ACCENT,
                                font=("Helvetica", 11, "bold"))
        self.draw_symbol_formula(view["expression"], 48, final_top+76, step=44 if len(view["symbols"]) == 4 else 28)
        self.canvas.create_text(368, final_top+76, text="=", fill=INK, font=("Helvetica", 22))
        self.canvas.create_text(520, final_top+25, text="DEIN ERGEBNIS", fill=ACCENT,
                                font=("Helvetica", 10, "bold"))
        self.add_entry("Ergebnis", 520, final_top+76, 56, width=150, font_size=26)
        self.canvas.create_text(48, final_top+126, text="Setze die ermittelten Zahlen in die Schlussformel ein.",
                                anchor="nw", fill=MUTED, font=("Helvetica", 10))
        self.canvas.configure(scrollregion=(0, 0, 680, final_top+178))
