"""Move-based jump and chess boards, independent of numeric answer inputs."""
import tkinter as tk
import base64
from importlib.resources import files

from .maze_puzzles import DIRECTIONS

INK,ACCENT,PAPER='#233a32','#27644c','#fffef9'


class StrategyUI:
    def close_chess_menu(self):
        menu=getattr(self,'chess_promotion_menu',None)
        if menu is not None:
            menu.destroy()
        self.chess_promotion_menu=None
    def render_jump(self):
        self.ensure_chess_images()
        self.jump_path=[self.puzzle.view['start']]
        self.jump_geometry=28,68,82
        self.canvas.configure(cursor='hand2',scrollregion=(0,0,466,506))
        self.canvas.bind('<Button-1>',self.click_jump)
        self.paint_jump()

    def click_jump(self,event):
        if self.busy or self.showing_solution:return
        left,top,step=self.jump_geometry;n=self.puzzle.view['size']
        r=int((self.canvas.canvasy(event.y)-top)//step);c=int((self.canvas.canvasx(event.x)-left)//step)
        target=r*n+c
        v=self.puzzle.view
        if 0<=r<n and 0<=c<n and target in self.puzzle.targets(self.jump_path[-1]):
            self.jump_path.append(target);self.on_change()

    def paint_jump(self):
        self.canvas.delete('jump-board')
        v=self.puzzle.view;n=v['size'];left,top,step=self.jump_geometry
        current=self.jump_path[-1]
        reachable=self.puzzle.targets(current) if not self.showing_solution else ()
        self.canvas.create_text(left,24,text=f'Züge: {len(self.jump_path)-1}   ·   Benötigt: {v["par"]}',anchor='w',fill=INK,
            font=('Helvetica',14,'bold'),tags=('jump-board','jump-counter'))
        for position in range(n*n):
            r,c=divmod(position,n);x,y=left+c*step,top+r*step
            goal=position==v['goal'];active=position==current
            bg='#d8eadb' if goal else '#d5e5fa' if active else '#eff3f6' if position in self.jump_path else PAPER
            self.canvas.create_rectangle(x+2,y+2,x+step-2,y+step-2,fill=bg,
                outline='#175ba2' if active or position in reachable else '#bac7c0',
                width=3.5 if active or position in reachable else 1.5,
                # Tk's thick rectangle strokes fill very short dash gaps.
                dash=(10,8) if position in reachable else (),tags=('jump-board','jump-cell',f'jump-cell:{position}'))
            if position==v['start']:
                self.canvas.create_text(x+11,y+12,text='S',fill='#357bc1',font=('Helvetica',10,'bold'),tags=('jump-board',))
            if v.get('mode')=='chess-maze':
                self.canvas.create_scaled_image(x+step/2,y+step/2,size=step*.72,
                    factory=lambda pixels,symbol=v['pieces'][position]:self.chess_piece_image(symbol,pixels),
                    tags=('jump-board','jump-number','maze-piece'))
                if goal:
                    self.canvas.create_line(x+step-16,y+23,x+step-16,y+7,x+step-4,y+11,x+step-16,y+15,
                        fill=ACCENT,width=2,tags=('jump-board','jump-number'))
            elif goal:
                self.canvas.create_line(x+step*.35,y+step*.75,x+step*.35,y+step*.25,fill=ACCENT,width=3,tags=('jump-board','jump-number'))
                self.canvas.create_polygon(x+step*.35,y+step*.25,x+step*.7,y+step*.36,x+step*.35,y+step*.47,
                    fill=ACCENT,tags=('jump-board','jump-number'))
            elif v.get('mode')=='arrows':
                dr,dc=DIRECTIONS[v['arrows'][position]]
                self.canvas.create_line(x+step*(.5-.27*dc),y+step*(.5-.27*dr),
                    x+step*(.5+.27*dc),y+step*(.5+.27*dr),fill=INK,width=7,arrow='last',arrowshape=(16,18,7),
                    tags=('jump-board','jump-number','maze-arrow'))
            else:
                self.canvas.create_text(x+step/2,y+step/2,text=str(v['numbers'][position]),fill=INK,font=('Helvetica',25,'bold'),tags=('jump-board','jump-number'))
        if self.showing_solution:
            for a,b in zip(self.jump_path,self.jump_path[1:]):
                r,c=divmod(a,n);rr,cc=divmod(b,n)
                self.canvas.create_line(left+(c+.5)*step,top+(r+.5)*step,left+(cc+.5)*step,top+(rr+.5)*step,
                    fill='#77a99b',width=3,arrow='last',tags=('jump-board','jump-route'))
            self.canvas.tag_raise('jump-number')

    def on_jump_change(self):
        self.paint_jump()
        state=self.puzzle.check_path(self.jump_path)
        if state=='correct':self.show_success()
        elif state=='nonoptimal':self.show_error_popup('Ziel erreicht – finde noch einen kürzeren Weg.')
        else:
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            current=self.jump_path[-1]
            v=self.puzzle.view
            instruction=(f'aktuelle Sprungweite {v["numbers"][current]}' if 'numbers' in v else
                         'folge dem Pfeil' if v['mode']=='arrows' else 'ziehe wie die aktuelle Figur auf die andere Farbe')
            self.status.configure(text=f'{len(self.jump_path)-1} Züge · {instruction}. Blau gestrichelte Felder sind erreichbar.',foreground=INK)

    def render_chess(self):
        import chess
        self.chess_move=''
        self.chess_selected=None
        self.chess_promotion_menu=None
        self.chess_geometry=48,48,58
        self.chess_white_bottom=chess.Board(self.puzzle.view['fen']).turn==chess.WHITE
        self.ensure_chess_images()
        self.canvas.configure(cursor='hand2',scrollregion=(0,0,560,660))
        self.canvas.bind('<Button-1>',self.click_chess)
        self.paint_chess()

    def ensure_chess_images(self):
        if not hasattr(self,'chess_master_images'):
            self.chess_master_images={}
            self.chess_scaled_images={}

    def chess_piece_image(self,symbol,pixels):
        if symbol not in self.chess_master_images:
            kind={'k':'king','q':'queen','r':'rook','b':'bishop','n':'knight','p':'pawn'}[symbol.lower()]
            name=('white-' if symbol.isupper() else 'black-')+kind+'.png'
            data=files('raetselkalender').joinpath('data/pieces',name).read_bytes()
            self.chess_master_images[symbol]=tk.PhotoImage(master=self.root,data=base64.b64encode(data),format='png')
        divisor=max(1,round(512/max(1,pixels)))
        key=symbol,divisor
        if key not in self.chess_scaled_images:
            self.chess_scaled_images[key]=self.chess_master_images[symbol].subsample(divisor)
        return self.chess_scaled_images[key]

    def chess_xy(self,square):
        import chess
        left,top,step=self.chess_geometry
        file,rank=chess.square_file(square),chess.square_rank(square)
        c,r=(file,7-rank) if self.chess_white_bottom else (7-file,rank)
        return left+(c+.5)*step,top+(r+.5)*step

    def chess_square_at(self,event):
        import chess
        left,top,step=self.chess_geometry
        c=int((self.canvas.canvasx(event.x)-left)//step);r=int((self.canvas.canvasy(event.y)-top)//step)
        if not 0<=r<8 or not 0<=c<8:return None
        return chess.square(c,7-r) if self.chess_white_bottom else chess.square(7-c,r)

    def click_chess(self,event):
        import chess
        if self.busy or self.showing_solution or self.chess_move:return
        square=self.chess_square_at(event)
        if square is None:return
        board=chess.Board(self.puzzle.view['fen'])
        if self.chess_selected is not None:
            choices=[move for move in board.legal_moves if move.from_square==self.chess_selected and move.to_square==square]
            if len(choices)==1:
                self.play_chess_move(choices[0].uci());return
            if choices:
                menu=tk.Menu(self.root,tearoff=False)
                self.chess_promotion_menu=menu
                names={chess.QUEEN:'Dame',chess.ROOK:'Turm',chess.BISHOP:'Läufer',chess.KNIGHT:'Springer'}
                for move in choices:
                    menu.add_command(label=names[move.promotion],command=lambda m=move,p=self.puzzle:self.play_chess_move(m.uci()) if self.puzzle is p else None)
                menu.tk_popup(event.x_root,event.y_root);return
        piece=board.piece_at(square)
        self.chess_selected=square if piece and piece.color==board.turn and square!=self.chess_selected else None
        self.paint_chess()

    def play_chess_move(self,uci):
        if self.busy or self.showing_solution or self.puzzle.view['kind']!='chess' or self.chess_move:return
        if self.puzzle.check_move(uci)=='invalid':return
        self.chess_move=uci;self.chess_selected=None
        self.on_change()

    def paint_chess(self):
        import chess
        self.canvas.delete('chess-board')
        self.canvas.configure(scrollregion=(0,0,560,660))
        board=chess.Board(self.puzzle.view['fen'])
        selected=self.chess_selected
        targets={move.to_square for move in board.legal_moves if move.from_square==selected} if selected is not None and not self.chess_move else set()
        played=chess.Move.from_uci(self.chess_move) if self.chess_move else None
        san=''
        if played:
            san=board.san(played);board.push(played)
        left,top,step=self.chess_geometry
        for square in chess.SQUARES:
            x,y=self.chess_xy(square)
            dark=(chess.square_file(square)+chess.square_rank(square))%2==0
            bg='#95af8a' if dark else '#eef1df'
            if square==selected:bg='#dbc783'
            self.canvas.create_rectangle(x-step/2,y-step/2,x+step/2,y+step/2,fill=bg,outline='',
                tags=('chess-board','chess-cell',f'chess-cell:{chess.square_name(square)}'))
            piece=board.piece_at(square)
            if piece:
                self.canvas.create_scaled_image(x,y,size=step*.93,
                    factory=lambda pixels,symbol=piece.symbol():self.chess_piece_image(symbol,pixels),
                    tags=('chess-board','chess-piece',f'chess-piece:{chess.square_name(square)}'))
            if square in targets:
                self.canvas.create_oval(x-6,y-6,x+6,y+6,fill='#456957',outline='',tags=('chess-board','chess-legal-target'))
        for i in range(8):
            file=i if self.chess_white_bottom else 7-i
            rank=8-i if self.chess_white_bottom else i+1
            self.canvas.create_text(left+(i+.5)*step,top+8*step+17,text=chess.FILE_NAMES[file],fill=INK,font=('Helvetica',11,'bold'),tags=('chess-board',))
            self.canvas.create_text(left-17,top+(i+.5)*step,text=str(rank),fill=INK,font=('Helvetica',11,'bold'),tags=('chess-board',))
        if played:
            a,b=self.chess_xy(played.from_square),self.chess_xy(played.to_square)
            self.canvas.create_line(*a,*b,fill='#b27932',width=3,arrow='last',tags=('chess-board','chess-move-arrow'))
        side='Weiß' if chess.Board(self.puzzle.view['fen']).turn else 'Schwarz'
        text=f'{side} am Zug' if not played else f'Zug: {san}'
        self.canvas.create_text(left,top+8*step+50,text=text,anchor='w',fill=INK,font=('Helvetica',14,'bold'),tags=('chess-board','chess-turn'))
        if self.showing_solution:
            notation='   '.join(step['san'] for step in self.puzzle.logical_steps)
            self.canvas.create_text(left,top+8*step+80,text='Eine Lösungsvariante: '+notation,anchor='nw',width=460,
                fill=ACCENT,font=('Helvetica',12),tags=('chess-board','chess-variation'))
        if self.showing_solution or self.puzzle.check_move(self.chess_move)=='correct':
            self.canvas.create_text(left,top+8*step+135,text=self.puzzle.solution_explanation(),anchor='nw',width=470,
                fill=INK,font=('Helvetica',12),tags=('chess-board','chess-explanation'))
            box=self.canvas.bbox('chess-explanation')
            self.canvas.configure(scrollregion=(0,0,560,max(880,box[3]+28)))

    def on_chess_change(self):
        import chess
        self.paint_chess()
        state=self.puzzle.check_move(self.chess_move)
        if state=='correct':self.show_success()
        elif state in ('wrong','invalid'):
            self.show_error_count(1)
            self.status.configure(text='Zug geprüft · Rückgängig stellt die Ausgangsstellung wieder her.',foreground=INK)
        else:
            self.hide_success(reset=True);self.dismiss_error(reset=True)
            side='Weiß' if chess.Board(self.puzzle.view['fen']).turn else 'Schwarz'
            self.status.configure(text=f'{side} am Zug · wähle Figur und Zielfeld.',foreground=INK)

    def toggle_strategy_solution(self):
        self.showing_solution=not self.showing_solution
        if self.puzzle.view['kind']=='jump':
            if self.showing_solution:
                self.saved_jump_path=self.jump_path.copy()
                self.jump_path=[self.puzzle.view['start']]+[self.puzzle.solution[k] for k in self.puzzle.editable]
            else:self.jump_path=self.saved_jump_path.copy()
            self.paint_jump()
        else:
            self.chess_selected=None
            if self.showing_solution:
                self.saved_chess_move=self.chess_move;self.chess_move=self.puzzle.best_move
            else:self.chess_move=self.saved_chess_move
            self.paint_chess()
        self.solution_button.configure(text='Zurück zu meinen Eingaben' if self.showing_solution else 'Lösung ansehen')
        self.reset_button.configure(state='disabled' if self.showing_solution else 'normal')
        explanation=self.puzzle.solution_explanation() if self.showing_solution and self.puzzle.view['kind']=='chess' else ''
        self.status.configure(text=explanation or ('Lösungsansicht · dein Spielstand bleibt erhalten.' if self.showing_solution else 'Dein Spielstand ist wiederhergestellt.'),foreground=INK)
