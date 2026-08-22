#!/usr/bin/env python3
"""Render the Day One / Day Two lesson exercises as MP3 play-along audio.

One MP3 per lesson: exercises in book order, steady teaching tempo,
one bar of silence between exercises.
"""
import os, subprocess
import musiclib

OUT = "/srv/files/piano/lessons" if os.path.isdir("/srv/files/piano/lessons") and os.access("/srv/files/piano/lessons", os.W_OK) else os.path.dirname(os.path.abspath(__file__))

# --- lesson note data (letter, octave, dur, finger) — mirrors the books ----
RH_WALK = [("C",4,1,1),("D",4,1,2),("E",4,1,3),("F",4,1,4),
           ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),("C",4,4,1)]
LH_WALK = [("C",3,1,5),("D",3,1,4),("E",3,1,3),("F",3,1,2),
           ("G",3,1,1),("F",3,1,2),("E",3,1,3),("D",3,1,4),("C",3,4,5)]
HCB = [("E",4,2,3),("D",4,2,2),("C",4,4,1),
       ("E",4,2,3),("D",4,2,2),("C",4,4,1),
       ("C",4,1,1),("C",4,1,1),("C",4,1,1),("C",4,1,1),
       ("D",4,1,2),("D",4,1,2),("D",4,1,2),("D",4,1,2),
       ("E",4,2,3),("D",4,2,2),("C",4,4,1)]
MARY = [("E",4,1,3),("D",4,1,2),("C",4,1,1),("D",4,1,2),
        ("E",4,1,3),("E",4,1,3),("E",4,2,3),
        ("D",4,1,2),("D",4,1,2),("D",4,2,2),
        ("E",4,1,3),("G",4,1,5),("G",4,2,5),
        ("E",4,1,3),("D",4,1,2),("C",4,1,1),("D",4,1,2),
        ("E",4,1,3),("E",4,1,3),("E",4,1,3),("E",4,1,3),
        ("D",4,1,2),("D",4,1,2),("E",4,1,3),("D",4,1,2),
        ("C",4,4,1)]
ODE_RH = [("E",4,1,3),("E",4,1,3),("F",4,1,4),("G",4,1,5),
          ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
          ("C",4,1,1),("C",4,1,1),("D",4,1,2),("E",4,1,3),
          ("E",4,1.5,3),("D",4,0.5,2),("D",4,2,2),
          ("E",4,1,3),("E",4,1,3),("F",4,1,4),("G",4,1,5),
          ("G",4,1,5),("F",4,1,4),("E",4,1,3),("D",4,1,2),
          ("C",4,1,1),("C",4,1,1),("D",4,1,2),("E",4,1,3),
          ("D",4,1.5,2),("C",4,0.5,1),("C",4,2,1)]
ODE_LH = [("C",3,4,5),("C",3,4,5),("C",3,4,5),("G",2,4,1),
          ("C",3,4,5),("C",3,4,5),("G",2,4,1),("C",3,4,5)]
HCB_LH = [("C",3,4,5)] * 8
REST = []

def to_midi(notes):
    return [(musiclib.midi_note(f"{l}{o}"), d) for l, o, d, _ in notes]

def chunk(notes, beats=4):
    """Split (midi, dur) list into bars of `beats`; ([notes], dur) for lh=None means rh."""
    bars, cur, total = [], [], 0.0
    for n, d in notes:
        cur.append((n, d)); total += d
        if abs(total - beats) < 1e-9:
            bars.append(cur); cur, total = [], 0.0
    assert not cur, f"last bar incomplete ({total} beats)"
    return bars

def chunk_lh(notes, beats=4):
    return [[([n], d) for n, d in bar] for bar in chunk(notes, beats)]

def lesson_score(title, exercises, bpm=66):
    """exercises: [(rh_notes, lh_notes), ...]; None = silent hand."""
    bars = []
    for k, (rh, lh) in enumerate(exercises):
        if k:
            bars.append({"rh": [], "lh": []})          # one bar of silence
        rh_bars = chunk(to_midi(rh)) if rh else []
        lh_bars = chunk_lh(to_midi(lh)) if lh else []
        n = max(len(rh_bars), len(lh_bars))
        for i in range(n):
            bars.append({"rh": rh_bars[i] if i < len(rh_bars) else [],
                         "lh": lh_bars[i] if i < len(lh_bars) else []})
    return {"title": title, "bpm": bpm, "rit": False, "time": (4, 4),
            "sections": [{"bar": 0, "name": "", "dynamic": "mp"}], "bars": bars}

def render(title, exercises, out_name):
    score = lesson_score(title, exercises)
    wav = os.path.join(OUT, out_name + ".wav")
    dur = musiclib.render_audio(score, wav)
    mp3 = os.path.join(OUT, out_name + ".mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                    "-codec:a", "libmp3lame", "-q:a", "3", mp3], check=True)
    os.remove(wav)
    print(f"{mp3}  ({dur:.0f}s)")

if __name__ == "__main__":
    render("Piano Day One Lesson",
           [(RH_WALK, None), (None, LH_WALK), (HCB, None), (MARY, None)],
           "Piano_Day_One_Lesson")
    render("Piano Day Two Lesson",
           [(RH_WALK, LH_WALK), (HCB, HCB_LH), (ODE_RH, ODE_LH)],
           "Piano_Day_Two_Lesson")
