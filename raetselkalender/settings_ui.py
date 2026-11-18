"""Persistent audio/accessibility controls, without rebuilding a live board."""
import tkinter as tk
from tkinter import ttk

from .preferences import save_preferences


class SettingsUI:
    def open_settings(self):
        current=getattr(self,'settings_window',None)
        if current is not None and current.winfo_exists():current.lift();return
        window=self.settings_window=tk.Toplevel(self.root);window.title('Einstellungen');window.transient(self.root)
        body=ttk.Frame(window,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Siegsound',font=('Helvetica',15,'bold')).pack(anchor='w')
        volume=tk.DoubleVar(value=self.preferences['volume']);colorblind=tk.BooleanVar(value=self.preferences['colorblind'])
        label=ttk.Label(body);label.pack(anchor='w',pady=(8,0))
        def edit_volume(value=None):
            self.preferences['volume']=round(volume.get());label.configure(text=f'Lautstärke: {self.preferences["volume"]} % · 0 = stumm')
        self.volume_slider=ttk.Scale(body,from_=0,to=100,variable=volume,command=edit_volume,length=340)
        self.volume_slider.pack(fill='x',pady=8);edit_volume()
        ttk.Button(body,text='Ton testen',command=lambda:self.victory_sound.play(self.preferences['volume'])).pack(anchor='w')
        ttk.Separator(body).pack(fill='x',pady=16)
        def edit_colors():
            self.preferences['colorblind']=colorblind.get();self.paint_color_labels()
        self.colorblind_check=ttk.Checkbutton(body,text='Farbblindheitsmodus: Farben mit Buchstaben kennzeichnen',variable=colorblind,command=edit_colors)
        self.colorblind_check.pack(anchor='w')
        error=ttk.Label(body,text='',foreground='#9a3c30');error.pack(anchor='w',pady=(12,0))
        def close():
            edit_volume();edit_colors()
            if save_preferences(self.preferences,self.preferences_file):window.destroy();self.settings_window=None
            else:error.configure(text='Einstellungen konnten nicht gespeichert werden.')
        ttk.Button(body,text='Speichern und schließen',command=close).pack(anchor='e',pady=(10,0))
        window.protocol('WM_DELETE_WINDOW',close)
        self.settings_volume=volume;self.settings_colorblind=colorblind;self.save_settings=close
        window.update_idletasks()
        x=max(0,self.root.winfo_rootx()+(self.root.winfo_width()-window.winfo_reqwidth())//2)
        y=max(0,self.root.winfo_rooty()+(self.root.winfo_height()-window.winfo_reqheight())//2)
        window.geometry(f'+{x}+{y}')

    def paint_color_labels(self):
        self.canvas.delete('colorblind-label')
        if not self.preferences.get('colorblind') or self.puzzle is None:return
        v=self.puzzle.view;kind=v['kind'];mode=v.get('mode')
        def label(x,y,text,fill='#172d3a'):
            self.canvas.create_text(x,y,text=text,anchor='nw',fill=fill,font=('Helvetica',9,'bold'),
                                    tags=('colorblind-label',))
        if kind=='cats':
            left,top,step=self.matrix_geometry
            for i,group in enumerate(v['regions']):
                for key in group:
                    r,c=map(int,key.split(','));label(left+c*step+4,top+r*step+3,chr(65+i))
        elif kind=='activity' and mode=='sets':
            columns=4 if len(v['cards'])==12 else 5
            for i,card in enumerate(v['cards']):
                r,c=divmod(i,columns);label(34+c*128,76+r*132,chr(65+card[3]))
        elif kind=='activity' and mode=='water-sort':
            for i,tube in enumerate(self.activity_state['tubes']):
                for level,color in enumerate(tube):
                    label(48+i*105,330-(level+1)*240/v['capacity']+8,chr(65+color),'white')
        elif kind=='activity' and mode=='pipes':
            left,top,step=self.workshop_geometry
            for key,color in v['colors'].items():
                r,c=map(int,key.split(','));label(left+c*step+3,top+r*step+3,chr(65+color))
        # Superhirn and Pentomino already display their distinct letters.
