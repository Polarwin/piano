#!/usr/bin/env python3
"""Reviewed, simplified public-domain melodies for the lesson course.

The AI writes lesson *text*; the notes for named famous themes come from here,
deterministically, so the printed score and MP3 always match the curriculum's
promise. All data is v2 events (see lesson_day_one.as_events), simplified to
beginner level per CURRICULUM.md (five-finger positions, one note at a time
per hand except slow chords).

Run `python3 melodies.py` to self-check bar totals.
"""
import re

def N(name, dur, finger=None):
    """Note: N("F#4", 1, 3) -> v2 note event."""
    m = re.match(r"^([A-G])(#|b)?(\d)$", name)
    if not m:
        raise ValueError(f"bad note {name!r}")
    return ("note", (m.group(1), m.group(2) or "", int(m.group(3))), float(dur), finger)

def R(dur):
    return ("rest", None, float(dur), None)

def CH(names, dur, fingers=None):
    """Chord: CH("C3 E3 G3", 4, "5-3-1") -> v2 chord event."""
    return ("chord", [(t[0], t[1:-1], int(t[-1])) for t in names.split()],
            float(dur), fingers)

# --- chord shorthands (left hand, root position) ---------------------------
C_ = ("C3 E3 G3", "5-3-1"); G_ = ("G2 B2 D3", "5-3-1"); F_ = ("F2 A2 C3", "5-3-1")
AM = ("A2 C3 E3", "5-3-1"); EM = ("E2 G2 B2", "5-3-1"); DM = ("D3 F#3 A3", "5-3-1")

def LH(chords, dur):
    """Whole/dotted-half chord per bar: LH([C_, G_], 4)."""
    return [CH(names, dur, fingers) for names, fingers in chords]

MELODIES = {
    # Beethoven — Ode to Joy, melody only (treble reading)
    "ode_to_joy": {
        "time": (4, 4), "bpm": 66,
        "rh": [N("E4",1,3),N("E4",1,3),N("F4",1,4),N("G4",1,5),
               N("G4",1,5),N("F4",1,4),N("E4",1,3),N("D4",1,2),
               N("C4",1,1),N("C4",1,1),N("D4",1,2),N("E4",1,3),
               N("E4",1.5,3),N("D4",0.5,2),N("D4",2,2),
               N("E4",1,3),N("E4",1,3),N("F4",1,4),N("G4",1,5),
               N("G4",1,5),N("F4",1,4),N("E4",1,3),N("D4",1,2),
               N("C4",1,1),N("C4",1,1),N("D4",1,2),N("E4",1,3),
               N("D4",1.5,2),N("C4",0.5,1),N("C4",2,1)],
        "lh": None},
    # Ode to Joy with simple chord accompaniment (Day 14 song)
    "ode_to_joy_chords": {
        "time": (4, 4), "bpm": 66,
        "rh": [N("E4",1,3),N("E4",1,3),N("F4",1,4),N("G4",1,5),
               N("G4",1,5),N("F4",1,4),N("E4",1,3),N("D4",1,2),
               N("C4",1,1),N("C4",1,1),N("D4",1,2),N("E4",1,3),
               N("E4",1.5,3),N("D4",0.5,2),N("D4",2,2),
               N("E4",1,3),N("E4",1,3),N("F4",1,4),N("G4",1,5),
               N("G4",1,5),N("F4",1,4),N("E4",1,3),N("D4",1,2),
               N("C4",1,1),N("C4",1,1),N("D4",1,2),N("E4",1,3),
               N("D4",1.5,2),N("C4",0.5,1),N("C4",2,1)],
        "lh": LH([C_, C_, C_, G_, C_, C_, G_, C_], 4)},
    # Ode to Joy transposed to the bass C position (bass reading)
    "ode_to_joy_bass": {
        "time": (4, 4), "bpm": 60,
        "rh": None,
        "lh": [N("E3",1,3),N("E3",1,3),N("F3",1,2),N("G3",1,1),
               N("G3",1,1),N("F3",1,2),N("E3",1,3),N("D3",1,4),
               N("C3",1,5),N("C3",1,5),N("D3",1,4),N("E3",1,3),
               N("E3",1.5,3),N("D3",0.5,4),N("D3",2,4),
               N("E3",1,3),N("E3",1,3),N("F3",1,2),N("G3",1,1),
               N("G3",1,1),N("F3",1,2),N("E3",1,3),N("D3",1,4),
               N("C3",1,5),N("C3",1,5),N("D3",1,4),N("E3",1,3),
               N("D3",1.5,4),N("C3",0.5,5),N("C3",2,5)]},
    # Mozart — Twinkle theme (rhythm values)
    "twinkle": {
        "time": (4, 4), "bpm": 72,
        "rh": [N("C4",1,1),N("C4",1,1),N("G4",1,5),N("G4",1,5),
               N("A4",1,5),N("A4",1,5),N("G4",2,4),
               N("F4",1,4),N("F4",1,4),N("E4",1,3),N("E4",1,3),
               N("D4",1,2),N("D4",1,2),N("C4",2,1),
               N("G4",1,4),N("G4",1,4),N("F4",1,3),N("F4",1,3),
               N("E4",1,2),N("E4",1,2),N("D4",2,1),
               N("C4",1,1),N("C4",1,1),N("G4",1,5),N("G4",1,5),
               N("A4",1,5),N("A4",1,5),N("G4",2,4)],
        "lh": None},
    # Beethoven — Fifth Symphony "fate" motif, adapted in C (rests)
    "beethoven_fifth": {
        "time": (4, 4), "bpm": 76,
        "rh": [N("G4",0.5,5),N("G4",0.5,5),N("G4",0.5,5),R(0.5),N("E4",2,3),
               N("F4",0.5,4),N("F4",0.5,4),N("F4",0.5,4),R(0.5),N("D4",2,2),
               N("G4",0.5,5),N("G4",0.5,5),N("G4",0.5,5),R(0.5),N("E4",2,3),
               N("F4",0.5,4),N("F4",0.5,4),N("F4",0.5,4),R(0.5),N("D4",2,2)],
        "lh": None},
    # Haydn — Surprise Symphony theme, simplified (dynamics p/f)
    "surprise": {
        "time": (4, 4), "bpm": 66,
        "rh": [N("C4",1,1),N("C4",1,1),N("E4",1,3),N("E4",1,3),
               N("G4",1,5),N("G4",1,5),N("E4",2,3),
               N("F4",1,4),N("F4",1,4),N("E4",1,3),N("E4",1,3),
               N("D4",1,2),N("D4",1,2),N("C4",2,1),
               N("C4",1,1),N("C4",1,1),N("E4",1,3),N("E4",1,3),
               N("G4",1,5),N("G4",1,5),N("E4",2,3),
               N("F4",1,4),N("F4",1,4),N("E4",1,3),N("E4",1,3),
               N("D4",1,2),N("D4",1,2),N("C4",2,1)],
        "lh": None},
    # After Mozart — Eine kleine Nachtmusik (staccato vs legato)
    "eine_kleine": {
        "time": (4, 4), "bpm": 88,
        "rh": [N("C4",1,1),N("E4",1,3),N("G4",1,5),N("E4",1,3),
               N("F4",1,4),N("E4",1,3),N("D4",1,2),N("C4",1,1),
               N("C4",1,1),N("E4",1,3),N("G4",1,5),N("E4",1,3),
               N("D4",1,2),N("D4",1,2),N("C4",2,1)],
        "lh": None},
    # Beethoven — Für Elise opening motif (A minor)
    "fur_elise": {
        "time": (4, 4), "bpm": 60,
        "rh": [N("E5",0.5,5),N("D#5",0.5,4),N("E5",0.5,5),N("D#5",0.5,4),
               N("E5",0.5,5),N("B4",0.5,2),N("D5",0.5,4),N("C5",0.5,3),
               N("A4",4,1),
               N("E5",0.5,5),N("D#5",0.5,4),N("E5",0.5,5),N("D#5",0.5,4),
               N("E5",0.5,5),N("B4",0.5,2),N("D5",0.5,4),N("C5",0.5,3),
               N("A4",4,1)],
        "lh": LH([AM, AM, AM, AM], 4)},
    # Brahms — Lullaby / Wiegenlied (3/4), um-pah-pah left hand
    "brahms_lullaby": {
        "time": (3, 4), "bpm": 60,
        "rh": [N("E4",1,3),N("E4",1,3),N("G4",1,5),
               N("E4",1,3),N("E4",1,3),N("G4",1,5),
               N("E4",1,3),N("G4",2,5),
               N("G4",1,5),N("F4",1,4),N("E4",1,3),
               N("F4",1,4),N("E4",1,3),N("D4",1,2),
               N("D4",1,2),N("E4",1,3),N("F4",1,4),
               N("E4",1,3),N("D4",1,2),N("C4",1,1),
               N("C4",3,1)],
        "lh": [N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("G2",1,5),CH("B2 D3",1,"3-1"),CH("B2 D3",1,"3-1"),
               N("G2",1,5),CH("B2 D3",1,"3-1"),CH("B2 D3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1")]},
    # Bach/Petzold — Minuet in G, opening phrase (3/4)
    "minuet_in_g": {
        "time": (3, 4), "bpm": 72,
        "rh": [N("D5",1,5),N("G4",0.5,1),N("A4",0.5,2),N("B4",0.5,3),N("C5",0.5,4),
               N("D5",1,5),N("G4",1,1),N("G4",1,1),
               N("E5",1,4),N("C5",0.5,1),N("D5",0.5,2),N("E5",0.5,3),N("F#5",0.5,4),
               N("G5",2,5),N("G4",1,1)],
        "lh": LH([G_, C_, DM, G_], 3)},
    # Pachelbel — Canon progression in C (broken-chord accompaniment day)
    "canon_in_c": {
        "time": (4, 4), "bpm": 56,
        "rh": [N("E4",4,3),N("D4",4,2),N("C4",4,1),N("E4",4,3),
               N("F4",4,4),N("G4",4,5),N("A4",4,4),N("B4",4,5)],
        "lh": LH([C_, G_, AM, EM, F_, C_, F_, G_], 4)},
    # Traditional — Amazing Grace (melody over held chords)
    "amazing_grace": {
        "time": (4, 4), "bpm": 56,
        "rh": [N("C4",1,1),N("F4",1.5,4),N("A4",0.5,5),N("G4",1,4),
               N("F4",2,4),N("A4",1,5),N("F4",1,4),
               N("A4",1,5),N("C5",1.5,5),N("A4",0.5,4),N("F4",1,2),
               N("G4",2,4),N("F4",2,3),
               N("F4",1,4),N("D4",1,2),N("C4",2,1),
               N("C4",4,1)],
        "lh": LH([F_, F_, F_, C_, F_, C_], 4)},
    # After Schumann — Träumerei opening phrase, simplified (expressive shaping)
    "traumerei": {
        "time": (4, 4), "bpm": 52,
        "rh": [N("C5",2,5),N("A4",1,3),N("F4",1,1),
               N("A4",1.5,3),N("G4",0.5,2),N("F4",2,1),
               N("E4",2,1),N("G4",1,2),N("C5",1,5),
               N("A4",1.5,3),N("G4",0.5,2),N("F4",2,1)],
        "lh": LH([F_, F_, C_, F_], 4)},
    # After Brahms — Waltz Op. 39 No. 15, simplified (3/4)
    "brahms_waltz": {
        "time": (3, 4), "bpm": 66,
        "rh": [N("G4",1,1),N("C5",1,3),N("E5",1,5),
               N("D5",1,4),N("C5",1,3),N("B4",1,2),
               N("A4",1,1),N("C5",1,3),N("E5",1,5),
               N("D5",1,4),N("B4",1,2),N("G4",1,1),
               N("G4",1,1),N("C5",1,3),N("E5",1,5),
               N("D5",1,4),N("C5",1,3),N("B4",1,2),
               N("A4",1,1),N("B4",1,2),N("C5",1,3),
               N("C5",3,3)],
        "lh": [N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("G2",1,5),CH("B2 D3",1,"3-1"),CH("B2 D3",1,"3-1"),
               N("A2",1,5),CH("C3 E3",1,"3-1"),CH("C3 E3",1,"3-1"),
               N("G2",1,5),CH("B2 D3",1,"3-1"),CH("B2 D3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1"),
               N("G2",1,5),CH("B2 D3",1,"3-1"),CH("B2 D3",1,"3-1"),
               N("F2",1,5),CH("A2 C3",1,"3-1"),CH("A2 C3",1,"3-1"),
               N("C3",1,5),CH("E3 G3",1,"3-1"),CH("E3 G3",1,"3-1")]},
    # G major scale, one octave up and down (with F#)
    "g_major_scale": {
        "time": (4, 4), "bpm": 60,
        "rh": [N("G4",1,1),N("A4",1,2),N("B4",1,3),N("C5",1,1),
               N("D5",1,2),N("E5",1,3),N("F#5",1,4),N("G5",1,5),
               N("G5",1,5),N("F#5",1,4),N("E5",1,3),N("D5",1,2),
               N("C5",1,1),N("B4",1,3),N("A4",1,2),N("G4",1,1)],
        "lh": None},
}

def check():
    ok = True
    for key, m in MELODIES.items():
        beats = m["time"][0] * 4 // m["time"][1]
        for hand in ("rh", "lh"):
            evs = m.get(hand)
            if not evs:
                continue
            total = sum(ev[2] for ev in evs)
            if total % beats:
                print(f"{key} {hand}: {total} beats is not a multiple of {beats}")
                ok = False
        if m.get("rh") and m.get("lh"):
            tr = sum(ev[2] for ev in m["rh"])
            tl = sum(ev[2] for ev in m["lh"])
            if tr != tl:
                print(f"{key}: hands differ ({tr} vs {tl})")
                ok = False
    print("all melodies OK" if ok else "ERRORS above")
    return ok

if __name__ == "__main__":
    import sys
    sys.exit(0 if check() else 1)
