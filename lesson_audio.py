#!/usr/bin/env python3
"""Render the Day One / Day Two lesson exercises as MP3 play-along audio.

One MP3 per lesson: exercises in book order, steady teaching tempo,
one bar of silence between exercises.
"""
import os, subprocess
import musiclib
from lesson_day_one import as_events

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
ODE_LH = [("C",3,4,5),("C",3,4,5),("C",3,4,5),("G",3,4,1),
          ("C",3,4,5),("C",3,4,5),("G",3,4,1),("C",3,4,5)]
HCB_LH = [("C",3,4,5)] * 8
REST = []

def to_midi(notes):
    """v1 tuples or v2 events -> (midi | [midi, ...] | None, dur) list."""
    out = []
    evs = as_events(notes)
    skip_attack = False
    for i, (kind, payload, dur, label) in enumerate(evs):
        if skip_attack:
            out.append((None, dur))
            skip_attack = False
            continue
        if kind == "rest":
            out.append((None, dur))
        elif kind == "chord":
            out.append(([musiclib.midi_note(f"{l}{a}{o}") for l, a, o in payload], dur))
        else:
            l, a, o = payload
            note = musiclib.midi_note(f"{l}{a}{o}")
            tied = isinstance(label, tuple) and label[1]
            if tied and i + 1 < len(evs) and evs[i + 1][0] == "note" \
                    and evs[i + 1][1] == payload:
                out.append((note, dur, dur + evs[i + 1][2]))
                skip_attack = True
            else:
                out.append((note, dur))
    return out

def chunk(notes, beats=4, pickup=0):
    """Split (group, dur) list into bars of `beats`."""
    bars, cur, total = [], [], 0.0
    target = pickup or beats
    for ev in notes:
        n, d = ev[:2]
        cur.append(ev); total += d
        if abs(total - target) < 1e-9:
            bars.append(cur); cur, total = [], 0.0
            target = beats
    if cur and pickup and abs(total - (beats - pickup)) < 1e-9:
        bars.append(cur); cur = []
    assert not cur, f"last bar incomplete ({total} beats)"
    return bars

def chunk_hand(notes, beats=4, pickup=0):
    """Wrap single notes/rests as groups so both hands share one shape."""
    out = []
    for bar in chunk(notes, beats, pickup):
        converted = []
        for ev in bar:
            n, d = ev[:2]
            group = n if isinstance(n, (list, tuple)) or n is None else [n]
            converted.append((group, d, ev[2]) if len(ev) > 2 else (group, d))
        out.append(converted)
    return out

def lesson_score(title, exercises, bpm=66):
    """exercises: [(rh_notes, lh_notes, meta), ...]; None = silent hand.
    meta may carry time=(num, den), bpm, dynamic."""
    metas = [ex[2] for ex in exercises if len(ex) > 2 and ex[2]]
    time = tuple(metas[0]["time"]) if metas and metas[0].get("time") else (4, 4)
    bpm = int(metas[0]["bpm"]) if metas and metas[0].get("bpm") else bpm
    beats = time[0] * 4 / time[1]
    bars, sections = [], []
    for k, ex in enumerate(exercises):
        rh, lh = ex[0], ex[1]
        meta = ex[2] if len(ex) > 2 else {}
        if k:
            bars.append({"rh": [], "lh": []})          # one bar of silence
        if meta.get("dynamic"):
            sections.append({"bar": len(bars), "name": "", "dynamic": meta["dynamic"]})
        pickup = float(meta.get("pickup", 0) or 0)
        rh_bars = chunk_hand(to_midi(rh), beats, pickup) if rh else []
        lh_bars = chunk_hand(to_midi(lh), beats, pickup) if lh else []
        n = max(len(rh_bars), len(lh_bars))
        for i in range(n):
            hand_bar = (rh_bars[i] if i < len(rh_bars) else
                        lh_bars[i] if i < len(lh_bars) else [])
            duration = sum(ev[1] for ev in hand_bar) or beats
            bars.append({"rh": rh_bars[i] if i < len(rh_bars) else [],
                         "lh": lh_bars[i] if i < len(lh_bars) else [],
                         "_beats": duration})
    return {"title": title, "bpm": bpm, "rit": False, "time": time,
            "sections": sections or [{"bar": 0, "name": "", "dynamic": "mp"}],
            "bars": bars}

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
