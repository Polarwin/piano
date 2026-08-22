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

ARRANGEMENTS = {"amazing-grace": ("Amazing_Grace", AMAZING_GRACE)}


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
