#!/usr/bin/env python3
"""lesson_gen — prompt-to-piano-lesson CLI.

Describe a lesson in plain words; an AI CLI writes the lesson as structured
JSON, and the lesson engine renders a printable PDF (text + engraved
exercises) plus an MP3 play-along of the exercises.

Usage:
    python3 lesson_gen.py "introduce the C major chord to an adult beginner"
    python3 lesson_gen.py "G major five-finger position" --title "Day Three" --composer codex
"""
import argparse, json, os, re, subprocess, sys, tempfile

import musiclib
from lesson_day_one import Doc, exercise
from lesson_day_two import grand_exercise
from lesson_audio import lesson_score

SCHEMA = """Create a piano lesson from this request: "{prompt}".
Write the result as JSON to the file {path} using your file-writing tool. Do not print the JSON in your reply; just write the file and reply with one line: OK.

JSON schema (strict):
{{
  "title": "short lesson title",
  "intro": "one welcoming paragraph",
  "sections": [
    {{
      "heading": "section heading",
      "paragraphs": ["..."],        // optional
      "bullets": ["..."],           // optional
      "exercise": {{                 // optional
        "time": [3, 4],              // optional, default [4,4]; one of [2,4], [3,4], [4,4]
        "tempo": "Slowly",           // optional text mark shown above the staff
        "dynamic": "p",              // optional: ppp pp p mp mf f ff
        "bpm": 56,                   // optional play-along tempo, 40-120
        "rh": [["E", 4, 1, 3], ...], // either hand may be null
        "lh": [["C", 3, 4, 5], ...]
      }}
    }}
  ]
}}

Hand entries — each hand is a list mixing these forms:
- Note: ["letter", octave, duration, finger] — letter A-G, optionally with # or b (only if the lesson teaches that accidental), octave 2-5, duration one of 0.5, 1, 1.5, 2, 3, 4 (quarter = 1), finger 1-5 (thumb = 1).
- Rest: ["R", duration] — same duration set.
- Chord (real simultaneous notes): {{"chord": [["C", 3], ["E", 3], ["G", 3]], "dur": 4, "fingers": "1-3-5"}} — 2-4 tones within one hand's span; "fingers" optional.

Rules:
- Audience: an adult absolute beginner. Warm, plain language, short paragraphs. 4-7 sections, 1-4 exercises.
- Every exercise's durations must sum to a multiple of the bar length (4 beats in 4/4, 3 in 3/4, 2 in 2/4); no single note may be longer than one bar. Use [3,4] time when the lesson teaches waltz or triple meter. All exercises in one lesson share the same time signature.
- Both hands of one exercise must have equal total beats. Keep hands in five-finger positions (left C2-G2 area, right C4-G5 area) unless the lesson specifically moves beyond them.
- Chords are now supported — prefer genuine chords over broken-chord workarounds when the lesson is about chords. Keep them slow (half or whole notes) for beginners.
- Exercises must fit the lesson topic and progress gently.
"""

DURS = {0.5, 1, 1.5, 2, 3, 4}
LETTER_RE = re.compile(r"^[A-G](#|b)?$")
TIMES = {(2, 4), (3, 4), (4, 4)}

def parse_letter(value, where):
    s = str(value)
    if not LETTER_RE.match(s):
        raise ValueError(f"{where}: bad letter {value!r}")
    return s[0], s[1:]          # (letter, accidental)

def check_dur(dur, where, bar_beats):
    d = float(dur)
    if d not in DURS:
        raise ValueError(f"{where}: bad duration {dur!r}")
    if d > bar_beats:
        raise ValueError(f"{where}: duration {d} longer than a bar")
    return d

def check_finger(finger, where):
    if finger in (None, 0):
        return None
    if not 1 <= int(finger) <= 5:
        raise ValueError(f"{where}: bad finger {finger!r}")
    return int(finger)

def validate_hand(notes, where, bar_beats=4):
    """Returns v2 events: ("note",(letter,acc,octave),dur,finger),
    ("rest",None,dur,None) or ("chord",[(letter,acc,octave),...],dur,fingers)."""
    if notes is None:
        return None
    out = []
    total = 0.0
    for item in notes:
        if isinstance(item, dict) and "chord" in item:
            tones = []
            for t in item["chord"]:
                letter, acc = parse_letter(t[0], where)
                octave = int(t[1])
                if not 2 <= octave <= 6:
                    raise ValueError(f"{where}: bad octave {t[1]!r}")
                tones.append((letter, acc, octave))
            if not 2 <= len(tones) <= 4:
                raise ValueError(f"{where}: chord needs 2-4 tones")
            dur = check_dur(item.get("dur"), where, bar_beats)
            out.append(("chord", tones, dur, str(item.get("fingers") or "") or None))
        elif isinstance(item, (list, tuple)) and str(item[0]).upper() == "R":
            dur = check_dur(item[1], where, bar_beats)
            out.append(("rest", None, dur, None))
        else:
            letter, acc = parse_letter(item[0], where)
            octave = int(item[1])
            if not 2 <= octave <= 6:
                raise ValueError(f"{where}: bad octave {item[1]!r}")
            dur = check_dur(item[2], where, bar_beats)
            finger = check_finger(item[3] if len(item) > 3 else None, where)
            out.append(("note", (letter, acc, octave), dur, finger))
        total += out[-1][2]
    if not out or total % bar_beats != 0:
        raise ValueError(f"{where}: exercise must total a multiple of {bar_beats} beats (got {total})")
    return out

DYN_RE = re.compile(r"^(ppp|pp|p|mp|mf|f|ff)(.*)$")

def validate_meta(ex, where):
    """Optional exercise-level marks: time signature, tempo, dynamic, bpm."""
    t = ex.get("time", [4, 4])
    try:
        time = (int(t[0]), int(t[1]))
    except (TypeError, IndexError, ValueError):
        raise ValueError(f"section {where}: bad time signature {t!r}")
    if time not in TIMES:
        raise ValueError(f"section {where}: time must be [2,4], [3,4] or [4,4]")
    tempo = str(ex.get("tempo") or "")[:40]
    dynamic = str(ex.get("dynamic") or "")
    if dynamic and not DYN_RE.match(dynamic):
        raise ValueError(f"section {where}: bad dynamic {dynamic!r}")
    bpm = ex.get("bpm")
    if bpm is not None and not 40 <= int(bpm) <= 120:
        raise ValueError(f"section {where}: bpm must be 40-120")
    return {"time": time, "tempo": tempo, "dynamic": dynamic,
            "bpm": int(bpm) if bpm else None}

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("lesson must be a JSON object")
    lesson = {"title": str(data.get("title") or "Piano Lesson"),
              "intro": str(data.get("intro") or ""), "sections": []}
    sections = data.get("sections", [])
    if not 3 <= len(sections) <= 10:
        raise ValueError(f"need 3-10 sections, got {len(sections)}")
    n_ex = 0
    lesson_time = None
    for i, s in enumerate(sections):
        sec = {"heading": str(s.get("heading") or f"Part {i+1}"),
               "paragraphs": [str(p) for p in s.get("paragraphs") or []],
               "bullets": [str(b) for b in s.get("bullets") or []],
               "exercise": None}
        ex = s.get("exercise")
        if ex:
            meta = validate_meta(ex, i + 1)
            if lesson_time is None:
                lesson_time = meta["time"]
            elif meta["time"] != lesson_time:
                raise ValueError(f"section {i+1}: all exercises must share one time "
                                 f"signature (first exercise uses {lesson_time})")
            bar_beats = meta["time"][0] * 4 // meta["time"][1]
            rh = validate_hand(ex.get("rh"), f"section {i+1} rh", bar_beats)
            lh = validate_hand(ex.get("lh"), f"section {i+1} lh", bar_beats)
            if not rh and not lh:
                raise ValueError(f"section {i+1}: exercise has no notes")
            if rh and lh:
                tr = sum(e[2] for e in rh)
                tl = sum(e[2] for e in lh)
                if abs(tr - tl) > 1e-9:
                    raise ValueError(f"section {i+1}: hands differ ({tr} vs {tl} beats)")
            sec["exercise"] = {"rh": rh, "lh": lh, "meta": meta}
            n_ex += 1
        if not (sec["paragraphs"] or sec["bullets"] or sec["exercise"]):
            raise ValueError(f"section {i+1} is empty")
        lesson["sections"].append(sec)
    if n_ex == 0:
        raise ValueError("lesson needs at least one exercise")
    return lesson

def generate_with_ai(provider, prompt, json_path, timeout):
    full = SCHEMA.format(prompt=prompt, path=json_path)
    for attempt in (1, 2):
        if os.path.exists(json_path):
            os.remove(json_path)
        if provider == "kimi":
            cmd = ["kimi", "-p", full]
        else:
            cmd = ["codex", "exec", "--ephemeral", "-C",
                   os.path.dirname(os.path.abspath(__file__)), full]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if not os.path.exists(json_path):
            if attempt == 2:
                raise RuntimeError(f"{provider} did not write the lesson file. Output:\n"
                                   + (proc.stdout + proc.stderr)[-500:])
            full += ("\n\nPrevious attempt failed: do not inspect or explain. Immediately "
                     "WRITE THE JSON FILE at the exact path with your file tool, then reply OK.")
            continue
        try:
            return validate(json.load(open(json_path)))
        except (json.JSONDecodeError, ValueError, KeyError, TypeError, IndexError) as e:
            if attempt == 2:
                raise RuntimeError(f"invalid lesson after retry: {e}")
            full = SCHEMA.format(prompt=prompt, path=json_path) + \
                   f"\n\nPrevious attempt failed validation: {e}. Fix it and write the file again."

def render(lesson, basename, audio=True):
    musiclib.register_fonts()
    pdf = basename + ".pdf"
    doc = Doc(pdf)
    doc.h1(lesson["title"])
    if lesson["intro"]:
        doc.para(lesson["intro"])
    pairs = []
    for sec in lesson["sections"]:
        doc.h2(sec["heading"])
        for p in sec["paragraphs"]:
            doc.para(p)
        if sec["bullets"]:
            doc.bullets(sec["bullets"])
        ex = sec["exercise"]
        if ex:
            rh, lh, meta = ex["rh"], ex["lh"], ex["meta"]
            marks = {"time": meta["time"], "tempo": meta["tempo"] or None,
                     "dynamic": meta["dynamic"] or None}
            if rh and lh:
                grand_exercise(doc, rh, lh, **marks)
            elif rh:
                exercise(doc, rh, "treble", **marks)
            else:
                exercise(doc, lh, "bass", **marks)
            pairs.append((rh, lh, meta))
    doc.save()
    made = [pdf]
    if audio and pairs:
        score = lesson_score(lesson["title"], pairs)
        wav = basename + ".wav"
        musiclib.render_audio(score, wav)
        mp3 = basename + ".mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                        "-codec:a", "libmp3lame", "-q:a", "3", mp3], check=True)
        os.remove(wav)
        made.append(mp3)
    return made

def main():
    ap = argparse.ArgumentParser(description="Generate a piano lesson from a text prompt.")
    ap.add_argument("prompt")
    ap.add_argument("--title")
    ap.add_argument("--out", help="output basename (default: Piano_Lesson in the lessons share)")
    ap.add_argument("--composer", choices=("kimi", "codex"), default="kimi")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    default_dir = "/srv/files/piano/lessons"
    if not (os.path.isdir(default_dir) and os.access(default_dir, os.W_OK)):
        default_dir = "."
    basename = args.out or os.path.join(default_dir, "Piano_Lesson")

    with tempfile.TemporaryDirectory() as tmp:
        json_path = os.path.join(tmp, "lesson.json")
        print(f"Writing lesson with {args.composer.title()}...", flush=True)
        lesson = generate_with_ai(args.composer, args.prompt, json_path, args.timeout)
    if args.title:
        lesson["title"] = args.title
    made = render(lesson, basename, audio=not args.no_audio)
    for f in made:
        print("created:", f)

if __name__ == "__main__":
    main()
