#!/usr/bin/env python3
"""Lettre d'Amour — an original romantic piano solo (2-3 minutes), PDF score.

Grand staff (right hand + left hand), Clayderman-style: a singable melody
over flowing left-hand broken-chord patterns.  The PDF is engraved directly
with ReportLab; no external notation software is needed.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import math, os, struct

OUT = "/srv/files/piano" if os.path.isdir("/srv/files/piano") and os.access("/srv/files/piano", os.W_OK) else os.path.dirname(os.path.abspath(__file__))

NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def midi_note(name):
    letter = name[0]; i = 1; acc = 0
    while i < len(name) and name[i] in "#b":
        acc += 1 if name[i] == "#" else -1; i += 1
    return 12 * (int(name[i:]) + 1) + NOTE_PC[letter] + acc

def note_name(n):
    sharp = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    return sharp[n % 12] + str(n // 12 - 1)

# --------------------------------------------------------------------------
# The composition: 40 bars in C major, ~2.5 minutes at Andantino (q = 69).
# Each bar: (chord, [(melody note, beats), ...]); melody always sums to 4.
# Left hand: broken 10th pattern derived from the chord, eighth notes.
# --------------------------------------------------------------------------
# chord -> (left-hand root midi, third interval in semitones)
CHORDS = {"C": (36, 4), "Am": (33, 3), "F": (41, 4), "G": (43, 4),
          "Em": (40, 3), "Dm": (38, 3), "E7": (40, 4)}

BARS = [
    # A — the love-letter theme
    ("C",  [("E5",1),("D5",1),("C5",2)]),
    ("Am", [("C5",1),("B4",1),("A4",2)]),
    ("F",  [("A4",1),("C5",1),("F5",2)]),
    ("G",  [("E5",1.5),("D5",0.5),("D5",2)]),
    ("C",  [("E5",1),("D5",0.5),("E5",0.5),("G5",2)]),
    ("F",  [("A5",2),("G5",1),("F5",1)]),
    ("Em", [("E5",1.5),("D5",0.5),("B4",2)]),
    ("G",  [("D5",2),("B4",1),("G4",1)]),
    # A' — theme, gently varied
    ("C",  [("E5",1),("G5",1),("A5",2)]),
    ("Am", [("G5",1),("E5",1),("C5",2)]),
    ("F",  [("F5",1.5),("E5",0.5),("D5",2)]),
    ("G",  [("D5",2),("B4",2)]),
    ("C",  [("C5",1),("D5",0.5),("E5",0.5),("G5",2)]),
    ("F",  [("A5",2),("G5",1),("E5",1)]),
    ("C",  [("G5",1.5),("E5",0.5),("C5",2)]),
    ("G",  [("D5",2),("B4",1),("G4",1)]),
    # B — poco piu mosso, the emotional heart
    ("Am", [("A4",0.5),("C5",0.5),("E5",1),("A5",2)]),
    ("F",  [("G5",1),("F5",1),("C5",2)]),
    ("Dm", [("D5",1),("F5",1),("A5",2)]),
    ("G",  [("B5",1.5),("A5",0.5),("G5",2)]),
    ("Am", [("A5",2),("E5",1),("C5",1)]),
    ("F",  [("F5",1.5),("G5",0.5),("A5",2)]),
    ("Em", [("E5",1),("G5",1),("B5",2)]),
    ("E7", [("G#5",2),("E5",2)]),
    # A'' — the theme returns, tenderly
    ("C",  [("E5",1),("D5",1),("C5",2)]),
    ("Am", [("C5",1),("B4",1),("A4",2)]),
    ("F",  [("A4",1),("C5",1),("F5",2)]),
    ("G",  [("G5",1.5),("F5",0.5),("E5",2)]),
    ("C",  [("E5",1),("G5",0.5),("A5",0.5),("G5",2)]),
    ("F",  [("F5",2),("E5",1),("D5",1)]),
    ("Em", [("E5",2),("B4",2)]),
    ("G",  [("D5",2),("G4",2)]),
    # Coda — a last whisper
    ("C",  [("C5",1),("E5",1),("G5",2)]),
    ("F",  [("A5",1),("G5",1),("F5",2)]),
    ("C",  [("E5",2),("G5",2)]),
    ("Am", [("A5",2),("E5",2)]),
    ("F",  [("F5",1.5),("E5",0.5),("D5",2)]),
    ("G",  [("D5",2),("B4",2)]),
    ("C",  [("C5",2),("E5",1),("G5",1)]),
    ("C",  [("C6",4)]),
]

SECTIONS = {0: "A — dolce e cantabile", 8: "A'", 16: "B — poco più mosso",
            24: "A''", 32: "Coda"}
DYNAMICS = {0: "p dolce", 8: "mp espressivo", 16: "mf appassionato",
            24: "mp dolce", 32: "p", 36: "dim.", 38: "rit.  ·  pp morendo"}

def build_measures():
    measures = []
    for bar, (chord, melody) in enumerate(BARS):
        assert abs(sum(d for _, d in melody) - 4) < 1e-9, f"bar {bar+1} rhythm"
        root, third = CHORDS[chord]
        rh = [(midi_note(n), d) for n, d in melody]
        if bar == len(BARS) - 1:
            lh = [(root, 2), (root + 12, 2)]
        else:
            pat = [0, 7, third + 12, 7, third + 12, 7, third + 12, 7]
            lh = [(root + off, 0.5) for off in pat]
        measures.append({"chord": chord, "rh": rh, "lh": lh})
    return measures

MEASURES = build_measures()

# --------------------------------------------------------------------------
# MIDI (tempo map and dynamics mirror render_lettre_d_amour.py)
# --------------------------------------------------------------------------
PPQ = 480

def bpm_for_bar(bar):
    if bar >= 33:  # rit. e morendo over the coda's last phrase
        return [69, 69, 69, 65, 60, 54, 46][min(6, bar - 33)]
    return 69

def base_vel(bar):
    if bar < 8:  return 58   # p dolce
    if bar < 16: return 64   # mp espressivo
    if bar < 24: return 73   # mf appassionato
    if bar < 32: return 64   # mp dolce
    if bar < 36: return 57   # p
    return 50                # pp morendo

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

def write_midi(path):
    meta = [(0, 0, b"\xff\x03\x1bLettre d'Amour - Piano Solo"),
            (0, 1, b"\xff\x58\x04\x04\x02\x18\x08"),   # 4/4
            (0, 1, b"\xff\x59\x02\x00\x00")]           # C major
    for bar in range(len(MEASURES)):
        us = round(60_000_000 / bpm_for_bar(bar))
        meta.append((bar * 4 * PPQ, 2, b"\xff\x51\x03" + us.to_bytes(3, "big")))
    notes = [(0, 0, bytes([0xC0, 0])), (0, 0, bytes([0xC1, 0]))]  # grand piano
    for bar, m in enumerate(MEASURES):
        base = bar * 4 * PPQ
        # Sustain pedal per harmony, lifted just before the next bar.
        notes += [(base, 0, bytes([0xB0, 64, 100])),
                  (base + 4 * PPQ - 30, 0, bytes([0xB0, 64, 0]))]
        swell = int(6 * math.sin((bar % 8) / 7 * math.pi))
        for hand, channel, vscale in [(m["rh"], 0, 1.0), (m["lh"], 1, 0.74)]:
            t = base
            for n, d in hand:
                vel = max(30, min(100, int((base_vel(bar) + swell) * vscale)))
                length = max(60, int(d * PPQ * 0.92))
                notes += [(t, 2, bytes([0x90 | channel, n, vel])),
                          (t + length, 1, bytes([0x80 | channel, n, 40]))]
                t += int(d * PPQ)
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 2, PPQ)
    with open(path, "wb") as f:
        f.write(header + make_track(meta) + make_track(notes))

# --------------------------------------------------------------------------
# Engraving
# --------------------------------------------------------------------------
LINE = 6.3            # distance between staff lines
STEP = LINE / 2       # one diatonic step
INK = HexColor("#171717")
GRAY = HexColor("#555555")

def staff_y(note, bottom_y, clef):
    """y of a midi note on a staff whose bottom line is at bottom_y."""
    names = ["C","D","E","F","G","A","B"]
    nn = note_name(note)
    idx = int(nn[-1]) * 7 + names.index(nn[0])
    ref = 4 * 7 + names.index("E") if clef == "treble" else 2 * 7 + names.index("G")
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
    c.bezier(x, y, x + 7*s, y - 3*s, x + 6*s, y - 9*s, x + 2*s, y - 11*s)

def draw_hand(c, notes, x0, x1, bottom_y, clef):
    middle = bottom_y + 2 * LINE
    # Resolve positions first so eighth notes can be beamed.
    pts = []
    beat = 0.0
    for n, d in notes:
        x = x0 + 9 + (x1 - x0 - 18) * (beat / 4)
        pts.append((x, staff_y(n, bottom_y, clef), d, n))
        beat += d
    i = 0
    while i < len(pts):
        x, y, d, n = pts[i]
        if d == 0.5 and i + 1 < len(pts) and pts[i + 1][2] == 0.5:
            # Beam a run of eighth notes.
            j = i
            while j < len(pts) and pts[j][2] == 0.5:
                j += 1
            grp = pts[i:j]
            up = sum(p[1] for p in grp) / len(grp) < middle
            by = (max(p[1] for p in grp) + 20) if up else (min(p[1] for p in grp) - 20)
            c.setLineWidth(0.9); c.setStrokeColor(INK)
            for gx, gy, gd, gn in grp:
                draw_ledger(c, gx, gy, bottom_y)
                draw_notehead(c, gx, gy, hollow=False)
                sx = gx + 2.7 if up else gx - 2.7
                c.line(sx, gy, sx, by)
            x_a = grp[0][0] + 2.7 if up else grp[0][0] - 2.7
            x_b = grp[-1][0] + 2.7 if up else grp[-1][0] - 2.7
            c.setFillColor(INK)
            if up:
                c.rect(x_a, by - 2.4, x_b - x_a, 2.4, fill=1, stroke=0)
            else:
                c.rect(x_a, by, x_b - x_a, 2.4, fill=1, stroke=0)
            i = j
            continue
        # Single note: quarter, dotted quarter, half, whole, or lone eighth.
        up = y < middle
        c.setLineWidth(0.9); c.setStrokeColor(INK)
        draw_ledger(c, x, y, bottom_y)
        draw_notehead(c, x, y, hollow=(d >= 2))
        if d < 4:
            sx = x + 2.7 if up else x - 2.7
            end = y + 20 if up else y - 20
            c.line(sx, y, sx, end)
            if d <= 0.5:
                draw_flag(c, sx, end, up)
        if d in (0.75, 1.5, 3):  # augmentation dot
            on_line = round((y - bottom_y) / STEP) % 2 == 0
            c.setFillColor(INK)
            c.circle(x + 6.5, y + (STEP if on_line else 0), 0.9, fill=1, stroke=0)
        i += 1
    # Accidentals, shown once per pitch per bar (standard notation practice).
    seen = set()
    for x, y, d, n in pts:
        nn = note_name(n)
        if len(nn) > 2 and n not in seen:
            seen.add(n)
            c.setFont("Music", 9); c.setFillColor(INK)
            c.drawRightString(x - 4.5, y - 3, "♯" if nn[1] == "#" else "♭")

def draw_staff_lines(c, y, x0, x1):
    c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
    for k in range(5):
        c.line(x0, y + k * LINE, x1, y + k * LINE)

def write_pdf(path):
    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle("Lettre d'Amour — Romantic Piano Solo")
    margin = 42
    per_system, per_page = 4, 5
    total_systems = (len(MEASURES) + per_system - 1) // per_system
    for page in range((total_systems + per_page - 1) // per_page):
        c.setFillColor(INK)
        if page == 0:
            c.setFont("Serif", 24)
            c.drawCentredString(W / 2, H - 46, "Lettre d'Amour")
            c.setFont("SerifItalic", 11)
            c.drawCentredString(W / 2, H - 63, "une mélodie romantique pour piano")
            top = H - 128
        else:
            c.setFont("Serif", 8)
            c.drawString(margin, H - 24, "LETTRE D'AMOUR")
            c.drawRightString(W - margin, H - 24, "Romantic Piano Solo")
            top = H - 76
        gap = 145
        for s in range(per_page):
            sys_idx = page * per_page + s
            first = sys_idx * per_system
            if first >= len(MEASURES):
                break
            yt = top - s * gap
            yb = yt - 58
            xs, xe = margin + 24, W - margin
            if first in SECTIONS:
                c.setFont("SerifItalic", 9); c.setFillColor(INK)
                c.drawString(xs + 2, yt + 52, SECTIONS[first])
            draw_staff_lines(c, yt, xs, xe)
            draw_staff_lines(c, yb, xs, xe)
            # Clefs and a connecting barline at the start of every system.
            c.setFont("Clef", 25); c.setFillColor(INK)
            c.drawString(xs + 2, yt - 7, "\U0001D11E")
            c.setFont("Clef", 21)
            c.drawString(xs + 2, yb + 3, "\U0001D122")
            c.setLineWidth(0.9)
            c.line(xs, yb, xs, yt + 4 * LINE)
            if sys_idx == 0:
                c.setFont("SerifItalic", 10)
                tempo = "Andantino amoroso"
                c.drawString(xs + 26, yt + 32, tempo)
                tx = xs + 26 + pdfmetrics.stringWidth(tempo, "SerifItalic", 10) + 8
                c.setFont("Music", 10)
                c.drawString(tx, yt + 32, "♩")
                c.setFont("Serif", 10)
                c.drawString(tx + 9, yt + 32, "= 69")
                c.setFont("Serif", 13)
                for yy in (yt, yb):
                    c.drawString(xs + 26, yy + 12, "4")
                    c.drawString(xs + 26, yy + 2, "4")
                c.setFont("SerifItalic", 7.5)
                c.drawRightString(xe, yb - 13, "Ped. simile")
            left = xs + 40
            width = xe - left
            for j in range(per_system):
                bar = first + j
                if bar >= len(MEASURES):
                    break
                x0 = left + j * width / per_system
                x1 = left + (j + 1) * width / per_system
                m = MEASURES[bar]
                c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
                for yy in (yt, yb):
                    c.line(x0, yy, x0, yy + 4 * LINE)
                c.setFont("Serif", 6.5); c.setFillColor(GRAY)
                c.drawString(x0 + 1.5, yt + 4 * LINE + 3, str(bar + 1))
                c.setFont("Serif", 8); c.setFillColor(GRAY)
                c.drawCentredString((x0 + x1) / 2, yt + 4 * LINE + 15, m["chord"])
                if bar in DYNAMICS:
                    c.setFont("SerifItalic", 8); c.setFillColor(INK)
                    c.drawString(x0 + 2, yb - 26, DYNAMICS[bar])
                draw_hand(c, m["rh"], x0, x1, yt, "treble")
                draw_hand(c, m["lh"], x0, x1, yb, "bass")
                # Barline at the end of the last bar on the system.
                end_bar = min(first + per_system, len(MEASURES)) - 1
                if bar == end_bar:
                    last = bar == len(MEASURES) - 1
                    c.setLineWidth(0.55)
                    for yy in (yt, yb):
                        c.line(x1, yy, x1, yy + 4 * LINE)
                    if last:
                        c.setLineWidth(2.2)
                        for yy in (yt, yb):
                            c.line(x1 - 3.5, yy, x1 - 3.5, yy + 4 * LINE)
        c.setFont("Serif", 8); c.setFillColor(INK)
        c.drawCentredString(W / 2, 20, str(page + 1))
        c.showPage()
    c.save()

if __name__ == "__main__":
    pdfmetrics.registerFont(TTFont("Serif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"))
    pdfmetrics.registerFont(TTFont("SerifItalic", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"))
    pdfmetrics.registerFont(TTFont("Music", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("Clef", os.path.join(OUT, "NotoMusic-Regular.ttf")))
    out = os.path.join(OUT, "Lettre_d_Amour.pdf")
    write_pdf(out)
    mid = os.path.join(OUT, "Lettre_d_Amour.mid")
    write_midi(mid)
    print(f"Created {out} and {mid}  ({len(MEASURES)} bars, ~2.5 min at q=69)")
