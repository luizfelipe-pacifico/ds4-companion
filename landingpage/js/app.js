// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Contribuidores do DS4 Companion
//
// Interações da landing page: prévia da janela, fader em dB, grafo do áudio em paralelo.
// Nada é enviado para fora da página.

"use strict";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// Mesmos limites do SECURITY.md: livre ≤ −6 dB, alto até 0 dB, acima exige confirmação.
const DB_MIN = -30;
const DB_MAX = 6;
const DB_HIGH = -6;
const DB_LIMIT = 0;

const state = {
    db: -9,
    maxDb: DB_LIMIT,
    conn: "usb",
    mirror: true,
};

const fmtDb = (db) => (db < 0 ? "−" + Math.abs(db) : db > 0 ? "+" + db : "0");

function band(db) {
    if (db > DB_LIMIT) return "over";
    if (db > DB_HIGH) return "high";
    return "free";
}

const BAND_TEXT = { free: "Livre", high: "Alto", over: "Acima do limite" };

const WARN_ICON =
    '<svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3.5 17.5 16h-15L10 3.5ZM10 8.5v3.5M10 14v.01"/></svg>';

// ---------- topo ----------

const topbar = $(".topbar");
const onScroll = () => topbar.classList.toggle("scrolled", window.scrollY > 24);
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// ---------- abas da janela (roving tabindex) ----------

const win = $("#janela");

function rovingGroup(buttons, attr, onSelect) {
    buttons.forEach((btn, i) => {
        btn.addEventListener("click", () => select(i, false));
        btn.addEventListener("keydown", (e) => {
            const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
            if (e.key in keys) {
                e.preventDefault();
                select((i + keys[e.key] + buttons.length) % buttons.length, true);
            } else if (e.key === "Home") {
                e.preventDefault();
                select(0, true);
            } else if (e.key === "End") {
                e.preventDefault();
                select(buttons.length - 1, true);
            }
        });
    });

    function select(i, focus) {
        buttons.forEach((b, j) => {
            b.setAttribute(attr, String(i === j));
            b.tabIndex = i === j ? 0 : -1;
        });
        if (focus) buttons[i].focus();
        onSelect(buttons[i]);
    }
}

rovingGroup($$(".win-sidebar [role=tab]"), "aria-selected", (btn) => {
    $$(".win-page", win).forEach((p) => {
        p.hidden = p.id !== btn.getAttribute("aria-controls");
    });
    win.dataset.page = btn.dataset.page;
});

// ---------- conexão e espelhamento ----------

const graph = $("#grafo");

function renderConn() {
    win.dataset.conn = state.conn;
    const bt = state.conn === "bt";
    $("[data-conn-text]").textContent = bt ? "Conectado por Bluetooth" : "Conectado por cabo USB";
    $("[data-mirror-text]").textContent = bt
        ? "indisponível por Bluetooth"
        : state.mirror
          ? "ativo"
          : "desligado";

    const linked = !bt && state.mirror;
    graph.classList.toggle("unlinked", !linked);
    $("[data-ds4-sub]").textContent = bt ? "sem áudio por Bluetooth" : state.mirror ? "alto-falante" : "espelhamento desligado";
    $(".link.extra").style.opacity = linked ? "" : "0";
}

rovingGroup($$("[data-set-conn]"), "aria-checked", (btn) => {
    state.conn = btn.dataset.setConn;
    renderConn();
});

const mirrorSwitch = $("#mirror-switch");
mirrorSwitch.addEventListener("click", () => {
    state.mirror = !state.mirror;
    mirrorSwitch.setAttribute("aria-checked", String(state.mirror));
    $(".audio-usb").classList.toggle("muted", !state.mirror);
    renderConn();
});

// ---------- fader em dB ----------

const faders = $$("[data-fader]");
const confirmBox = $("[data-limit-confirm]");

const dbToPct = (db) => ((db - DB_MIN) / (DB_MAX - DB_MIN)) * 100;
const pctToDb = (pct) => Math.round(DB_MIN + (pct / 100) * (DB_MAX - DB_MIN));

function setDb(db, { askAbove = true } = {}) {
    db = Math.max(DB_MIN, Math.min(DB_MAX, db));
    // O teto só abre com confirmação (max_db); até lá o fader para em 0 dB.
    if (db > state.maxDb) {
        if (askAbove && confirmBox.hidden) confirmBox.hidden = false;
        db = state.maxDb;
    }
    if (db === state.db) return;
    state.db = db;
    render();
}

function render() {
    const b = band(state.db);
    const text = fmtDb(state.db) + " dB";
    faders.forEach((f) => {
        f.style.setProperty("--pos", dbToPct(state.db) + "%");
        f.dataset.band = b;
        f.setAttribute("aria-valuenow", String(state.db));
        f.setAttribute("aria-valuetext", text + ", " + BAND_TEXT[b].toLowerCase());
    });
    $$("[data-db-out]").forEach((o) => (o.textContent = text));
    $("[data-db-big]").textContent = fmtDb(state.db);

    const bandEl = $("[data-band-text]");
    bandEl.dataset.band = b;
    bandEl.innerHTML =
        (b === "free" ? "" : WARN_ICON) +
        BAND_TEXT[b] +
        (state.db === state.maxDb && state.maxDb === DB_LIMIT ? " · no teto de 0 dB" : "");

    $$(".bands li").forEach((li) => li.classList.toggle("active", li.classList.contains("band-" + b)));
}

faders.forEach((f) => {
    const thumb = $(".fader-thumb", f);
    let grabOffset = 0;

    const pctAt = (clientX) => {
        const r = f.getBoundingClientRect();
        return ((clientX - grabOffset - r.left) / r.width) * 100;
    };

    f.addEventListener("pointerdown", (e) => {
        if (e.button !== 0) return;
        f.setPointerCapture(e.pointerId);
        f.classList.add("dragging");
        // Respeita onde o dedo pegou o botão; no trilho, o botão vem até o dedo.
        const t = thumb.getBoundingClientRect();
        const onThumb = Math.abs(e.clientX - (t.left + t.width / 2)) <= t.width;
        grabOffset = onThumb ? e.clientX - (t.left + t.width / 2) : 0;
        setDb(pctToDb(pctAt(e.clientX)));
        f.focus({ preventScroll: true });
    });

    f.addEventListener("pointermove", (e) => {
        if (!f.hasPointerCapture(e.pointerId)) return;
        setDb(pctToDb(pctAt(e.clientX)));
    });

    const end = (e) => {
        if (f.hasPointerCapture(e.pointerId)) f.releasePointerCapture(e.pointerId);
        f.classList.remove("dragging");
    };
    f.addEventListener("pointerup", end);
    f.addEventListener("pointercancel", end);

    f.addEventListener("keydown", (e) => {
        const steps = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 6, PageDown: -6 };
        if (e.key in steps) {
            e.preventDefault();
            setDb(state.db + steps[e.key]);
        } else if (e.key === "Home") {
            e.preventDefault();
            setDb(DB_MIN);
        } else if (e.key === "End") {
            e.preventDefault();
            setDb(DB_MAX);
        }
    });
});

$("[data-limit-keep]").addEventListener("click", () => {
    confirmBox.hidden = true;
    state.maxDb = DB_LIMIT;
    setDb(Math.min(state.db, DB_LIMIT), { askAbove: false });
    $("#big-fader").focus();
});

$("[data-limit-pass]").addEventListener("click", () => {
    confirmBox.hidden = true;
    state.maxDb = DB_MAX;
    setDb(state.db + 1, { askAbove: false });
    $("#big-fader").focus();
});

render();

// ---------- apito de teste (toca no computador, no volume escolhido) ----------

let audioCtx;
$("[data-beep]").addEventListener("click", () => {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const t = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    // Ganho em dB relativo a um nível baixo, para nunca assustar ninguém.
    const peak = 0.2 * Math.pow(10, state.db / 20);
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(peak, t + 0.01);
    gain.gain.setValueAtTime(peak, t + 0.3);
    gain.gain.linearRampToValueAtTime(0, t + 0.36);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + 0.4);
    pulseStrip();
});

function pulseStrip() {
    const strip = $(".light-strip", win);
    if (reduceMotion.matches) return;
    strip.animate([{ opacity: 1 }, { opacity: 0.25 }, { opacity: 1 }], { duration: 400, easing: "ease-out" });
}

// ---------- vibração: teste curto, de verdade quando há controle no navegador ----------

$$("[data-motor]").forEach((input) => {
    const out = input.nextElementSibling;
    const update = () => {
        out.textContent = input.value + "%";
        input.style.setProperty("--p", input.value + "%");
    };
    input.addEventListener("input", update);
    update();
});

const rumbleBtn = $("[data-rumble]");
const rumbleNote = $("[data-rumble-note]");
const RUMBLE_MS = 800; // abaixo do máximo de 2 s do SECURITY.md

rumbleBtn.addEventListener("click", async () => {
    rumbleBtn.disabled = true;
    const strong = $("#motor-forte").valueAsNumber / 100;
    const weak = $("#motor-fraco").valueAsNumber / 100;
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    const pad = pads.find((p) => p.vibrationActuator);

    if (pad) {
        try {
            await pad.vibrationActuator.playEffect("dual-rumble", {
                duration: RUMBLE_MS,
                strongMagnitude: strong,
                weakMagnitude: weak,
            });
            rumbleNote.textContent = "Vibrou no controle ligado ao navegador.";
        } catch {
            rumbleNote.textContent = "O navegador não deixou vibrar o controle. Tente apertar um botão dele antes.";
        }
    } else {
        if (navigator.vibrate) navigator.vibrate(Math.round(RUMBLE_MS * Math.max(strong, weak)));
        if (!reduceMotion.matches) {
            const amp = 1 + 2 * Math.max(strong, weak);
            win.animate(
                [
                    { transform: "translateX(0)" },
                    { transform: `translateX(${amp}px)` },
                    { transform: `translateX(-${amp}px)` },
                    { transform: "translateX(0)" },
                ],
                { duration: 90, iterations: 4 },
            );
        }
        rumbleNote.textContent = "Nenhum controle no navegador. Ligue o DualShock 4 e aperte um botão dele para testar de verdade.";
    }
    // Intervalo mínimo entre testes.
    setTimeout(() => (rumbleBtn.disabled = false), 2000);
});

window.addEventListener("gamepadconnected", () => {
    rumbleNote.textContent = "Controle detectado pelo navegador. O teste vibra de verdade.";
});

// ---------- cor da barra de luz (é dado do hardware, por isso pinta a foto) ----------

rovingGroup($$("[data-led]"), "aria-checked", (btn) => {
    const root = document.documentElement.style;
    root.setProperty("--led", btn.dataset.led);
    const hue = btn.dataset.hue;
    root.setProperty("--led-hue", hue === "white" ? "0deg" : hue + "deg");
    root.setProperty("--led-sat", hue === "white" ? "0" : "1");
    pulseStrip();
});

// ---------- grafo: trocar a saída não mexe no link do controle ----------

const OUTS = { hdmi: "TV (HDMI)", fone: "Fone de ouvido", notebook: "Notebook" };

rovingGroup($$(".graph-controls [data-out]"), "aria-checked", (btn) => {
    const out = btn.dataset.out;
    $("[data-out-name]").textContent = OUTS[out];
    graph.dataset.out = out;
    graph.classList.remove("switching");
    void graph.offsetWidth; // reinicia a animação
    graph.classList.add("switching");
    $("[data-graph-note]").textContent =
        "Som principal agora em " + OUTS[out].toLowerCase().replace("tv", "TV") + ". O link do controle ficou intacto.";
});

renderConn();

// ---------- copiar comando ----------

$$("[data-copy]").forEach((btn) => {
    const label = $("span", btn);
    btn.addEventListener("click", async () => {
        const text = document.getElementById(btn.dataset.copy).textContent.trim();
        try {
            await navigator.clipboard.writeText(text);
            label.textContent = "Copiado";
        } catch {
            const range = document.createRange();
            range.selectNodeContents(document.getElementById(btn.dataset.copy));
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            label.textContent = "Selecionado";
        }
        setTimeout(() => (label.textContent = "Copiar"), 1800);
    });
});
