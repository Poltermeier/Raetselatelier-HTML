"""Pencil marks live in separate variables and never count as answers."""
import tkinter as tk
from tkinter import font as tkfont
from .board_canvas import BoardNoteLabel

PAPER = "#fffef9"
ACCENT = "#27644c"
MUTED = "#63736a"


def note_values(text, domain):
    values = set()
    for token in text.replace(",", " ").split():
        try:
            value = int(token)
        except ValueError:
            continue
        if value in domain:
            values.add(value)
    return sorted(values)


class NotesUI:
    def init_notes(self):
        self.note_mode = False
        self.note_vars = {}
        self.note_labels = {}
        self.note_settings = {}
        self.saved_note_mode = False
        self.last_note_key = None

    def notes_supported(self):
        return bool(self.puzzle and self.puzzle.view["kind"] not in ("rectangles", "lock", 'pouring','jump','chess') and self.note_vars)

    def update_notes_button(self):
        active = self.notes_supported() and not self.showing_solution and not self.busy
        self.notes_button.configure(state="normal" if active else "disabled",
            text="Notizen aktiv (N)" if self.note_mode else "Notizen (N)",
            style="NotesOn.TButton" if self.note_mode else "TButton")

    def register_notes(self, key, entry, window):
        entry.bind('<FocusIn>',lambda event,k=key:self.remember_note_focus(k),add='+')
        # Consume N before the Entry class can replace selected note text.
        entry.bind('<KeyPress-n>',self.notes_hotkey,add='+')
        entry.bind('<KeyPress-N>',self.notes_hotkey,add='+')
        var = tk.StringVar()
        prefixes = {str(value)[:i] for value in self.puzzle.model.domains[key]
                    for i in range(1, len(str(value))+1)}
        def validate(text):
            return (len(text) <= 80 and all(c in "0123456789 -," for c in text)
                    and all(token in prefixes for token in text.replace(",", " ").split()))
        self.note_vars[key] = var
        self.note_settings[key] = dict(font=entry.cget("font"), justify=entry.cget("justify"),
            validate=entry.cget("validate"), validatecommand=entry.cget("validatecommand"),
            note_validate=(self.root.register(validate), "%P"),
            window=window, coords=tuple(self.canvas.coords(window)),
            width=float(self.canvas.itemcget(window, "width")),
            height=float(self.canvas.itemcget(window, "height")),
            anchor=self.canvas.itemcget(window, "anchor"),
            borderwidth=entry.cget("borderwidth"), highlightthickness=entry.cget("highlightthickness"))
        label = BoardNoteLabel(entry, text="", font=("Helvetica", 7), fg=MUTED, bg=entry.cget("bg"),
                         justify="left", anchor="nw", borderwidth=0, padx=0, pady=0, takefocus=False)
        label.bind("<Button-1>", lambda event, e=entry: e.focus_set())
        entry.bind("<Configure>", lambda event, k=key: self.refresh_note_preview(k), add="+")
        self.note_labels[key] = label
        var.trace_add("write", lambda *args, k=key: self.on_note_change(k))

    def on_note_change(self, key):
        if self.updating:
            return
        self.record_history()
        self.refresh_note_preview(key)
        if self.note_mode:
            self.note_status()

    def note_status(self):
        if self.puzzle and self.puzzle.view['kind']=='binary-symbols' and self.puzzle.view['mode']=='hitori':
            self.status.configure(text='Notizen aktiv · Klicken markiert oder entfernt einen Kreis für ein weißes Feld.',foreground=ACCENT)
            return
        if self.puzzle and self.puzzle.view['kind']=='treasure':
            self.status.configure(text='Notizen aktiv · Kisten anklicken zum manuellen Durchstreichen.',foreground=ACCENT)
            return
        if self.puzzle and self.puzzle.view['kind'] in ('cats','matrix'):
            self.status.configure(text='Notizen aktiv · Felder anklicken zum manuellen Durchstreichen. Automatische Kreuze folgen deinen Auswahlen.',foreground=ACCENT)
            return
        if self.puzzle and self.puzzle.view['kind']=='routes':
            self.status.configure(text='Notizen aktiv · Kanten oder Zwischenräume anklicken zum Durchstreichen.',foreground=ACCENT)
            return
        if self.puzzle and self.puzzle.type_id == 'kaesekaestchen':
            self.status.configure(text='Notizen aktiv · Freie Felder anklicken für X, O oder X,O. Erneut auf Notizen klicken beendet den Modus.', foreground=ACCENT)
            return
        if self.is_click_board():
            target = "Verbindungen" if self.puzzle.type_id == "pontifex-hashikake" else "freie Felder"
            self.status.configure(text=f"Notizen aktiv · {target} anklicken zum Durchstreichen. Erneut auf Notizen klicken beendet den Modus.", foreground=ACCENT)
            return
        self.status.configure(text="Notizen aktiv · In freien Feldern Kandidaten mit Kommas trennen, z. B. 1,3,7. Erneut klicken für normale Eingaben.",
                              foreground=ACCENT)

    def refresh_note_preview(self, key):
        if key not in self.note_labels:
            return
        label, entry = self.note_labels[key], self.entries[key]
        values = note_values(self.note_vars[key].get(), self.puzzle.model.domains[key])
        if self.note_mode or self.showing_solution or self.vars[key].get() or not values:
            label.place_forget()
            return
        parts = [str(value) for value in values[:9]]
        lines = [",".join(parts[i:i+3]) for i in range(0, len(parts), 3)]
        if len(values) > 9:
            lines[-1] += " +"
        font_size = (9 if len(lines) == 1 and len(lines[0]) <= 5
                     else 6 if entry.winfo_height()/self.canvas.zoom < 32 and len(lines) >= 3 else 7)
        while font_size > 6:
            font = tkfont.Font(self.root, family="Helvetica", size=font_size)
            if max(font.measure(line) for line in lines) <= max(1, entry.winfo_width()/self.canvas.zoom-5):
                break
            font_size -= 1
        label.configure(text=",\n".join(lines), bg=entry.cget("bg"), font=("Helvetica", font_size))
        label.place(x=1, y=1, anchor="nw", relwidth=.95, relheight=.95)
        if key in getattr(self,'diagonal_overlays',{}):self.refresh_diagonal_entry(key)

    def refresh_note_previews(self):
        if self.is_click_board():
            self.paint_click_board()
            return
        for key in self.note_vars:
            self.refresh_note_preview(key)
        self.refresh_diagonal_entries()

    def set_note_mode(self, active):
        self.note_mode = active
        for key, settings in self.note_settings.items():
            entry = self.entries[key]
            entry.configure(validate="none")
            self.canvas.coords(settings["window"], *settings["coords"])
            self.canvas.itemconfigure(settings["window"], anchor=settings["anchor"],
                                      width=settings["width"], height=settings["height"])
            entry.configure(borderwidth=settings["borderwidth"], highlightthickness=settings["highlightthickness"])
            if active and self.vars[key].get():
                # Existing answers stay visible and cannot accidentally become
                # pencil marks. Notes are edited only in unanswered cells.
                entry.configure(textvariable=self.vars[key], font=settings["font"],
                    justify=settings["justify"], readonlybackground=entry.cget("bg"), state="readonly")
                entry.configure(validatecommand=settings["validatecommand"], validate=settings["validate"])
            elif active:
                bg = self.cell_bgs.get(key, PAPER)
                font_size = 7 if settings["width"] < 33 else 9
                entry.configure(textvariable=self.note_vars[key], font=("Helvetica", font_size),
                    justify="left", fg=MUTED, bg=bg, state="normal", borderwidth=0)
                x, y = settings["coords"]
                self.canvas.coords(settings["window"], x-settings["width"]/2+1, y-settings["height"]/2+1)
                self.canvas.itemconfigure(settings["window"], anchor="nw",
                    width=settings["width"]-2, height=min(18, settings["height"]-2))
                entry.configure(validatecommand=settings["note_validate"], validate="key")
                if self.puzzle.view["kind"] == "pearls":
                    self.canvas.itemconfigure(f"pearl:{key}", fill=bg)
            else:
                entry.configure(textvariable=self.vars[key], font=settings["font"],
                                justify=settings["justify"], fg=ACCENT, state="normal")
                entry.configure(validatecommand=settings["validatecommand"], validate=settings["validate"])
        self.update_notes_button()
        self.refresh_note_previews()

    def remember_note_focus(self,key):
        self.last_note_key=key

    def notes_hotkey(self,event):
        if event.state & (4|8|0x20000):return
        focus=self.root.focus_get()
        if focus is not None and focus not in self.entries.values() and focus.winfo_class() in ('Entry','TEntry','Text','TCombobox','Spinbox','TSpinbox'):
            return
        self.toggle_notes()
        return 'break'

    def toggle_notes(self):
        if not self.notes_supported() or self.showing_solution or self.busy:
            return
        self.finish_route_drag()
        self.cancel_nonogram_clicks()
        self.set_note_mode(not self.note_mode)
        if self.note_mode:
            self.note_status()
        else:
            self.on_change()
        entry=self.entries.get(self.last_note_key)
        if entry is not None:
            entry.focus_set()
            entry.selection_range(0,'end')
            entry.icursor('end')
        elif self.is_click_board():
            self.canvas.focus_set()

    def pause_notes_for_solution(self):
        self.saved_note_mode = self.note_mode
        if self.note_mode:
            self.set_note_mode(False)

    def resume_notes_after_solution(self):
        if self.saved_note_mode:
            self.set_note_mode(True)
        self.saved_note_mode = False

    def clear_notes(self):
        for var in self.note_vars.values():
            var.set("")
        self.refresh_note_previews()
