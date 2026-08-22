#!/usr/bin/env python3
"""Render reviewed, simplified two-hand pieces for the music library.

The right hand carries the melody and musiclib derives a playable left-hand
accompaniment from the reviewed chord progression.  These arrangements are
course editions, not replacements for the cited historical/source editions.
"""
import argparse
import os
from pathlib import Path

import musiclib


LIBRARY = Path("/srv/files/piano/library")

AMAZING_GRACE = {
    "title": "Amazing Grace",
    "subtitle": "Traditional — simplified for piano solo, two hands",
    "key_sig": -1,
    "minor": False,
    "time": [3, 4],
    "bpm": 60,
    "tempo_mark": "Gently",
    "accompaniment": "waltz",
    "sections": [
        {"bar": 0, "name": "Verse", "dynamic": "mp"},
        {"bar": 8, "name": "With warmth", "dynamic": "mf"},
        {"bar": 14, "name": "calando", "dynamic": "p"},
    ],
    # A simplified F-major setting derived from the traditional tune. The
    # melody omits ornamental notes so an early learner can keep a steady 3/4.
    "bars": [
        {"chord": "F",  "melody": [["C4", 1], ["F4", 2]]},
        {"chord": "F",  "melody": [["F4", 1.5], ["A4", .5], ["G4", .5], ["F4", .5]]},
        {"chord": "F",  "melody": [["A4", 2], ["G4", 1]]},
        {"chord": "Bb", "melody": [["F4", 2], ["D4", 1]]},
        {"chord": "F",  "melody": [["C4", 2], ["C4", .5], ["F4", .5]]},
        {"chord": "F",  "melody": [["F4", 1.5], ["A4", .5], ["G4", .5], ["F4", .5]]},
        {"chord": "C",  "melody": [["A4", 2], ["G4", .5], ["A4", .5]]},
        {"chord": "C7", "melody": [["C5", 3]]},
        {"chord": "F",  "melody": [["C5", 2], ["A4", .5], ["C5", .5]]},
        {"chord": "F",  "melody": [["C5", 1.5], ["A4", .5], ["G4", .5], ["F4", .5]]},
        {"chord": "F",  "melody": [["A4", 2], ["G4", 1]]},
        {"chord": "Bb", "melody": [["F4", 2], ["D4", 1]]},
        {"chord": "F",  "melody": [["C4", 2], ["C4", .5], ["F4", .5]]},
        {"chord": "C",  "melody": [["F4", 1.5], ["A4", .5], ["G4", .5], ["F4", .5]]},
        {"chord": "F",  "melody": [["A4", 2], ["G4", 1]]},
        {"chord": "F",  "melody": [["F4", 3]]},
    ],
}

TWINKLE = {
    "title": "Twinkle, Twinkle, Little Star",
    "subtitle": "After Mozart's theme — simplified for piano solo, two hands",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 72,
    "tempo_mark": "Simply", "accompaniment": "chords",
    "sections": [{"bar": 0, "name": "Theme", "dynamic": "mp"},
                 {"bar": 8, "name": "Return", "dynamic": "mf"}],
    "bars": [
        {"chord": "C", "melody": [["C4",1],["C4",1],["G4",1],["G4",1]]},
        {"chord": "F", "melody": [["A4",1],["A4",1],["G4",2]]},
        {"chord": "F", "melody": [["F4",1],["F4",1],["E4",1],["E4",1]]},
        {"chord": "C", "melody": [["D4",1],["D4",1],["C4",2]]},
        {"chord": "G", "melody": [["G4",1],["G4",1],["F4",1],["F4",1]]},
        {"chord": "C", "melody": [["E4",1],["E4",1],["D4",2]]},
        {"chord": "G", "melody": [["G4",1],["G4",1],["F4",1],["F4",1]]},
        {"chord": "C", "melody": [["E4",1],["E4",1],["D4",2]]},
        {"chord": "C", "melody": [["C4",1],["C4",1],["G4",1],["G4",1]]},
        {"chord": "F", "melody": [["A4",1],["A4",1],["G4",2]]},
        {"chord": "F", "melody": [["F4",1],["F4",1],["E4",1],["E4",1]]},
        {"chord": "C", "melody": [["D4",1],["D4",1],["C4",2]]},
    ],
}

EINE_KLEINE = {
    "title": "Eine kleine Nachtmusik",
    "subtitle": "After Mozart, K. 525 — simplified for piano solo, two hands",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 88,
    "tempo_mark": "Allegretto", "accompaniment": "alberti",
    "sections": [{"bar": 0, "name": "Opening theme", "dynamic": "mf"}],
    "bars": [
        {"chord":"C", "melody":[["C4",1],["E4",1],["G4",1],["E4",1]]},
        {"chord":"F", "melody":[["F4",1],["E4",1],["D4",1],["C4",1]]},
        {"chord":"C", "melody":[["C4",1],["E4",1],["G4",1],["E4",1]]},
        {"chord":"G", "melody":[["D4",1],["D4",1],["C4",2]]},
        {"chord":"C", "melody":[["G4",1],["E4",1],["G4",1],["C5",1]]},
        {"chord":"F", "melody":[["A4",1],["F4",1],["E4",1],["D4",1]]},
        {"chord":"G", "melody":[["G4",1],["F4",1],["D4",1],["B3",1]]},
        {"chord":"C", "melody":[["C4",4]]},
    ],
}

HAYDN_SURPRISE = {
    "title": "Surprise Symphony Theme",
    "subtitle": "After Haydn, Symphony No. 94 — simplified piano solo",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 72,
    "tempo_mark": "Andante", "accompaniment": "chords",
    "sections": [{"bar": 0, "name": "Theme", "dynamic": "p"},
                 {"bar": 4, "name": "Surprise!", "dynamic": "f"}],
    "bars": [
        {"chord":"C", "melody":[["C4",1],["C4",1],["E4",1],["E4",1]]},
        {"chord":"C", "melody":[["G4",1],["G4",1],["E4",2]]},
        {"chord":"G", "melody":[["F4",1],["F4",1],["D4",1],["D4",1]]},
        {"chord":"G", "melody":[["B3",1],["B3",1],["G3",2]]},
        {"chord":"C", "melody":[["C4",1],["C4",1],["E4",1],["E4",1]]},
        {"chord":"C", "melody":[["G4",1],["G4",1],["E4",2]]},
        {"chord":"G", "melody":[["F4",1],["D4",1],["B3",1],["G3",1]]},
        {"chord":"C", "melody":[["C4",4]]},
    ],
}

ARRANGEMENTS = {
    "amazing-grace": ("Amazing_Grace", AMAZING_GRACE),
    "twinkle": ("Mozart_Twinkle_Theme", TWINKLE),
    "eine-kleine": ("Mozart_Eine_Kleine_Nachtmusik", EINE_KLEINE),
    "haydn-surprise": ("Haydn_Surprise_Symphony", HAYDN_SURPRISE),
}


def render(name, output_dir):
    stem, data = ARRANGEMENTS[name]
    output_dir.mkdir(parents=True, exist_ok=True)
    score = musiclib.build_score(data)
    basename = str(output_dir / stem)
    made = musiclib.render_all(score, basename, audio=True)
    wav = basename + ".wav"
    if os.path.exists(wav):
        os.remove(wav)
        made = [path for path in made if path != wav]
    return made


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pieces", nargs="*", choices=sorted(ARRANGEMENTS),
                        default=sorted(ARRANGEMENTS))
    parser.add_argument("--output-dir", type=Path, default=LIBRARY)
    args = parser.parse_args()
    for name in args.pieces:
        for path in render(name, args.output_dir):
            print("created:", path)


if __name__ == "__main__":
    main()
