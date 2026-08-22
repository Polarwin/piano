#!/usr/bin/env python3
"""Day One piano lesson for adult beginners — printable PDF.

Text + engraved exercises (single staff, quarter/half/whole notes) with
note names and finger numbers. Output goes to /srv/files/piano when present.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics

import musiclib
from musiclib import draw_notehead, draw_ledger, staff_y, register_fonts, LINE, STEP

OUT = "/srv/files/piano/lessons" if os.path.isdir("/srv/files/piano/lessons") and os.access("/srv/files/piano/lessons", os.W_OK) else os.path.dirname(os.path.abspath(__file__))
W, H = A4
MARGIN = 56
INK = HexColor("#171717")
GRAY = HexColor("#555555")
ACCENT = HexColor("#7a2e3f")

# --------------------------------------------------------------------------
# text helpers with a flowing y-cursor
# --------------------------------------------------------------------------
class Doc:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle("Day One at the Piano — A First Lesson for Adults")
        self.y = H - MARGIN

    def need(self, h):
        if self.y - h < MARGIN + 20:
            self.c.setFont("Serif", 8); self.c.setFillColor(GRAY)
            self.c.drawCentredString(W / 2, 28, str(self.c.getPageNumber()))
            self.c.showPage()
            self.y = H - MARGIN

    def h1(self, text):
        self.need(60)
        self.c.setFont("Serif", 22); self.c.setFillColor(INK)
        self.c.drawString(MARGIN, self.y - 24, text)
        self.y -= 40

    def h2(self, text):
        self.need(40)
        self.c.setFont("Serif", 14); self.c.setFillColor(ACCENT)
        self.c.drawString(MARGIN, self.y - 16, text)
        self.y -= 28

    def para(self, text, size=10.5, leading=15):
        self.c.setFont("Serif", size); self.c.setFillColor(INK)
        words = text.split()
        line = ""
        for w in words:
            t = (line + " " + w).strip()
            if pdfmetrics.stringWidth(t, "Serif", size) > W - 2 * MARGIN:
                self.need(leading)
                self.y -= leading
                self.c.drawString(MARGIN, self.y, line)
                line = w
            else:
                line = t
        if line:
            self.need(leading)
            self.y -= leading
            self.c.drawString(MARGIN, self.y, line)
        self.y -= 5

    def bullets(self, items, size=10.5, leading=15):
        for it in items:
            self.para("•  " + it, size, leading)
        self.y -= 3

    def gap(self, h=8):
        self.y -= h

    def save(self):
        self.c.setFont("Serif", 8); self.c.setFillColor(GRAY)
        self.c.drawCentredString(W / 2, 28, str(self.c.getPageNumber()))
        self.c.save()

# --------------------------------------------------------------------------
# music drawing
# --------------------------------------------------------------------------
def exercise(doc, notes, clef="treble", show_names=True, show_fingers=True):
    """notes: [(letter, octave, dur, finger), ...]; 4/4, barline every 4 beats."""
    doc.need(105)
    c = doc.c
    x0, x1 = MARGIN + 30, W - MARGIN
    yb = doc.y - 70                      # bottom line of the staff
    c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
    for k in range(5):
        c.line(x0, yb + k * LINE, x1, yb + k * LINE)
    c.setFont("Clef", 25 if clef == "treble" else 21); c.setFillColor(INK)
    c.drawString(x0 + 2, yb - 7 if clef == "treble" else yb + 3,
                 "\U0001D11E" if clef == "treble" else "\U0001D122")
    c.setFont("Serif", 12)
    c.drawString(x0 + 30, yb + 12, "4"); c.drawString(x0 + 30, yb + 2, "4")
    left = x0 + 48
    width = x1 - left
    total = sum(d for _, _, d, _ in notes)
    # Uniform baseline for note names, below the lowest notehead or down-stem.
    name_y = yb - 13
    for letter, octave, dur, _ in notes:
        y = staff_y(letter, octave, yb, clef)
        reach = y - (24 if (dur < 4 and y < yb + 2 * LINE) else 8)
        name_y = min(name_y, reach)
    beat = 0.0
    for letter, octave, dur, finger in notes:
        x = left + width * (beat / total) + (width / total) * 0.35
        y = staff_y(letter, octave, yb, clef)
        c.setLineWidth(0.9); c.setStrokeColor(INK)
        draw_ledger(c, x, y, yb)
        draw_notehead(c, x, y, hollow=(dur >= 2))
        if dur < 4:
            up = y < yb + 2 * LINE
            c.line(x + 2.7 if up else x - 2.7, y, x + 2.7 if up else x - 2.7,
                   y + (20 if up else -20))
        if dur in (1.5, 3):
            c.setFillColor(INK)
            c.circle(x + 6.5, y + (STEP if round((y - yb) / STEP) % 2 == 0 else 0), 0.9, fill=1, stroke=0)
        if show_fingers and finger:
            c.setFont("Serif", 8.5); c.setFillColor(ACCENT)
            c.drawCentredString(x, yb + 4 * LINE + 8, str(finger))
        if show_names:
            c.setFont("Serif", 8.5); c.setFillColor(GRAY)
            c.drawCentredString(x, name_y, letter)
        beat += dur
        if abs(beat % 4) < 1e-9 and beat < total:      # barline every 4 beats
            bx = left + width * (beat / total)
            c.setLineWidth(0.55); c.setStrokeColor(HexColor("#222222"))
            c.line(bx, yb, bx, yb + 4 * LINE)
    bx = x1
    c.setLineWidth(0.55); c.line(bx, yb, bx, yb + 4 * LINE)
    c.setLineWidth(2.2); c.line(bx - 3.5, yb, bx - 3.5, yb + 4 * LINE)
    doc.y = min(yb - 28, name_y - 14)

def keyboard_diagram(doc):
    """Two octaves of keys with Middle C marked."""
    doc.need(120)
    c = doc.c
    kw = (W - 2 * MARGIN) / 15            # 15 white keys
    kh = 78
    x0 = MARGIN; y0 = doc.y - 20 - kh
    white = ["C", "D", "E", "F", "G", "A", "B"]
    black_after = {0, 1, 3, 4, 5}         # black key after C,D,F,G,A
    c.setFont("Serif", 9)
    for i in range(15):
        c.setFillColorRGB(1, 1, 1); c.setStrokeColor(INK); c.setLineWidth(0.8)
        c.rect(x0 + i * kw, y0, kw, kh, fill=1, stroke=1)
        if i % 7 == 0:
            c.setFillColor(ACCENT if i == 7 else GRAY)
            c.drawCentredString(x0 + i * kw + kw / 2, y0 + 6, "C")
    for i in range(14):
        if i % 7 in black_after:
            c.setFillColor(INK)
            c.rect(x0 + (i + 1) * kw - kw * 0.3, y0 + kh * 0.42, kw * 0.6, kh * 0.58, fill=1, stroke=0)
    mc = x0 + 7 * kw + kw / 2
    c.setStrokeColor(ACCENT); c.setLineWidth(1.2)
    c.line(mc, y0 - 16, mc, y0 - 2)
    c.setFillColor(ACCENT); c.setFont("Serif", 9.5)
    c.drawCentredString(mc, y0 - 27, "Middle C")
    doc.y = y0 - 40

# --------------------------------------------------------------------------
# the lesson
# --------------------------------------------------------------------------
def build(path):
    register_fonts()
    d = Doc(path)

    d.h1("Day One at the Piano")
    d.c.setFont("SerifItalic", 12); d.c.setFillColor(GRAY)
    d.c.drawString(MARGIN, d.y - 4, "A first lesson for grown-up beginners — about 30 relaxed minutes")
    d.y -= 24
    d.para("Welcome. Today you will sit correctly, find your way around the keys, and play your first "
           "two songs. Nothing more. Learning piano as an adult is not a race — your advantage is "
           "patience and understanding, not speed. Fifteen unhurried minutes a day will carry you "
           "further than an occasional heroic weekend.")

    d.h2("1. Sit well (2 minutes)")
    d.bullets([
        "Sit on the front half of the bench, facing the middle of the keyboard.",
        "Feet flat on the floor, back tall but not stiff — imagine a string lifting the crown of your head.",
        "Elbows slightly in front of your body, forearms roughly level with the keys.",
        "Let your hands rest on the white keys with gently curved fingers, as if holding a small ball. "
        "Play on your fingertips, not the flat of the finger."])

    d.h2("2. Meet the keyboard (3 minutes)")
    d.para("Look at the black keys: they come in groups of two and three. That pattern repeats all the "
           "way up and down the piano, and it is your map. Every white key just left of a group of two "
           "black keys is a C. The C nearest the middle of the piano is Middle C — home base for "
           "everything today.")
    keyboard_diagram(d)
    d.para("White keys are named with seven letters, A B C D E F G, then the pattern repeats. Today "
           "you only need five of them: C D E F G.")

    d.h2("3. Finger numbers (1 minute)")
    d.para("Pianists number the fingers: thumb is 1, index 2, middle 3, ring 4, little finger 5 — same "
           "in both hands. In the exercises below, the small number above each note tells you which "
           "finger to use; the letter below tells you which key to play.")

    d.h2("4. Exercise: right hand five-finger walk (5 minutes)")
    d.para("Place your right thumb (1) on Middle C (C4) and let each finger rest on its own white key: "
           "2 on D, 3 on E, 4 on F, 5 on G. Play up and down slowly, one note per second. Say the "
           "letter names out loud as you play — it feels silly, and it works.")
    exercise(d, [("C",4,1,1),("D",4,1,2),("E",4,1,3),("F",4,1,4),
                 ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
                 ("C",4,4,1)])

    d.h2("5. Exercise: left hand five-finger walk (5 minutes)")
    d.para("Now the left hand, in the bass clef. Place your little finger (5) on the C below Middle C "
           "(C3): 5 on C, 4 on D, 3 on E, 2 on F, thumb (1) on G. Same slow walk, same out-loud "
           "letter names.")
    exercise(d, [("C",3,1,5),("D",3,1,4),("E",3,1,3),("F",3,1,2),
                 ("G",3,1,1),("F",3,1,2),("E",3,1,3),("D",3,1,4),
                 ("C",3,4,5)], clef="bass")

    d.h2("6. Your first song: Hot Cross Buns (5 minutes)")
    d.para("Right hand, same position. This uses only three notes — E, D, C (fingers 3, 2, 1). "
           "The open noteheads last two beats; give them time. If you know the nursery rhyme, hum it "
           "as you play: your ear will tell you when it sounds right.")
    exercise(d, [("E",4,2,3),("D",4,2,2),("C",4,4,1),
                 ("E",4,2,3),("D",4,2,2),("C",4,4,1),
                 ("C",4,1,1),("C",4,1,1),("C",4,1,1),("C",4,1,1),
                 ("D",4,1,2),("D",4,1,2),("D",4,1,2),("D",4,1,2),
                 ("E",4,2,3),("D",4,2,2),("C",4,4,1)])

    d.h2("7. Your second song: Mary Had a Little Lamb (8 minutes)")
    d.para("Four notes now — C, D, E and G (fingers 1, 2, 3, 5). Take it in small bites: learn the "
           "first line alone, repeat it three times, then move on. Slow and correct beats fast and "
           "wobbly, every single time.")
    exercise(d, [("E",4,1,3),("D",4,1,2),("C",4,1,1),("D",4,1,2),
                 ("E",4,1,3),("E",4,1,3),("E",4,2,3),
                 ("D",4,1,2),("D",4,1,2),("D",4,2,2),
                 ("E",4,1,3),("G",4,1,5),("G",4,2,5),
                 ("E",4,1,3),("D",4,1,2),("C",4,1,1),("D",4,1,2),
                 ("E",4,1,3),("E",4,1,3),("E",4,1,3),("E",4,1,3),
                 ("D",4,1,2),("D",4,1,2),("E",4,1,3),("D",4,1,2),
                 ("C",4,4,1)])

    d.h2("8. How to practice from here")
    d.bullets([
        "Little and often: 10–15 minutes daily beats an hour on Sunday.",
        "Hands separately first; only combine when each hand feels easy alone.",
        "Slower than you think. If you make the same mistake twice, halve the speed.",
        "Stop while it still feels good — you will come back tomorrow happier.",
        "Expect fingers to feel clumsy for a week or two. That is not age; that is everyone's day one."])

    d.h2("Tomorrow")
    d.para("Repeat today's two songs until they feel comfortable, then try playing Hot Cross Buns with "
           "the left hand (same notes, one octave lower, fingers 3-2-1). When that is easy, you are "
           "ready for both hands together — day two.")
    d.save()

if __name__ == "__main__":
    out = os.path.join(OUT, "Piano_Day_One_Lesson.pdf")
    build(out)
    print("Created", out)
