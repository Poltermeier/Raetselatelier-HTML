"""Completion feedback, a small celebration and committed numeric input."""
import random
import tkinter as tk
from tkinter import ttk

PAPER = "#fffef9"
ACCENT = "#27644c"
INK = "#233a32"


def can_extend_number(text, domain):
    """A first digit can still belong to a longer permitted number."""
    return bool(text) and any(str(value).startswith(text) and len(str(value)) > len(text) for value in domain)


class FeedbackUI:
    def setup_feedback(self):
        self.validation_job = None
        self.input_key = None
        self.input_open = False
        self.input_idle_ms = 650
        self.confetti_job = None
        self.celebrated = False
        self.success_dismissed = False
        self.success_visible = False
        self.error_count = None
        self.celebration_runs = 0
        self.error_visible = False
        self.last_error_signature = None
        self.error_popups = 0
        self.success_panel = tk.Frame(self.board_holder,bg=PAPER,highlightbackground=ACCENT,highlightthickness=2)
        self.confetti_canvas = tk.Canvas(self.success_panel,width=480,height=70,bg=PAPER,highlightthickness=0)
        self.confetti_canvas.pack(fill="x",pady=(5,0))
        tk.Label(self.success_panel,text="Richtig gelöst!",fg=ACCENT,bg=PAPER,
                 font=("Times",28,"bold")).pack(pady=(0,8))
        self.success_explanation=tk.Label(self.success_panel,text='',fg=INK,bg=PAPER,justify='left',font=('Helvetica',11))
        buttons = tk.Frame(self.success_panel,bg=PAPER)
        buttons.pack(fill="x",padx=16,pady=(10,18))
        self.success_random_button = ttk.Button(buttons,text="Zufälliges neues Rätsel",command=self.random_puzzle)
        self.success_random_button.pack(side="left",fill="x",expand=True,padx=(0,4))
        self.success_same_button = ttk.Button(buttons,text="Neues Rätsel gleichen Typs",command=self.same_type_puzzle)
        self.success_same_button.pack(side="left",fill="x",expand=True,padx=(4,0))
        tk.Button(self.success_panel,text="×",command=self.dismiss_success,bg=PAPER,fg=ACCENT,
                  activebackground=PAPER,relief="flat",borderwidth=0,font=("Helvetica",14)).place(relx=1,x=-6,y=4,anchor="ne")

        self.error_panel = tk.Frame(self.board_holder,bg=PAPER,highlightbackground="#9a3c30",highlightthickness=2)
        self.error_message = tk.Label(self.error_panel,text="",fg="#9a3c30",bg=PAPER,
                                     font=("Times",26,"bold"),wraplength=480,justify="center")
        self.error_message.pack(fill="x",padx=24,pady=(32,20))
        self.error_continue_button = ttk.Button(self.error_panel,text="Weiter rätseln",command=self.dismiss_error)
        self.error_continue_button.pack(pady=(0,24))
        tk.Button(self.error_panel,text="×",command=self.dismiss_error,bg=PAPER,fg="#9a3c30",
                  activebackground=PAPER,relief="flat",borderwidth=0,font=("Helvetica",14)).place(relx=1,x=-6,y=4,anchor="ne")

    def cancel_validation(self):
        if self.validation_job is not None:
            self.root.after_cancel(self.validation_job)
            self.validation_job = None
        self.input_open = False

    def register_input_commit(self,key,entry):
        entry.bind("<FocusOut>",lambda event,k=key:self.commit_answer(k),add="+")
        entry.bind("<Return>",lambda event,k=key:self.commit_answer(k) or "break",add="+")

    def answer_edited(self,key):
        self.dismiss_error()
        self.cancel_validation()
        self.input_key = key
        entry = self.entries.get(key)
        self.input_open = bool(entry and self.root.focus_get() is entry)
        if self.input_open:
            self.validation_job = self.root.after(self.input_idle_ms,self.commit_answer)

    def commit_answer(self,key=None):
        if key is not None and key != self.input_key:
            return
        was_open = self.input_open
        self.cancel_validation()
        if was_open and self.puzzle is not None and not self.busy and not self.showing_solution:
            self.on_change()

    def pending_answer(self,wrong):
        key = self.input_key
        if not self.input_open or key not in self.vars or self.puzzle.view["kind"] == "lock":
            return None
        text = self.vars[key].get()
        # Even a correct single-digit value may be the start of a two-digit
        # entry. Never celebrate in the middle of typing such a number.
        if can_extend_number(text,self.puzzle.model.domains[key]) or wrong == [key]:
            return key
        return None

    def reset_feedback(self):
        self.cancel_validation()
        self.input_key = None
        self.hide_success(reset=True)
        self.dismiss_error()
        self.last_error_signature = None
        self.error_popups = 0
        self.celebration_runs = 0

    def stop_confetti(self):
        if self.confetti_job is not None:
            self.root.after_cancel(self.confetti_job)
            self.confetti_job = None
        self.confetti_canvas.delete("all")

    def hide_success(self,reset=False):
        self.success_panel.place_forget()
        self.success_visible = False
        self.stop_confetti()
        if reset:
            self.celebrated = False
            self.success_dismissed = False
            self.error_count = None

    def dismiss_success(self):
        self.success_dismissed = True
        self.hide_success()

    def escape(self,event=None):
        if getattr(self,'pentomino_drag',None) is not None:
            self.cancel_pentomino_drag();return 'break'
        if (self.puzzle and self.puzzle.view['kind']=='activity' and self.activity_selected is not None):
            self.activity_selected=None;self.paint_activity();return 'break'
        if self.route_drag_active:
            self.finish_route_drag(cancel=True)
        elif self.border_drag_active:
            self.finish_rectangle_drag()
        elif self.error_visible:
            self.dismiss_error()
        elif self.success_visible:
            self.dismiss_success()
        return "break"

    def show_success(self):
        if self.showing_solution or self.busy:
            return
        self.cancel_validation()
        self.dismiss_error(reset=True)
        self.error_count = 0
        self.status.configure(text="Richtig gelöst!",foreground=ACCENT)
        if self.success_dismissed:
            return
        width = min(540,max(300,self.board_holder.winfo_width()-24))
        explanation=self.puzzle.solution_explanation() if self.puzzle.view['kind']=='chess' else ''
        if self.puzzle.view['kind']=='activity' and self.puzzle.view['mode']=='solitaire':
            explanation=f'Score: 100 / 100 · Zielbild mit {len(self.activity_state["moves"])} Sprüngen erreicht.'
        if explanation:
            self.success_explanation.configure(text=explanation,wraplength=width-36)
            self.success_explanation.pack(fill='x',padx=16,pady=(0,5),before=self.success_random_button.master)
        else:self.success_explanation.pack_forget()
        self.success_panel.update_idletasks()
        self.success_panel.place(relx=.5,rely=.45,anchor="center",width=width,
                                 height=max(230,self.success_panel.winfo_reqheight()+8) if explanation else 230)
        self.success_panel.lift()
        self.success_visible = True
        if not self.celebrated:
            self.celebrated = True
            self.victory_sound.play(self.preferences['volume'])
            self.start_confetti()

    def dismiss_error(self,reset=False):
        self.error_panel.place_forget()
        self.error_visible = False
        if reset:
            self.last_error_signature = None

    def error_signature(self):
        """Only answers identify an attempt; notes, focus and resize do not."""
        if self.puzzle.view['kind']=='activity':return self.activity_signature()
        if self.puzzle.view['kind'] == 'pouring':
            return tuple(self.pour_row_values())
        if self.puzzle.view['kind']=='jump':
            return tuple(self.jump_path)
        if self.puzzle.view['kind']=='chess':
            return self.chess_move
        if self.puzzle.view["kind"] == "rectangles":
            return tuple(sorted(self.borders))
        answers = []
        for key,var in sorted(self.vars.items()):
            text = var.get()
            try:
                value = int(text) if text else 0 if self.is_click_board() else ""
            except ValueError:
                value = text
            answers.append((key,value))
        return tuple(answers)

    def show_error_count(self,count):
        text = "Es ist noch 1 Fehler vorhanden." if count == 1 else f"Es sind noch {count} Fehler vorhanden."
        self.show_error_popup(text, count)

    def show_error_popup(self, text, count=None):
        self.hide_success(reset=True)
        self.cancel_validation()
        self.error_count = count
        self.status.configure(text="Eingabe vollständig.",foreground="#63736a")
        signature = self.error_signature()
        if signature == self.last_error_signature:
            return
        self.last_error_signature = signature
        width = min(540,max(300,self.board_holder.winfo_width()-24))
        self.error_message.configure(text=text,wraplength=width-48)
        self.error_panel.place(relx=.5,rely=.5,anchor="center",width=width,height=220)
        self.error_panel.lift()
        self.error_visible = True
        self.error_popups += 1

    def start_confetti(self):
        self.stop_confetti()
        self.celebration_runs += 1
        rng = random.Random(self.puzzle.seed)
        width = max(480,self.confetti_canvas.winfo_width())
        colors = ("#27644c","#d5a744","#5375a2","#ad658b","#6b9d8a")
        particles = []
        for i in range(26):
            x,y = rng.uniform(12,width-12),rng.uniform(-24,25)
            item = self.confetti_canvas.create_rectangle(x,y,x+rng.randint(4,8),y+rng.randint(5,11),
                       fill=colors[i%len(colors)],outline="",tags=("confetti",))
            particles.append((item,rng.uniform(-1,1),rng.uniform(1.8,3.2)))
        def frame(step=0):
            self.confetti_job = None
            if not self.success_visible:
                return
            for item,dx,dy in particles:
                self.confetti_canvas.move(item,dx,dy)
            if step < 42:
                self.confetti_job = self.root.after(35,lambda:frame(step+1))
            else:
                self.confetti_canvas.delete("all")
        frame()

    def same_type_puzzle(self):
        if self.puzzle is None or self.busy:
            return
        if self.puzzle.type_id=='katzensuche':
            self.cat_size.set(self.puzzle.view['size'])
        if self.puzzle.type_id=='pipes':self.pipe_size.set(self.puzzle.view['size'])
        self.choice.current(self.type_ids.index(self.puzzle.type_id))
        self.seed.delete(0,"end")
        self.selection_changed()
        self.new_puzzle()
