"""Native controls for Gruppen and Ermittlungsakte."""
import random
import tkinter as tk

from .case_clues import COLUMNS
from .ermittlungsakte import MODE as CASE, ROLES
from .gruppen import MODE as GROUPS

MODES = (GROUPS, CASE)
BOARD_WIDTH = 458
INK, MUTED, ERROR = "#233a32", "#63736a", "#94412d"


class DeductionUI:
    def initial_deduction_state(self):
        if self.puzzle.view["mode"] == GROUPS:
            return dict(words=list(self.puzzle.view["words"]), selected=[], found=[])
        return dict(entries={})

    def render_deduction(self):
        if self.puzzle.view["mode"] == GROUPS:
            self.render_groups()
        else:
            self.render_case()
        self.paint_activity()

    def update_deduction_tile(self, button, text, *, selected=False, related=False, resolved=False, disabled=False):
        if selected:
            style = "DeductionSelected.TButton"
        elif related:
            style = "DeductionLinked.TButton"
        elif resolved:
            style = "DeductionResolved.TButton"
        else:
            style = "Deduction.TButton"
        button.configure(text=text, style=style, state="disabled" if disabled else "normal")

    def render_groups(self):
        self.group_feedback = ""
        self.group_buttons = [
            self.activity_button("", lambda index=index: self.pick_group_word(index),
                                 73 + index % 4 * 104, 90 + index // 4 * 62, 96,
                                 height=54, style="Deduction.TButton", tags=("group-tile",f"group-tile:{index}"))
            for index in range(16)
        ]
        self.group_clear = self.activity_button("Auswahl leeren", self.clear_group, 95, 337, 140, height=48,
                                               tags=("group-actions",), style="TButton")
        self.group_shuffle = self.activity_button("Mischen", self.shuffle_group_words, 224, 337, 102, height=48,
                                                 tags=("group-actions",), style="TButton")
        self.group_submit = self.activity_button("Gruppe prüfen", self.submit_group, 358, 337, 150, height=48,
                                                tags=("group-actions",))

    def group_finished(self):
        return len(self.activity_state["found"]) == 4

    def group_owners(self):
        found = range(4) if self.showing_solution else self.activity_state["found"]
        return {word: number for number, group in enumerate(found, 1) for word in self.puzzle.groups[group][1]}

    def pick_group_word(self, index):
        if self.busy or self.showing_solution or self.group_finished():
            return
        word = self.activity_state["words"][index]
        selected = self.activity_state["selected"]
        if word in self.group_owners():
            return
        if word in selected:
            selected.remove(word)
        elif len(selected) < 4:
            selected.append(word)
        else:
            return
        self.group_feedback = ""
        self.update_group_selection()

    def clear_group(self):
        if self.busy or self.showing_solution:
            return
        self.activity_state["selected"].clear()
        self.group_feedback = ""
        self.update_group_selection()

    def update_group_selection(self):
        self.paint_activity()
        self.refresh_assist_review()
        self.status.configure(text=f'{len(self.activity_state["selected"])} von 4 Wörtern ausgewählt.', foreground=INK)

    def shuffle_group_words(self):
        if self.busy or self.showing_solution or self.group_finished():
            return
        words = self.activity_state["words"]
        owners = self.group_owners()
        positions = [index for index, word in enumerate(words) if word not in owners]
        remaining = [words[index] for index in positions]
        random.shuffle(remaining)
        for index, word in zip(positions, remaining):
            words[index] = word
        self.activity_state["selected"].clear()
        self.on_change()

    def submit_group(self):
        if self.busy or self.showing_solution or self.group_finished():
            return
        chosen = self.activity_state["selected"]
        if len(chosen) != 4:
            return
        match = self.puzzle.check_group(chosen)
        if match is None:
            nearly = any(len(set(chosen).intersection(words)) == 3 for _, words in self.puzzle.groups)
            self.group_feedback = "Ein Wort passt noch nicht." if nearly else "Diese vier Wörter bilden keine Gruppe."
            self.paint_activity()
            self.status.configure(text=self.group_feedback, foreground=ERROR)
            return
        self.activity_state["found"].append(match)
        chosen.clear()
        self.on_change()

    def paint_groups(self):
        state = self.activity_state
        owners = self.group_owners()
        disabled = self.busy or self.showing_solution or self.group_finished()
        for word, button in zip(state["words"], self.group_buttons):
            number = owners.get(word)
            self.update_deduction_tile(
                button, f"{word}\nGruppe {number}" if number else word,
                resolved=bool(number), selected=word in state["selected"] and not self.showing_solution,
                disabled=disabled or bool(number),
            )
        self.canvas.itemconfigure("group-actions", state="hidden" if self.showing_solution else "normal")
        self.group_clear.configure(state="normal" if state["selected"] and not disabled else "disabled")
        self.group_submit.configure(state="normal" if len(state["selected"]) == 4 and not disabled else "disabled")
        self.group_shuffle.configure(state="disabled" if disabled else "normal")
        found = range(4) if self.showing_solution else state["found"]
        heading = "Alle Gruppen" if self.showing_solution else f"{len(found)} von 4 Gruppen gefunden"
        self.word_text(25, 22, heading, size=14, bold=True)
        if state["selected"] and not self.showing_solution:
            self.word_text(307, 25, f'{len(state["selected"])} von 4 gewählt', size=11, color=MUTED)
        for index, group in enumerate(found, 1):
            theme, members = self.puzzle.groups[group]
            y = 267 + index * 65 if self.showing_solution else 325 + index * 65
            self.word_text(25, y, f"{index} · {theme}", size=13, bold=True, width=408)
            self.word_text(25, y + 25, " · ".join(members), size=10, width=408)
        if self.group_feedback and not self.showing_solution:
            self.word_text(25, 368, self.group_feedback, size=11, color=ERROR, width=408)
        height = 598 if self.showing_solution else 390 + 65 * len(found)
        self.canvas.configure(scrollregion=(0, 0, BOARD_WIDTH, height))

    def render_case(self):
        self.case_clue_index = 0
        self.case_solution_index = 0
        self.case_feedback = ""
        self.case_heading = tk.Label(self.canvas, text="", anchor="w", font=("Helvetica", 12, "bold"),
                                     background="#fffef9", foreground=INK)
        self.case_clue = tk.Label(self.canvas, text="", anchor="w", justify="left", wraplength=398,
                                  font=("Helvetica", 12), background="#eef3ec", foreground=INK, padx=9)
        self.case_prompt = tk.Label(self.canvas, text="", anchor="w", justify="left", wraplength=402,
                                    font=("Helvetica", 11), background="#fffef9", foreground=INK)
        self.extra_widgets.extend((self.case_heading, self.case_clue, self.case_prompt))
        self.canvas.create_window(25, 17, window=self.case_heading, width=408, height=24, anchor="nw")
        self.canvas.create_window(25, 47, window=self.case_clue, width=408, height=94, anchor="nw")
        self.canvas.create_window(25, 197, window=self.case_prompt, width=408, height=33,
                                  anchor="nw", tags=("case-actions",))
        self.case_previous = self.activity_button("Vorige Spur", lambda: self.turn_case_clue(-1), 90, 168, 130,
                                                  height=44, style="TButton")
        self.case_next = self.activity_button("Nächste Spur", lambda: self.turn_case_clue(1), 238, 168, 150,
                                              height=44, style="TButton")
        self.case_roles = [
            self.activity_button(role, lambda value=value: self.mark_case_person(value),
                                 128 + value * 202, 257, 194, tags=("case-actions",),
                                 height=48, style="TButton")
            for value, role in enumerate(ROLES)
        ]
        self.case_people = {}
        self.case_rooms = []
        view = self.puzzle.view
        stride = 420 / len(COLUMNS)
        for column, letter in enumerate(COLUMNS):
            label = tk.Label(self.canvas, text=letter, justify="center", font=("Helvetica", 11, "bold"),
                             background="#eef3ec", foreground=INK)
            self.extra_widgets.append(label)
            self.canvas.create_window(17 + (column + .5) * stride, 299, window=label, width=stride - 4, height=23)
        for row, (room, people) in enumerate(zip(view["rooms"], view["people"])):
            label = tk.Label(self.canvas, text=room, anchor="w", font=("Helvetica", 11, "bold"),
                             background="#fffef9", foreground=INK)
            self.extra_widgets.append(label)
            self.case_rooms.append(label)
            self.canvas.create_window(25, 315 + row * 78, window=label, width=408, height=18, anchor="nw")
            for column, name in enumerate(people):
                self.case_people[name] = self.activity_button(
                    name, lambda person=name: self.select_case_person(person),
                    17 + (column + .5) * stride, 363 + row * 78, stride - 4, height=56,
                    style="Deduction.TButton", tags=("case-person",),
                )

    def case_clues(self):
        confirmed = ((step["person"] for step in self.puzzle.logical_steps)
                     if self.showing_solution else self.activity_state["entries"])
        return self.puzzle.revealed_clues(confirmed)

    def turn_case_clue(self, step):
        if self.busy:
            return
        if self.showing_solution:
            self.case_solution_index += step
        else:
            self.case_clue_index += step
        self.paint_activity()

    def select_case_person(self, name):
        if self.busy or self.showing_solution:
            return
        had_feedback = bool(self.case_feedback)
        self.case_feedback = ""
        entries = self.activity_state["entries"]
        if name in entries:
            self.case_clue_index = list(entries).index(name) + 1
            self.activity_selected = None
        else:
            self.activity_selected = None if self.activity_selected == name else name
        self.paint_activity()
        if had_feedback:
            self.status.configure(text=f"{len(entries)} von {len(self.case_people)} Personen zugeordnet.", foreground=INK)

    def mark_case_person(self, value):
        name = self.activity_selected
        if self.busy or self.showing_solution or name is None:
            return
        entries = self.activity_state["entries"]
        result = self.puzzle.classify(name, value, entries)
        if result == "correct":
            entries[name] = value
            self.activity_selected = None
            self.case_clue_index = len(entries)
            self.on_change()
            return
        if result == "invalid":
            return
        self.case_feedback = {
            "wrong": "Die Spuren belegen die andere Rolle.",
            "undetermined": "Die offenen Spuren lassen beide Rollen zu.",
            "unproven": "Die Ableitung konnte gerade nicht geprüft werden.",
        }[result]
        self.paint_activity()
        self.status.configure(text=self.case_feedback, foreground=ERROR)

    def paint_case(self):
        clues = self.case_clues()
        index_attr = "case_solution_index" if self.showing_solution else "case_clue_index"
        index = max(0, min(getattr(self, index_attr), len(clues) - 1))
        setattr(self, index_attr, index)
        source, clue = clues[index]
        heading = f"Spur von {source}" if source else "Startspur"
        self.case_heading.configure(text=f"{heading} · {index + 1}/{len(clues)}")
        if self.case_clue.cget("text") != clue.text:
            self.case_clue.configure(text=clue.text)
        self.case_previous.configure(state="disabled" if self.busy or index == 0 else "normal")
        self.case_next.configure(state="disabled" if self.busy or index == len(clues) - 1 else "normal")
        entries = self.puzzle.solution if self.showing_solution else self.activity_state["entries"]
        references = set(clue.anchors)
        for name, button in self.case_people.items():
            known = name in entries
            role = ROLES[entries[name]] if known else "Offen"
            self.update_deduction_tile(
                button, f"{name}\n{role}", selected=self.activity_selected == name,
                related=name in references, resolved=known, disabled=self.busy or self.showing_solution,
            )
        self.canvas.itemconfigure("case-actions", state="hidden" if self.showing_solution else "normal")
        editing = not self.busy and not self.showing_solution and self.activity_selected is not None
        for button in self.case_roles:
            button.configure(state="normal" if editing else "disabled")
        if not self.showing_solution:
            done, total = len(entries), len(self.case_people)
            self.word_text(327, 163, f"{done}/{total} geklärt", size=11, color=MUTED)
            if self.activity_selected:
                prompt = f"Gewählt: {self.activity_selected}"
            else:
                prompt = "Akte abgeschlossen." if done == total else "Wähle eine Person auf dem Raster."
            self.case_prompt.configure(text=self.case_feedback or prompt, foreground=ERROR if self.case_feedback else INK)
        self.canvas.configure(scrollregion=(0, 0, 440, 644))

    def paint_deduction(self):
        if self.puzzle.view["mode"] == GROUPS:
            self.paint_groups()
        else:
            self.paint_case()

    def on_deduction_change(self):
        state = self.activity_state
        if self.puzzle.view["mode"] == GROUPS:
            self.group_feedback = ""
            finished = self.group_finished()
            text = f'{len(state["found"])} von 4 Gruppen gefunden.'
        else:
            self.case_feedback = ""
            assigned = len(state["entries"])
            total = len(self.case_people)
            finished = assigned == total
            text = f"{assigned} von {total} Personen zugeordnet."
            if assigned:
                text += f" Spur von {next(reversed(state['entries']))} freigeschaltet."
        self.paint_activity()
        if finished:
            self.show_success()
        else:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text=text, foreground=INK)
