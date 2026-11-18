"""Paint Sudoku diagonals through native input fields without a redraw timer."""
import tkinter as tk
from tkinter import font as tkfont

from .notes_ui import note_values

DIAGONAL_COLOR='#367db8'
WINDOW_COLOR='#9fc5eb'


class DiagonalUI:
    def register_diagonal_entry(self,key):
        entry=self.entries[key]
        overlay=tk.Canvas(entry,highlightthickness=0,borderwidth=0,takefocus=False,cursor='xterm')
        overlay.place(x=0,y=0,relwidth=1,relheight=1,bordermode='outside')
        self.diagonal_overlays[key]=overlay
        def select(event):
            entry.focus_set();entry.selection_range(0,'end');entry.icursor('end')
            self.refresh_diagonal_entry(key)
            return 'break'
        overlay.bind('<Button-1>',select)
        overlay.bind('<Double-Button-1>',select)
        for event in ('<Configure>','<FocusIn>','<FocusOut>','<KeyRelease>'):
            entry.bind(event,lambda event,k=key:self.refresh_diagonal_entry(k),add='+')
        self.vars[key].trace_add('write',lambda *args,k=key:self.refresh_diagonal_entry(k))
        self.note_vars[key].trace_add('write',lambda *args,k=key:self.refresh_diagonal_entry(k))
        self.refresh_diagonal_entry(key)

    def refresh_diagonal_entries(self):
        for key in getattr(self,'diagonal_overlays',{}):self.refresh_diagonal_entry(key)

    def refresh_diagonal_entry(self,key):
        overlay=getattr(self,'diagonal_overlays',{}).get(key)
        if overlay is None or not overlay.winfo_exists():return
        entry=self.entries[key];zoom=self.canvas.zoom
        width,height=entry.winfo_width(),entry.winfo_height()
        bg=entry.cget('readonlybackground') if str(entry.cget('state'))=='readonly' else entry.cget('bg')
        overlay.configure(bg=bg);overlay.delete('all')
        overlay.tk.call('raise',str(overlay))
        # Canvas scrolling and zoom are measured in physical pixels here, so
        # the inset lines join the main drawing at precisely the same point.
        offset_x=entry.winfo_x()+float(tk.Canvas.canvasx(self.canvas,0))
        offset_y=entry.winfo_y()+float(tk.Canvas.canvasy(self.canvas,0))
        for a,b,c,d in self.diagonal_segments:
            overlay.create_line(a*zoom-offset_x,b*zoom-offset_y,c*zoom-offset_x,d*zoom-offset_y,
                                fill=DIAGONAL_COLOR,width=4*zoom,tags=('diagonal-through-entry',))
        value=self.vars[key].get();focused=self.root.focus_get() is entry
        if value:
            overlay.create_text(width/2,height/2,text=value,fill=entry.cget('fg'),font=entry.cget('font'))
        elif self.note_mode:
            text=self.note_vars[key].get()
            overlay.create_text(2,1,text=text,anchor='nw',fill=entry.cget('fg'),font=entry.cget('font'))
        elif not self.showing_solution:
            values=note_values(self.note_vars[key].get(),self.puzzle.model.domains[key])
            parts=[str(v) for v in values[:9]]
            text=',\n'.join(','.join(parts[i:i+3]) for i in range(0,len(parts),3))
            overlay.create_text(1,1,text=text,anchor='nw',fill='#63736a',font=('Helvetica',max(6,round(7*zoom))))
        if focused and not self.showing_solution:
            overlay.create_rectangle(1,1,max(2,width-1),max(2,height-1),outline='#175ba2',width=max(1,zoom))
            # A static caret gives a clear insertion point without an idle timer.
            if not entry.selection_present():
                font=tkfont.Font(entry,font=entry.cget('font'))
                text=self.note_vars[key].get() if self.note_mode and not value else value
                x=(2+font.measure(text) if self.note_mode and not value else width/2+font.measure(text)/2+1)
                cy=height/2
                overlay.create_line(x,max(2,cy-7*zoom),x,min(height-2,cy+7*zoom),fill='#175ba2')
