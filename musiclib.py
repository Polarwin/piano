#!/usr/bin/env python3
"""musiclib — shared score engine for prompt-generated piano music.

Takes a score dict (see build_score for the schema), and produces:
  - an engraved grand-staff PDF (ReportLab, no notation software needed)
  - a standard MIDI file
  - a rendered WAV (pure-stdlib soft-piano synthesis)

Used by compose.py; can also be driven standalone from a JSON score file:

    python3 musiclib.py score.json outname
"""
from array import array
import json, math, os, re, struct, subprocess, sys, wave

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

OUT = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Notes and chords
# --------------------------------------------------------------------------
NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

NOTE_RE = re.compile(r"^([A-G])([#b]?)(-?\d)$")

def midi_note(name):
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError(f"bad note name: {name!r}")
    letter, acc, octave = m.group(1), m.group(2), int(m.group(3))
    n = 12 * (octave + 1) + NOTE_PC[letter] + (1 if acc == "#" else -1 if acc == "b" else 0)
    if not 21 <= n <= 108:
        raise ValueError(f"note out of piano range: {name!r}")
    return n

def spell(midi, prefer_flat=False):
    """Return (letter, accidental, octave) for a midi note."""
    table = FLAT if prefer_flat else SHARP
    name = table[midi % 12]
    letter = name[0]
    acc = name[1:]  # "", "#" or "b"
    return letter, {"": 0, "#": 1, "b": -1}[acc], midi // 12 - 1

QUALITIES = {
    "": (4, 7), "m": (3, 7), "min": (3, 7), "7": (4, 7, 10),
    "maj7": (4, 7, 11), "m7": (3, 7, 10), "dim": (3, 6),
    "m7b5": (3, 6, 10), "sus4": (5, 7), "sus2": (2, 7),
    "6": (4, 7, 9), "m6": (3, 7, 9), "add9": (4, 7, 14), "aug": (4, 8),
}
CHORD_RE = re.compile(
    r"^([A-G][#b]?)(maj7|m7b5|add9|sus4|sus2|min|m7|m6|m|dim|aug|6|7)?(?:/([A-G][#b]?))?$")

def parse_chord(sym):
    """'G/B' -> (root_pc, intervals, bass_pc). Raises ValueError."""
    m = CHORD_RE.match(sym)
    if not m:
        raise ValueError(f"unsupported chord symbol: {sym!r}")
    root = midi_note(m.group(1) + "4") % 12
    intervals = QUALITIES[m.group(2) or ""]
    bass = midi_note(m.group(3) + "4") % 12 if m.group(3) else root
    return root, intervals, bass

# --------------------------------------------------------------------------
# Score schema
# --------------------------------------------------------------------------
# {
#   "title": str, "subtitle": str,
#   "key_sig": int (-7..7, fifths; -1 = F major, 1 = G major, 0 = C/Am),
#   "minor": bool,
#   "time": [num, den],            # [4,4] or [3,4]
#   "bpm": int,
#   "accompaniment": "flowing" | "alberti" | "waltz" | "chords",
#   "sections": [{"bar": int, "name": str, "dynamic": str}],
#   "bars": [{"chord": str, "melody": [[noteName, beats], ...]}, ...]
# }
ALLOWED_DURS = {0.5, 1, 1.5, 2, 3, 4}

def build_score(data):
    if not isinstance(data, dict):
        raise ValueError("score must be a JSON object")
    score = {
        "title": str(data.get("title") or "Untitled"),
        "subtitle": str(data.get("subtitle") or "for piano solo"),
        "key_sig": int(data.get("key_sig", 0)),
        "minor": bool(data.get("minor", False)),
        "bpm": int(data.get("bpm", 72)),
        "tempo_mark": str(data.get("tempo_mark") or "Andantino"),
        "accompaniment": data.get("accompaniment", "flowing"),
    }
    if not -7 <= score["key_sig"] <= 7:
        raise ValueError("key_sig must be between -7 and 7")
    if not 40 <= score["bpm"] <= 160:
        raise ValueError("bpm must be between 40 and 160")
    num, den = data.get("time", [4, 4])
    if (num, den) not in [(2, 4), (3, 4), (4, 4), (6, 8)]:
        raise ValueError("time must be [2,4], [3,4], [4,4] or [6,8]")
    bar_beats = num * 4 / den
    score["time"] = (num, den)
    if score["accompaniment"] not in ("flowing", "alberti", "waltz", "chords"):
        raise ValueError("accompaniment must be flowing|alberti|waltz|chords")
    if score["accompaniment"] == "waltz" and (num, den) != (3, 4):
        raise ValueError("waltz accompaniment needs 3/4 time")

    bars = []
    for i, b in enumerate(data.get("bars", [])):
        chord = b.get("chord")
        parse_chord(chord)  # validates
        melody = []
        total = 0.0
        for item in b.get("melody", []):
            name, dur = item[0], float(item[1])
            n = midi_note(name)  # validates
            if not 48 <= n <= 84:
                raise ValueError(f"bar {i+1}: melody note {name} outside G3-C6 range")
            if dur not in ALLOWED_DURS or dur > bar_beats:
                raise ValueError(f"bar {i+1}: bad duration {dur} (allowed: {sorted(ALLOWED_DURS)})")
            melody.append((midi_note(name), dur))
            total += dur
        if abs(total - bar_beats) > 1e-9:
            raise ValueError(f"bar {i+1}: melody sums to {total} beats, need {bar_beats}")
        bars.append({"chord": chord, "rh": melody})
    if not 8 <= len(bars) <= 256:
        raise ValueError(f"need 8-256 bars, got {len(bars)}")
    score["bars"] = bars

    sections = []
    for s in data.get("sections", []):
        bar = int(s.get("bar", 0))
        if 0 <= bar < len(bars):
            sections.append({"bar": bar, "name": str(s.get("name", "")),
                             "dynamic": str(s.get("dynamic", ""))})
    score["sections"] = sections

    # Left hand is generated from the chord symbols.
    for b in bars:
        root, intervals, bass = parse_chord(b["chord"])
        low = 36 + bass          # bass note between C2 and B2
        up = [36 + root + 12 + iv for iv in intervals]  # chord tones above
        acc = score["accompaniment"]
        if acc == "flowing":
            pat = [0, 7, intervals[0] + 12, 7, intervals[0] + 12, 7, intervals[0] + 12, 7]
            evs = [([36 + root + (p if p < 12 else p)], 0.5) for p in pat[: int(bar_beats * 2)]]
        elif acc == "alberti":
            cell = [0, intervals[0] + 12, 7, intervals[0] + 12]
            evs = [([36 + root + cell[k % 4]], 0.5) for k in range(int(bar_beats * 2))]
        elif acc == "waltz":
            evs = [([low], 1)] + [(up, 1)] * (int(bar_beats) - 1)
        else:  # chords
            evs = [([low], bar_beats / 2), ([36 + root + 12] + up, bar_beats / 2)]
        b["lh"] = [(notes, dur) for notes, dur in evs]
    return score

def section_at(score, bar):
    name, dyn = "", "mp"
    for s in score["sections"]:
        if s["bar"] <= bar:
            name, dyn = s["name"], s["dynamic"] or dyn
    return name, dyn

def bpm_map(score):
    """Per-bar tempo: constant, with a ritardando over the final three bars."""
    n = len(score["bars"])
    bpm = score["bpm"]
    if score.get("rit") is False:
        return [float(bpm)] * n
    out = [float(bpm)] * n
    for k, f in enumerate((0.85, 0.7, 0.55)):
        if n >= 8:
            out[n - 3 + k] = bpm * f
    return out

DYN_VEL = {"ppp": 42, "pp": 50, "p": 57, "mp": 64, "mf": 72, "f": 80, "ff": 86}

def dyn_vel(dynamic):
    m = re.match(r"(fff|ff|f|mf|mp|p|pp|ppp)", dynamic.strip())
    return DYN_VEL.get(m.group(1), 64) if m else 64

# --------------------------------------------------------------------------
# MIDI
# --------------------------------------------------------------------------
PPQ = 480

def vlq(v):
    out = [v & 127]; v >>= 7
    while v:
        out.append((v & 127) | 128); v >>= 7
    return bytes(reversed(out))

def make_track(events):
    events.sort(key=lambda e: (e[0], e[1]))
    data = b""; last = 0
    for tick, order, msg in events:
        data += vlq(tick - last) + msg; last = tick
    data += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + data

def write_midi(score, path):
    num, den = score["time"]
    bpms = bpm_map(score)
    dd = {2: 1, 4: 2, 8: 3}[den]
    title_bytes = score["title"].encode("utf-8", "replace")
    meta = [(0, 0, b"\xff\x03" + vlq(len(title_bytes)) + title_bytes),
            (0, 1, bytes([0xFF, 0x58, 0x04, num, dd, 0x18, 0x08])),
            (0, 1, bytes([0xFF, 0x59, 0x02]) + struct.pack("b", score["key_sig"]) + bytes([1 if score["minor"] else 0]))]
    bar_beats = num * 4 / den
    bar_offsets = []
    cursor = 0.0
    for item in score["bars"]:
        bar_offsets.append(cursor)
        cursor += item.get("_beats", bar_beats)
    for bar in range(len(score["bars"])):
        us = round(60_000_000 / bpms[bar])
        meta.append((round(bar_offsets[bar] * PPQ), 2,
                     b"\xff\x51\x03" + us.to_bytes(3, "big")))
    notes = [(0, 0, bytes([0xC0, 0])), (0, 0, bytes([0xC1, 0]))]
    for bar, m in enumerate(score["bars"]):
        actual_beats = m.get("_beats", bar_beats)
        base = round(bar_offsets[bar] * PPQ)
        notes += [(base, 0, bytes([0xB0, 64, 100])),
                  (base + round(actual_beats * PPQ) - 30, 0, bytes([0xB0, 64, 0]))]
        vel0 = dyn_vel(section_at(score, bar)[1])
        swell = int(6 * math.sin((bar % 8) / 7 * math.pi))
        # Right hand: single notes. Left hand: possibly chords.
        for hand, channel, vscale in [("rh", 0, 1.0), ("lh", 1, 0.74)]:
            t = base
            for ev in m[hand]:
                group, dur = (ev[:2] if hand == "lh" else ([ev[0]], ev[1]))
                sound_dur = ev[2] if len(ev) > 2 else dur
                vel = max(30, min(100, int((vel0 + swell) * vscale)))
                length = max(60, int(sound_dur * PPQ * 0.92))
                for n in group:
                    notes += [(t, 2, bytes([0x90 | channel, n, vel])),
                              (t + length, 1, bytes([0x80 | channel, n, 40]))]
                t += int(dur * PPQ)
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 2, PPQ)
    with open(path, "wb") as f:
        f.write(header + make_track(meta) + make_track(notes))

# --------------------------------------------------------------------------
# Audio (soft-piano additive synthesis, pure stdlib)
# --------------------------------------------------------------------------
def render_audio(score, path, sr=32000):
    bpms = bpm_map(score)
    bar_beats = score["time"][0] * 4 / score["time"][1]
    starts = [0.0]
    for bar, item in enumerate(score["bars"]):
        starts.append(starts[-1] + 60 * item.get("_beats", bar_beats) / bpms[bar])
    duration = starts[-1] + 4.0
    mix = array("f", [0.0]) * int(duration * sr)
    TBL = 8192
    sines = [math.sin(2 * math.pi * i / TBL) for i in range(TBL)]

    def add_note(start, midi, beats, velocity, hand, bpm):
        freq = 440.0 * 2 ** ((midi - 69) / 12)
        decay = (2.8 if hand == "lh" else 2.2) * 2 ** ((60 - midi) / 40)
        sustain = beats * 60 / bpm
        count = int(min(4.5, sustain + decay) * sr)
        base = int(start * sr)
        amp = (velocity / 127) ** 1.65 * (0.25 if hand == "rh" else 0.20)
        phase = 0.0; step = freq * TBL / sr
        for i in range(count):
            idx = base + i
            if idx >= len(mix):
                break
            t = i / sr
            env = min(1.0, t / 0.009) * math.exp(-t / decay)
            if t > sustain + 0.25:
                env *= math.exp(-(t - sustain - 0.25) * 2.8)
            p = int(phase) & (TBL - 1)
            mix[idx] += amp * env * (sines[p] + 0.34 * sines[int(phase * 2.003) & (TBL - 1)]
                                     + 0.13 * sines[int(phase * 3.008) & (TBL - 1)])
            phase += step

    for bar, m in enumerate(score["bars"]):
        spb = 60 / bpms[bar]
        vel0 = dyn_vel(section_at(score, bar)[1])
        swell = int(6 * math.sin((bar % 8) / 7 * math.pi))
        for hand, vscale in [("rh", 1.0), ("lh", 0.74)]:
            beat = 0.0
            for ev in m[hand]:
                group, dur = ev[:2]
                sound_dur = ev[2] if len(ev) > 2 else dur
                if not isinstance(group, (list, tuple)):
                    group = [group]
                vel = int((vel0 + swell) * vscale)
                for n in group:
                    if n is None:
                        continue          # rest
                    add_note(starts[bar] + beat * spb, n, sound_dur, vel, hand, bpms[bar])
                beat += dur
    peak = max(max(mix), -min(mix), 0.001)
    gain = 0.92 / peak
    pcm = array("h", (max(-32767, min(32767, int(v * gain * 32767))) for v in mix))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return duration

# --------------------------------------------------------------------------
# Engraving
# --------------------------------------------------------------------------
LINE = 6.3
STEP = LINE / 2
INK = HexColor("#171717")
GRAY = HexColor("#555555")
LETTER_IDX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}

def staff_y(letter, octave, bottom_y, clef):
    idx = octave * 7 + LETTER_IDX[letter]
    ref = 4 * 7 + LETTER_IDX["E"] if clef == "treble" else 2 * 7 + LETTER_IDX["G"]
    return bottom_y + (idx - ref) * STEP

def draw_notehead(c, x, y, hollow):
    c.saveState(); c.translate(x, y); c.rotate(13)
    c.setFillColor(INK); c.setStrokeColor(INK); c.setLineWidth(0.9)
    if hollow:
        c.ellipse(-3, -2, 3, 2, fill=0, stroke=1)
        c.setFillColorRGB(1, 1, 1); c.ellipse(-1.8, -1.1, 1.8, 1.1, fill=1, stroke=0)
    else:
        c.ellipse(-3, -2, 3, 2, fill=1, stroke=0)
    c.restoreState()

def draw_ledger(c, x, y, bottom_y):
    top = bottom_y + 4 * LINE
    p = top + LINE
    while p <= y + 0.1:
        c.line(x - 5, p, x + 5, p); p += LINE
    p = bottom_y - LINE
    while p >= y - 0.1:
        c.line(x - 5, p, x + 5, p); p -= LINE

def draw_flag(c, x, y, up):
    s = 1 if up else -1
    c.bezier(x, y, x + 7 * s, y - 3 * s, x + 6 * s, y - 9 * s, x + 2 * s, y - 11 * s)

ACC_GLYPH = {1: "♯", -1: "♭", 0: "♮"}
SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]
# Diatonic steps above each staff's bottom line (treble E4, bass G2).
SIG_POS = {
    "treble": {"sharp": [9, 6, 10, 8, 4, 7, 5], "flat": [5, 7, 4, 8, 2, 6, 9]},
    "bass":   {"sharp": [6, 3, 7, 4, 1, 5, 2], "flat": [2, 5, 1, 4, 0, 3, 6]},
}

def key_sig_defaults(key_sig):
    d = {}
    if key_sig > 0:
        for letter in SHARP_ORDER[:key_sig]:
            d[letter] = 1
    elif key_sig < 0:
        for letter in FLAT_ORDER[:-key_sig]:
            d[letter] = -1
    return d

def draw_key_sig(c, x, key_sig, bottom_y, clef):
    if key_sig == 0:
        return x
    kind = "sharp" if key_sig > 0 else "flat"
    glyph = "♯" if key_sig > 0 else "♭"
    c.setFont("Music", 9); c.setFillColor(INK)
    for i in range(abs(key_sig)):
        step = SIG_POS[clef][kind][i]
        c.drawString(x + i * 8.5, bottom_y + step * STEP - 3.2, glyph)
    return x + abs(key_sig) * 8.5 + 4

def draw_hand(c, events, spelled, x0, x1, bottom_y, clef, sig_default):
    """events: [(dur, [midi,...]), ...]; spelled: parallel letter/acc/octave lists."""
    middle = bottom_y + 2 * LINE
    active_acc = {}  # (letter, octave) -> accidental in force this bar
    pts = []
    beat = 0.0
    for (dur, midis), notes in zip(events, spelled):
        x = x0 + 9 + (x1 - x0 - 18) * (beat / 4)
        group = []
        for midi, (letter, acc, octave) in zip(midis, notes):
            y = staff_y(letter, octave, bottom_y, clef)
            key2 = (letter, octave)
            cur = active_acc.get(key2, sig_default.get(letter, 0))
            show = acc != cur
            active_acc[key2] = acc
            group.append({"y": y, "acc": acc if show else None})
        pts.append({"x": x, "dur": dur, "notes": group})
        beat += dur

    i = 0
    while i < len(pts):
        p = pts[i]
        x, d = p["x"], p["dur"]
        ys = [n["y"] for n in p["notes"]]
        if d == 0.5 and i + 1 < len(pts) and pts[i + 1]["dur"] == 0.5:
            j = i
            while j < len(pts) and pts[j]["dur"] == 0.5:
                j += 1
            grp = pts[i:j]
            avg = sum(sum(n["y"] for n in g["notes"]) / len(g["notes"]) for g in grp) / len(grp)
            up = avg < middle
            lo = min(min(n["y"] for n in g["notes"]) for g in grp)
            hi = max(max(n["y"] for n in g["notes"]) for g in grp)
            by = hi + 20 if up else lo - 20
            c.setLineWidth(0.9); c.setStrokeColor(INK)
            for g in grp:
                gys = [n["y"] for n in g["notes"]]
                for n in g["notes"]:
                    draw_ledger(c, g["x"], n["y"], bottom_y)
                    draw_notehead(c, g["x"], n["y"], hollow=False)
                sx = g["x"] + 2.7 if up else g["x"] - 2.7
                c.line(sx, max(gys) if up else min(gys), sx, by)
            xa = grp[0]["x"] + (2.7 if up else -2.7)
            xb = grp[-1]["x"] + (2.7 if up else -2.7)
            c.setFillColor(INK)
            c.rect(xa, by - 2.4 if up else by, xb - xa, 2.4, fill=1, stroke=0)
            i = j
            continue
        up = (sum(ys) / len(ys)) < middle
        c.setLineWidth(0.9); c.setStrokeColor(INK)
        for n in p["notes"]:
            draw_ledger(c, x, n["y"], bottom_y)
            draw_notehead(c, x, n["y"], hollow=(d >= 2))
        if d < 4:
            sx = x + 2.7 if up else x - 2.7
            end = (max(ys) + 20) if up else (min(ys) - 20)
            c.line(sx, max(ys) if up else min(ys), sx, end)
            if d <= 0.5:
                draw_flag(c, sx, end, up)
        if d in (0.75, 1.5, 2.5, 3, 3.5):
            top = max(ys)
            on_line = round((top - bottom_y) / STEP) % 2 == 0
            c.setFillColor(INK)
            c.circle(x + 6.5, top + (STEP if on_line else 0), 0.9, fill=1, stroke=0)
        i += 1
    # Accidentals on top of everything.
    c.setFont("Music", 9); c.setFillColor(INK)
    for p in pts:
        offs = 0
        for n in p["notes"]:
            if n["acc"] is not None:
                c.drawRightString(p["x"] - 4.5 - offs, n["y"] - 3, ACC_GLYPH[n["acc"]])
                offs += 6

def draw_staff_lines(c, y, x0, x1):
    c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
    for k in range(5):
        c.line(x0, y + k * LINE, x1, y + k * LINE)

def write_pdf(score, path):
    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(f"{score['title']} — Piano Solo")
    margin = 42
    per_system, per_page = 4, 5
    bars = score["bars"]
    num, den = score["time"]
    prefer_flat = score["key_sig"] < 0
    sig_default = key_sig_defaults(score["key_sig"])
    section_marks = {s["bar"]: s["name"] for s in score["sections"] if s["name"]}
    dynamics = {s["bar"]: s["dynamic"] for s in score["sections"] if s["dynamic"]}
    total_systems = (len(bars) + per_system - 1) // per_system
    for page in range((total_systems + per_page - 1) // per_page):
        c.setFillColor(INK)
        if page == 0:
            c.setFont("Serif", 24)
            c.drawCentredString(W / 2, H - 46, score["title"])
            c.setFont("SerifItalic", 11)
            c.drawCentredString(W / 2, H - 63, score["subtitle"])
            top = H - 136
        else:
            c.setFont("Serif", 8)
            c.drawString(margin, H - 24, score["title"].upper()[:40])
            c.drawRightString(W - margin, H - 24, "Piano Solo")
            top = H - 80
        gap = 145
        for s in range(per_page):
            first = (page * per_page + s) * per_system
            if first >= len(bars):
                break
            yt = top - s * gap
            yb = yt - 58
            xs, xe = margin + 24, W - margin
            sec_x = xs + 2
            if page * per_page + s == 0:
                c.setFont("SerifItalic", 10); c.setFillColor(INK)
                tempo = score["tempo_mark"]
                c.drawString(sec_x, yt + 52, tempo)
                tx = sec_x + pdfmetrics.stringWidth(tempo, "SerifItalic", 10) + 8
                c.setFont("Music", 10)
                c.drawString(tx, yt + 52, "♩")
                c.setFont("Serif", 10)
                bpm_txt = f"= {score['bpm']}"
                c.drawString(tx + 9, yt + 52, bpm_txt)
                sec_x = tx + 9 + pdfmetrics.stringWidth(bpm_txt, "Serif", 10) + 14
            if first in section_marks:
                c.setFont("SerifItalic", 9); c.setFillColor(INK)
                c.drawString(sec_x, yt + 52, section_marks[first])
            draw_staff_lines(c, yt, xs, xe)
            draw_staff_lines(c, yb, xs, xe)
            c.setFont("Clef", 25); c.setFillColor(INK)
            c.drawString(xs + 2, yt - 7, "\U0001D11E")
            c.setFont("Clef", 21)
            c.drawString(xs + 2, yb + 3, "\U0001D122")
            c.setLineWidth(0.9)
            c.line(xs, yb, xs, yt + 4 * LINE)
            x_after_clef = xs + 26
            xt = draw_key_sig(c, x_after_clef, score["key_sig"], yt, "treble")
            xb_ = draw_key_sig(c, x_after_clef, score["key_sig"], yb, "bass")
            left = max(xt, xb_) + 8
            if page * per_page + s == 0:
                c.setFont("Serif", 13)
                for yy in (yt, yb):
                    c.drawString(left, yy + 12, str(num))
                    c.drawString(left, yy + 2, str(den))
                left += 18
            width = xe - left
            for j in range(per_system):
                bar = first + j
                if bar >= len(bars):
                    break
                x0 = left + j * width / per_system
                x1 = left + (j + 1) * width / per_system
                m = bars[bar]
                c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
                for yy in (yt, yb):
                    c.line(x0, yy, x0, yy + 4 * LINE)
                c.setFont("Serif", 6.5); c.setFillColor(GRAY)
                c.drawString(x0 + 1.5, yt + 4 * LINE + 3, str(bar + 1))
                c.setFont("Serif", 8)
                c.drawCentredString((x0 + x1) / 2, yt + 4 * LINE + 16, m["chord"])
                if bar in dynamics:
                    c.setFont("SerifItalic", 8); c.setFillColor(INK)
                    c.drawString(x0 + 2, yb - 26, dynamics[bar])
                rh_ev = [(d, [n]) for n, d in m["rh"]]
                rh_sp = [[spell(n, prefer_flat)] for n, d in m["rh"]]
                lh_ev = [(d, notes) for notes, d in m["lh"]]
                lh_sp = [[spell(n, prefer_flat) for n in notes] for notes, d in m["lh"]]
                draw_hand(c, rh_ev, rh_sp, x0, x1, yt, "treble", sig_default)
                draw_hand(c, lh_ev, lh_sp, x0, x1, yb, "bass", sig_default)
                end_bar = min(first + per_system, len(bars)) - 1
                if bar == end_bar:
                    c.setLineWidth(0.55)
                    for yy in (yt, yb):
                        c.line(x1, yy, x1, yy + 4 * LINE)
                    if bar == len(bars) - 1:
                        c.setLineWidth(2.2)
                        for yy in (yt, yb):
                            c.line(x1 - 3.5, yy, x1 - 3.5, yy + 4 * LINE)
        c.setFont("Serif", 8); c.setFillColor(INK)
        c.drawCentredString(W / 2, 20, str(page + 1))
        c.showPage()
    c.save()

def register_fonts():
    pdfmetrics.registerFont(TTFont("Serif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"))
    pdfmetrics.registerFont(TTFont("SerifItalic", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"))
    pdfmetrics.registerFont(TTFont("Music", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("Clef", os.path.join(OUT, "NotoMusic-Regular.ttf")))

def render_all(score, basename, audio=True):
    register_fonts()
    pdf, mid = f"{basename}.pdf", f"{basename}.mid"
    write_pdf(score, pdf)
    write_midi(score, mid)
    made = [pdf, mid]
    if audio:
        wav = f"{basename}.wav"
        render_audio(score, wav)
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                            "-codec:a", "libmp3lame", "-q:a", "3", f"{basename}.mp3"],
                           check=True)
            made.append(f"{basename}.mp3")
            os.remove(wav)
        except (subprocess.CalledProcessError, FileNotFoundError):
            made.append(wav)  # retain the WAV only when MP3 conversion failed
    return made

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    sc = build_score(data)
    out = render_all(sc, sys.argv[2] if len(sys.argv) > 2 else "score")
    print("created:", ", ".join(out))
