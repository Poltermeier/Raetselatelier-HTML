"""Opt-in, local background CPU report without puzzle answers or key contents."""
from collections import Counter
import cProfile
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import pstats
import sys
import time
import _tkinter


class IdleDiagnostics:
    def __init__(self, app, path, *, delay_ms=10000, duration_ms=30000):
        self.app, self.root, self.path = app, app.root, Path(path)
        self.delay_ms, self.duration_ms = delay_ms, duration_ms
        self.job = None
        self.profile = None
        self.bindings = []
        self.events = Counter()
        self.generations_started = 0
        self.finished = False

    def arm(self):
        if self.finished or self.job is not None or self.profile is not None:
            return
        self.app.status.configure(text='CPU-Diagnose startet in 10 Sekunden. Fenster danach im Hintergrund lassen.')
        self.job = self.root.after(self.delay_ms, self.start)

    def generation_started(self):
        if self.profile is not None:
            self.generations_started += 1
        elif self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None

    def snapshot(self):
        return dict(window_state=self.root.state(),
                    focused=bool(self.root.tk.call('focus', '-displayof', self.root._w)),
                    generating=self.app.busy,
                    pending_timers=len(self.root.tk.splitlist(self.root.tk.call('after', 'info'))),
                    puzzle_type=self.app.puzzle.type_id if self.app.puzzle else None)

    def start(self):
        self.job = None
        if self.finished or self.app.busy or self.app.puzzle is None:
            return
        self.app.status.configure(text='CPU-Diagnose läuft für 30 Sekunden. Fenster im Hintergrund lassen.')
        self.root.update_idletasks()
        for event in ('<Configure>', '<Expose>', '<Motion>', '<KeyPress>', '<ButtonPress>', '<FocusIn>', '<FocusOut>'):
            def count(_event, name=event):
                self.events[name] += 1
            self.bindings.append((event, self.root.bind(event, count, add='+')))
        self.initial = self.snapshot()
        self.wall_start, self.cpu_start = time.perf_counter(), time.process_time()
        self.profile = cProfile.Profile()
        self.profile.enable()
        self.job = self.root.after(self.duration_ms, self.finish)

    def finish(self):
        self.job = None
        self.profile.disable()
        elapsed, cpu = time.perf_counter()-self.wall_start, time.process_time()-self.cpu_start
        stats = pstats.Stats(self.profile).stats
        self.profile = None
        self.finished = True
        self.remove_bindings()
        functions = [dict(file=Path(file).name, line=line, function=name,
                          calls=data[1], self_wall_seconds=data[2], total_wall_seconds=data[3])
                     for (file, line, name), data in stats.items()]
        functions.sort(key=lambda item: item['self_wall_seconds'], reverse=True)
        logical_cpus = os.cpu_count() or 1
        report = dict(schema=1, recorded_at=datetime.now(timezone.utc).isoformat(),
                      system=platform.system(), system_release=platform.release(),
                      python=platform.python_version(), packaged_exe=bool(getattr(sys, 'frozen', False)),
                      tcl=self.root.tk.call('info', 'patchlevel'), tk=self.root.tk.call('package', 'provide', 'Tk'),
                      tcl_threaded=(bool(int(self.root.tk.getvar('tcl_platform(threaded)')))
                                    if self.root.tk.call('info', 'exists', 'tcl_platform(threaded)') else None),
                      tkinter_busywait_ms=_tkinter.getbusywaitinterval(),
                      pid=os.getpid(), parent_pid=os.getppid(), logical_cpus=logical_cpus,
                      elapsed_seconds=elapsed, process_cpu_seconds=cpu,
                      cpu_percent_one_core=100*cpu/max(elapsed, .001),
                      cpu_percent_machine=100*cpu/max(elapsed, .001)/logical_cpus,
                      start=self.initial, end=self.snapshot(), events=dict(self.events),
                      generations_started=self.generations_started, top_functions=functions[:30],
                      profiling_overhead_included=True)
        try:
            self.path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            self.app.status.configure(text='CPU-Diagnose konnte nicht gespeichert werden. Bitte einen beschreibbaren Dateipfad wählen.')
        else:
            self.app.status.configure(text=f'CPU-Diagnose gespeichert: {self.path}')

    def remove_bindings(self):
        for event, binding in self.bindings:
            self.root.unbind(event, binding)
        self.bindings.clear()

    def close(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        if self.profile is not None:
            self.profile.disable()
            self.profile = None
        self.remove_bindings()
        self.finished = True
