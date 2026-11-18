"use strict";

const host = document.querySelector("#atelier");
const startup = document.querySelector("#startup");
const dialog = document.querySelector("#message-dialog");
const widgets = new Map();
const styles = new Map();
const fonts = new Map();
const images = new Map();
const pendingDraw = new Set();
const preferencesKey = "simons-raetselatelier.settings";
let engine, frame, audio, currentDialog;
const dialogs = [];

function post(data) {
    engine?.postMessage(data);
}

function fontStyle(spec) {
    const [family, size, ...traits] = Array.isArray(spec) ? spec : ["Helvetica", 10];
    const key = JSON.stringify(spec);
    if (!fonts.has(key)) {
        const flags = traits.join(" ");
        const pixels = Math.abs(size) * (size < 0 ? 1 : 4 / 3);
        const families = family.startsWith("Times") ? 'Georgia, "Times New Roman", serif' :
            family.startsWith("Courier") ? 'monospace' : 'Helvetica, Arial, sans-serif';
        fonts.set(key, {
            css: `${flags.includes("italic") ? "italic " : ""}${flags.includes("bold") ? "bold " : ""}${pixels}px ${families}`,
            pixels
        });
    }
    return fonts.get(key);
}

const length = (value) => typeof value === "number" ? `${value}px` : value;
const pair = (value = 0) => Array.isArray(value) ? value : [value, value];

function makeWidget(id, kind, parentId) {
    const parent = widgets.get(parentId);
    const element = document.createElement(kind === "Toplevel" ? "dialog" : "div");
    element.className = `tk-widget tk-${kind.toLowerCase()}`;
    element.dataset.widget = id;
    element.hidden = kind !== "Root";
    const widget = { id, kind, element, parent, options: {}, bindings: new Set() };
    widgets.set(id, widget);
    (kind === "Toplevel" || kind === "Menu" ? document.body : parent?.element || host).append(element);
    const tag = { Button: "button", Entry: "input", Combobox: "select", Scale: "input", Checkbutton: "input" }[kind];
    if (tag) {
        const input = widget.input = document.createElement(tag);
        if (kind === "Entry") {
            input.type = "text";
            input.autocomplete = "off";
            input.spellcheck = false;
        }
        if (kind === "Scale") input.type = "range";
        if (kind === "Checkbutton") {
            input.type = "checkbox";
            const label = document.createElement("label");
            widget.label = document.createElement("span");
            label.append(input, widget.label);
            element.append(label);
        } else element.append(input);

        if (kind === "Button") input.addEventListener("click", () => post({ kind: "command", id }));
        if (kind === "Entry") input.addEventListener("input", () => {
            const revision = (widget.inputRevision || 0) + 1;
            widget.inputRevision = revision;
            post({ kind: "input", id, value: input.value, revision, selection: selection(widget) });
        });
        if (kind === "Combobox" || kind === "Checkbutton" || kind === "Scale") {
            input.addEventListener(kind === "Scale" ? "input" : "change", () => {
                post({ kind: "change", id, value: kind === "Checkbutton" ? input.checked : input.value });
            });
        }
        input.addEventListener("focus", () => eventFor(widget, "<FocusIn>"));
        input.addEventListener("blur", () => eventFor(widget, "<FocusOut>"));
    }
    if (kind === "Canvas") setupCanvas(widget);
    else {
        for (const [type, sequence] of [["pointerdown", "<Button-1>"], ["dblclick", "<Double-Button-1>"]]) {
            element.addEventListener(type, (event) => {
                if (widget.bindings.has(sequence) && event.target.closest("[data-widget]") === element && event.button === 0) {
                    eventFor(widget, sequence, event);
                }
            });
        }
    }
    if (kind === "Toplevel") {
        element.hidden = false;
        element.addEventListener("cancel", (event) => {
            event.preventDefault();
            post({ kind: "close", id });
        });
        element.showModal();
    }
}

function setOptions(widget, changed) {
    Object.assign(widget.options, changed);
    const options = widget.options;
    const { element, input, kind } = widget;
    const target = input || element;
    const style = styles.get(options.style || `T${kind}`) || {};
    const font = options.font || style.font;
    if (font) target.style.font = fontStyle(font).css;
    const background = options.state === "readonly" && kind === "Entry" && options.readonlybackground ||
        options.bg || options.background || (kind === "Frame" || kind === "Label" ? style.background : "");
    target.style.backgroundColor = background || "";
    target.style.color = options.foreground || options.fg || (kind === "Button" ? "" : style.foreground) || "";
    if (options.wraplength && kind === "Label") element.style.maxWidth = length(options.wraplength);
    if (options.justify) target.style.textAlign = options.justify;
    if (options.padding != null) {
        const [horizontal, vertical] = pair(options.padding);
        target.style.padding = `${vertical}px ${horizontal}px`;
    }
    if (options.highlightthickness !== undefined) {
        const width = options.highlightthickness;
        target.style.border = width ? `${width}px solid ${options.highlightbackground || "#d1d8cf"}` : "0";
    }
    if (options.cursor !== undefined) {
        target.style.cursor = ({ hand2: "pointer", xterm: "text", fleur: "move", crosshair: "crosshair" })[options.cursor] || "";
    }
    if (options.takefocus === false) target.tabIndex = -1;
    if (input) {
        input.disabled = options.state === "disabled";
        if (kind === "Entry") {
            input.readOnly = options.state === "readonly";
            if (widget.parent?.kind === "Canvas") {
                input.setAttribute("aria-label", widget.accessibleName || "Rätselfeld");
                if (options.validate === "key" && options.justify === "center" && options.width === 3) input.inputMode = "numeric";
                else input.removeAttribute("inputmode");
            }
        }
    }
    if (kind === "Button") {
        input.classList.toggle("accent", ["Accent.TButton", "NotesOn.TButton", "DifficultyOn.TButton"].includes(options.style));
        if ("text" in changed || "image" in changed) {
            input.replaceChildren();
            if (options.image) {
                const { width, height, rects } = options.image;
                const icon = document.createElement("canvas");
                icon.width = width; icon.height = height;
                icon.setAttribute("aria-hidden", "true");
                const context = icon.getContext("2d");
                for (const [color, x1, y1, x2, y2] of rects) {
                    context.fillStyle = color;
                    context.fillRect(x1, y1, x2 - x1, y2 - y1);
                }
                input.append(icon);
            }
            input.append(document.createTextNode(options.text || ""));
        }
        if (options.text === "×") input.setAttribute("aria-label", "Schließen");
        if (options.style === "DifficultyOn.TButton" || ["Mittel", "Schwer"].includes(options.text)) {
            input.setAttribute("aria-pressed", options.style === "DifficultyOn.TButton");
        }
        if ((options.text || "").startsWith("Notizen")) input.setAttribute("aria-pressed", options.style === "NotesOn.TButton");
    }
    if (kind === "Label" && "text" in changed) element.textContent = options.text || "";
    if (kind === "Checkbutton" && "text" in changed) widget.label.textContent = options.text;
    if (kind === "Combobox" && "values" in changed) {
        const active = input.value;
        input.replaceChildren();
        for (const value of options.values) input.add(new Option(value, value));
        if ([...input.options].some((option) => option.value === active)) input.value = active;
    }
    if (kind === "Scale") {
        input.min = options.from_ ?? 0;
        input.max = options.to ?? 100;
        input.setAttribute("aria-label", "Lautstärke");
    }
    if (kind === "Canvas") queueDraw(widget);
}

function pack(widget, options) {
    const { element, parent } = widget;
    const [left, right] = pair(options.padx);
    const [top, bottom] = pair(options.pady);
    const row = options.side === "left" || options.side === "right";
    if (!widget.packed || options.before) {
        const before = widgets.get(options.before)?.element;
        if (before?.parentElement === parent.element) parent.element.insertBefore(element, before);
        else if (options.side === "bottom") parent.element.append(element);
    }
    widget.packed = true;
    element.hidden = false;
    if (row && widget.kind !== "Scrollbar") parent.element.classList.add("tk-row");
    Object.assign(element.style, {
        position: "relative",
        margin: `${top}px ${right}px ${bottom}px ${left}px`,
        flexGrow: options.expand ? 1 : "",
        flexShrink: options.expand ? 1 : 0,
        flexBasis: options.expand && (row ? options.fill?.includes("x") : options.fill?.includes("y") || options.fill === "both") ? "0" : "",
        alignSelf: row ? (options.fill === "y" || options.fill === "both" ? "stretch" : "center") :
            (options.fill === "x" || options.fill === "both" ? "stretch" : options.anchor?.includes("w") ? "flex-start" :
                options.anchor?.includes("e") ? "flex-end" : "center"),
    });
    if (widget.kind === "Canvas" && !options.expand && widget.options.height) element.style.height = length(widget.options.height);
    if (options.side === "right") element.style.marginLeft = "auto";
}

function anchorOffset(anchor = "center") {
    return [
        anchor.includes("w") ? 0 : ["e", "ne", "se"].includes(anchor) ? 1 : .5,
        ["n", "ne", "nw"].includes(anchor) ? 0 : anchor.includes("s") ? 1 : .5
    ];
}

function place(widget, options) {
    const [x, y] = anchorOffset(options.anchor);
    const { element } = widget;
    Object.assign(element.style, {
        position: "absolute",
        left: `calc(${100 * (options.relx || 0)}% + ${options.x || 0}px)`,
        top: `calc(${100 * (options.rely || 0)}% + ${options.y || 0}px)`,
        transform: `translate(${-100 * x}%, ${-100 * y}%)`,
        width: options.relwidth != null ? `${options.relwidth * 100}%` : length(options.width ?? ""),
        height: options.relheight != null ? `${options.relheight * 100}%` : length(options.height ?? "")
    });
    element.hidden = false;
}

function setupCanvas(widget) {
    const { element } = widget;
    const content = widget.content = document.createElement("div");
    const surface = widget.surface = document.createElement("canvas");
    const windows = widget.windows = document.createElement("div");
    surface.setAttribute("aria-hidden", "true");
    content.className = "tk-canvas-content";
    surface.className = "tk-canvas-surface";
    windows.className = "tk-canvas-windows";
    content.append(surface, windows);
    element.append(content);
    widget.items = [];
    widget.windowIds = new Set();
    const pointer = (sequence, event) => {
        if (event.target.closest("[data-widget]") !== element) return;
        if (widget.bindings.has(sequence)) eventFor(widget, sequence, event);
    };
    element.addEventListener("pointerdown", (event) => {
        if (event.target.closest("[data-widget]") !== element) return;
        if (event.button === 0 && widget.bindings.has("<B1-Motion>")) element.setPointerCapture(event.pointerId);
        if (event.button === 0) pointer("<Button-1>", event);
        if (event.button === 2) pointer("<Button-3>", event);
    });
    element.addEventListener("dblclick", (event) => pointer("<Double-Button-1>", event));
    element.addEventListener("pointerup", (event) => pointer("<ButtonRelease-1>", event));
    element.addEventListener("pointercancel", (event) => pointer("<ButtonRelease-1>", event));
    element.addEventListener("pointermove", (event) => {
        if (event.buttons & 1) pointer("<B1-Motion>", event);
        else pointer("<Motion>", event);
    });
    element.addEventListener("pointerleave", (event) => pointer("<Leave>", event));
    element.addEventListener("contextmenu", (event) => {
        if (widget.bindings.has("<Button-3>")) event.preventDefault();
    });
    element.addEventListener("scroll", () => {
        post({ kind: "event", id: widget.id, sequence: "<Scroll>", scroll: scrollPosition(widget) });
        queueDraw(widget);
    }, { passive: true });
    element.addEventListener("focus", () => eventFor(widget, "<FocusIn>"));
    element.addEventListener("blur", () => eventFor(widget, "<FocusOut>"));
}

function selection(widget) {
    return [widget.input?.selectionStart ?? 0, widget.input?.selectionEnd ?? 0];
}

function scrollPosition(widget) {
    return [widget.element.scrollLeft, widget.element.scrollTop];
}

function geometry(widget) {
    const { element, parent } = widget;
    const box = element.getBoundingClientRect();
    const base = parent?.element.getBoundingClientRect();
    return {
        width: element.clientWidth, height: element.clientHeight,
        x: base ? box.left - base.left - parent.element.clientLeft : box.left,
        y: base ? box.top - base.top - parent.element.clientTop : box.top,
    };
}

function eventFor(widget, sequence, event, kind = "event") {
    const payload = { kind, id: widget.id, sequence, selection: selection(widget) };
    if (widget.kind === "Canvas") payload.scroll = scrollPosition(widget);
    if (event instanceof PointerEvent || event instanceof MouseEvent) {
        const box = widget.element.getBoundingClientRect();
        payload.x = event.clientX - box.left - widget.element.clientLeft;
        payload.y = event.clientY - box.top - widget.element.clientTop;
        payload.x_root = event.clientX;
        payload.y_root = event.clientY;
    }
    if (event instanceof KeyboardEvent) {
        payload.keysym = event.key;
        payload.char = event.key.length === 1 ? event.key : "";
    }
    post(payload);
}

const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
        const widget = widgets.get(Number(entry.target.dataset.widget));
        if (!widget) continue;
        const area = geometry(widget);
        if (widget.kind === "Canvas") queueDraw(widget);
        post({ kind: "event", id: widget.id, sequence: "<Configure>", geometry: area,
            width: area.width, height: area.height });
    }
});

function queueDraw(widget) {
    pendingDraw.add(widget);
    if (!frame) frame = requestAnimationFrame(() => {
        frame = 0;
        for (const next of pendingDraw) if (widgets.has(next.id)) paint(next);
        pendingDraw.clear();
    });
}

function registerImage(id, imageData) {
    const image = new Image();
    const record = { image, users: new Set() };
    image.onload = () => {
        for (const user of record.users) queueDraw(user);
        record.users.clear();
    };
    image.src = "data:image/png;base64," + imageData;
    images.set(id, record);
}

function imageFor(descriptor, widget) {
    const record = images.get(descriptor?.source);
    if (!record) return null;
    if (!record.image.complete) record.users.add(widget);
    return record.image.complete && record.image.naturalWidth ? record.image : null;
}

function textLines(context, text, width) {
    return String(text).split("\n").flatMap((paragraph) => {
        if (!width) return [paragraph];
        const lines = [];
        let line = "";
        for (const word of paragraph.split(" ")) {
            const candidate = line ? line + " " + word : word;
            if (line && context.measureText(candidate).width > width) {
                lines.push(line);
                line = word;
            } else line = candidate;
        }
        lines.push(line);
        return lines;
    });
}

function drawText(context, x, y, options) {
    const font = fontStyle(options.font);
    context.font = font.css;
    const lines = textLines(context, options.text ?? "", options.width);
    const widths = lines.map((line) => context.measureText(line).width);
    const widest = Math.max(...widths);
    const lineHeight = font.pixels * 1.19;
    const [ax, ay] = anchorOffset(options.anchor);
    const left = x - widest * ax;
    const top = y - lines.length * lineHeight * ay;
    context.textBaseline = "middle";
    context.fillStyle = options.fill || "#000";
    const align = options.justify === "right" ? 1 : options.justify === "left" ? 0 : .5;
    lines.forEach((line, i) => context.fillText(line, left + (widest - widths[i]) * align, top + (i + .5) * lineHeight));
}

function drawShape(context, kind, points, options) {
    const [x, y, x2, y2] = points;
    context.beginPath();
    if (kind === "rectangle") context.rect(x, y, x2 - x, y2 - y);
    if (kind === "oval" || kind === "arc") {
        const start = kind === "arc" ? -(options.start || 0) * Math.PI / 180 : 0;
        const end = kind === "arc" ? start - (options.extent ?? 90) * Math.PI / 180 : 2 * Math.PI;
        const centerX = (x + x2) / 2, centerY = (y + y2) / 2;
        if (kind === "arc" && (options.style || "pieslice") === "pieslice") context.moveTo(centerX, centerY);
        context.ellipse(centerX, centerY, Math.abs(x2 - x) / 2, Math.abs(y2 - y) / 2, 0, start, end, kind === "arc" && end < start);
        if (kind === "arc" && options.style !== "arc") context.closePath();
    }
    if (kind === "line" || kind === "polygon") {
        const closed = kind === "polygon";
        const n = points.length;
        if (options.smooth && n >= 6) {
            context.moveTo(closed ? (points[n - 2] + x) / 2 : x, closed ? (points[n - 1] + y) / 2 : y);
            for (let i = closed ? 0 : 2; i < n - (closed ? 0 : 2); i += 2) {
                const next = (i + 2) % n;
                context.quadraticCurveTo(points[i], points[i + 1], (points[i] + points[next]) / 2, (points[i + 1] + points[next + 1]) / 2);
            }
            if (!closed) context.lineTo(points[n - 2], points[n - 1]);
        } else {
            context.moveTo(x, y);
            for (let i = 2; i < n; i += 2) context.lineTo(points[i], points[i + 1]);
        }
        if (closed) context.closePath();
    }
    const fill = kind === "line" || options.style === "arc" ? "" : options.fill;
    const stroke = kind === "line" ? options.fill ?? "#000" : options.outline ?? (kind === "polygon" ? "" : "#000");
    if (fill) {
        context.fillStyle = fill;
        if (options.stipple) context.globalAlpha = options.stipple === "gray25" ? .25 : .5;
        context.fill();
        context.globalAlpha = 1;
    }
    if (stroke && options.width !== 0) {
        context.strokeStyle = stroke;
        context.lineWidth = options.width || 1;
        context.lineCap = options.capstyle === "round" ? "round" : options.capstyle === "projecting" ? "square" : "butt";
        context.lineJoin = options.joinstyle || "round";
        context.setLineDash(Array.isArray(options.dash) ? options.dash : []);
        context.lineDashOffset = options.dashoffset || 0;
        context.stroke();
    }
    if (kind === "line" && options.arrow) {
        const [inset, size, spread] = options.arrowshape || [8, 10, 4];
        const arrow = (i, j) => {
            const angle = Math.atan2(points[i + 1] - points[j + 1], points[i] - points[j]);
            context.save();
            context.translate(points[i], points[i + 1]);
            context.rotate(angle);
            context.beginPath();
            context.moveTo(0, 0); context.lineTo(-size, spread);
            context.lineTo(-inset, 0); context.lineTo(-size, -spread);
            context.closePath();
            context.fillStyle = stroke || "#000";
            context.fill();
            context.restore();
        };
        if (["first", "both"].includes(options.arrow)) arrow(0, 2);
        if (["last", "both"].includes(options.arrow)) arrow(points.length - 2, points.length - 4);
    }
}

function setWindow(child, widget, item, width, height, left, top) {
    const hidden = item.state === "hidden";
    const previous = child.canvasGeometry;
    if (child.element.parentElement !== widget.windows) widget.windows.append(child.element);
    Object.assign(child.element.style, {
        width: length(width), height: length(height), left: length(left), top: length(top),
        position: "absolute", margin: 0
    });
    child.element.hidden = hidden;
    if (!hidden && (!previous || previous.width !== width || previous.height !== height || previous.left !== left || previous.top !== top)) {
        child.canvasGeometry = { width, height, left, top };
        post({ kind: "event", id: child.id, sequence: "<Configure>", width, height,
            geometry: { width, height, x: left, y: top } });
    }
}

function paint(widget) {
    const { element, content, surface, windows, options } = widget;
    const width = Math.max(1, element.clientWidth), height = Math.max(1, element.clientHeight);
    const [left, top] = scrollPosition(widget);
    const region = options.scrollregion || [];
    const extent = Math.max(width, region[2] || width);
    const depth = Math.max(height, region[3] || height);
    content.style.width = length(extent);
    content.style.height = length(depth);
    windows.style.width = length(extent);
    windows.style.height = length(depth);
    const ratio = Math.min(window.devicePixelRatio || 1, 3);
    if (surface.width !== Math.ceil(width * ratio)) surface.width = Math.ceil(width * ratio);
    if (surface.height !== Math.ceil(height * ratio)) surface.height = Math.ceil(height * ratio);
    Object.assign(surface.style, { width: length(width), height: length(height), transform: `translate(${left}px,${top}px)` });
    const context = surface.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, -left * ratio, -top * ratio);
    context.clearRect(left, top, width, height);
    const newWindows = new Set();
    for (const [, kind, points, item] of widget.items) {
        const [x, y] = points;
        if (kind === "window") {
            const child = widgets.get(item.window);
            if (!child) continue;
            const [ax, ay] = anchorOffset(item.anchor);
            const w = item.width || child.element.offsetWidth || 40;
            const h = item.height || child.element.offsetHeight || 24;
            setWindow(child, widget, item, w, h, x - ax * w, y - ay * h);
            newWindows.add(child.id);
            continue;
        }
        if (item.state === "hidden") continue;
        if (kind === "text") drawText(context, x, y, item);
        else if (kind === "image") {
            const image = imageFor(item.image, widget);
            if (!image) continue;
            const [ax, ay] = anchorOffset(item.anchor);
            context.drawImage(image, x - item.image.width * ax, y - item.image.height * ay, item.image.width, item.image.height);
        } else drawShape(context, kind, points, item);
    }
    for (const id of widget.windowIds) {
        if (!newWindows.has(id) && widgets.has(id)) widgets.get(id).element.hidden = true;
    }
    widget.windowIds = newWindows;
    if (widget.focusAfterPaint && !widget.focusAfterPaint.element.hidden) {
        (widget.focusAfterPaint.input || widget.focusAfterPaint.element).focus({ preventScroll: true });
        widget.focusAfterPaint = null;
    }
}

function showNextDialog() {
    if (currentDialog || !dialogs.length) return;
    const [title, message, confirm] = currentDialog = dialogs.shift();
    dialog.returnValue = "";
    document.querySelector("#message-title").textContent = title;
    document.querySelector("#message-text").textContent = message;
    document.querySelector("#message-cancel").hidden = !confirm;
    document.querySelector("#message-ok").textContent = confirm ? "Zurücksetzen" : "OK";
    dialog.showModal();
}

dialog.addEventListener("close", () => {
    const confirmation = currentDialog?.[2];
    if (confirmation) {
        const [id, token] = confirmation;
        post({ kind: "confirm", id, token, confirmed: dialog.returnValue === "ok" });
    }
    currentDialog = null;
    showNextDialog();
});

function playSound(volume) {
    if (!audio || audio.state !== "running" || !volume) return;
    let time = audio.currentTime + .01;
    for (const [frequency, duration] of [[523.25, .09], [659.25, .09], [783.99, .17]]) {
        const oscillator = audio.createOscillator();
        const gain = audio.createGain();
        oscillator.frequency.value = frequency;
        oscillator.connect(gain).connect(audio.destination);
        const amplitude = .24 * volume / 100;
        gain.gain.setValueAtTime(0, time);
        gain.gain.linearRampToValueAtTime(amplitude, time + .008);
        gain.gain.setValueAtTime(amplitude, time + duration - .035);
        gain.gain.linearRampToValueAtTime(0, time + duration);
        oscillator.start(time);
        oscillator.stop(time + duration);
        time += duration;
    }
}

document.addEventListener("pointerdown", (event) => {
    for (const widget of widgets.values()) {
        if (widget.kind === "Menu" && !widget.element.hidden && !widget.element.contains(event.target)) {
            post({ kind: "close", id: widget.id });
        }
    }
    if (!audio && window.AudioContext) audio = new AudioContext();
    if (audio?.state === "suspended") audio.resume().catch(() => {});
});

function role(widget, name) {
    widget.element.classList.add("tk-role-" + name);
    if (name === "board") {
        widget.element.tabIndex = 0;
        widget.element.setAttribute("aria-label", "Rätselfläche");
        widget.element.dataset.drag = "false";
    }
    if (name === "title") {
        widget.element.setAttribute("role", "heading");
        widget.element.setAttribute("aria-level", "1");
    }
    if (name === "sidebar") widget.element.setAttribute("aria-label", "Rätsel auswählen");
    if (name === "status") widget.element.setAttribute("role", "status");
    if (name === "main") widget.element.setAttribute("role", "main");
    if (name === "success" || name === "error") {
        widget.element.setAttribute("role", "group");
        widget.element.setAttribute("aria-label", name === "success" ? "Richtig gelöst" : "Rätsel prüfen");
    }
}

function applyOperations(operations) {
    for (const [operation, id, ...args] of operations) {
        const widget = widgets.get(id);
        switch (operation) {
        case "create": makeWidget(id, ...args); break;
        case "style": styles.set(id, args[0]); break;
        case "options": setOptions(widget, args[0]); break;
        case "pack": pack(widget, args[0]); break;
        case "place": place(widget, args[0]); break;
        case "hide": widget.element.hidden = true; break;
        case "propagate":
            if (!args[0] && widget.options.width) widget.element.style.width = length(widget.options.width);
            break;
        case "role": role(widget, args[0]); break;
        case "label":
            widget.accessibleName = args[0];
            widget.input.setAttribute("aria-label", args[0]);
            break;
        case "value": {
            const value = String(args[0]);
            const revision = args[1];
            if (revision != null && revision < (widget.inputRevision || 0)) break;
            if (widget.kind === "Checkbutton") widget.input.checked = Boolean(args[0]);
            else if (widget.input.value !== value) widget.input.value = value;
            break;
        }
        case "draw": widget.items = args[0]; queueDraw(widget); break;
        case "image-source": registerImage(id, args[0]); break;
        case "destroy":
            observer.unobserve(widget.element);
            widget.element.remove();
            widgets.delete(id);
            break;
        case "bind": {
            const [sequence, active] = args;
            if (active) widget.bindings.add(sequence);
            else widget.bindings.delete(sequence);
            if (sequence === "<Configure>" && widget.parent?.kind !== "Canvas") {
                if (active) observer.observe(widget.element);
                else observer.unobserve(widget.element);
            }
            if (sequence === "<B1-Motion>" && widget.kind === "Canvas") widget.element.dataset.drag = String(active);
            break;
        }
        case "focus":
            if (widget.element.hidden && widget.parent?.kind === "Canvas") {
                widget.parent.focusAfterPaint = widget;
            } else (widget.input || widget.element).focus({ preventScroll: true });
            break;
        case "selection":
            if (widget.input?.type === "text") widget.input.setSelectionRange(...args);
            break;
        case "scroll": {
            const [axis, fraction] = args;
            const size = (widget.options.scrollregion || [0, 0, 1, 1])[axis + 2];
            if (axis === 0) widget.element.scrollLeft = fraction * size;
            else widget.element.scrollTop = fraction * size;
            queueDraw(widget);
            break;
        }
        case "title":
            if (widget.kind === "Root") document.title = args[0];
            else widget.element.setAttribute("aria-label", args[0]);
            break;
        case "raise": widget.element.style.zIndex = "3"; break;
        case "reveal":
            if (matchMedia("(max-width: 760px)").matches) widget.element.scrollIntoView({ block: "start" });
            break;
        case "progress": widget.element.classList.toggle("running", args[0]); break;
        case "dialog": dialogs.push([id, ...args]); showNextDialog(); break;
        case "download": {
            const url = URL.createObjectURL(new Blob([args[0]], { type: "application/json" }));
            const link = document.createElement("a");
            link.href = url;
            link.download = id;
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            break;
        }
        case "menu_item": {
            const button = document.createElement("button");
            button.textContent = args[1];
            button.addEventListener("click", () => post({ kind: "menu", id, index: args[0] }));
            widget.element.append(button);
            break;
        }
        case "menu_open":
            widget.element.hidden = false;
            widget.element.style.left = length(Math.max(0, Math.min(innerWidth - widget.element.offsetWidth, args[0])));
            widget.element.style.top = length(Math.max(0, Math.min(innerHeight - widget.element.offsetHeight, args[1])));
            widget.element.querySelector("button")?.focus();
            break;
        }
    }
}

function activeWidget(event) {
    return widgets.get(Number(event.target.closest?.("[data-widget]")?.dataset.widget)) ||
        [...widgets.values()].find((widget) => widget.kind === "Root");
}

document.addEventListener("keydown", (event) => {
    if (document.querySelector("dialog[open]")) return;
    const widget = activeWidget(event);
    if (!widget) return;
    const root = [...widgets.values()].find((item) => item.kind === "Root");
    let sequence;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") sequence = "<Control-z>";
    else if (!event.ctrlKey && !event.metaKey && !event.altKey) {
        if (event.key === "Escape") sequence = "<Escape>";
        else if (event.key === "Enter") sequence = "<Return>";
        else if (event.key.startsWith("Arrow")) sequence = `<${event.key.slice(5)}>`;
        else if (event.key.length === 1) sequence = `<KeyPress-${event.key}>`;
    }
    if (!sequence || !widget.bindings.has(sequence) && !root?.bindings.has(sequence)) return;
    const nativeEntry = widget.kind === "Entry" || widget.kind === "Combobox";
    const useNativeKey = nativeEntry && !widget.bindings.has(sequence) && (event.key === "n" || event.key === "N");
    if (!useNativeKey) event.preventDefault();
    eventFor(widget, sequence, event, "key");
});

document.addEventListener("keyup", (event) => {
    const widget = activeWidget(event);
    if (widget?.bindings.has("<KeyRelease>")) eventFor(widget, "<KeyRelease>", event);
});

function startupFailure(message) {
    startup.hidden = false;
    startup.querySelector("p").textContent = message;
    const retry = document.createElement("button");
    retry.textContent = "Erneut laden";
    retry.addEventListener("click", () => location.reload());
    if (!startup.querySelector("button")) startup.append(retry);
}

function start() {
    if (location.protocol === "file:") {
        startup.querySelector("p").textContent = "Starte einen lokalen Webserver im Projektordner und öffne dessen Adresse im Browser. Die Anleitung steht in README.md.";
        return;
    }
    let preferences = "{}";
    try { preferences = localStorage.getItem(preferencesKey) || "{}"; } catch { /* optional storage */ }
    try { engine = new Worker("browser/worker.js"); }
    catch {
        startupFailure("Der Browser konnte die Rätsel-Engine nicht starten.");
        return;
    }
    engine.onerror = () => startupFailure("Der Browser konnte die Rätsel-Engine nicht laden.");
    engine.onmessage = ({ data }) => {
        if (data.type === "operations") applyOperations(JSON.parse(data.json));
        if (data.type === "ready") startup.hidden = true;
        if (data.type === "startup-error") startupFailure("Das Rätselatelier konnte nicht geladen werden. Details stehen in der Browserkonsole.");
        if (data.type === "runtime-error") {
            dialogs.push(["Rätselatelier", "Bei der Bedienung ist ein Fehler aufgetreten. Details stehen in der Browserkonsole.", null]);
            showNextDialog();
        }
        if (data.type === "sound") playSound(data.volume);
        if (data.type === "preferences") {
            try { localStorage.setItem(preferencesKey, data.json); } catch { /* private browsing restrictions */ }
        }
    };
    post({ kind: "start", preferences });
}
start();
