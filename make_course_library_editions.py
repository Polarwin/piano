#!/usr/bin/env python3
"""Build shortened preparatory editions for Days 91–180.

These are deliberately modest course studies derived from characteristic
material in the named public-domain pieces.  They sit beside, and never
replace, the authentic library scores.
"""
import argparse
import os
from pathlib import Path

import musiclib


LIBRARY = Path("/srv/files/piano/library")


SCHUMANN_MELODY_STUDY = {
    "title": "Melody, Op. 68 No. 1 — Preparatory Study",
    "subtitle": "After Schumann — shortened Month Four course edition",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 66,
    "tempo_mark": "Gently", "accompaniment": "chords",
    "sections": [{"bar": 0, "name": "First phrase", "dynamic": "mp"},
                 {"bar": 8, "name": "Return", "dynamic": "mf"},
                 {"bar": 14, "name": "calando", "dynamic": "p"}],
    # Quarter- and half-note skeleton of the source phrase.  The reduced
    # accompaniment lets Days 112–117 focus on line, fingering and balance.
    "bars": [
        {"chord":"C",  "melody":[["C4",1],["G4",1],["F4",1],["G4",1]]},
        {"chord":"C",  "melody":[["E4",1],["G4",1],["B4",2]]},
        {"chord":"Dm", "melody":[["A4",1],["C5",1],["B4",1],["D5",1]]},
        {"chord":"C",  "melody":[["C5",2],["G4",2]]},
        {"chord":"G",  "melody":[["E4",1],["G4",1],["D4",1],["G4",1]]},
        {"chord":"C",  "melody":[["C4",1],["G4",1],["E4",1],["G4",1]]},
        {"chord":"D7", "melody":[["B4",2],["A4",2]]},
        {"chord":"G",  "melody":[["G4",4]]},
        {"chord":"C",  "melody":[["C4",1],["G4",1],["F4",1],["G4",1]]},
        {"chord":"C",  "melody":[["E4",1],["G4",1],["B4",2]]},
        {"chord":"Dm", "melody":[["A4",1],["C5",1],["B4",1],["D5",1]]},
        {"chord":"C",  "melody":[["C5",2],["G4",2]]},
        {"chord":"G",  "melody":[["E4",1],["G4",1],["D4",1],["G4",1]]},
        {"chord":"C",  "melody":[["C4",1],["G4",1],["E4",1],["G4",1]]},
        {"chord":"G7", "melody":[["D4",1],["F4",1],["B4",1],["D5",1]]},
        {"chord":"C",  "melody":[["C5",4]]},
    ],
}


SCHUMANN_LITTLE_PIECE_STUDY = {
    "title": "Little Piece, Op. 68 No. 5 — Preparatory Study",
    "subtitle": "After Schumann — shortened Month Five course edition",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 60,
    "tempo_mark": "Quietly", "accompaniment": "flowing",
    "sections": [{"bar": 0, "name": "Phrase A", "dynamic": "mp"},
                 {"bar": 8, "name": "Phrase B", "dynamic": "mf"},
                 {"bar": 14, "name": "Return", "dynamic": "p"}],
    # The source's moving accompaniment is reduced to regular eighth notes;
    # the melody retains its stepwise direction and two-bar breathing points.
    "bars": [
        {"chord":"C",  "melody":[["E4",2],["G4",1],["F4",1]]},
        {"chord":"G",  "melody":[["D4",1],["G4",1],["E4",1],["F4",1]]},
        {"chord":"G",  "melody":[["G4",1],["B4",1],["D5",2]]},
        {"chord":"G7", "melody":[["C5",1],["B4",1],["A4",1],["G4",1]]},
        {"chord":"C",  "melody":[["C5",2],["D5",1],["E5",1]]},
        {"chord":"C",  "melody":[["E5",2],["D5",2]]},
        {"chord":"D7", "melody":[["D5",1],["A4",1],["C5",2]]},
        {"chord":"G",  "melody":[["B4",2],["G4",2]]},
        {"chord":"G",  "melody":[["F4",1],["G4",1],["B4",1],["D5",1]]},
        {"chord":"G",  "melody":[["D5",2],["E5",2]]},
        {"chord":"Dm", "melody":[["F5",1],["E5",1],["D5",1],["C5",1]]},
        {"chord":"G7", "melody":[["B4",1],["C5",1],["D5",2]]},
        {"chord":"Em", "melody":[["E5",2],["D5",2]]},
        {"chord":"G7", "melody":[["D5",1],["B4",1],["G4",2]]},
        {"chord":"G7", "melody":[["D5",1],["C5",1],["B4",2]]},
        {"chord":"C",  "melody":[["C5",4]]},
    ],
}


BACH_PRELUDE_STUDY = {
    "title": "Little Prelude in C, BWV 939 — Pattern Study",
    "subtitle": "After J. S. Bach — shortened Month Six preparation",
    "key_sig": 0, "minor": False, "time": [4, 4], "bpm": 60,
    "tempo_mark": "Clearly", "accompaniment": "alberti",
    "sections": [{"bar": 0, "name": "Opening patterns", "dynamic": "mp"},
                 {"bar": 8, "name": "Toward the cadence", "dynamic": "mf"}],
    # One-note-per-beat outline: the authentic score's sixteenth-note texture
    # is postponed until the learner can read these harmonic shapes securely.
    "bars": [
        {"chord":"C",  "melody":[["C4",1],["E4",1],["G4",1],["C5",1]]},
        {"chord":"C",  "melody":[["E4",1],["G4",1],["C5",1],["G4",1]]},
        {"chord":"F",  "melody":[["F4",1],["A4",1],["C5",1],["A4",1]]},
        {"chord":"F",  "melody":[["A4",1],["C5",1],["F5",1],["C5",1]]},
        {"chord":"G",  "melody":[["G4",1],["B4",1],["D5",1],["B4",1]]},
        {"chord":"G7", "melody":[["F4",1],["G4",1],["B4",1],["D5",1]]},
        {"chord":"C",  "melody":[["E5",2],["C5",2]]},
        {"chord":"C",  "melody":[["E4",1],["G4",1],["C5",2]]},
        {"chord":"D7", "melody":[["F#4",1],["A4",1],["D5",2]]},
        {"chord":"G",  "melody":[["G4",1],["B4",1],["D5",2]]},
        {"chord":"G7", "melody":[["F5",1],["D5",1],["B4",1],["G4",1]]},
        {"chord":"C",  "melody":[["C5",4]]},
    ],
}


BURGMULLER_ARABESQUE_STUDY = {
    "title": "Arabesque, Op. 100 No. 2 — Slow Pattern Study",
    "subtitle": "After Burgmüller — shortened optional Month Six preparation",
    "key_sig": 0, "minor": True, "time": [2, 4], "bpm": 56,
    "tempo_mark": "Slowly and lightly", "accompaniment": "chords",
    "sections": [{"bar": 0, "name": "Light repeated pattern", "dynamic": "p"},
                 {"bar": 8, "name": "Sequence", "dynamic": "mp"},
                 {"bar": 14, "name": "Cadence", "dynamic": "p"}],
    # Eighth notes replace the authentic rapid sixteenths.  This is a touch
    # and directional-pattern drill, not a simplified claim to the full piece.
    "bars": [
        {"chord":"Am", "melody":[["A4",.5],["B4",.5],["C5",.5],["B4",.5]]},
        {"chord":"Am", "melody":[["A4",.5],["C5",.5],["E5",.5],["C5",.5]]},
        {"chord":"Am", "melody":[["B4",.5],["C5",.5],["D5",.5],["C5",.5]]},
        {"chord":"E7", "melody":[["B4",.5],["G#4",.5],["E4",1]]},
        {"chord":"Dm", "melody":[["D5",.5],["C5",.5],["B4",.5],["A4",.5]]},
        {"chord":"Am", "melody":[["C5",.5],["B4",.5],["A4",1]]},
        {"chord":"E7", "melody":[["G#4",.5],["B4",.5],["E5",1]]},
        {"chord":"Am", "melody":[["A4",2]]},
        {"chord":"C",  "melody":[["C5",.5],["D5",.5],["E5",.5],["D5",.5]]},
        {"chord":"G",  "melody":[["B4",.5],["C5",.5],["D5",.5],["B4",.5]]},
        {"chord":"F",  "melody":[["A4",.5],["C5",.5],["F5",.5],["E5",.5]]},
        {"chord":"E7", "melody":[["D5",.5],["B4",.5],["G#4",1]]},
        {"chord":"Dm", "melody":[["F5",.5],["E5",.5],["D5",.5],["C5",.5]]},
        {"chord":"Am", "melody":[["B4",.5],["C5",.5],["A4",1]]},
        {"chord":"E7", "melody":[["G#4",1],["B4",1]]},
        {"chord":"Am", "melody":[["A4",2]]},
    ],
}


EDITIONS = {
    "schumann-melody-study": ("Course_Schumann_Melody_Study", SCHUMANN_MELODY_STUDY),
    "schumann-little-piece-study": ("Course_Schumann_Little_Piece_Study", SCHUMANN_LITTLE_PIECE_STUDY),
    "bach-prelude-study": ("Course_Bach_BWV939_Pattern_Study", BACH_PRELUDE_STUDY),
    "burgmuller-arabesque-study": ("Course_Burgmuller_Arabesque_Pattern_Study", BURGMULLER_ARABESQUE_STUDY),
}


def render(name, output_dir):
    stem, data = EDITIONS[name]
    output_dir.mkdir(parents=True, exist_ok=True)
    score = musiclib.build_score(data)
    basename = str(output_dir / stem)
    made = musiclib.render_all(score, basename, audio=True)
    wav = Path(basename + ".wav")
    if wav.exists():
        wav.unlink()
        made = [path for path in made if path != str(wav)]
    return made


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pieces", nargs="*", choices=sorted(EDITIONS),
                        default=sorted(EDITIONS))
    parser.add_argument("--output-dir", type=Path, default=LIBRARY)
    args = parser.parse_args()
    for name in args.pieces:
        for path in render(name, args.output_dir):
            print("created:", path)


if __name__ == "__main__":
    main()
