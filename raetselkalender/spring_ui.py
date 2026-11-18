"""Lantern/Hitori click grids and statement boxes with speech bubbles."""
import tkinter as tk
from tkinter import ttk

from .notes_ui import note_values

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'


class SpringUI:
    def render_symbol_grid(self):
        v=self.puzzle.view;n=v['size'];left,top,step=self.symbol_geometry=(28,28,62)
        for r in range(n):
            for c in range(n):
                key=f'{r},{c}';x,y=left+c*step,top+r*step
                house=key in v['labels']
                self.canvas.create_rectangle(x,y,x+step,y+step,fill=INK if house else PAPER,
                    outline='#aabbb0',tags=('symbol-cell',f'symbol-cell:{key}'))
                if house:
                    self.canvas.create_text(x+step/2,y+step/2,text=str(v['labels'][key]),fill='white',
                        font=('Helvetica',20,'bold'),tags=('symbol-house',))
                else:self.register_click_value(key)
        self.symbol_check_button=ttk.Button(self.canvas,text='Fertig – prüfen',command=self.check_symbol_grid,style='Accent.TButton')
        self.extra_widgets.append(self.symbol_check_button)
        self.canvas.create_window(left+n*step/2,top+n*step+34,window=self.symbol_check_button,width=210,height=38)
        self.canvas.configure(scrollregion=(0,0,left+n*step+28,top+n*step+68),cursor='hand2')
        self.canvas.bind('<Button-1>',self.click_symbol_grid)
        self.paint_symbol_grid()

    def click_symbol_grid(self,event):
        if self.busy or self.showing_solution:return
        left,top,step=self.symbol_geometry
        r=int((self.canvas.canvasy(event.y)-top)//step);c=int((self.canvas.canvasx(event.x)-left)//step)
        key=f'{r},{c}'
        if key not in self.vars:return
        var=self.note_vars[key] if self.note_mode else self.vars[key]
        var.set('' if var.get() else 'x' if self.note_mode else '1')

    def paint_symbol_grid(self):
        self.canvas.delete('symbol-mark')
        v=self.puzzle.view;left,top,step=self.symbol_geometry
        for key,var in self.vars.items():
            r,c=map(int,key.split(','));x,y=left+(c+.5)*step,top+(r+.5)*step
            marked=var.get()=='1'
            if v['mode']=='hitori':
                self.canvas.itemconfigure(f'symbol-cell:{key}',fill=INK if marked else PAPER)
                self.canvas.create_text(x,y,text=str(v['numbers'][key]),fill='#dce4dc' if marked else INK,
                    font=('Helvetica',20,'bold'),tags=('symbol-mark','hitori-number'))
            elif marked:
                self.canvas.create_oval(x-13,y-18,x+13,y+8,fill='#ffda59',outline=INK,width=2,tags=('symbol-mark','lantern'))
                self.canvas.create_line(x,y+8,x,y+22,x-9,y+22,x+9,y+22,fill=INK,width=3,tags=('symbol-mark',))
            if self.note_vars[key].get() and not marked and not self.showing_solution:
                if v['mode']=='hitori':
                    self.canvas.create_oval(x-20,y-20,x+20,y+20,outline='#61796c',width=2,tags=('symbol-mark','symbol-note'))
                else:
                    for direction in (-1,1):
                        self.canvas.create_line(x+step*.19,y+step*.19*direction,x+step*.36,y+step*.36*direction,
                            fill='#61796c',width=2,tags=('symbol-mark','symbol-note'))
        self.symbol_check_button.configure(state='disabled' if self.busy or self.showing_solution or self.note_mode else 'normal')

    def on_symbol_change(self):
        self.paint_symbol_grid()
        if self.note_mode:
            self.hide_success();self.dismiss_error();self.note_status();return
        values={k:int(var.get()=='1') for k,var in self.vars.items()}
        if self.puzzle.check(values)[0]=='correct':self.show_success()
        else:
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            self.status.configure(text='Markierungen werden übernommen · mit „Fertig – prüfen“ prüfen.',foreground=INK)

    def check_symbol_grid(self):
        if self.busy or self.showing_solution or self.note_mode:return
        values={k:int(var.get()=='1') for k,var in self.vars.items()}
        state,wrong=self.puzzle.check(values)
        if state=='correct':self.show_success()
        else:self.show_error_count(len(wrong))

    def render_treasure(self):
        n=self.puzzle.view['size'];step=178
        self.treasure_geometry=28,28,step
        self.register_click_value('Schatz')
        for i,text in enumerate(self.puzzle.view['statements']):
            x=28+i*step
            self.canvas.create_rectangle(x,28,x+step-14,166,fill='#eef3ee',outline='#8da795',width=2,
                                         tags=('treasure-bubble',))
            self.canvas.create_polygon(x+60,166,x+77,184,x+87,166,fill='#eef3ee',outline='#8da795',tags=('treasure-bubble',))
            self.canvas.create_text(x+12,42,text=text,anchor='nw',width=step-38,fill=INK,
                                    font=('Helvetica',11),tags=('treasure-statement',))
            self.draw_treasure_person(x+80,207,i)
            self.canvas.create_text(x+80,287,text=f'Person {chr(65+i)}',fill=INK,font=('Helvetica',12,'bold'))
        self.canvas.configure(scrollregion=(0,0,28+n*step,430),cursor='hand2')
        self.canvas.bind('<Button-1>',self.click_treasure)
        self.paint_treasure()

    def draw_treasure_person(self,x,y,index):
        tags=('treasure-person',f'treasure-person:{index}')
        skin=('#edc39d','#b77c54','#d7a77e','#f1cdb2','#996341')[index]
        shirt=('#32658d','#9c4c75','#44784e','#9a6c31','#6c55a0')[index]
        hair=('#49372d','#2e2522','#8b5832','#694633','#211d1d')[index]
        for direction in (-1,1):
            self.canvas.create_line(x+direction*8,y+44,x+direction*9,y+62,fill='#344954',width=9,tags=tags)
            self.canvas.create_oval(x+direction*9-8,y+59,x+direction*9+8,y+66,fill='#293238',outline='',tags=tags)
            self.canvas.create_line(x+direction*15,y+28,x+direction*28,y+45,fill=shirt,width=10,tags=tags)
            self.canvas.create_oval(x+direction*28-4,y+42,x+direction*28+4,y+50,fill=skin,outline='',tags=tags)
        self.canvas.create_rectangle(x-6,y+14,x+6,y+28,fill=skin,outline='',tags=tags)
        self.canvas.create_polygon(x-16,y+24,x+16,y+24,x+19,y+48,x-19,y+48,fill=shirt,outline=INK,tags=tags)
        self.canvas.create_oval(x-19,y-20,x+19,y+20,fill=skin,outline=INK,width=1.5,tags=tags)
        self.canvas.create_arc(x-20,y-22,x+20,y+18,start=15,extent=155,fill=hair,outline=hair,width=5,tags=tags)
        for direction in (-1,1):
            self.canvas.create_oval(x+direction*7-2,y-3,x+direction*7+2,y+1,fill='#202a2d',outline='',tags=tags+('treasure-eyes',))
        self.canvas.create_line(x,y+2,x-2,y+8,x+2,y+8,fill='#99684a',width=1,tags=tags)
        self.canvas.create_arc(x-7,y+5,x+7,y+15,start=200,extent=140,style='arc',outline='#804c3a',width=1.5,tags=tags)

    def paint_treasure(self):
        self.canvas.delete('treasure-choice')
        selected=self.vars['Schatz'].get();notes=note_values(self.note_vars['Schatz'].get(),self.puzzle.model.domains['Schatz'])
        for i in range(self.puzzle.view['size']):
            x=28+i*178;active=selected==str(i)
            self.canvas.create_rectangle(x+26,314,x+134,390,fill='#e4bd80' if not active else '#aad2b6',
                outline=ACCENT if active else '#74502c',width=4 if active else 2,tags=('treasure-choice',f'treasure-box:{i}'))
            self.canvas.create_line(x+26,334,x+134,334,fill='#74502c',width=3,tags=('treasure-choice',))
            self.canvas.create_text(x+80,362,text=chr(65+i),fill=INK,font=('Helvetica',22,'bold'),tags=('treasure-choice',))
            if i in notes and not self.showing_solution and not active:
                for direction in (-1,1):
                    self.canvas.create_line(x+40,350-20*direction,x+120,350+20*direction,fill='#61796c',width=3,tags=('treasure-choice',))

    def click_treasure(self,event):
        if self.busy or self.showing_solution:return
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        i=int((x-28)//178)
        if not (0<=i<self.puzzle.view['size'] and 314<=y<=390):return
        if self.note_mode:
            notes=set(note_values(self.note_vars['Schatz'].get(),self.puzzle.model.domains['Schatz']))
            notes.symmetric_difference_update({i});self.note_vars['Schatz'].set(','.join(map(str,sorted(notes))))
        else:self.vars['Schatz'].set('' if self.vars['Schatz'].get()==str(i) else str(i))

    def on_treasure_change(self):
        self.paint_treasure()
        selected=self.vars['Schatz'].get()
        if self.note_mode:
            self.hide_success();self.dismiss_error();self.note_status();return
        if selected=='':
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            self.status.configure(text='Wähle die Kiste mit dem Schatz.',foreground=INK);return
        state,wrong=self.puzzle.check({'Schatz':int(selected)})
        if state=='correct':self.show_success()
        else:self.show_error_count(len(wrong))
