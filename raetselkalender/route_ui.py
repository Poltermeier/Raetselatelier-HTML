"""Grid-edge drawing for loops, number pairs and numbered plate paths."""
from collections import Counter

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'


class RouteUI:
    def render_routes(self):
        v=self.puzzle.view
        rows,cols=v['rows'],v['cols'];left,top,step=self.route_geometry=(28,28,65)
        self.route_drag_active=False
        self.route_segments={}
        owner={k:i for i,g in enumerate(v.get('regions',[])) for k in g}
        for r in range(rows):
            for c in range(cols):
                x,y=left+c*step,top+r*step;k=f'{r},{c}'
                self.canvas.create_rectangle(x,y,x+step,y+step,fill=PAPER,
                    outline='#8ea797' if v['mode'] in ('contact','abknicker','lichtstrahl') else '#d7dfd5',tags=('route-cell',))
                if owner:
                    for other,segment in ((f'{r-1},{c}',(x,y,x+step,y)),(f'{r},{c-1}',(x,y,x,y+step))):
                        if owner.get(other)!=owner[k]:
                            self.canvas.create_line(*segment,width=2.5,fill=INK,tags=('road-region',))
        if owner:
            self.canvas.create_line(left+cols*step,top,left+cols*step,top+rows*step,left,top+rows*step,
                width=2.5,fill=INK,tags=('road-region',))
        offset=0 if v['mode']=='slitherlink' else .5
        for key,a,b in v['edges']:
            r,c=map(int,a.split(','));rr,cc=map(int,b.split(','))
            segment=(left+(c+offset)*step,top+(r+offset)*step,left+(cc+offset)*step,top+(rr+offset)*step)
            self.route_segments[key]=segment
            if key not in self.puzzle.givens:self.register_click_value(key)
            if v['mode']!='slitherlink':
                self.canvas.create_line(*segment,fill='#d0dbd2',dash=(2,6),tags=('route-guide',))
        if v['mode']=='slitherlink':
            for r in range(rows+1):
                for c in range(cols+1):
                    x,y=left+c*step,top+r*step
                    self.canvas.create_oval(x-2,y-2,x+2,y+2,fill=INK,outline='',tags=('route-label',))
        for key,label in v['labels'].items():
            r,c=map(int,key.split(','));x,y=left+(c+.5)*step,top+(r+.5)*step
            if v['mode']=='lichtstrahl':
                self.canvas.create_rectangle(x-step/2,y-step/2,x+step/2,y+step/2,fill=INK,outline='#8ea797',
                                             tags=('route-label','ray-clue-cell'))
            if v['mode']=='numberlink':
                self.canvas.create_oval(x-17,y-17,x+17,y+17,fill=PAPER,outline=INK,width=1.5,tags=('route-label',))
            self.canvas.create_text(x,y,text=str(label),fill='white' if v['mode']=='lichtstrahl' else INK,
                                    font=('Helvetica',18,'bold'),tags=('route-label',))
        for filled,name in ((True,'black_circles'),(False,'white_circles')):
            for key in v.get(name,[]):
                r,c=map(int,key.split(','));x,y=left+(c+.5)*step,top+(r+.5)*step
                self.canvas.create_oval(x-21,y-21,x+21,y+21,fill='#76b9e9' if filled else PAPER,outline=INK,width=2,
                                        tags=('route-circle','filled-circle' if filled else 'white-circle'))
        for key in v.get('plates',[]):
            r,c=map(int,key.split(','));x,y=left+(c+.5)*step,top+(r+.5)*step
            self.canvas.create_oval(x-18,y-18,x+18,y+18,fill='#76b9e9',outline=INK,width=2,
                                    tags=('route-label','contact-plate',f'contact-plate:{key}'))
        for i,total in v.get('region_clues',{}).items():
            r,c=map(int,min(v['regions'][i]).split(','))
            self.canvas.create_text(left+c*step+7,top+r*step+7,text=str(total),anchor='nw',fill=INK,
                font=('Helvetica',11,'bold'),tags=('route-label','road-clue'))
        self.canvas.configure(scrollregion=(0,0,left+cols*step+28,top+rows*step+28),cursor='crosshair')
        self.canvas.bind('<Button-1>',self.start_route_drag)
        self.canvas.bind('<B1-Motion>',self.drag_route)
        self.canvas.bind('<ButtonRelease-1>',self.finish_route_drag)
        self.canvas.bind('<Motion>',self.hover_route)
        self.canvas.bind('<Leave>',lambda event:self.canvas.delete('route-hover'))
        self.paint_routes()

    def hit_route(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        candidates=[]
        for key,(a,b,c,d) in self.route_segments.items():
            if key in self.puzzle.givens:continue
            t=((x-a)*(c-a)+(y-b)*(d-b))/((c-a)**2+(d-b)**2)
            if .12<=t<=.88:
                distance=(x-a-t*(c-a))**2+(y-b-t*(d-b))**2
                if distance<=12**2:
                    candidates.append((distance,key))
        return min(candidates)[1] if candidates else None

    def start_route_drag(self,event):
        if self.busy or self.showing_solution:
            return
        key=self.hit_route(event)
        if key is None:
            return
        self.route_drag_active=True
        self.route_drag_before=self.capture_history()
        self.route_drag_seen=set()
        variable=self.note_vars[key] if self.note_mode else self.vars[key]
        self.route_drag_value=('' if variable.get() else 'x') if self.note_mode else ('' if variable.get()=='1' else '1')
        self.drag_route(event)

    def drag_route(self,event):
        if not getattr(self,'route_drag_active',False):
            return
        key=self.hit_route(event)
        if key is not None and key not in self.route_drag_seen:
            self.route_drag_seen.add(key)
            (self.note_vars if self.note_mode else self.vars)[key].set(self.route_drag_value)

    def finish_route_drag(self,event=None,*,cancel=False):
        if not getattr(self,'route_drag_active',False):
            return
        self.route_drag_active=False
        if cancel:
            self.updating=True
            for key,value in self.route_drag_before['values'].items():self.vars[key].set(value)
            for key,value in self.route_drag_before['notes'].items():self.note_vars[key].set(value)
            self.updating=False
        self.on_change()

    def hover_route(self,event):
        self.canvas.delete('route-hover')
        if self.busy or self.showing_solution:
            return
        key=self.hit_route(event)
        if key is not None:
            self.canvas.create_line(*self.route_segments[key],fill='#a3c6aa',width=9,tags=('route-hover',))
            if self.canvas.find_withtag('route-label'):
                self.canvas.tag_lower('route-hover','route-label')

    def paint_routes(self):
        self.canvas.delete('route-mark')
        self.canvas.delete('route-hover')
        step=self.route_geometry[2]
        for key,value in self.puzzle.givens.items():
            if value and key in self.route_segments:
                self.canvas.create_line(*self.route_segments[key],fill='#175ba2',width=5,capstyle='round',
                    tags=('route-mark','route-line','route-given',f'route-given:{key}'))
        for key,var in self.vars.items():
            a,b,c,d=self.route_segments[key]
            tags=('route-mark',f'route-mark:{key}')
            if var.get()=='1':
                self.canvas.create_line(a,b,c,d,fill=ACCENT,width=4,capstyle='round',tags=tags+('route-line',))
            elif self.note_vars[key].get() and not self.showing_solution:
                x,y=(a+c)/2,(b+d)/2
                for direction in (-1,1):
                    self.canvas.create_line(x-6,y-6*direction,x+6,y+6*direction,fill='#7a877d',width=2,tags=tags+('route-cross',))
        self.canvas.tag_raise('route-label')

    def on_routes_change(self):
        self.paint_routes()
        if self.note_mode:
            self.hide_success();self.dismiss_error();self.note_status();return
        values=self.puzzle.givens|{k:int(var.get() or 0) for k,var in self.vars.items()}
        selected=[(a,b) for key,a,b in self.puzzle.view['edges'] if values[key]]
        degree=Counter(node for pair in selected for node in pair)
        mode=self.puzzle.view['mode']
        if mode in ('numberlink','contact'):
            v=self.puzzle.view
            terminals=set(v['labels'])|set(v.get('plates',[]))
            satisfied=sum(degree[f'{r},{c}']==(1 if f'{r},{c}' in terminals else 2)
                for r in range(v['rows']) for c in range(v['cols']))
            ready=satisfied==v['rows']*v['cols']
            progress=f'{satisfied} von {v["rows"]*v["cols"]} Feldern verbunden.'
        elif mode=='abknicker':
            v=self.puzzle.view;total=v['rows']*v['cols']
            count=sum(degree[f'{r},{c}']==2 for r in range(v['rows']) for c in range(v['cols']))
            ready=count==total
            progress=f'{count} von {total} Feldern im Rundweg.'
        elif mode=='lichtstrahl':
            v=self.puzzle.view;free={f'{r},{c}' for r in range(v['rows']) for c in range(v['cols'])}-set(v['labels'])
            count=sum(degree[k]>0 for k in free)
            ready=count==len(free) and all(degree[k]>0 for k in v['labels'])
            progress=f'{count} von {len(free)} leeren Feldern von Strahlen erreicht.'
        else:
            ready=bool(selected) and all(d==2 for d in degree.values())
            progress=f'{len(selected)} Wegstücke gezeichnet · schließe den Rundweg.'
        if not ready or getattr(self,'route_drag_active',False):
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            self.status.configure(text=progress,foreground=INK);return
        state,wrong=self.puzzle.check(values)
        if state=='correct':self.show_success()
        else:self.show_error_count(len(wrong))
