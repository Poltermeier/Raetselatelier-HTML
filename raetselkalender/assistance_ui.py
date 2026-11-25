"""Hints and reversible visual checks for the current player inputs."""
from tkinter import ttk

from .assistance import ACTIVITY_HINTS, jump_distances, model_hint, wrong_answers
from .card_code_matches import valid_set
from .hashi_ui import bridge_segments
from .mahjong import group, open_tiles
from .word_games import normalize_word

RED, PALE_RED, BLUE = "#a62531", "#ffe6e7", "#17619b"
MARK = "assist-error"
TIP = "assist-tip"
CELL_TAGS = ("box-cell", "camping-cell", "cheese-cell", "nest-cell", "mine-cell", "symbol-cell", "cell")
MODEL_ACTIVITIES = {"crypto", "circuit", "pipes"}


class AssistanceUI:
    def setup_assistance(self):
        self.assist_review = False
        self.assist_fields = {}
        self.assist_marks = False
        panel = ttk.Frame(self.main)
        panel.pack(fill="x", pady=(0, 10))
        buttons = ttk.Frame(panel)
        buttons.pack(anchor="w")
        self.hint_button = ttk.Button(buttons, text="Tipp", command=self.show_hint, state="disabled")
        self.hint_button.pack(side="left", padx=(0, 6))
        self.review_button = ttk.Button(buttons, text="Falsche anzeigen", command=self.toggle_assist_review, state="disabled")
        self.review_button.pack(side="left")
        self.hint_message = ttk.Label(panel, text="", foreground=BLUE, justify="left", wraplength=700)
        self.review_message = ttk.Label(panel, text="", justify="left", wraplength=700)

    def update_assist_buttons(self):
        enabled = (self.puzzle is not None and self.puzzle.view['kind'] not in ('chess-match', 'popout', 'symbol-duel', 'sequence')
                   and not self.busy and not self.showing_solution and self.nonogram_lives != 0)
        state = "normal" if enabled else "disabled"
        self.hint_button.configure(state=state)
        self.review_button.configure(state=state, text="Falsche ausblenden" if self.assist_review else "Falsche anzeigen")

    def clear_hint(self):
        if self.hint_message.cget("text"):
            self.hint_message.configure(text="")
            self.hint_message.pack_forget()
            self.canvas.delete(TIP)

    def clear_assist_marks(self):
        if self.assist_marks:
            self.canvas.delete(MARK)
            self.assist_marks = False
        for entry, (key, options) in self.assist_fields.items():
            if entry.winfo_exists():
                entry.configure(**options)
                self.set_assist_invalid(entry, False)
                self.refresh_diagonal_entry(key)
        self.assist_fields.clear()

    def close_assistance(self):
        self.clear_hint()
        self.clear_assist_marks()
        self.assist_review = False
        self.review_message.pack_forget()
        self.update_assist_buttons()

    def set_assist_invalid(self, entry, invalid):
        pass  # The browser adapter exposes the visual error to assistive technologies.

    def mark_assist_entry(self, key, entry):
        if entry in self.assist_fields:
            return
        options = {option: entry.cget(option) for option in ("bg", "fg", "readonlybackground", "highlightbackground")}
        self.assist_fields[entry] = (key, options)
        entry.configure(bg=PALE_RED, fg=RED, readonlybackground=PALE_RED, highlightbackground=RED)
        self.set_assist_invalid(entry, True)
        self.refresh_diagonal_entry(key)

    def assist_answers(self):
        p = self.puzzle
        kind, mode = p.view["kind"], p.view.get("mode")
        if kind == "activity":
            if mode not in MODEL_ACTIVITIES:
                return {}
            values = self.workshop_entries()
            if mode == "pipes":
                values = {key: value for key, value in values.items() if value != p.view["initial"][key]}
            return values
        if kind == "lock":
            return dict(zip(p.view["code_keys"], map(int, self.vars["Code"].get())))
        if kind in ("rectangles", "jump", "chess", "pouring"):
            return {}
        answers = {}
        for key, var in self.vars.items():
            text = var.get().strip()
            if text:
                try:
                    answers[key] = int(text)
                except ValueError:
                    answers[key] = text
        return answers

    def outline_assist(self, box, *, hint=False, line=False):
        if not box or len(box) != 4:
            return
        color, tag = (BLUE, TIP) if hint else (RED, MARK)
        if line:
            self.canvas.create_line(*box, fill=color, width=4, capstyle="round",
                                    dash=(6, 3) if hint else (), tags=(tag,))
        else:
            a, b, c, d = box
            self.canvas.create_rectangle(a+2, b+2, c-2, d-2, outline=color, width=3, tags=(tag,))
        if not hint:
            self.assist_marks = True

    def assist_position(self, key, value=None, *, hint=False):
        kind, mode = self.puzzle.view["kind"], self.puzzle.view.get("mode")
        entry = self.entries.get(key)
        if mode == "crypto":
            entry = self.workshop_entries_ui.get(key)
        if entry is not None and not hint:
            self.mark_assist_entry(key, entry)
            return
        if kind == "routes":
            self.outline_assist(self.route_segments.get(key), hint=hint, line=True)
            return
        if kind == "hashi":
            _, a, b = next(edge for edge in self.puzzle.view["edges"] if edge[0] == key)
            for segment in bridge_segments(self.hashi_xy(a), self.hashi_xy(b), value if value in (1, 2, 3) else 1):
                self.outline_assist(segment, hint=hint, line=True)
            return
        if kind in ("cats", "matrix"):
            row = self.matrix_keys.index(key)
            left, top, step = self.matrix_geometry
            box = (left, top+row*step, left+self.puzzle.view["size"]*step, top+(row+1)*step)
            if isinstance(value, int) and value in self.puzzle.model.domains[key]:
                box = (left+(value-1)*step, box[1], left+value*step, box[3])
            self.outline_assist(box, hint=hint)
            return
        if kind == "treasure":
            self.outline_assist(self.canvas.bbox(f"treasure-box:{value}"), hint=hint)
            return
        tags = [f"assist-field:{key}", *(f"{prefix}:{key}" for prefix in CELL_TAGS),
                f"pipe-cell:{key}", f"circuit-input:{key}"]
        box = next((self.canvas.bbox(tag) for tag in tags if self.canvas.find_withtag(tag)), None)
        if box and entry is not None:
            a, b, c, d = box
            box = a-6, b-6, c+6, d+6  # Keep the outline outside the native input.
        self.outline_assist(box, hint=hint)

    def toggle_assist_review(self):
        if self.busy or self.showing_solution or self.puzzle is None:
            return
        self.cancel_validation()
        self.assist_review = not self.assist_review
        self.update_assist_buttons()
        self.clear_assist_marks()
        if self.assist_review:
            self.dismiss_error()
            self.paint_assist_review()
            self.review_message.pack(anchor="w", pady=(4, 0))
        else:
            self.review_message.pack_forget()

    def paint_assist_review(self):
        p = self.puzzle
        kind, mode = p.view["kind"], p.view.get("mode")
        wrong = wrong_answers(p, self.assist_answers())
        count, extra = len(wrong), ""
        if kind == "lock" and count:
            self.assist_position("Code")
            positions = [str(i+1) for i, key in enumerate(p.view["code_keys"]) if key in wrong]
            extra = " Falsche Stellen im Code: " + ", ".join(positions) + "."
        else:
            for key, value in wrong.items():
                self.assist_position(key, value)
        if kind == "rectangles":
            for edge in self.borders - self.solution_borders():
                self.outline_assist(self.canvas.coords(self.border_items[edge]), line=True)
                count += 1
        elif kind == "chess" and self.chess_move and p.check_move(self.chess_move) != "correct":
            self.outline_assist(self.canvas.bbox(f"chess-cell:{self.chess_move[2:4]}"))
            count = 1
        elif kind == "jump" and p.view["require_shortest"] and len(self.jump_path) > 1:
            distances = jump_distances(p)
            for steps, position in enumerate(self.jump_path[1:], 1):
                if steps + distances.get(position, float("inf")) > p.view["par"]:
                    self.outline_assist(self.canvas.bbox(f"jump-cell:{position}"))
                    count, extra = 1, " Ab dem markierten Sprung reicht die vorgegebene Zugzahl nicht mehr."
                    break
        elif kind == "pouring":
            _, _, blocked = self.preview_pours()
            if blocked:
                offset = (blocked - 1) * 50
                self.outline_assist((69, 375+offset, 428, 425+offset))
                count, extra = 1, f" Der Umfüllvorgang in Zeile {blocked} ist mit diesen Füllständen nicht möglich."
        elif mode in ("target24", "friedman"):
            expression = self.activity_state["expression"].strip()
            if expression and p.check_expression(expression)[0] != "correct":
                self.mark_assist_entry("expression", self.workshop_entries_ui["expression"])
                count = 1
        elif mode == "twiddle":
            for index, (value, target) in enumerate(zip(self.activity_state["board"], p.view["target"])):
                if value != target:
                    self.outline_assist(self.canvas.bbox(f"twiddle-tile:{index}"))
                    count += 1
            if count:
                extra = " Die markierten Zahlen stehen noch nicht an ihrem Zielplatz."
        elif mode in ("h2o", "schachaufstellung"):
            for key, value in self.activity_state["placed"].items():
                if p.solution.get(key) != value:
                    cell = key if mode == "h2o" else value
                    self.outline_assist(self.canvas.bbox(f"placement-cell:{cell}"))
                    count += 1
        elif mode == "matches":
            state = self.activity_state
            if len(state["moves"]) == p.view["moves_required"] and p.check_mask(state["mask"]) != "correct":
                self.outline_assist((28, 132, 605, 246))
                count, extra = 1, " Die Gleichung stimmt in dieser Anordnung nicht."
        elif mode in ("sets", "gruppen"):
            draft = self.activity_state["draft"] if mode == "sets" else self.activity_state["selected"]
            invalid = (len(draft) == 3 and not valid_set([p.view["cards"][i] for i in draft])
                       if mode == "sets" else len(draft) == 4 and p.check_group(draft) is None)
            if invalid:
                if mode == "sets":
                    for index in draft:
                        self.outline_assist(self.canvas.bbox(f"set-card:{index}"))
                else:
                    for word in draft:
                        box = self.canvas.bbox(f"group-tile:{self.activity_state['words'].index(word)}")
                        if box:
                            a,b,c,d = box
                            self.outline_assist((a-6,b-6,c+6,d+6))
                count, extra = 1, " Diese Auswahl passt als Gruppe nicht zusammen."
        elif mode in ("buchstabenwerkstatt", "wortring"):
            word = normalize_word(self.activity_state["draft"])
            if word and len(word) >= p.view.get("minimum", p.view.get("length", 1)) and p.word_error(word):
                self.mark_assist_entry("word", self.word_entry)
                count = 1
        if count:
            text = ("1 Fehler gefunden." if count == 1 else f"{count} Fehler gefunden.") + extra
        elif mode in ("hearts", "solitaire", "freecell", "mahjong", "water-sort", "row-shift", "pentomino", "ermittlungsakte"):
            text = "Die Regeln werden bei jedem Zug geprüft. Bisher ist kein regelwidriger Zug eingetragen."
        elif mode == "wortspur":
            text = "Die farbigen Zeichen hinter deinen Versuchen zeigen, welche Buchstaben und Positionen passen."
        elif mode == "mastermind":
            text = "Die Rückmeldung neben jedem Versuch zeigt die Anzahl passender Farben und Positionen."
        else:
            text = "Keine falschen Eingaben gefunden."
        self.review_message.configure(text=text, foreground=RED if count else "#63736a")

    def refresh_assist_review(self):
        if self.assist_review and not self.busy and not self.showing_solution:
            self.clear_assist_marks()
            self.paint_assist_review()

    def show_hint(self):
        if self.busy or self.showing_solution or self.puzzle is None:
            return
        self.cancel_validation()
        self.clear_hint()
        p = self.puzzle
        kind, mode = p.view["kind"], p.view.get("mode")
        answers = self.assist_answers()
        wrong = wrong_answers(p, answers)
        if wrong:
            key = next(iter(wrong))
            if kind == "lock":
                self.assist_position("Code", hint=True)
                text = "Mindestens eine Stelle im bisherigen Code passt nicht zu den Hinweisen. Vergleiche die Testcodes."
            else:
                self.assist_position(key, wrong[key], hint=True)
                text = "Eine deiner Eingaben widerspricht den Vorgaben. Prüfe zuerst die markierte Stelle."
        elif kind == "rectangles":
            target = self.borders - self.solution_borders()
            if target:
                self.outline_assist(self.canvas.coords(self.border_items[min(target)]), hint=True, line=True)
                text = "Prüfe die markierte Grenze. Passt sie zu einem Rechteck mit der angegebenen Größe?"
            else:
                text = "Ermittle für eine Vorgabe die möglichen Rechteckformen und streiche die Formen, die eine zweite Vorgabe einschließen."
        elif kind == "chess":
            square = p.best_move[:2]
            self.outline_assist(self.canvas.bbox(f"chess-cell:{square}"), hint=True)
            text = f"Schau dir die Figur auf {square} an. Welche Drohung kann sie aufstellen?"
        elif kind == "jump":
            current = self.jump_path[-1]
            distances = jump_distances(p)
            text = "Vergleiche bei den erreichbaren Feldern, von welchem du dem Ziel am nächsten kommst. Achte auf das Zuglimit."
            if current == p.view["goal"] and p.check_path(self.jump_path) == "correct":
                text = "Das Ziel ist erreicht."
            elif current not in distances or (p.view["require_shortest"] and
                    len(self.jump_path)-1 + distances[current] > p.view["par"]):
                text = "Von hier reicht die Zugzahl nicht mehr. Nimm die letzten Sprünge zurück und prüfe eine Abzweigung."
            else:
                next_step = next((target for target in p.targets(current)
                                  if distances.get(target) == distances[current]-1), None)
                if next_step is not None:
                    self.outline_assist(self.canvas.bbox(f"jump-cell:{next_step}"), hint=True)
                    text = "Das markierte Feld ist erreichbar und führt auf einem kürzesten Weg weiter zum Ziel."
        elif kind == "pouring":
            text = "Gieße so um, dass ein Gefäß komplett voll oder leer wird. Vergleiche die resultierenden Mengen mit dem Ziel."
        elif kind == "lock":
            text = "Beginne mit einem Testcode, dessen Rückmeldung Ziffern ausschließt. Vergleiche dann, wo dieselben Ziffern in anderen Testcodes stehen."
        elif kind == "treasure":
            text = "Nimm eine Kiste als Kandidatin an. Prüfe dann jede Aussage anhand dieser Annahme."
        elif kind == "distance":
            text = "Beginne mit einem kurzen Abstand. Nach jeder Verbindung müssen alle übrigen Schritte noch länger werden können."
        elif p.type_id == "summe-produkt":
            if p.view["rows"] == 3:
                text = "Berechne aus der vollständigen Spalte das Produkt und aus der vollständigen Zeile die Summe. Suche passende Faktorpaare für die übrigen Spalten."
            else:
                text = "Nenne das gemeinsame Spaltenprodukt P. Teile P durch die bekannte Zahl jeder Spalte. Setze die Ergebnisse in die Zeilensummen ein."
        elif p.type_id == "fillomino":
            text = "Beginne mit kleinen Gruppen. Eine 1 steht allein. Prüfe bei größeren Gruppen, welche benachbarten Felder Platz für alle benötigten Felder bieten."
        elif kind == "harakiri":
            text = "Vergleiche die fehlenden Zahlen eines Rings mit den fehlenden Zahlen auf dem Durchmesser durch das jeweilige Feld."
        elif mode in ("h2o", "schachaufstellung"):
            text = self.placement_hint()
        elif mode == "friedman":
            text = "Teile die Ziffern gedanklich in Blöcke. Prüfe, welche Blöcke sich als Basis und Exponent eignen."
        elif mode == "twiddle":
            text = self.twiddle_hint()
        elif mode == "gruppen":
            solved = self.activity_state["found"]
            theme = next((name for i, (name, _) in enumerate(p.groups) if i not in solved), None)
            text = f"Vier der übrigen Wörter passen zu „{theme}“." if theme else "Alle Gruppen sind gefunden."
        elif mode == "mahjong":
            open_pieces = open_tiles(self.activity_state["board"], self.mahjong_geometry)
            candidates = {}
            pair = None
            for index in open_pieces:
                face = group(p.view["faces"][index])
                if face in candidates:
                    pair = candidates[face], index
                    break
                candidates[face] = index
            if pair:
                for index in pair:
                    self.outline_assist(self.canvas.bbox(f"mahjong-tile:{index}"), hint=True)
                text = "Die beiden markierten Steine sind frei und bilden ein Paar."
            else:
                text = "Aktuell gibt es kein freies Paar. Mit Rückgängig kannst du eine andere Auswahl versuchen."
        elif mode == "ermittlungsakte":
            text = self.next_case_tip()
        elif p.analysis.get("logical_solvable") and (kind != "activity" or mode in MODEL_ACTIVITIES):
            if not set(p.editable).difference(answers):
                text = "Die Eingaben stimmen."
            else:
                step = model_hint(p, answers)
                if step:
                    key, text = step
                    self.assist_position(key, hint=True)
                else:
                    text = "Konzentriere dich auf die Vorgabe mit den wenigsten offenen Möglichkeiten."
        else:
            text = ACTIVITY_HINTS.get(mode, "Prüfe zuerst die Vorgabe mit den wenigsten offenen Möglichkeiten.")
        self.hint_message.configure(text="Tipp · " + text)
        self.hint_message.pack(anchor="w", pady=(4, 0))
