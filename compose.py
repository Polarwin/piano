#!/usr/bin/env python3
"""compose — prompt-to-music CLI.

Describe a piano piece in plain words; the selected AI CLI composes it as
structured JSON, and musiclib renders sheet music (PDF), MIDI and audio
(WAV/MP3).

Usage:
    python3 compose.py "a dreamy waltz in F major, slow and gentle"
    python3 compose.py "sad nocturne in A minor" --title "Night Rain" --bars 24
    python3 compose.py "happy ragtime" --no-audio --keep-json

Requires a logged-in `kimi` or `codex` CLI for composition, and ffmpeg for MP3
(optional; WAV is always produced).
"""
import argparse, json, os, re, subprocess, sys, tempfile

import musiclib

SCHEMA = """Compose an original solo piano piece from this description: "{prompt}".
{constraints}
Write the result as JSON to the file {path} using your file-writing tool. Do not print the JSON in your reply; just write the file and reply with one line: OK.

The JSON schema (strict):
{{
  "title": "short evocative title",
  "subtitle": "for piano solo",
  "key_sig": -7..7 (circle of fifths: 0 = C major/A minor, 1 = G major/E minor, -1 = F major/D minor, etc.),
  "minor": true/false,
  "time": [4,4] or [3,4],
  "bpm": 40..160,
  "tempo_mark": "Italian tempo/expression marking, e.g. Andantino amoroso",
  "accompaniment": "flowing" (8th-note broken chords, ballad style) | "alberti" | "waltz" (3/4 only) | "chords" (half-note bass+chord),
  "sections": [{{"bar": 0, "name": "A", "dynamic": "p dolce"}}, ...] (bar = 0-based index where each section starts; dynamics from ppp..ff with an expression word),
  "bars": [{{"chord": "C", "melody": [["E5", 1], ["D5", 0.5], ...]}}, ...]
}}

Rules:
- melody note names like "C5", "F#4", "Bb3" (middle C = C4); keep the right hand between G4 and C6.
- durations are in quarter notes; allowed values: 0.5, 1, 1.5, 2, 3, 4.
- the melody durations in every bar must sum to exactly the bar length (4 for 4/4, 3 for 3/4).
- chords: root plus optional quality (C, Am, G7, Cmaj7, Dm7, F#dim, Asus4, Cadd9...) and optional slash bass (G/B). Left hand is generated automatically from the chord symbols — do not write left-hand notes.
- use only notes that fit the chosen key signature; accidentals outside the key are fine sparingly.
- make it musical: clear phrases, mostly stepwise melody with a few leaps, a climactic section around 2/3 through, and a proper cadence at the end.
- write exactly {bars} bars with 3-5 sections (A, A', B, A'', Coda or similar)."""

def slugify(text):
    s = re.sub(r"[^\w\s-]", "", text).strip().replace(" ", "_")
    return re.sub(r"_+", "_", s) or "composition"

def compose_with_ai(provider, prompt, bars, json_path, constraints, timeout):
    full = SCHEMA.format(prompt=prompt, constraints=constraints,
                         path=json_path, bars=bars)
    for attempt in (1, 2):
        if os.path.exists(json_path):
            os.remove(json_path)
        if provider == "kimi":
            command = ["kimi", "-p", full]
        else:
            command = ["codex", "exec", "--ephemeral", "-C",
                       os.path.dirname(os.path.abspath(__file__)), full]
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=timeout)
        if not os.path.exists(json_path):
            err = (proc.stdout + proc.stderr)[-500:]
            if attempt == 2:
                raise RuntimeError(f"{provider} did not write the score file. Output:\n" + err)
            full += ("\n\nPrevious attempt failed: do not inspect or explain. "
                     "Immediately WRITE THE JSON FILE at the exact path with your file tool, "
                     "validate every bar, then reply OK.")
            continue
        try:
            data = json.load(open(json_path))
            return musiclib.build_score(data)
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            if attempt == 2:
                raise RuntimeError(f"invalid score after retry: {e}")
            full = SCHEMA.format(prompt=prompt, constraints=constraints,
                                 path=json_path, bars=bars) + \
                   f"\n\nPrevious attempt failed validation: {e}. Fix it and write the file again."

def main():
    ap = argparse.ArgumentParser(description="Compose piano music from a text prompt.")
    ap.add_argument("prompt", help="description of the piece, e.g. 'a dreamy waltz in F major'")
    ap.add_argument("--title", help="override the generated title (also sets output filenames)")
    ap.add_argument("--bars", type=int, default=32, help="number of bars, 8-64 (default 32; 32 bars at ~70bpm ≈ 2 min)")
    ap.add_argument("--constraints", default="",
                    help="extra composition constraints appended to the prompt")
    ap.add_argument("--composer", choices=("kimi", "codex"), default="kimi",
                    help="AI CLI used to compose the score (default: kimi)")
    ap.add_argument("--out", help="output basename (default: slugified title)")
    ap.add_argument("--no-audio", action="store_true", help="skip WAV/MP3 rendering")
    ap.add_argument("--keep-json", action="store_true", help="keep the intermediate score JSON")
    ap.add_argument("--timeout", type=int, default=600, help="AI CLI timeout in seconds")
    args = ap.parse_args()

    if not 8 <= args.bars <= 64:
        ap.error("--bars must be between 8 and 64")

    basename = args.out or slugify(args.title or "composition")
    if not os.path.dirname(basename):
        outdir = "/srv/files/piano"
        if not (os.path.isdir(outdir) and os.access(outdir, os.W_OK)):
            outdir = "."
        basename = os.path.join(outdir, basename)

    with tempfile.TemporaryDirectory() as tmp:
        json_path = os.path.join(tmp, "score.json")
        print(f"Composing {args.bars} bars with {args.composer.title()}...", flush=True)
        score = compose_with_ai(args.composer, args.prompt, args.bars, json_path,
                                args.constraints, args.timeout)
        if not args.out:
            basename = os.path.join(os.path.dirname(basename), slugify(score["title"]))
        if args.keep_json:
            keep = basename + ".json"
            with open(keep, "w") as f:
                json.dump(json.load(open(json_path)), f, indent=1, ensure_ascii=False)
            print(f"score JSON kept at {keep}")

    if args.title:
        score["title"] = args.title
    print(f"Rendering '{score['title']}' ({len(score['bars'])} bars, "
          f"{score['time'][0]}/{score['time'][1]}, q={score['bpm']})...", flush=True)
    made = musiclib.render_all(score, basename, audio=not args.no_audio)
    for f in made:
        print("created:", f)

if __name__ == "__main__":
    main()
