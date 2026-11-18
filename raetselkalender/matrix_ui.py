"""Click matrices for cats and letter equations, plus fixed-clue mines."""
from .notes_ui import note_values
from functools import lru_cache
import random

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'
COLORS=('#65b5f2','#f27c7f','#a4d65d','#bd87e4','#ffd252','#4dc9bb','#ffa450','#ed80bb','#94a2de','#b9c6cb')


@lru_cache(maxsize=64)
def contrasting_palette(count,adjacent):
    """Use distinct, saturated colours; separate neighbours as far as possible."""
    rgb=[tuple(int(color[i:i+2],16) for i in (1,3,5)) for color in COLORS[:count]]
    distances={(i,j):sum(weight*(a-b)**2 for weight,a,b in zip((1,2,1),rgb[i],rgb[j]))
               for i in range(count) for j in range(count)}
    order=list(range(count));best=None;rng=random.Random(0)
    for _ in range(256):
        rng.shuffle(order)
        differences=[distances[order[a],order[b]] for a,b in adjacent]
        score=min(differences,default=0),sum(differences)
        if best is None or score>best[0]:best=score,order.copy()
    return tuple(COLORS[i] for i in best[1])


class MatrixUI:
    def render_matrix(self):
        p,v=self.puzzle,self.puzzle.view
        n=v['size'];left,top,step=self.matrix_geometry=(48,48,58 if n<=7 else 50)
        cats=v['kind']=='cats'
        keys=list(p.model.domains)
        self.matrix_keys=keys
        owner={k:i for i,g in enumerate(v.get('regions',[])) for k in g}
        palette=()
        if cats:
            adjacent=set()
            for key,i in owner.items():
                r,c=map(int,key.split(','))
                for other in (f'{r+1},{c}',f'{r},{c+1}'):
                    if other in owner and owner[other]!=i:adjacent.add(tuple(sorted((i,owner[other]))))
            palette=contrasting_palette(n,tuple(sorted(adjacent)))
        for i in range(n):
            self.canvas.create_text(left+(i+.5)*step,top-20,text=str(i+1),fill=INK,font=('Helvetica',12,'bold'))
            self.canvas.create_text(left-22,top+(i+.5)*step,text=str(i+1) if cats else keys[i],fill=INK,font=('Helvetica',12,'bold'))
        for r in range(n):
            for c in range(n):
                x,y=left+c*step,top+r*step
                self.canvas.create_rectangle(x,y,x+step,y+step,
                    fill=palette[owner[f'{r},{c}']] if cats else PAPER,outline='#7b9386' if cats else '#b2bfb7',
                    tags=('matrix-cell',f'matrix-cell:{r},{c}'))
                if cats:
                    for neighbor,segment in ((f'{r-1},{c}',(x,y,x+step,y)),(f'{r},{c-1}',(x,y,x,y+step))):
                        if owner.get(neighbor)!=owner[f'{r},{c}']:
                            self.canvas.create_line(*segment,fill=INK,width=2.5,tags=('cat-region',))
        if cats:
            self.canvas.create_line(left+n*step,top,left+n*step,top+n*step,left,top+n*step,fill=INK,width=2.5,tags=('cat-region',))
        for key in keys:
            self.register_click_value(key)
        right=left+n*step+28
        if not cats:
            x=right+20
            for i,equation in enumerate(v['equations']):
                self.canvas.create_text(x,top+30+i*55,text=equation,anchor='w',fill=INK,font=('Helvetica',16,'bold'),tags=('logic-equation',))
            right+=260
        self.canvas.configure(scrollregion=(0,0,right,top+n*step+30),cursor='hand2')
        self.canvas.bind('<Button-1>',self.click_matrix)

    def click_matrix(self,event):
        if self.busy or self.showing_solution:
            return
        left,top,step=self.matrix_geometry;n=self.puzzle.view['size']
        c=int((self.canvas.canvasx(event.x)-left)//step)
        r=int((self.canvas.canvasy(event.y)-top)//step)
        if not (0<=r<n and 0<=c<n):
            return
        key=self.matrix_keys[r];value=str(c+1)
        if self.note_mode:
            marked=set(note_values(self.note_vars[key].get(),self.puzzle.model.domains[key]))
            if c+1 in marked:marked.remove(c+1)
            else:marked.add(c+1)
            self.note_vars[key].set(','.join(map(str,sorted(marked))))
        else:
            old=self.vars[key].get()
            self.updating=True
            if old==value:
                self.vars[key].set('')
            else:
                for other,var in self.vars.items():
                    if other!=key and var.get()==value:
                        var.set('')
                self.vars[key].set(value)
            self.updating=False
            self.on_change()

    def paint_matrix(self):
        self.canvas.delete('matrix-mark')
        left,top,step=self.matrix_geometry;n=self.puzzle.view['size']
        columns={var.get() for var in self.vars.values() if var.get()}
        cat_exclusions=set()
        if self.puzzle.view['kind']=='cats':
            cat_positions=set()
            for r,key in enumerate(self.matrix_keys):
                selected=self.vars[key].get()
                if selected:
                    c=int(selected)-1
                    cat_positions.add(f'{r},{c}')
                    cat_exclusions.update((rr,cc) for rr in (r-1,r+1) for cc in (c-1,c+1)
                                          if 0<=rr<n and 0<=cc<n)
            for region in self.puzzle.view['regions']:
                if cat_positions.intersection(region):
                    cat_exclusions.update(tuple(map(int,key.split(','))) for key in region)
        for r,key in enumerate(self.matrix_keys):
            selected=self.vars[key].get()
            notes=note_values(self.note_vars[key].get(),self.puzzle.model.domains[key])
            for c in range(n):
                x,y=left+(c+.5)*step,top+(r+.5)*step
                automatic=bool(selected or str(c+1) in columns or (r,c) in cat_exclusions)
                if selected==str(c+1):
                    if self.puzzle.view['kind']=='cats':
                        self.draw_cat(x,y,step*.28)
                    else:
                        self.canvas.create_oval(x-12,y-12,x+12,y+12,fill=ACCENT,outline='',tags=('matrix-mark','matrix-choice'))
                elif automatic or c+1 in notes and not self.showing_solution:
                    tag='matrix-auto-cross' if automatic else 'matrix-note-cross'
                    color=INK if self.puzzle.view['kind']=='cats' else '#75857c' if automatic else '#51755c'
                    for direction in (-1,1):
                        self.canvas.create_line(x-9,y-9*direction,x+9,y+9*direction,
                            fill=color,width=1.8,tags=('matrix-mark',tag,f'{tag}:{r},{c}'))

        self.paint_color_labels()

    def draw_cat(self,x,y,radius):
        tags=('matrix-mark','matrix-choice','cat-icon')
        self.canvas.create_polygon(x-radius,y-radius*.2,x-radius,y-radius*1.25,x-radius*.2,y-radius*.55,
            x+radius*.2,y-radius*.55,x+radius,y-radius*1.25,x+radius,y-radius*.2,fill=ACCENT,outline=INK,tags=tags)
        self.canvas.create_oval(x-radius,y-radius*.7,x+radius,y+radius*.85,fill=ACCENT,outline=INK,tags=tags)
        for direction in (-1,1):
            self.canvas.create_oval(x+direction*radius*.4-2,y-3,x+direction*radius*.4+2,y+1,fill=PAPER,outline='',tags=tags)
            for dy in (-.2,.2):
                self.canvas.create_line(x+direction*radius*.55,y+radius*.3,x+direction*radius*1.3,y+radius*(.3+dy),fill=INK,tags=tags)
        self.canvas.create_polygon(x-3,y+radius*.25,x+3,y+radius*.25,x,y+radius*.5,fill='#efc4b2',tags=tags)

    def on_matrix_change(self):
        self.paint_matrix()
        if self.note_mode:
            self.hide_success();self.dismiss_error();self.note_status();return
        values={}
        for key,var in self.vars.items():
            if var.get():
                try:values[key]=int(var.get())
                except ValueError:values[key]=-1
        if len(values)<len(self.vars):
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            noun='Katzen' if self.puzzle.view['kind']=='cats' else 'Zuordnungen'
            self.status.configure(text=f'{len(values)} von {len(self.vars)} {noun} gesetzt.',foreground=INK)
            return
        state,wrong=self.puzzle.check(values)
        if state=='correct':self.show_success()
        else:self.show_error_count(len(wrong) if wrong else sum(values[k] not in self.puzzle.model.domains[k] for k in values))

    def render_mines(self):
        v=self.puzzle.view;n=v['size']
        left,top,step=self.mine_geometry=28,28,58
        for r in range(n):
            for c in range(n):
                key=f'{r},{c}';x,y=left+c*step,top+r*step
                clue=key in v['labels']
                self.canvas.create_rectangle(x,y,x+step,y+step,fill='#edf0e7' if clue else PAPER,
                    outline='#b3c2b8',tags=('mine-cell',f'mine-cell:{key}'))
                if clue:
                    total=v['labels'][key]
                    self.canvas.create_text(x+step/2,y+step/2,text=str(total),
                        fill=('#738174','#306a9b','#27644c','#9b4840','#704d94','#85622a','#417b80','#233a32','#233a32')[total],
                        font=('Helvetica',20,'bold'),tags=('mine-clue',))
                else:self.register_click_value(key)
        self.canvas.configure(scrollregion=(0,0,left+n*step+28,top+n*step+28),cursor='hand2')
        self.canvas.bind('<Button-1>',self.click_mine)

    def click_mine(self,event):
        left,top,step=self.mine_geometry
        r=int((self.canvas.canvasy(event.y)-top)//step);c=int((self.canvas.canvasx(event.x)-left)//step)
        self.toggle_click_cell(f'{r},{c}')

    def paint_mines(self):
        self.canvas.delete('mine-mark')
        left,top,step=self.mine_geometry
        for key,var in self.vars.items():
            r,c=map(int,key.split(','));x,y=left+(c+.5)*step,top+(r+.5)*step
            tags=('mine-mark',f'mine-mark:{key}')
            if var.get()=='1':
                self.canvas.create_line(x-9,y+20,x-9,y-20,fill=INK,width=2,tags=tags+('mine-flag',))
                self.canvas.create_polygon(x-8,y-20,x+16,y-11,x-8,y-3,fill='#ae5950',outline=INK,tags=tags)
                self.canvas.create_line(x-17,y+20,x+3,y+20,fill=INK,width=2,tags=tags)
            elif self.note_vars[key].get() and not self.showing_solution:
                for direction in (-1,1):
                    self.canvas.create_line(x-13,y-13*direction,x+13,y+13*direction,fill='#738174',width=2,tags=tags+('mine-cross',))
