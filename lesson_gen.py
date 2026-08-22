#!/usr/bin/env python3
"""lesson_gen — prompt-to-piano-lesson CLI.

Describe a lesson in plain words; an AI CLI writes the lesson as structured
JSON, and the lesson engine renders a printable PDF (text + engraved
exercises) plus an MP3 play-along of the exercises.

Usage:
    python3 lesson_gen.py "introduce the C major chord to an adult beginner"
    python3 lesson_gen.py "G major five-finger position" --title "Day Three" --composer codex
"""
import argparse, json, os, subprocess, sys, tempfile

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
      "exercise": {{"rh": [["E", 4, 1, 3], ...], "lh": [["C", 3, 4, 5], ...]}}  // optional; either hand may be null
    }}
  ]
}}

Rules:
- Audience: an adult absolute beginner. Warm, plain language, short paragraphs. 4-7 sections, 1-4 exercises.
- Exercise notes: ["letter", octave, duration, finger] — letter A-G (sharps/flats only if the lesson teaches them), octave 2-5, duration one of 0.5, 1, 1.5, 2, 3, 4 (quarter note = 1), finger 1-5 (thumb = 1).
- Every exercise's durations must sum to a multiple of 4 beats. Keep hands in five-finger positions (left C2-G2 area, right C4-G5 area).
- Exercises must fit the lesson topic and progress gently.
"""

DURS = {0.5, 1, 1.5, 2, 3, 4}

def validate_hand(notes, where):
    if notes is None:
        return None
    out = []
    total = 0.0
    for item in notes:
        letter, octave, dur, finger = item
        if letter not in "ABCDEFG" or len(letter) != 1:
            raise ValueError(f"{where}: bad letter {letter!r}")
        if not 2 <= int(octave) <= 6:
            raise ValueError(f"{where}: bad octave {octave!r}")
        if float(dur) not in DURS:
            raise ValueError(f"{where}: bad duration {dur!r}")
        if not 1 <= int(finger) <= 5:
            raise ValueError(f"{where}: bad finger {finger!r}")
        out.append((letter, int(octave), float(dur), int(finger)))
        total += float(dur)
    if not out or total % 4 != 0:
        raise ValueError(f"{where}: exercise must total a multiple of 4 beats (got {total})")
    return out

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("lesson must be a JSON object")
    lesson = {"title": str(data.get("title") or "Piano Lesson"),
              "intro": str(data.get("intro") or ""), "sections": []}
    sections = data.get("sections", [])
    if not 3 <= len(sections) <= 10:
        raise ValueError(f"need 3-10 sections, got {len(sections)}")
    n_ex = 0
    for i, s in enumerate(sections):
        sec = {"heading": str(s.get("heading") or f"Part {i+1}"),
               "paragraphs": [str(p) for p in s.get("paragraphs") or []],
               "bullets": [str(b) for b in s.get("bullets") or []],
               "exercise": None}
        ex = s.get("exercise")
        if ex:
            rh = validate_hand(ex.get("rh"), f"section {i+1} rh")
            lh = validate_hand(ex.get("lh"), f"section {i+1} lh")
            if not rh and not lh:
                raise ValueError(f"section {i+1}: exercise has no notes")
            sec["exercise"] = {"rh": rh, "lh": lh}
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
            rh, lh = ex["rh"], ex["lh"]
            if rh and lh:
                grand_exercise(doc, rh, lh)
            elif rh:
                exercise(doc, rh, "treble")
            else:
                exercise(doc, lh, "bass")
            pairs.append((rh, lh))
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
