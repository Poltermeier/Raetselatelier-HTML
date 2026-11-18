"""Interactive cards, guesses, pegs, matches and coloured maximal pours."""
from copy import deepcopy
import json
import math
import tkinter as tk
from tkinter import ttk

from .board_canvas import BoardCombobox
from .moving_games import PEG_CELLS,PEG_HOPS,peg_move,sort_pour,sorted_water
from .workshop_games import WORKSHOP_MODES

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'


class ActivityUI:
    def initial_activity_state(self):
        v=self.puzzle.view;mode=v['mode']
        if mode in WORKSHOP_MODES:return self.initial_workshop_state()
        if mode=='sets':return dict(draft=[],found=[])
        if mode=='mastermind':return dict(draft=[-1]*4,guesses=[])
        if mode=='solitaire':return dict(board=v['initial'],moves=[])
        if mode=='matches':return dict(mask=v['initial'],moves=[])
        return dict(tubes=[list(t) for t in v['initial']],moves=[])

    def activity_signature(self):return json.dumps(self.activity_state,sort_keys=True)

    def activity_button(self,text,command,x,y,width=210,*,tags=()):
        button=ttk.Button(self.canvas,text=text,command=command,style='Accent.TButton')
        self.extra_widgets.append(button)
        self.activity_controls.append(button)
        self.canvas.create_window(x,y,window=button,width=width,height=38,tags=('activity-controls',*tags))
        return button

    def render_activity(self):
        self.activity_state=self.initial_activity_state();self.activity_selected=None
        self.activity_controls=[];self.activity_draft_vars=[]
        mode=self.puzzle.view['mode']
        if mode in WORKSHOP_MODES:
            self.render_workshop();return
        if mode=='sets':
            self.activity_button('Set bestätigen',self.confirm_set,340,510)
        elif mode=='mastermind':
            names=self.puzzle.view['color_names']
            for i in range(4):
                variable=tk.StringVar();self.activity_draft_vars.append(variable)
                combo=BoardCombobox(self.canvas,textvariable=variable,values=[f'{chr(65+j)} · {name}' for j,name in enumerate(names)],
                    state='readonly',justify='center',font=('Helvetica',12))
                self.extra_widgets.append(combo);self.activity_controls.append(combo)
                self.canvas.create_window(88+i*132,100,window=combo,width=122,height=36,tags=('activity-controls',))
                variable.trace_add('write',lambda *args,index=i:self.edit_code_draft(index))
            self.activity_button('Versuch abgeben',self.submit_code_guess,302,150,250)
        elif mode=='solitaire':
            self.solitaire_solution_states=();self.solitaire_solution_step=0
            self.activity_button('Fertig – Score',self.finish_solitaire,510,540,tags=('peg-score-control',))
            self.solitaire_navigation=[]
            for label,command,x in (
                ('Anfang',lambda:self.show_solitaire_step(0),102),
                ('Zurück',lambda:self.show_solitaire_step(self.solitaire_solution_step-1),264),
                ('Weiter',lambda:self.show_solitaire_step(self.solitaire_solution_step+1),426),
                ('Ziel',lambda:self.show_solitaire_step(len(self.solitaire_solution_states)-1),588)):
                self.solitaire_navigation.append(self.activity_button(label,command,x,540,145,tags=('peg-solution-controls',)))
        self.canvas.bind('<Button-1>',self.click_activity)
        self.paint_activity()

    def update_activity_controls(self):
        disabled=self.busy or self.showing_solution or getattr(self,'pour_animating',False)
        mode=self.puzzle.view['mode']
        if mode=='sets':disabled|=len(self.activity_state['found'])>=self.puzzle.view['required_sets']
        if mode=='mastermind':
            guesses=self.activity_state['guesses']
            disabled|=len(guesses)>=self.puzzle.view['attempt_limit'] or bool(guesses and self.puzzle.feedback(guesses[-1])==(4,0))
        for control in self.activity_controls:
            control.configure(state='disabled' if disabled else 'readonly' if isinstance(control,BoardCombobox) else 'normal')
        if mode=='solitaire':
            self.canvas.itemconfigure('peg-score-control',state='hidden' if self.showing_solution else 'normal')
            self.canvas.itemconfigure('peg-solution-controls',state='normal' if self.showing_solution else 'hidden')
            for i,control in enumerate(self.solitaire_navigation):
                endpoint=self.solitaire_solution_step==0 if i<2 else self.solitaire_solution_step>=len(self.solitaire_solution_states)-1
                control.configure(state='disabled' if self.busy or not self.showing_solution or endpoint else 'normal')
        elif mode=='row-shift':
            self.canvas.itemconfigure('shift-solution-controls',state='normal' if self.showing_solution else 'hidden')
            for i,control in enumerate(self.row_shift_navigation):
                endpoint=self.row_shift_solution_step==0 if i<2 else self.row_shift_solution_step>=len(self.row_shift_solution_states)-1
                control.configure(state='disabled' if self.busy or not self.showing_solution or endpoint else 'normal')

    def paint_activity(self):
        self.canvas.delete('activity-board')
        mode=self.puzzle.view['mode']
        if mode in WORKSHOP_MODES:
            self.paint_workshop();return
        if mode=='sets':self.paint_sets()
        elif mode=='mastermind':self.paint_mastermind()
        elif mode=='solitaire':self.paint_solitaire()
        elif mode=='matches':self.paint_matches()
        else:self.paint_water_sort()
        self.paint_color_labels()
        self.update_activity_controls()

    def activity_text(self,x,y,text,**kwargs):
        self.canvas.create_text(x,y,text=text,fill=INK,font=('Helvetica',13,'bold'),anchor='nw',tags=('activity-board',),**kwargs)

    def paint_sets(self):
        v=self.puzzle.view;cards=v['cards'];columns=4 if len(cards)==12 else 5
        self.set_geometry=(28,70,128,132,columns)
        self.activity_text(28,24,f'Gefundene Sets: {len(self.activity_state["found"])} / {v["required_sets"]}')
        owners={i:k+1 for k,group in enumerate(self.activity_state['found']) for i in group}
        for i,card in enumerate(cards):
            r,c=divmod(i,columns);x,y=28+c*128,70+r*132
            selected=i in self.activity_state['draft'];found=i in owners
            self.canvas.create_rectangle(x,y,x+116,y+116,fill='#e6f0e7' if found else PAPER,
                outline='#bc792b' if selected else ACCENT if found else '#a8b7ae',width=4 if selected or found else 1.5,
                tags=('activity-board','set-card',f'set-card:{i}'))
            number,shape,filling,color=card;ink=('#bb353b','#267b43','#8244a5')[color]
            for j in range(number+1):
                cy=y+58+(j-number/2)*30
                self.draw_set_symbol(x+58,cy,shape,filling,ink)
            if found:
                self.canvas.create_text(x+106,y+9,text=str(owners[i]),fill=ACCENT,font=('Helvetica',8,'bold'),
                                        tags=('activity-board','set-badge'))
        self.canvas.configure(scrollregion=(0,0,28+columns*128,550),cursor='hand2')

    def draw_set_symbol(self,x,y,shape,filling,color):
        tags=('activity-board','set-symbol')
        if shape==0:
            self.canvas.create_oval(x-33,y-11,x+33,y+11,fill=color if filling==2 else PAPER,outline=color,width=2,tags=tags)
            polygon=None
        else:
            polygon=([(x-34,y),(x,y-13),(x+34,y),(x,y+13)] if shape==1 else
                [(x-34,y+6),(x-28,y-7),(x-12,y-12),(x+5,y-6),(x+29,y-11),(x+34,y-3),
                 (x+28,y+10),(x+11,y+12),(x-8,y+6),(x-29,y+13)])
            self.canvas.create_polygon(*[v for point in polygon for v in point],fill=color if filling==2 else PAPER,
                outline=color,width=2,smooth=shape==2,tags=tags)
        if filling==1:
            for dy in range(-8,9,4):
                yy=y+dy
                if polygon is None:
                    half=31*math.sqrt(max(0,1-(dy/11)**2));segments=[x-half,x+half]
                else:
                    segments=[]
                    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                        if min(a[1],b[1])<=yy<max(a[1],b[1]):segments.append(a[0]+(yy-a[1])*(b[0]-a[0])/(b[1]-a[1]))
                    segments.sort()
                for a,b in zip(segments[::2],segments[1::2]):
                    self.canvas.create_line(a+2,yy,b-2,yy,fill=color,width=1.5,tags=tags)

    def edit_code_draft(self,index):
        if self.updating or self.busy or self.showing_solution:return
        text=self.activity_draft_vars[index].get()
        value=ord(text[0])-65 if text else -1
        self.activity_state['draft'][index]=value;self.on_change()

    def paint_mastermind(self):
        v=self.puzzle.view;s=self.activity_state
        self.activity_text(28,24,f'Versuche: {len(s["guesses"])} / {v["attempt_limit"]}')
        previous=self.updating;self.updating=True
        for i,var in enumerate(self.activity_draft_vars):
            c=s['draft'][i];text=f'{chr(65+c)} · {v["color_names"][c]}' if c>=0 else ''
            if var.get()!=text:var.set(text)
        self.updating=previous
        for row,guess in enumerate(s['guesses']):
            y=211+row*53
            self.activity_text(28,y-10,f'{row+1}.')
            for i,c in enumerate(guess):
                x=87+i*60
                self.canvas.create_oval(x-19,y-19,x+19,y+19,fill=v['palette'][c],outline=INK,width=1.5,
                    tags=('activity-board','code-peg'))
                self.canvas.create_text(x,y,text=chr(65+c),fill='white' if c!=3 else INK,
                    font=('Helvetica',12,'bold'),tags=('activity-board',))
            placed,elsewhere=self.puzzle.feedback(guess)
            self.canvas.create_text(348,y,text=f'{placed+elsewhere} Farben stimmen:\n{placed} richtig platziert, {elsewhere} an anderer Stelle',
                anchor='w',fill=INK,font=('Helvetica',11),tags=('activity-board','code-feedback'))
        if self.showing_solution:
            self.activity_text(28,66,'Lösung: '+' · '.join(chr(65+c) for c in self.puzzle.solution.values()))
        self.canvas.configure(scrollregion=(0,0,690,245+v['attempt_limit']*53),cursor='')

    def paint_solitaire(self):
        v=self.puzzle.view;s=self.activity_state
        self.peg_geometry=(28,80,55)
        if self.showing_solution:
            self.activity_text(28,24,f'Lösung · Schritt {self.solitaire_solution_step} von {len(self.solitaire_solution_states)-1}')
            for i in range(7):
                self.canvas.create_text(28+(i+.5)*55,65,text=chr(65+i),fill=INK,font=('Helvetica',10),tags=('activity-board',))
                self.canvas.create_text(15,80+(i+.5)*55,text=str(i+1),fill=INK,font=('Helvetica',10),tags=('activity-board',))
        else:
            self.activity_text(28,24,f'Sprünge: {len(s["moves"])} · Ziel erreichbar in {self.puzzle.analysis["minimum_moves"]} Sprüngen')
        self.activity_text(448,72,'Zielbild')
        for i,(r,c) in enumerate(PEG_CELLS):
            x,y=28+(c+.5)*55,80+(r+.5)*55
            occupied=bool(s['board']&(1<<i));active=self.activity_selected==i
            self.canvas.create_oval(x-21,y-21,x+21,y+21,fill='#bd713b' if occupied else '#e3ded0',
                outline=ACCENT if active else '#705b43',width=4 if active else 1.5,
                tags=('activity-board','peg-hole','peg-occupied' if occupied else 'peg-empty',f'peg-hole:{i}'))
            xx,yy=448+(c+.5)*29,112+(r+.5)*29
            self.canvas.create_oval(xx-10,yy-10,xx+10,yy+10,fill='#27644c' if v['target']&(1<<i) else '#ecebe1',
                outline='#82998c',tags=('activity-board','peg-target'))
        if self.activity_selected is not None:
            for action,(a,b,c) in enumerate(PEG_HOPS):
                if a==self.activity_selected and peg_move(s['board'],action) is not None:
                    r,cc=PEG_CELLS[c];x,y=28+(cc+.5)*55,80+(r+.5)*55
                    self.canvas.create_oval(x-10,y-10,x+10,y+10,outline='#2f8a61',width=3,dash=(3,3),tags=('activity-board','peg-landing'))
        if self.showing_solution:
            moves=list(self.puzzle.solution.values());step=self.solitaire_solution_step
            if step<len(moves):
                source,over,target=PEG_HOPS[moves[step]]
                r,c=PEG_CELLS[source];rr,cc=PEG_CELLS[target]
                x,y=28+(c+.5)*55,80+(r+.5)*55;xx,yy=28+(cc+.5)*55,80+(rr+.5)*55
                self.canvas.create_oval(x-23,y-23,x+23,y+23,outline='#a85c18',width=3,tags=('activity-board','peg-solution-source'))
                self.canvas.create_oval(xx-23,yy-23,xx+23,yy+23,outline='#27644c',width=3,dash=(6,4),tags=('activity-board','peg-solution-target'))
                self.canvas.create_line(x,y,xx,yy,fill='#175ba2',width=4,arrow='last',arrowshape=(12,15,6),tags=('activity-board','peg-solution-arrow'))
                def square(i):
                    r,c=PEG_CELLS[i];return chr(65+c)+str(r+1)
                message=f'Nächster Sprung: {square(source)} nach {square(target)} · über {square(over)}'
            else:message=f'Zielbild erreicht · {len(moves)} Sprünge'
            self.canvas.create_text(28,497,text=message,fill=INK,font=('Helvetica',13,'bold'),anchor='nw',tags=('activity-board','peg-solution-instruction'))
        else:self.activity_text(28,497,f'Score: {self.puzzle.score(s["board"])} / 100')
        self.canvas.configure(scrollregion=(0,0,690,582),cursor='' if self.showing_solution else 'hand2')

    def show_solitaire_step(self,step):
        if (self.busy or not self.showing_solution or self.puzzle is None
                or self.puzzle.view.get('mode')!='solitaire' or not self.solitaire_solution_states):return
        step=max(0,min(step,len(self.solitaire_solution_states)-1))
        self.solitaire_solution_step=step
        self.activity_state=dict(board=self.solitaire_solution_states[step],moves=list(self.puzzle.solution.values())[:step])
        self.activity_selected=None
        self.paint_activity()
        self.status.configure(text=f'Lösungsansicht · Schritt {step} von {len(self.solitaire_solution_states)-1} · deine Eingaben bleiben erhalten.',foreground=INK)

    def match_segments(self):
        segments={};pattern=((0,0,50,0),(50,0,50,44),(50,44,50,88),(0,88,50,88),
                            (0,44,0,88),(0,0,0,44),(0,44,50,44))
        for offset,left in ((0,42),(9,290),(16,541)):
            for i,(a,b,c,d) in enumerate(pattern):segments[offset+i]=(left+a,146+b,left+c,146+d)
        segments[7]=(158,190,216,190);segments[8]=(187,161,187,219)
        return segments

    def paint_matches(self):
        s=self.activity_state;required=self.puzzle.view['moves_required']
        self.match_geometry=self.match_segments()
        self.activity_text(28,28,f'Versetzte Hölzer: {len(s["moves"])} / {required}')
        self.activity_text(28,67,'Holz anklicken, dann eine freie Segmentposition wählen.')
        for i,(a,b,c,d) in self.match_geometry.items():
            active=bool(s['mask']&(1<<i));picked=self.activity_selected==i
            self.canvas.create_line(a,b,c,d,fill='#cf7a25' if picked else '#72522e' if active else '#d8ded5',
                width=8 if active else 3,capstyle='round',tags=('activity-board','match-stick' if active else 'match-guide',f'match-slot:{i}'))
            if active:
                self.canvas.create_oval(a-5,b-5,a+5,b+5,fill='#b33d35',outline='',tags=('activity-board',))
        for y in (179,201):self.canvas.create_line(413,y,470,y,fill=INK,width=6,capstyle='round',tags=('activity-board',))
        self.canvas.configure(scrollregion=(0,0,660,310),cursor='hand2')

    def paint_water_sort(self,animation=None):
        v=self.puzzle.view;s=self.activity_state;capacity=v['capacity'];count=len(s['tubes'])
        unit=240/capacity
        self.water_geometry=(28,82,105,44)
        self.activity_text(28,24,f'Umfüllvorgänge: {len(s["moves"])} · kürzester Weg: {self.puzzle.analysis["minimum_moves"]}')
        for i,tube in enumerate(s['tubes']):
            x,bottom=70+i*105,330
            self.canvas.create_line(x-30,82,x-30,bottom,x+30,bottom,x+30,82,
                fill='#cf7a25' if self.activity_selected==i else INK,width=4,
                tags=('activity-board','sort-vessel',f'sort-vessel:{i}'))
            display=tube;volume=len(tube)
            if animation is not None:
                source,target,factor,before=animation
                amount=len(before[source])-len(s['tubes'][source])
                if i==source:display=before[i];volume=len(display)-amount*factor
                elif i==target:volume=len(before[i])+amount*factor
            for level,color in enumerate(display):
                fraction=max(0,min(1,volume-level))
                if not fraction:continue
                y=bottom-level*unit
                self.canvas.create_rectangle(x-26,y-max(3,unit*fraction-3),x+26,y-1,fill=v['palette'][color],outline=PAPER,
                    tags=('activity-board','sort-layer'))
        if animation is not None:
            source,target,factor,before=animation;sx,tx=70+source*105,70+target*105
            color=s['tubes'][target][-1]
            self.canvas.create_line(sx,80,sx,68,tx,68,tx,88,fill=v['palette'][color],width=6,arrow='last',
                dash=(9,5),dashoffset=round(factor*24),tags=('activity-board','sort-stream'))
        self.activity_text(28,370,'Quelle und Ziel anklicken · gleiche Farben zusammengießen.')
        self.canvas.configure(scrollregion=(0,0,28+count*105,420),cursor='hand2')
        self.paint_color_labels()

    def click_activity(self,event):
        if self.busy or self.showing_solution or getattr(self,'pour_animating',False):return
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y);mode=self.puzzle.view['mode']
        if mode in WORKSHOP_MODES:
            self.click_workshop(event);return
        s=self.activity_state
        if mode=='sets':
            left,top,sx,sy,columns=self.set_geometry;r,c=int((y-top)//sy),int((x-left)//sx);i=r*columns+c
            if not (0<=r<3 and 0<=c<columns and x-left-c*sx<=116 and y-top-r*sy<=116):return
            if any(i in group for group in s['found']):return
            if i in s['draft']:s['draft'].remove(i)
            elif len(s['draft'])<3:s['draft'].append(i)
            else:return
            self.on_change()
        elif mode=='solitaire':
            c,r=int((x-28)//55),int((y-80)//55)
            try:i=PEG_CELLS.index((r,c))
            except ValueError:return
            if self.activity_selected is not None:
                for action,(a,b,target) in enumerate(PEG_HOPS):
                    following=peg_move(s['board'],action)
                    if a==self.activity_selected and target==i and following is not None:
                        s['board']=following;s['moves'].append(action);self.activity_selected=None;self.on_change();return
            self.activity_selected=i if s['board']&(1<<i) and self.activity_selected!=i else None
            self.paint_activity()
        elif mode=='matches':
            choices=[]
            for i,(a,b,c,d) in self.match_geometry.items():
                t=max(0,min(1,((x-a)*(c-a)+(y-b)*(d-b))/((c-a)**2+(d-b)**2)))
                distance=(x-a-t*(c-a))**2+(y-b-t*(d-b))**2
                if distance<=12**2:choices.append((distance,i))
            if not choices:return
            i=min(choices)[1]
            if s['mask']&(1<<i):
                self.activity_selected=None if self.activity_selected==i else i;self.paint_activity()
            elif self.activity_selected is not None and len(s['moves'])<self.puzzle.view['moves_required']:
                source=self.activity_selected;s['mask']^=(1<<source)|(1<<i);s['moves'].append((source,i))
                self.activity_selected=None;self.on_change()
        elif mode=='water-sort':
            i=int((x-18)//105)
            if not (0<=i<len(s['tubes']) and 82<=y<=335 and abs(x-(70+i*105))<=34):return
            if self.activity_selected is None:
                self.activity_selected=i if s['tubes'][i] else None;self.paint_activity();return
            source=self.activity_selected;self.activity_selected=None
            if source==i:self.paint_activity();return
            before=tuple(tuple(t) for t in s['tubes'])
            after=sort_pour(before,source,i,self.puzzle.view['capacity'])
            if after is None:
                self.paint_activity();self.status.configure(text='Dieses Gefäß kann die oberste Farbe gerade nicht aufnehmen.',foreground=INK);return
            s['tubes']=[list(t) for t in after];s['moves'].append((source,i))
            self.pour_animating=True;self.on_change()
            self.animate_sort_pour(source,i,before)

    def confirm_set(self):
        if self.busy or self.showing_solution:return
        s=self.activity_state
        if len(s['draft'])!=3:self.show_error_popup('Wähle genau drei Karten.');return
        from .card_code_matches import valid_set
        if not valid_set([tuple(self.puzzle.view['cards'][i]) for i in s['draft']]):
            self.show_error_popup('Diese drei Karten bilden noch kein Set.');return
        s['found'].append(sorted(s['draft']));s['draft']=[];self.on_change()

    def submit_code_guess(self):
        if self.busy or self.showing_solution:return
        s=self.activity_state
        if len(s['guesses'])>=self.puzzle.view['attempt_limit']:return
        try:self.puzzle.feedback(s['draft'])
        except ValueError as exc:self.show_error_popup(str(exc));return
        s['guesses'].append(s['draft'].copy());s['draft']=[-1]*4;self.on_change()

    def finish_solitaire(self):
        if self.busy or self.showing_solution:return
        score=self.puzzle.score(self.activity_state['board'])
        if score==100:self.show_success()
        else:self.show_error_popup(f'Score: {score} / 100\nDie Stellung entspricht noch nicht dem Zielbild.')

    def animate_sort_pour(self,source,target,before):
        self.cancel_pour_animation();self.pour_animating=True;epoch=self.pour_epoch
        def frame(number=0):
            self.pour_job=None
            if epoch!=self.pour_epoch:return
            self.canvas.delete('activity-board');self.paint_water_sort((source,target,number/12,before));self.update_activity_controls()
            if number<12:self.pour_job=self.root.after(30,lambda:frame(number+1))
            else:
                self.pour_animating=False;self.on_activity_change()
        frame()

    def on_activity_change(self):
        if self.puzzle.view['mode'] in WORKSHOP_MODES:
            self.on_workshop_change();return
        self.paint_activity();s=self.activity_state;mode=self.puzzle.view['mode']
        solved=(self.puzzle.check_cards(s['found'])=='correct' if mode=='sets' else
                bool(s['guesses'] and self.puzzle.feedback(s['guesses'][-1])==(4,0)) if mode=='mastermind' else
                s['board']==self.puzzle.view['target'] if mode=='solitaire' else
                len(s['moves'])==self.puzzle.view['moves_required'] and self.puzzle.check_mask(s['mask'])=='correct' if mode=='matches' else
                sorted_water(tuple(tuple(t) for t in s['tubes']),self.puzzle.view['capacity']))
        if solved and not (mode=='water-sort' and getattr(self,'pour_animating',False)):
            self.show_success();return
        self.hide_success(reset=True);self.dismiss_error(reset=True)
        if mode=='sets':text=f'{len(s["draft"])} Karten gewählt · {len(s["found"])} von {self.puzzle.view["required_sets"]} Sets gefunden.'
        elif mode=='mastermind':
            text=f'{len(s["guesses"])} von {self.puzzle.view["attempt_limit"]} Versuchen abgegeben.'
            if len(s['guesses'])>=self.puzzle.view['attempt_limit']:self.show_error_popup('Alle Versuche sind aufgebraucht. Du kannst die Lösung ansehen oder ein neues Rätsel starten.')
        elif mode=='solitaire':text=f'Score: {self.puzzle.score(s["board"])} / 100 · wähle Stein und Zielloch.'
        elif mode=='matches':
            text=f'{len(s["moves"])} von {self.puzzle.view["moves_required"]} Hölzern versetzt.'
            if len(s['moves'])>=self.puzzle.view['moves_required']:self.show_error_popup('Die Gleichung stimmt noch nicht. Mit Rückgängig kannst du ein Holz anders versetzen.')
        else:text=f'{len(s["moves"])} Umfüllvorgänge · wähle Quelle und Ziel.'
        self.status.configure(text=text,foreground=INK)

    def toggle_activity_solution(self):
        self.cancel_pour_animation();self.activity_selected=None
        self.showing_solution=not self.showing_solution
        if self.showing_solution:
            self.saved_activity_state=deepcopy(self.activity_state);mode=self.puzzle.view['mode']
            if mode in WORKSHOP_MODES:self.activity_state=self.workshop_solution_state()
            elif mode=='sets':self.activity_state=dict(draft=[],found=[list(self.puzzle.sets[self.puzzle.solution[k]]) for k in self.puzzle.editable])
            elif mode=='mastermind':self.activity_state=dict(draft=list(self.puzzle.solution.values()),guesses=[])
            elif mode=='solitaire':
                _,states=self.puzzle.check_moves(list(self.puzzle.solution.values()))
                self.solitaire_solution_states=tuple(states);self.solitaire_solution_step=0
                self.activity_state=dict(board=states[0],moves=[])
            elif mode=='matches':self.activity_state=dict(mask=sum(v<<i for i,v in enumerate(self.puzzle.solution.values())),moves=[None]*self.puzzle.view['moves_required'])
            else:
                count=len(self.puzzle.view['initial']);moves=[divmod(v,count) for v in self.puzzle.solution.values()]
                _,states=self.puzzle.check_moves(moves);self.activity_state=dict(tubes=[list(t) for t in states[-1]],moves=moves)
        else:self.activity_state=self.saved_activity_state
        self.paint_activity()
        self.solution_button.configure(text='Zurück zu meinen Eingaben' if self.showing_solution else 'Lösung ansehen')
        self.reset_button.configure(state='disabled' if self.showing_solution else 'normal')
        self.update_notes_button()
        self.status.configure(text='Lösungsansicht · deine Eingaben bleiben erhalten.' if self.showing_solution else 'Deine Eingaben wurden wiederhergestellt.',foreground=INK)
        if self.showing_solution and self.puzzle.view['mode']=='solitaire':self.show_solitaire_step(0)
        elif self.showing_solution and self.puzzle.view['mode']=='row-shift':self.show_row_shift_step(0)
