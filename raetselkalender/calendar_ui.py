"""Printed calendar clues and X/O cells without obscuring answer inputs."""

INK, ACCENT, PAPER = '#233a32', '#27644c', '#fffef9'


class CalendarUI:
    def render_nest(self):
        left, top, step = self.nest_geometry = 28, 28, 70
        view = self.puzzle.view
        owner = {key: i for i, group in enumerate(view['regions']) for key in group}
        for r in range(6):
            for c in range(6):
                key, x, y = f'{r},{c}', left+c*step, top+r*step
                shade = ('#fffef9', '#f0f3e9')[owner[key] % 2]
                self.canvas.create_rectangle(x, y, x+step, y+step, fill=shade, outline='#b9c6b7',
                                             tags=('nest-cell', f'nest-cell:{key}'))
                if key in view['labels']:
                    self.canvas.create_text(x+step/2, y+step/2, text=str(view['labels'][key]),
                        fill=INK, font=('Helvetica', 23, 'bold'), tags=('nest-clue',))
                else:
                    self.register_click_value(key)
                for dr, dc, segment in ((-1, 0, (x, y, x+step, y)), (0, -1, (x, y, x, y+step))):
                    if owner.get(f'{r+dr},{c+dc}') != owner[key]:
                        self.canvas.create_line(*segment, fill=INK, width=3, tags=('nest-boundary',))
        self.canvas.create_line(left+6*step, top, left+6*step, top+6*step, left, top+6*step,
                                fill=INK, width=3, tags=('nest-boundary',))
        self.canvas.configure(cursor='hand2', scrollregion=(0, 0, 476, 476))
        self.canvas.bind('<Button-1>', self.click_nest)

    def click_nest(self, event):
        left, top, step = self.nest_geometry
        r = int((self.canvas.canvasy(event.y)-top)//step)
        c = int((self.canvas.canvasx(event.x)-left)//step)
        self.toggle_click_cell(f'{r},{c}')

    def paint_nest(self):
        self.canvas.delete('nest-mark')
        left, top, step = self.nest_geometry
        for key, var in self.vars.items():
            r, c = map(int, key.split(','))
            x, y = left+(c+.5)*step, top+(r+.5)*step
            if var.get() == '1':
                # Vector artwork remains sharp at every board scale and needs
                # no platform-specific emoji font.
                tags = ('nest-mark', 'nest-egg', f'nest-egg:{key}')
                self.canvas.create_oval(x-17, y-23, x+17, y+23, fill='#f3d58a',
                                        outline='#8b642b', width=2, tags=tags)
                self.canvas.create_line(x-15, y+4, x-7, y-2, x, y+4, x+7, y-2, x+15, y+4,
                                        fill='#bc7845', width=2, tags=tags)
            elif self.note_vars[key].get() and not self.showing_solution:
                tags = ('nest-mark', 'nest-cross', f'nest-cross:{key}')
                self.canvas.create_line(x-16, y-16, x+16, y+16, fill='#7c8980', width=2, tags=tags)
                self.canvas.create_line(x+16, y-16, x-16, y+16, fill='#7c8980', width=2, tags=tags)

    def draw_calendar_marks(self, left, top, step, rows, cols):
        v, canvas = self.puzzle.view, self.canvas
        for cage in v.get('cage_sums',[]):
            present=set(cage['cells'])
            for key in cage['cells']:
                r,c=map(int,key.split(','));x,y=left+c*step,top+r*step
                for neighbor,segment in ((f'{r-1},{c}',(x+3,y+3,x+step-3,y+3)),
                    (f'{r+1},{c}',(x+3,y+step-3,x+step-3,y+step-3)),
                    (f'{r},{c-1}',(x+3,y+3,x+3,y+step-3)),
                    (f'{r},{c+1}',(x+step-3,y+3,x+step-3,y+step-3))):
                    if neighbor not in present:
                        canvas.create_line(*segment,fill=ACCENT,width=1.3,dash=(3,3),tags=('killer-cage',))
        for r, c, total in v.get('intersection_sums', []):
            x, y = left+(c+1)*step, top+(r+1)*step
            tags = ('mini-sum', f'mini-sum:{r},{c}')
            canvas.create_rectangle(x-20, y-17, x+20, y+17, fill='#dceaf0', outline=ACCENT, width=1.5, tags=tags)
            canvas.create_text(x, y, text=str(total), fill=INK, font=('Helvetica', 14, 'bold'), tags=tags)
        if 'diagonal_sums' in v:
            right, bottom = left+cols*step, top+rows*step
            for direction, total, sign, y in (('main', v['diagonal_sums'][0], 1, bottom),
                                            ('anti', v['diagonal_sums'][1], -1, top)):
                canvas.create_line(right-6, y-sign*6, right+25, y+sign*25, arrow='last', width=2,
                                   fill=INK, tags=('diagonal-arrow', f'diagonal-arrow:{direction}'))
                canvas.create_text(right+43, y+sign*43, text=str(total), fill=INK,
                                   font=('Helvetica', 17, 'bold'), tags=('diagonal-sum', f'diagonal-sum:{direction}'))
        if v.get('sum_cells'):
            for axis, hints in ((0, v['row_hints']), (1, v['col_hints'])):
                for i, hint in enumerate(hints):
                    x, y = (left+cols*step, top+i*step) if axis == 0 else (left+i*step, top+rows*step)
                    tags = ('sum-cell', f'sum-cell:{axis}:{i}')
                    canvas.create_rectangle(x, y, x+step, y+step, fill='#dceaf0', outline='#9aafb3', tags=tags)
                    canvas.create_text(x+step/2, y+step/2, text=str(hint[0]), font=('Helvetica', 17, 'bold'), fill=INK, tags=tags)
            canvas.create_line(left+cols*step, top, left+cols*step, top+rows*step, width=4, fill=INK)
            canvas.create_line(left, top+rows*step, left+cols*step, top+rows*step, width=4, fill=INK)
        for a, b in v.get('door_edges', []):
            r, c = map(int, a.split(','))
            rr, cc = map(int, b.split(','))
            x, y = left+(c+cc+1)*step/2, top+(r+rr+1)*step/2
            segment = (x, y-step/2+3, x, y+step/2-3) if r == rr else (x-step/2+3, y, x+step/2-3, y)
            tags = ('door-edge', f'door-edge:{a}:{b}')
            canvas.create_line(*segment, fill=PAPER, width=5, tags=tags)
            canvas.create_line(*segment, fill='#398db5', width=3, dash=(4, 3), tags=tags)

    def render_cheese(self):
        self.cheese_geometry = 28, 28, 48
        left, top, step = self.cheese_geometry
        for key in self.puzzle.view['cells']:
            r, c = map(int, key.split(','))
            x, y = left+c*step, top+r*step
            self.canvas.create_rectangle(x, y, x+step, y+step, fill=PAPER, outline='#aebdb1',
                                         tags=('cheese-cell', f'cheese-cell:{key}'))
            if key in self.puzzle.givens:
                self.canvas.create_text(x+step/2, y+step/2, text='X' if self.puzzle.givens[key] else 'O',
                                        fill=INK, font=('Helvetica', 22, 'bold'), tags=('cheese-given',))
            else:
                self.register_click_value(key)
        self.canvas.bind('<Button-1>', self.click_cheese)
        self.canvas.configure(cursor='hand2', scrollregion=(0, 0, 536, 536))

    def click_cheese(self, event):
        if self.busy or self.showing_solution:
            return
        left, top, step = self.cheese_geometry
        r = int((self.canvas.canvasy(event.y)-top)//step)
        c = int((self.canvas.canvasx(event.x)-left)//step)
        key = f'{r},{c}'
        if key not in self.vars:
            return
        if self.note_mode:
            if not self.vars[key].get():
                marks = ('', 'X', 'O', 'X,O')
                self.note_vars[key].set(marks[(marks.index(self.note_vars[key].get())+1) % 4])
        else:
            values = ('', '1', '0')
            self.updating = True
            self.note_vars[key].set('')
            self.vars[key].set(values[(values.index(self.vars[key].get())+1) % 3])
            self.updating = False
            self.on_change()

    def paint_cheese(self):
        self.canvas.delete('cheese-mark')
        left, top, step = self.cheese_geometry
        for key, var in self.vars.items():
            r, c = map(int, key.split(','))
            if var.get() in ('0', '1'):
                self.canvas.create_text(left+(c+.5)*step, top+(r+.5)*step,
                    text='X' if var.get() == '1' else 'O', fill=ACCENT, font=('Helvetica', 22, 'bold'),
                    tags=('cheese-mark', f'cheese-mark:{key}'))
            elif self.note_vars[key].get() and not self.showing_solution:
                self.canvas.create_text(left+c*step+4, top+r*step+4, text=self.note_vars[key].get(),
                    fill='#63736a', anchor='nw', font=('Helvetica', 9), tags=('cheese-mark',))
