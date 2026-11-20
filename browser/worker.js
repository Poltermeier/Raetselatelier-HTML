"use strict";

const timers = new Map();
let python;
let dispatch;
let preferences = "{}";
let booted = false;

globalThis.atelierEmit = (json) => postMessage({ type: "operations", json });
globalThis.atelierTimer = (id, delay) => {
    timers.set(id, setTimeout(() => {
        timers.delete(id);
        deliver({ kind: "timer", id });
    }, delay));
};
globalThis.atelierCancelTimer = (id) => {
    clearTimeout(timers.get(id));
    timers.delete(id);
};
globalThis.atelierPreferences = () => preferences;
globalThis.atelierSave = (json) => {
    preferences = json;
    postMessage({ type: "preferences", json });
    return true;
};
globalThis.atelierSound = (volume) => postMessage({ type: "sound", volume });

function deliver(event) {
    try {
        dispatch(JSON.stringify(event));
    } catch (error) {
        console.error(error);
        postMessage({ type: "runtime-error", message: String(error) });
    }
}

class Stockfish {
    constructor() {
        this.name = "Stockfish 19 Lite";
        this.worker = new Worker("../runtime/stockfish/stockfish-19-lite-single.js");
        this.pending = null;
        this.rows = new Map();
        this.worker.onmessage = ({ data }) => this.receive(String(data));
        this.worker.onerror = (event) => {
            event.preventDefault();
            this.pending?.reject(new Error(event.message || "Stockfish konnte nicht gestartet werden."));
        };
        this.ready = this.waitFor("uciok", ["uci"]).then(() => this.waitFor("readyok", [
            "setoption name Hash value 32", "setoption name MultiPV value 2", "isready"
        ]));
    }

    waitFor(prefix, commands) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                this.pending = null;
                reject(new Error("Stockfish hat das Zeitlimit überschritten."));
            }, 20000);
            this.pending = {
                prefix,
                resolve: () => {
                    clearTimeout(timeout);
                    this.pending = null;
                    resolve();
                },
                reject: (error) => {
                    clearTimeout(timeout);
                    this.pending = null;
                    reject(error);
                }
            };
            for (const command of commands) this.worker.postMessage(command);
        });
    }

    receive(line) {
        if (line.startsWith("info depth ")) {
            const depth = Number(line.match(/\bdepth (\d+)/)?.[1]);
            const rank = Number(line.match(/\bmultipv (\d+)/)?.[1]);
            const score = line.match(/\bscore (cp|mate) (-?\d+)/);
            const moves = line.match(/\bpv (.+)$/)?.[1]?.trim().split(/\s+/);
            if (depth && rank && score && moves?.length && !/\b(?:lowerbound|upperbound)\b/.test(line)) {
                if (!this.rows.has(depth)) this.rows.set(depth, new Map());
                this.rows.get(depth).set(rank, { score: { [score[1]]: Number(score[2]) }, moves });
            }
        }
        if (this.pending && line.startsWith(this.pending.prefix)) this.pending.resolve();
    }

    async analyze(fen, nodes) {
        this.rows.clear();
        await this.waitFor("bestmove", [
            "setoption name Clear Hash", "position fen " + fen, "go nodes " + nodes
        ]);
        const depth = Math.max(0, ...[...this.rows].filter(([, pair]) => pair.has(1) && pair.has(2)).map(([depth]) => depth));
        if (!depth) return "";
        const best = this.rows.get(depth).get(1);
        const runner = this.rows.get(depth).get(2);
        return JSON.stringify({
            nodes_limit: nodes,
            depth,
            best_move: best.moves[0],
            runner_up_move: runner.moves[0],
            best: best.score,
            runner_up: runner.score,
            pv: best.moves.slice(0, 12),
            runner_pv: runner.moves.slice(0, 8)
        });
    }

    close() {
        this.worker.terminate();
    }
}
globalThis.atelierChess = () => new Stockfish();

async function start() {
    importScripts("../runtime/pyodide/pyodide.js");
    python = await loadPyodide({ indexURL: "../runtime/pyodide/" });
    const archive = await fetch("../runtime/atelier.zip" + self.location.search);
    if (!archive.ok) throw new Error("Der Rätselkatalog konnte nicht geladen werden.");
    python.unpackArchive(await archive.arrayBuffer(), "zip", { extractDir: "/atelier" });
    await python.runPythonAsync(`
import sys
sys.path.insert(0, "/atelier")
from app import start
from tkinter import wire_dispatch
app = start()
`);
    dispatch = python.globals.get("wire_dispatch");
    booted = true;
    postMessage({ type: "ready" });
}

onmessage = ({ data }) => {
    if (data.kind === "start") {
        preferences = data.preferences;
        start().catch((error) => {
            console.error(error);
            postMessage({ type: "startup-error", message: String(error) });
        });
    } else if (booted) {
        deliver(data);
    }
};
