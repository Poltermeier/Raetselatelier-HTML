"""Atomic pentomino drag-and-drop with a snapped, purely geometric preview."""
from .pentomino import SHAPES,PIECE_COLORS,normalize_shape,transform_shape


class PentominoDragUI:
    def cancel_pentomino_drag(self,*,paint=True):
        drag=getattr(self,'pentomino_drag',None)
        if drag is None:return
        self.pentomino_drag=None;self.canvas.delete('pentomino-drag')
        self.activity_selected,self.workshop_turns,self.workshop_mirror=drag['selection_before']
        if paint and self.puzzle is drag['puzzle']:self.paint_activity()

    def start_pentomino_drag(self,event):
        if self.busy or self.showing_solution:return 'break'
        self.canvas.focus_set();self.cancel_pentomino_drag(paint=False)
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        drag=dict(puzzle=self.puzzle,origin=(x,y),pointer=(x,y),active=False,piece=None,
                  selection_before=(self.activity_selected,self.workshop_turns,self.workshop_mirror))
        for a,b,c,d,data in self.workshop_hitboxes:
            if data[0]!='piece' or not(a<=x<=c and b<=y<=d):continue
            name=data[1]
            shape=transform_shape(SHAPES[name],self.workshop_turns,self.workshop_mirror) if self.activity_selected==name else normalize_shape(SHAPES[name])
            grab=int((y-b-12)//16),int((x-a-8)//16)
            if grab in shape:drag.update(piece=name,shape=shape,grab=grab)
            break
        else:
            left,top,step=self.workshop_geometry;v=self.puzzle.view
            r,c=int((y-top)//step),int((x-left)//step)
            if 0<=r<v['rows'] and 0<=c<v['cols']:
                point=r*v['cols']+c
                for name,index in self.activity_state['placements'].items():
                    cells=self.puzzle.options[name][index]
                    if point not in cells:continue
                    points=[divmod(cell,v['cols']) for cell in cells];rr=min(a for a,b in points);cc=min(b for a,b in points)
                    drag.update(piece=name,shape=normalize_shape(points),grab=(r-rr,c-cc));break
        self.pentomino_drag=drag
        if drag['piece'] is not None:
            self.activity_selected=drag['piece']
            self.workshop_turns,self.workshop_mirror=next((turn,mirror) for turn in range(4) for mirror in (False,True)
                if transform_shape(SHAPES[drag['piece']],turn,mirror)==drag['shape'])
            self.paint_activity()
        return 'break'

    def pentomino_drop(self,drag):
        left,top,step=self.workshop_geometry;v=self.puzzle.view;x,y=drag['pointer'];gr,gc=drag['grab']
        # Floor division also snaps correctly just above or left of the grid.
        r=int((y-top)//step)-gr;c=int((x-left)//step)-gc
        points=[(r+dr,c+dc) for dr,dc in drag['shape']]
        inside=all(0<=rr<v['rows'] and 0<=cc<v['cols'] for rr,cc in points)
        cells=tuple(sorted(rr*v['cols']+cc for rr,cc in points)) if inside else ()
        occupied={cell for name,index in self.activity_state['placements'].items() if name!=drag['piece'] for cell in self.puzzle.options[name][index]}
        return points,cells,inside and not occupied.intersection(cells)

    def paint_pentomino_drag(self):
        self.canvas.delete('pentomino-drag');drag=getattr(self,'pentomino_drag',None)
        if drag is None or not drag['active'] or drag['piece'] is None:return
        points,cells,valid=self.pentomino_drop(drag);left,top,step=self.workshop_geometry
        color=PIECE_COLORS[list(SHAPES).index(drag['piece'])]
        for r,c in points:
            x,y=left+c*step,top+r*step
            tags=('pentomino-drag','pentomino-drop-valid' if valid else 'pentomino-drop-invalid')
            self.canvas.create_rectangle(x+1,y+1,x+step-1,y+step-1,fill=color,stipple='gray50',
                outline='#175ba2' if valid else '#9a3c30',width=3,tags=tags)
            self.canvas.create_text(x+step/2,y+step/2,text=drag['piece'],fill='#172e26',font=('Helvetica',13,'bold'),tags=('pentomino-drag',))
        self.canvas.tag_raise('pentomino-drag')

    def move_pentomino_drag(self,event):
        drag=getattr(self,'pentomino_drag',None)
        if drag is None:return 'break'
        if self.busy or self.showing_solution or self.puzzle is not drag['puzzle']:
            self.cancel_pentomino_drag(paint=False);return 'break'
        drag['pointer']=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        dx=drag['pointer'][0]-drag['origin'][0];dy=drag['pointer'][1]-drag['origin'][1]
        if not drag['active'] and (dx*dx+dy*dy)*self.canvas.zoom**2<16:return 'break'
        drag['active']=True
        if drag['piece'] is not None:self.paint_pentomino_drag()
        return 'break'

    def finish_pentomino_drag(self,event):
        drag=getattr(self,'pentomino_drag',None)
        if drag is None:return 'break'
        if self.busy or self.showing_solution or self.puzzle is not drag['puzzle']:
            self.cancel_pentomino_drag(paint=False);return 'break'
        if not drag['active']:
            self.pentomino_drag=None;self.canvas.delete('pentomino-drag')
            self.activity_selected,self.workshop_turns,self.workshop_mirror=drag['selection_before']
            self.click_workshop(event);return 'break'
        if drag['piece'] is None:
            self.cancel_pentomino_drag();return 'break'
        drag['pointer']=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        points,cells,valid=self.pentomino_drop(drag)
        if not valid:
            self.cancel_pentomino_drag();self.status.configure(text='Hier passt das Teil nicht hin. Es bleibt an seiner bisherigen Stelle.',foreground='#233a32');return 'break'
        name=drag['piece'];index=self.puzzle.options[name].index(cells)
        self.pentomino_drag=None;self.canvas.delete('pentomino-drag');self.activity_selected=None
        if self.activity_state['placements'].get(name)!=index:
            self.activity_state['placements'][name]=index;self.activity_state['moves'].append((name,index));self.on_change()
        else:self.paint_activity()
        return 'break'
