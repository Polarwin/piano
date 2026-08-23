#!/usr/bin/env python3
"""Day Two piano lesson for adult beginners — printable PDF.

Both hands together: grand-staff exercises with finger numbers and note
names. Output goes to /srv/files/piano when present.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

import musiclib
from musiclib import (draw_notehead, draw_ledger, draw_flag, draw_key_sig,
                      staff_y, register_fonts, LINE, STEP)
from lesson_day_one import (Doc, MARGIN, INK, GRAY, ACCENT, W, H,
                            as_events, note_ys, draw_rest, draw_acc, event_name,
                            split_bars)

OUT = "/srv/files/piano/lessons" if os.path.isdir("/srv/files/piano/lessons") and os.access("/srv/files/piano/lessons", os.W_OK) else os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# grand-staff exercise: both hands, beats aligned
# --------------------------------------------------------------------------
def grand_exercise(doc, rh, lh, show_names=True, show_fingers=True,
                   time=(4, 4), tempo=None, dynamic=None, key_sig=0, pickup=0):
    """rh/lh: v1 tuples or v2 events (see as_events); equal total beats."""
    rh, lh = as_events(rh), as_events(lh)
    bar_beats = time[0] * 4 / time[1]
    if max(len(rh), len(lh)) > 12:
        rbars = split_bars(rh, bar_beats, pickup)
        lbars = split_bars(lh, bar_beats, pickup)
        chunks, cur_r, cur_l, count = [], [], [], 0
        for k, rbar in enumerate(rbars):
            lbar = lbars[k] if k < len(lbars) else []
            add = max(len(rbar), len(lbar))
            if cur_r and count + add > 12:
                chunks.append((cur_r, cur_l))
                cur_r, cur_l, count = [], [], 0
            cur_r += rbar
            cur_l += lbar
            count += add
        if cur_r:
            chunks.append((cur_r, cur_l))
        if len(chunks) > 1:
            for k, (rc, lc) in enumerate(chunks):
                grand_exercise(doc, rc, lc, show_names, show_fingers, time,
                               tempo if k == 0 else None, dynamic if k == 0 else None,
                               key_sig, pickup if k == 0 else 0)
                doc.gap(6)
            return
    doc.need(182)
    c = doc.c
    x0, x1 = MARGIN + 30, W - MARGIN
    yt = doc.y - 52                      # treble bottom line (clear of text + finger row)
    yb = yt - 58                         # bass bottom line
    c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
    for yy in (yt, yb):
        for k in range(5):
            c.line(x0, yy + k * LINE, x1, yy + k * LINE)
    c.setFont("Clef", 25); c.setFillColor(INK)
    c.drawString(x0 + 2, yt - 7, "\U0001D11E")
    c.setFont("Clef", 21)
    c.drawString(x0 + 2, yb + 3, "\U0001D122")
    xt = draw_key_sig(c, x0 + 28, key_sig, yt, "treble")
    xb = draw_key_sig(c, x0 + 28, key_sig, yb, "bass")
    sig_end = max(xt, xb)
    c.setFont("Serif", 12)
    for yy in (yt, yb):
        c.drawString(sig_end, yy + 12, str(time[0]))
        c.drawString(sig_end, yy + 2, str(time[1]))
    if tempo or dynamic:
        c.setFont("SerifItalic", 9); c.setFillColor(INK)
        c.drawString(x0 + 48, yt + 4 * LINE + 15,
                     "  ".join(m for m in (tempo, dynamic) if m))
    c.setLineWidth(0.9)
    c.line(x0, yb, x0, yt + 4 * LINE)
    left = sig_end + 18
    width = x1 - left
    total = sum(d for _, _, d, _ in rh)
    lowest = yb  # lowest ink, for advancing the cursor afterwards

    def draw_hand(evs, bottom, clef):
        nonlocal lowest
        beat = 0.0
        drawn = []
        for kind, payload, dur, label in evs:
            x = left + width * (beat / total) + (width / total) * 0.35
            c.setLineWidth(0.9); c.setStrokeColor(INK)
            if kind == "rest":
                draw_rest(c, x, bottom, dur)
                drawn.append((x, kind, payload, label, None))
                beat += dur
                continue
            tones = payload if isinstance(payload, list) else [payload]
            ys = [staff_y(l, o, bottom, clef) for l, _, o in tones]
            lowest = min(lowest, min(ys))
            prev_y = None
            for (l, a, o), y in zip(sorted(tones, key=lambda t: staff_y(t[0], t[2], bottom, clef)),
                                    sorted(ys)):
                hx = x
                if prev_y is not None and y - prev_y < STEP + 0.1:
                    hx += 5.5            # adjacent steps: stagger the head
                draw_ledger(c, hx, y, bottom)
                draw_notehead(c, hx, y, hollow=(dur >= 2))
                draw_acc(c, hx, y, a)
                prev_y = y
            lo, hi = min(ys), max(ys)
            up = (lo + hi) / 2 < bottom + 2 * LINE
            if dur < 4:
                sx = x + 2.7 if up else x - 2.7
                end = (hi + 20) if up else (lo - 20)
                c.line(sx, hi if up else lo, sx, end)
                if dur <= 0.5:
                    draw_flag(c, sx, end, up)
                    if dur == 0.25:
                        draw_flag(c, sx, end - (4 if up else -4), up)
            if dur in (1.5, 3):
                c.setFillColor(INK)
                c.circle(x + 6.5, hi + (STEP if round((hi - bottom) / STEP) % 2 == 0 else 0),
                         0.9, fill=1, stroke=0)
            finger = label[0] if isinstance(label, tuple) else label
            if show_fingers and finger:
                c.setFont("Serif", 8.5); c.setFillColor(ACCENT)
                c.drawCentredString(x, bottom + 4 * LINE + 8, str(finger))
            if show_names:
                # Name under the notehead; for down-stems shift left of the stem.
                c.setFont("Serif", 8.5); c.setFillColor(GRAY)
                if dur < 4 and not up:
                    c.drawRightString(x - 6, lo - 8, event_name(kind, payload))
                else:
                    c.drawCentredString(x, lo - 8, event_name(kind, payload))
            drawn.append((x, kind, payload, label, lo))
            beat += dur
        for current, following in zip(drawn, drawn[1:]):
            x, kind, payload, label, y = current
            nx, nkind, npayload, _, _ = following
            if kind == "note" and isinstance(label, tuple) and label[1] \
                    and nkind == "note" and payload == npayload:
                c.setLineWidth(0.7); c.setStrokeColor(INK)
                c.bezier(x + 4, y - 4, x + 10, y - 11,
                         nx - 10, y - 11, nx - 4, y - 4)

    draw_hand(rh, yt, "treble")
    draw_hand(lh, yb, "bass")

    # barlines across both staves, plus final double bar
    beat = float(pickup or bar_beats)
    c.setStrokeColor(HexColor("#222222"))
    while beat < total - 1e-9:
        bx = left + width * (beat / total)
        c.setLineWidth(0.55)
        c.line(bx, yb, bx, yt + 4 * LINE)
        beat += bar_beats
    c.setLineWidth(0.55); c.line(x1, yb, x1, yt + 4 * LINE)
    c.setLineWidth(2.2); c.line(x1 - 3.5, yb, x1 - 3.5, yt + 4 * LINE)
    doc.y = min(yb - 28, lowest - 22)

# --------------------------------------------------------------------------
# the lesson
# --------------------------------------------------------------------------
def build(path):
    register_fonts()
    d = Doc(path)

    d.h1("Day 2: Both Hands Together")
    d.c.setFont("SerifItalic", 12); d.c.setFillColor(GRAY)
    d.c.drawString(MARGIN, d.y - 4, "Both hands together — about 30 relaxed minutes")
    d.y -= 24
    d.para("Yesterday your hands learned the five-finger position separately. Today they play at the "
           "same time. This is the moment piano starts to feel like piano. Go slowly — slower than "
           "feels necessary — and the coordination will come on its own.")

    d.h2("1. Warm up (5 minutes)")
    d.bullets([
        "Right hand five-finger walk, twice (C D E F G F E D C).",
        "Left hand five-finger walk, twice.",
        "Play Hot Cross Buns and Mary Had a Little Lamb once each, right hand.",
        "If anything feels rusty, give it another minute. There is no hurry."])

    d.h2("2. Meet the grand staff (2 minutes)")
    d.para("Piano music writes both hands at once: the right hand on the upper staff (treble clef), "
           "the left hand on the lower staff (bass clef), joined by a line on the left. Notes that "
           "line up vertically are played at the same moment. Middle C lives between the two staves — "
           "one ledger line below the treble staff, one ledger line above the bass staff.")

    d.h2("3. How to play hands together")
    d.bullets([
        "Count out loud: one, two, three, four. Every note gets its number.",
        "Learn four beats at a time, then chain the chunks together.",
        "Keep your eyes on the music, not your hands — your fingers know the way by now.",
        "Three slow perfect repetitions teach more than ten fast sloppy ones."])

    d.h2("4. Exercise: together walk (5 minutes)")
    d.para("Both hands play the same walk at the same time — right hand starting on Middle C, left "
           "hand on the C below it. The notes move together like mirror images. Aim for steady, "
           "not fast.")
    grand_exercise(d,
        [("C",4,1,1),("D",4,1,2),("E",4,1,3),("F",4,1,4),
         ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
         ("C",4,4,1)],
        [("C",3,1,5),("D",3,1,4),("E",3,1,3),("F",3,1,2),
         ("G",3,1,1),("F",3,1,2),("E",3,1,3),("D",3,1,4),
         ("C",3,4,5)])

    d.h2("5. Hot Cross Buns, hands together (8 minutes)")
    d.para("Your right hand plays the song you know; your left hand plays one long C per bar — press "
           "it on beat one and let it ring. This is real piano texture: melody plus bass. If you "
           "stumble, drop to one bar at a time.")
    grand_exercise(d,
        [("E",4,2,3),("D",4,2,2),("C",4,4,1),
         ("E",4,2,3),("D",4,2,2),("C",4,4,1),
         ("C",4,1,1),("C",4,1,1),("C",4,1,1),("C",4,1,1),
         ("D",4,1,2),("D",4,1,2),("D",4,1,2),("D",4,1,2),
         ("E",4,2,3),("D",4,2,2),("C",4,4,1)],
        [("C",3,4,5)] * 8)

    d.h2("6. Milestone: Ode to Joy (10 minutes)")
    d.para("Beethoven, on your second day — honestly. The right hand carries the famous tune; the "
           "left hand plays one deep note per bar, alternating C and G. Two new things appear: a "
           "dotted note (hold it one and a half beats) and a short flagged note (half a beat). "
           "Take the first four bars only, repeat until easy, then finish the piece.")
    grand_exercise(d,
        [("E",4,1,3),("E",4,1,3),("F",4,1,4),("G",4,1,5),
         ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
         ("C",4,1,1),("C",4,1,1),("D",4,1,2),("E",4,1,3),
         ("E",4,1.5,3),("D",4,0.5,2),("D",4,2,2),
         ("E",4,1,3),("E",4,1,3),("F",4,1,4),("G",4,1,5),
         ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
         ("C",4,1,1),("C",4,1,1),("D",4,1,2),("E",4,1,3),
         ("D",4,1.5,2),("C",4,0.5,1),("C",4,2,1)],
        [("C",3,4,5),("C",3,4,5),("C",3,4,5),("G",3,4,1),
         ("C",3,4,5),("C",3,4,5),("G",3,4,1),("C",3,4,5)])

    d.h2("7. Your first-week plan")
    d.bullets([
        "Days 3–4: the together walk and Hot Cross Buns daily; Ode to Joy in two chunks.",
        "Days 5–7: all three pieces in one sitting; notice which bars still wobble and give them "
        "two extra slow repetitions.",
        "Keep every session under 20 minutes. Fresh concentration is the whole secret.",
        "When Ode to Joy feels smooth, you are ready for day three: your first chord, C major."])
    d.save()

if __name__ == "__main__":
    out = os.path.join(OUT, "Day_2_Both_Hands_Together.pdf")
    build(out)
    print("Created", out)
