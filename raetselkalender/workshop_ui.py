"""Interactive cryptograms, arithmetic, circuits, tilings, shifts and pipes."""
import math
import tkinter as tk
from .board_canvas import BoardEntry

from .pentomino_ui import PentominoDragUI
from .pentomino import transform_shape
from .pipes import rotate_pipe,STEPS
from .workshop_games import ALPHABET,shift_board,slide_targets

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'


class WorkshopUI(PentominoDragUI):
    def initial_workshop_state(self):
        v=self.puzzle.view;mode=v['mode'];state={'moves':[]}
        if mode=='crypto':state['values']={k:'' for k in self.puzzle.editable}
        elif mode=='target24':state['expression']=''
        elif mode=='circuit':state['values']={k:None for k in v['inputs']}
        elif mode=='pipes':state['values']=v['initial'].copy()
        elif mode=='pentomino':state['placements']={}
        else:state['board']=v['initial'].copy()
        return state

    def workshop_entry(self,x,y,width,variable,callback,*,key,letter=False):
        entry=BoardEntry(self.canvas,textvariable=variable,font=('Helvetica',17),justify='center',
                       relief='solid',borderwidth=1,bg=PAPER,fg=INK)
        if letter:
            validate=self.root.register(lambda text:not text or len(text)==1 and len(text.upper())==1 and text.upper() in ALPHABET)
            entry.configure(validate='key',validatecommand=(validate,'%P'))
        self.extra_widgets.append(entry);self.activity_controls.append(entry)
        self.canvas.create_window(x,y,window=entry,width=width,height=38,
                                  tags=('activity-controls',f'assist-field:{key}'))
        self.workshop_entries_ui[key] = entry
        variable.trace_add('write',lambda *args:callback())
        entry.bind('<Return>',lambda event:self.check_workshop() or 'break')
        return entry

    def render_workshop(self):
        self.workshop_entries_ui = {}
        self.workshop_variables={};self.workshop_turns=0;self.workshop_mirror=False;self.workshop_hitboxes=[]
        mode=self.puzzle.view['mode'];v=self.puzzle.view
        if mode=='crypto':
            for i,key in enumerate(self.puzzle.model.domains):
                if key in self.puzzle.givens:continue
                r,c=divmod(i,8);variable=tk.StringVar();self.workshop_variables[key]=variable
                self.workshop_entry(67+c*86,309+r*94,55,variable,lambda k=key:self.edit_workshop_text(k),key=key,letter=True)
            bottom=280+math.ceil(len(self.puzzle.model.domains)/8)*94
            self.activity_button('Satz prüfen',self.check_workshop,350,bottom+35)
        elif mode=='target24':
            variable=tk.StringVar();self.workshop_variables['expression']=variable
            self.workshop_entry(338,273,610,variable,lambda:self.edit_workshop_text('expression'),key='expression')
            self.activity_button('Ausdruck prüfen',self.check_workshop,338,335)
        elif mode=='pipes':
            n=v['size'];step=60 if n==4 else 50 if n==5 else 44 if n==7 else 38 if n==10 else 32 if n==12 else 28 if n==15 else 24
            self.workshop_geometry=28,70,step
            self.activity_button('Verbindungen prüfen',self.check_workshop,28+n*step/2,70+n*step+30)
            self.canvas.bind('<Button-3>',lambda event:self.click_workshop(event,reverse=True))
        elif mode=='row-shift':
            self.row_shift_solution_states=();self.row_shift_solution_step=0;self.row_shift_navigation=[]
            for label,command,x in (
                ('Anfang',lambda:self.show_row_shift_step(0),102),
                ('Zurück',lambda:self.show_row_shift_step(self.row_shift_solution_step-1),264),
                ('Weiter',lambda:self.show_row_shift_step(self.row_shift_solution_step+1),426),
                ('Ziel',lambda:self.show_row_shift_step(len(self.row_shift_solution_states)-1),588)):
                self.row_shift_navigation.append(self.activity_button(label,command,x,480,145,tags=('shift-solution-controls',)))
        elif mode=='pentomino':
            self.workshop_geometry=28,80,38;right=28+v['cols']*38+32
            self.activity_button('Drehen (R)',lambda:self.transform_workshop(),right+110,520,170)
            self.activity_button('Spiegeln (M)',lambda:self.transform_workshop(mirror=True),right+110,565,170)
            self.canvas.bind('<KeyPress-r>',lambda event:self.transform_workshop())
            self.canvas.bind('<KeyPress-R>',lambda event:self.transform_workshop())
            self.canvas.bind('<KeyPress-m>',lambda event:self.transform_workshop(mirror=True))
            self.canvas.bind('<KeyPress-M>',lambda event:self.transform_workshop(mirror=True))
        if mode=='pentomino':
            self.pentomino_drag=None
            self.canvas.bind('<Button-1>',self.start_pentomino_drag)
            self.canvas.bind('<B1-Motion>',self.move_pentomino_drag)
            self.canvas.bind('<ButtonRelease-1>',self.finish_pentomino_drag)
        else:self.canvas.bind('<Button-1>',self.click_activity)
        self.paint_workshop()

    def edit_workshop_text(self,key):
        if self.updating or self.busy or self.showing_solution:return
        text=self.workshop_variables[key].get()
        if self.puzzle.view['mode']=='crypto':self.activity_state['values'][key]=text.upper()
        else:self.activity_state['expression']=text
        self.on_change()

    def sync_workshop_text(self):
        old=self.updating;self.updating=True
        try:
            for key,var in self.workshop_variables.items():
                value=self.activity_state['expression'] if key=='expression' else self.activity_state['values'].get(key,'')
                if self.puzzle.view['mode']=='crypto' and var.get().upper()==value:continue
                if var.get()!=value:var.set(value)
        finally:self.updating=old

    def paint_workshop(self):
        self.canvas.delete('activity-board');self.workshop_hitboxes=[];self.sync_workshop_text()
        mode=self.puzzle.view['mode']
        if mode=='crypto':self.paint_crypto()
        elif mode=='target24':self.paint_target24()
        elif mode=='circuit':self.paint_circuit()
        elif mode=='pipes':self.paint_pipes()
        elif mode=='pentomino':self.paint_pentomino()
        else:self.paint_row_shift()
        self.paint_color_labels();self.update_activity_controls()
        if mode=='pentomino':self.paint_pentomino_drag()

    def paint_crypto(self):
        p=self.puzzle;v=p.view
        self.activity_text(28,22,'Thema: '+v['theme'])
        self.canvas.create_text(28,65,text=v['ciphertext'],width=690,anchor='nw',fill=INK,font=('Courier',15,'bold'),tags=('activity-board','crypto-cipher'))
        values={k:ALPHABET.index(text) for k,text in self.activity_state['values'].items() if text in ALPHABET and len(text)==1}
        decoded=p.decoded(values)
        self.canvas.create_text(28,165,text=decoded,width=690,anchor='nw',fill=ACCENT,font=('Courier',15,'bold'),tags=('activity-board','crypto-decoded'))
        for i,key in enumerate(p.model.domains):
            r,c=divmod(i,8);x,y=67+c*86,270+r*94
            self.canvas.create_text(x,y,text=key,fill=INK,font=('Helvetica',15,'bold'),tags=('activity-board',))
            self.canvas.create_text(x,y+69,text=f'{v["frequencies"][key]} ×',fill='#63736a',font=('Helvetica',10),tags=('activity-board',))
            if key in p.givens:
                self.canvas.create_rectangle(x-27,y+20,x+27,y+58,fill='#dcebdc',outline=ACCENT,tags=('activity-board',))
                self.canvas.create_text(x,y+39,text=ALPHABET[p.givens[key]],fill=INK,font=('Helvetica',17,'bold'),tags=('activity-board','crypto-given'))
        bottom=280+math.ceil(len(p.model.domains)/8)*94
        self.canvas.configure(scrollregion=(0,0,745,bottom+70),cursor='')

    def paint_target24(self):
        v=self.puzzle.view
        self.activity_text(28,24,'Vier Zahlen · jede genau einmal')
        for i,number in enumerate(v['numbers']):
            x=28+i*136
            self.canvas.create_rectangle(x,77,x+112,183,fill='#e6eff7',outline='#476d8c',width=2,tags=('activity-board','target-card'))
            self.canvas.create_text(x+56,130,text=str(number),fill=INK,font=('Helvetica',35,'bold'),tags=('activity-board',))
        self.activity_text(605,97,'Ziel: 24')
        self.activity_text(28,218,'Dein Ausdruck:')
        if self.showing_solution:self.activity_text(28,395,'Beispiel einer gültigen Lösung · andere Ausdrücke zählen ebenfalls.')
        else:self.activity_text(28,395,'Addition +  ·  Subtraktion -  ·  Multiplikation *  ·  Division /  ·  Klammern ( )')
        self.canvas.configure(scrollregion=(0,0,760,465),cursor='')

    def paint_circuit(self):
        v=self.puzzle.view;coords={key:(60,95+i*70) for i,key in enumerate(v['inputs'])}
        coords.update({g['id']:(215+g['layer']*165,95+g['row']*125) for g in v['gates']})
        for gate in v['gates']:
            x,y=coords[gate['id']]
            for i,source in enumerate(gate['inputs']):
                sx,sy=coords[source];end=y+(i-.5)*18 if len(gate['inputs'])==2 else y;middle=x-54-i*8
                self.canvas.create_line(sx+35,sy,middle,sy,middle,end,x-38,end,fill='#668477',width=2,tags=('activity-board','circuit-wire'))
        for key in v['inputs']:
            x,y=coords[key];value=self.activity_state['values'].get(key)
            self.canvas.create_text(x-40,y,text=key,fill=INK,font=('Helvetica',13,'bold'),tags=('activity-board',))
            self.canvas.create_rectangle(x-22,y-22,x+27,y+22,fill='#e6eff7',outline='#3572a0',width=2,
                                         tags=('activity-board','circuit-input',f'circuit-input:{key}'))
            self.canvas.create_text(x+2,y,text='?' if value is None else str(value),fill=INK,font=('Helvetica',20,'bold'),tags=('activity-board',))
            self.workshop_hitboxes.append((x-22,y-22,x+27,y+22,('input',key)))
        for gate in v['gates']:
            x,y=coords[gate['id']]
            output=gate['id'] in v.get('output_targets',())
            self.canvas.create_rectangle(x-38,y-24,x+38,y+24,fill='#e5eff9' if output else PAPER,outline='#175ba2' if output else INK,width=2.5 if output else 2,tags=('activity-board','circuit-gate'))
            self.canvas.create_text(x,y,text=gate['op'],fill=INK,font=('Helvetica',12,'bold'),tags=('activity-board',))
            self.canvas.create_text(x,y-36,text=gate['id']+' : '+', '.join(gate['inputs']),fill='#63736a',font=('Helvetica',8),tags=('activity-board',))
            if gate['id'] in v['targets']:
                self.canvas.create_oval(x+43,y-17,x+77,y+17,fill='#d5e7f6' if output else '#f5e3b7',outline='#3572a0' if output else '#94702b',width=2,tags=('activity-board','circuit-target','circuit-output-target' if output else 'circuit-helper-target'))
                self.canvas.create_text(x+60,y,text=str(v['targets'][gate['id']]),fill=INK,font=('Helvetica',16,'bold'),tags=('activity-board',))
        self.activity_text(28,30,'Gesuchte Eingänge · blaue Endausgänge · gelbe Hilfsmessungen')
        self.canvas.configure(scrollregion=(0,0,215+v['layers']*165,580),cursor='hand2')

    def paint_pipes(self):
        p=self.puzzle;v=p.view;n=v['size'];left,top,step=self.workshop_geometry
        self.activity_text(left,24,f'Drehungen: {len(self.activity_state["moves"])} · {n} × {n}')
        for key,mask in self.activity_state['values'].items():
            r,c=map(int,key.split(','));x,y=left+c*step,top+r*step;cx,cy=x+step/2,y+step/2
            color=v['palette'][v['colors'][key]]
            self.canvas.create_rectangle(x,y,x+step,y+step,fill='#f4f3ed',outline='#b4c4b9',tags=('activity-board','pipe-cell',f'pipe-cell:{key}'))
            for dr,dc,bit,rev in STEPS:
                if mask&bit:self.canvas.create_line(cx,cy,cx+dc*step/2,cy+dr*step/2,fill=color,width=max(3.5,step*.14),capstyle='round',tags=('activity-board','pipe-segment'))
            self.canvas.create_oval(cx-step*.085,cy-step*.085,cx+step*.085,cy+step*.085,fill=color,outline='',tags=('activity-board',))
            if key in p.givens:
                self.canvas.create_rectangle(x+step-9,y+5,x+step-3,y+11,fill='#9b752c',outline='',tags=('activity-board','pipe-lock'))
                self.canvas.create_arc(x+step-9,y+1,x+step-3,y+10,start=0,extent=180,style='arc',outline='#9b752c',width=1.5,tags=('activity-board',))
        self.canvas.configure(scrollregion=(0,0,max(340,left+n*step+28),top+n*step+65),cursor='hand2')

    def paint_pentomino(self):
        p=self.puzzle;v=p.view;left,top,step=self.workshop_geometry;right=left+v['cols']*step+32
        self.activity_text(28,24,f'Gelegte Teile: {len(self.activity_state["placements"])} / {len(v["shapes"])}')
        for r in range(v['rows']):
            for c in range(v['cols']):
                x,y=left+c*step,top+r*step
                self.canvas.create_rectangle(x,y,x+step,y+step,fill=PAPER,outline='#bccabd',tags=('activity-board','pentomino-cell'))
        for name,index in self.activity_state['placements'].items():
            color=p.piece_colors[name]
            for point in p.options[name][index]:
                r,c=divmod(point,v['cols']);x,y=left+c*step,top+r*step
                self.canvas.create_rectangle(x+1,y+1,x+step-1,y+step-1,fill=color,outline=INK,tags=('activity-board','pentomino-piece'))
                self.canvas.create_text(x+step/2,y+step/2,text=name,fill='white',font=('Helvetica',11,'bold'),tags=('activity-board',))
        dx,dy=self.pentomino_palette_offset;tile=self.pentomino_palette_step
        for i,(name,shape) in enumerate(v['shapes'].items()):
            r,c=divmod(i,3);x,y=right+c*105,65+r*107;selected=self.activity_selected==name;placed=name in self.activity_state['placements']
            self.canvas.create_rectangle(x,y,x+97,y+99,fill='#f4e4c7' if selected else PAPER,
                                         outline='#aa762d' if selected else '#c3cfc2',width=3 if selected else 1,tags=('activity-board','pentomino-palette'))
            self.canvas.create_text(x+80,y+15,text=name,fill=INK,font=('Helvetica',12,'bold'),tags=('activity-board',))
            points=transform_shape(shape,self.workshop_turns,self.workshop_mirror) if selected else shape
            for dr,dc in points:
                xx,yy=x+dx+dc*tile,y+dy+dr*tile
                self.canvas.create_rectangle(xx,yy,xx+tile,yy+tile,fill='#d9ddd6' if placed else p.piece_colors[name],outline=INK,tags=('activity-board',))
            self.workshop_hitboxes.append((x,y,x+97,y+99,('piece',name)))
        self.canvas.configure(scrollregion=(0,0,right+335,605),cursor='hand2')

    def paint_row_shift(self):
        v=self.puzzle.view;n=v['size'];left,top,step=self.workshop_geometry=65,90,64
        board=self.activity_state['board'];legal=slide_targets(board,n)
        if self.showing_solution:
            self.activity_text(28,24,f'Lösung · Schritt {self.row_shift_solution_step} von {len(self.row_shift_solution_states)-1}')
        else:self.activity_text(28,24,f'Schiebezüge: {len(self.activity_state["moves"])} · benachbarte Steine anklicken')
        for i,value in enumerate(board):
            r,c=divmod(i,n);x,y=left+c*step,top+r*step
            self.canvas.create_rectangle(x+2,y+2,x+step-2,y+step-2,fill='#eae6dc' if value==0 else '#dce9f2',
                outline='#c1c5ba' if value==0 else '#175ba2' if i in legal and not self.showing_solution else '#6f91a5',
                width=3 if i in legal and not self.showing_solution else 1.5,
                tags=('activity-board','shift-cell','shift-gap' if value==0 else 'shift-tile',f'shift-cell:{i}'))
            if value:
                self.canvas.create_text(x+step/2,y+step/2,text=str(value),fill=INK,font=('Helvetica',23,'bold'),tags=('activity-board','shift-number'))
                self.workshop_hitboxes.append((x+2,y+2,x+step-2,y+step-2,('slide',i)))
        goal_left=left+n*step+105
        self.activity_text(goal_left,50,'Zielbild')
        for i,value in enumerate(v['target']):
            r,c=divmod(i,n);x,y=goal_left+c*39,top+r*39
            self.canvas.create_rectangle(x,y,x+39,y+39,fill='#eae6dc' if value==0 else '#e7eee2',outline='#95aa91',tags=('activity-board','shift-goal'))
            if value:self.canvas.create_text(x+19,y+19,text=str(value),fill=INK,font=('Helvetica',12,'bold'),tags=('activity-board',))
        if self.showing_solution:
            moves=list(self.puzzle.solution.values());position=self.row_shift_solution_step
            if position<len(moves):
                source=moves[position];target=board.index(0)
                r,c=divmod(source,n);rr,cc=divmod(target,n)
                x,y=left+c*step,top+r*step;xx,yy=left+cc*step,top+rr*step
                self.canvas.create_rectangle(x+2,y+2,x+step-2,y+step-2,outline='#a85c18',width=3,
                    tags=('activity-board','shift-solution-source'))
                self.canvas.create_rectangle(xx+2,yy+2,xx+step-2,yy+step-2,outline=ACCENT,width=3,dash=(6,4),
                    tags=('activity-board','shift-solution-target'))
                cx,cy=x+step/2,y+step/2;tx,ty=xx+step/2,yy+step/2
                self.canvas.create_line(cx+(tx-cx)*.3,cy+(ty-cy)*.3,tx,ty,fill='#175ba2',width=4,
                    arrow='last',arrowshape=(12,15,6),tags=('activity-board','shift-solution-arrow'))
                message=f'Beispielweg · nächster Schritt: Stein {board[source]} in die Lücke schieben.'
            else:message=f'Zielbild erreicht · {len(moves)} Schiebezüge im Beispielweg.'
            self.canvas.create_text(28,405,text=message,width=650,anchor='nw',fill=INK,font=('Helvetica',13,'bold'),
                tags=('activity-board','shift-solution','shift-solution-instruction'))
        self.canvas.configure(scrollregion=(0,0,goal_left+n*39+30,570),cursor='' if self.showing_solution else 'hand2')

    def show_row_shift_step(self,step):
        if (self.busy or not self.showing_solution or self.puzzle is None
                or self.puzzle.view.get('mode')!='row-shift' or not self.row_shift_solution_states):return
        step=max(0,min(step,len(self.row_shift_solution_states)-1))
        self.row_shift_solution_step=step
        self.activity_state=dict(board=list(self.row_shift_solution_states[step]),moves=list(self.puzzle.solution.values())[:step])
        self.activity_selected=None
        self.paint_activity()
        self.status.configure(text=f'Lösungsansicht · Schritt {step} von {len(self.row_shift_solution_states)-1} · deine Eingaben bleiben erhalten.',foreground=INK)

    def click_workshop(self,event,reverse=False):
        if self.busy or self.showing_solution:return
        self.canvas.focus_set();v=self.puzzle.view;mode=v['mode'];s=self.activity_state
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        if mode=='pipes':
            left,top,step=self.workshop_geometry;r,c=int((y-top)//step),int((x-left)//step);key=f'{r},{c}'
            if not (0<=r<v['size'] and 0<=c<v['size']) or key in self.puzzle.givens:return
            mask=s['values'][key]
            for _ in range(3 if reverse else 1):mask=rotate_pipe(mask)
            if mask==s['values'][key]:return
            s['values'][key]=mask;s['moves'].append((key,-1 if reverse else 1));self.on_change();return
        for a,b,c,d,data in self.workshop_hitboxes:
            if not (a<=x<=c and b<=y<=d):continue
            kind,value=data
            if kind=='input':
                current=s['values'][value];s['values'][value]=0 if current is None else 1 if current==0 else None
                self.on_change();return
            if kind=='slide':
                if value not in slide_targets(s['board'],v['size']):return
                s['board']=list(shift_board(s['board'],v['size'],value));s['moves'].append(value);self.on_change();return
            if kind=='piece':
                self.activity_selected=value;self.workshop_turns=0;self.workshop_mirror=False
                if value in s['placements']:del s['placements'][value];self.on_change()
                else:self.paint_activity()
                return
        if mode=='pentomino':
            left,top,step=self.workshop_geometry;r,c=int((y-top)//step),int((x-left)//step)
            if not (0<=r<v['rows'] and 0<=c<v['cols']):return
            point=r*v['cols']+c
            name=self.activity_selected
            if name is None:
                for placed,index in list(s['placements'].items()):
                    if point in self.puzzle.options[placed][index]:
                        del s['placements'][placed];self.activity_selected=placed;self.workshop_turns=0;self.workshop_mirror=False;self.on_change();return
                return
            shape=transform_shape(v['shapes'][name],self.workshop_turns,self.workshop_mirror)
            if any(r+dr>=v['rows'] or c+dc>=v['cols'] for dr,dc in shape):return
            cells=tuple((r+dr)*v['cols']+c+dc for dr,dc in shape)
            occupied={point for other,index in s['placements'].items() for point in self.puzzle.options[other][index]}
            if occupied.intersection(cells):
                self.status.configure(text='Hier liegt bereits ein Teil. Wähle eine freie Stelle.',foreground=INK);return
            s['placements'][name]=self.puzzle.options[name].index(cells);s['moves'].append((name,s['placements'][name]));self.activity_selected=None;self.on_change()

    def transform_workshop(self,mirror=False):
        if self.busy or self.showing_solution or self.puzzle is None or self.puzzle.view.get('mode')!='pentomino' or self.activity_selected is None:return
        drag=getattr(self,'pentomino_drag',None)
        if drag is not None and drag.get('piece') is not None:
            old=drag['shape'];r,c=drag['grab']
            drag['grab']=(r,max(cc for rr,cc in old)-c) if mirror else (c,max(rr for rr,cc in old)-r)
            drag['shape']=transform_shape(old,0 if mirror else 1,mirror)
        if mirror:
            self.workshop_turns=(-self.workshop_turns)%4;self.workshop_mirror=not self.workshop_mirror
        else:self.workshop_turns=(self.workshop_turns+1)%4
        self.paint_activity();self.canvas.focus_set();return 'break'

    def workshop_entries(self):
        mode=self.puzzle.view['mode'];s=self.activity_state
        if mode=='crypto':return {k:ALPHABET.index(text) for k,text in s['values'].items() if text in ALPHABET and len(text)==1}
        if mode=='circuit':return {k:value for k,value in s['values'].items() if value is not None}
        if mode=='pipes':return s['values'].copy()
        if mode=='pentomino':return s['placements'].copy()
        return {}

    def workshop_state_result(self):
        mode=self.puzzle.view['mode'];s=self.activity_state
        if mode=='target24':return self.puzzle.check_expression(s['expression'])[0]
        if mode=='row-shift':return 'correct' if s['board']==self.puzzle.view['target'] else 'wrong'
        return self.puzzle.check(self.workshop_entries())[0]

    def on_workshop_change(self):
        self.paint_workshop();v=self.puzzle.view;mode=v['mode'];s=self.activity_state
        if self.workshop_state_result()=='correct':self.show_success();return
        self.hide_success(reset=True);self.dismiss_error(reset=True)
        text=('Buchstaben einsetzen · alle gleichen Zeichen ändern sich gemeinsam.' if mode=='crypto' else
              'Mit den vier Zahlen und Rechenzeichen 24 erreichen.' if mode=='target24' else
              'Alle Eingänge bestimmen, sodass die markierten Messpunkte stimmen.' if mode=='circuit' else
              f'{len(s["placements"])} von {len(v["shapes"])} Teilen gelegt · R dreht, M spiegelt.' if mode=='pentomino' else
              f'{len(s["moves"])} Verschiebungen · stelle das Zielbild her.' if mode=='row-shift' else
              f'{len(s["moves"])} Drehungen · verbinde alle Rohranschlüsse passend.')
        self.status.configure(text=text,foreground=INK)

    def check_workshop(self):
        if self.busy or self.showing_solution:return
        mode=self.puzzle.view['mode'];state=self.workshop_state_result()
        if state=='correct':self.show_success()
        elif mode=='target24':self.show_error_popup(self.puzzle.check_expression(self.activity_state['expression'])[1])
        elif state=='incomplete':self.show_error_popup('Vervollständige zuerst deine Eingabe.')
        else:self.show_error_popup('Die Eingabe erfüllt noch nicht alle Regeln.')

    def workshop_solution_state(self):
        mode=self.puzzle.view['mode'];state=self.initial_workshop_state()
        if mode=='crypto':state['values']={k:ALPHABET[self.puzzle.solution[k]] for k in self.puzzle.editable}
        elif mode=='target24':state['expression']=self.puzzle.result
        elif mode=='circuit':state['values']={k:self.puzzle.solution[k] for k in self.puzzle.editable}
        elif mode=='pipes':state['values']=self.puzzle.solution.copy()
        elif mode=='pentomino':state['placements']=self.puzzle.solution.copy()
        elif mode=='row-shift':
            states=[tuple(self.puzzle.view['initial'])]
            for action in self.puzzle.solution.values():states.append(shift_board(states[-1],self.puzzle.view['size'],action))
            self.row_shift_solution_states=tuple(states);self.row_shift_solution_step=0
        return state
