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
from musiclib import draw_notehead, draw_ledger, draw_flag, staff_y, register_fonts, LINE, STEP
from lesson_day_one import Doc, MARGIN, INK, GRAY, ACCENT, W, H

OUT = "/srv/files/piano/lessons" if os.path.isdir("/srv/files/piano/lessons") and os.access("/srv/files/piano/lessons", os.W_OK) else os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# grand-staff exercise: both hands, beats aligned
# --------------------------------------------------------------------------
def grand_exercise(doc, rh, lh, show_names=True, show_fingers=True):
    """rh/lh: [(letter, octave, dur, finger), ...]; 4/4, equal total beats."""
    doc.need(175)
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
    c.setFont("Serif", 12)
    for yy in (yt, yb):
        c.drawString(x0 + 30, yy + 12, "4"); c.drawString(x0 + 30, yy + 2, "4")
    c.setLineWidth(0.9)
    c.line(x0, yb, x0, yt + 4 * LINE)
    left = x0 + 48
    width = x1 - left
    total = sum(d for _, _, d, _ in rh)
    lowest = yb  # lowest ink, for advancing the cursor afterwards

    def draw_hand(notes, bottom, clef):
        nonlocal lowest
        beat = 0.0
        for letter, octave, dur, finger in notes:
            x = left + width * (beat / total) + (width / total) * 0.35
            y = staff_y(letter, octave, bottom, clef)
            lowest = min(lowest, y)
            c.setLineWidth(0.9); c.setStrokeColor(INK)
            draw_ledger(c, x, y, bottom)
            draw_notehead(c, x, y, hollow=(dur >= 2))
            up = y < bottom + 2 * LINE
            if dur < 4:
                sx = x + 2.7 if up else x - 2.7
                end = y + (20 if up else -20)
                c.line(sx, y, sx, end)
                if dur <= 0.5:
                    draw_flag(c, sx, end, up)
            if dur in (1.5, 3):
                c.setFillColor(INK)
                c.circle(x + 6.5, y + (STEP if round((y - bottom) / STEP) % 2 == 0 else 0), 0.9, fill=1, stroke=0)
            if show_fingers and finger:
                c.setFont("Serif", 8.5); c.setFillColor(ACCENT)
                c.drawCentredString(x, bottom + 4 * LINE + 8, str(finger))
            if show_names:
                # Name under the notehead; for down-stems shift left of the stem.
                c.setFont("Serif", 8.5); c.setFillColor(GRAY)
                if dur < 4 and not up:
                    c.drawRightString(x - 6, y - 8, letter)
                else:
                    c.drawCentredString(x, y - 8, letter)
            beat += dur

    draw_hand(rh, yt, "treble")
    draw_hand(lh, yb, "bass")

    # barlines across both staves every 4 beats, plus final double bar
    beat = 4.0
    c.setStrokeColor(HexColor("#222222"))
    while beat < total:
        bx = left + width * (beat / total)
        c.setLineWidth(0.55)
        c.line(bx, yb, bx, yt + 4 * LINE)
        beat += 4
    c.setLineWidth(0.55); c.line(x1, yb, x1, yt + 4 * LINE)
    c.setLineWidth(2.2); c.line(x1 - 3.5, yb, x1 - 3.5, yt + 4 * LINE)
    doc.y = min(yb - 28, lowest - 22)

# --------------------------------------------------------------------------
# the lesson
# --------------------------------------------------------------------------
def build(path):
    register_fonts()
    d = Doc(path)

    d.h1("Day Two at the Piano")
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
        [("C",3,4,5),("C",3,4,5),("C",3,4,5),("G",2,4,1),
         ("C",3,4,5),("C",3,4,5),("G",2,4,1),("C",3,4,5)])

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
