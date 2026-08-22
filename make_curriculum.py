#!/usr/bin/env python3
"""Batch-generate the daily lesson curriculum via lesson_gen.py.

Resumable: any day whose PDF already exists in the lessons folder is skipped,
so re-running the script only fills in the gaps. Use --force to regenerate
days that already exist (e.g. after changing the curriculum).

Usage:
    python3 make_curriculum.py --dry-run            # show the plan
    python3 make_curriculum.py                      # generate missing days
    python3 make_curriculum.py --from 8 --to 30     # a range of days
    python3 make_curriculum.py --force --from 8 --to 14
"""
import argparse, glob, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS_DIR = "/srv/files/piano/lessons"
LOG = os.path.join(HERE, "curriculum_build.log")

# (week theme, [(day, title, topic), ...])
# Practice melodies are simplified, public-domain famous themes wherever the
# day's skill allows — see CURRICULUM.md for the mapping.
WEEKS = [
    ("Reading music and steady rhythm", [
        (8,  "Reading the Treble Staff",
             "Reading notes on the treble staff: lines and spaces, middle C to G. "
             "Simple right-hand reading exercises in the C five-finger position. "
             "Use the opening phrase of Beethoven's 'Ode to Joy' (C major, fits the "
             "C position exactly) as the reading melody."),
        (9,  "Reading the Bass Staff",
             "Reading notes on the bass staff: lines and spaces, C2 to G2 area. "
             "Simple left-hand reading exercises in the bass C five-finger position. "
             "Include the 'Ode to Joy' theme transposed to the bass C position."),
        (10, "Note Values and Counting",
             "Quarter, half, dotted half and whole notes; counting aloud while playing. "
             "Use 'Twinkle, Twinkle, Little Star' (Mozart's variation theme) for the "
             "rhythm exercises, one hand at a time."),
        (11, "Rests and Silence",
             "Whole, half and quarter rests; learning to lift the hands and feel the silence. "
             "Use the four-note 'fate' motif from Beethoven's Fifth Symphony (adapted in C, "
             "no flats) to practise playing and resting."),
        (12, "Smooth Chord Changes C to G",
             "Moving between the C and G chords without stopping: prepare the hand early, "
             "look ahead, keep a slow steady beat. Left-hand chord change drills."),
        (13, "Chord Changes C F and G",
             "Three-chord progressions (C-F-G) in the left hand; one chord per bar, "
             "then two bars each. Keep the pulse rock steady."),
        (14, "Your First Song",
             "Put it together: Beethoven's 'Ode to Joy' — right-hand melody with left-hand "
             "C, F and G chords, one chord per bar. Playing a complete famous song from "
             "start to finish."),
    ]),
    ("Scales, touch and minor colours", [
        (15, "The C Major Scale Right Hand",
             "The C major scale right hand: fingering, the thumb-under crossing, "
             "one octave up and down, slow and even."),
        (16, "The C Major Scale Left Hand",
             "The C major scale left hand: fingering, the third-finger-over crossing, "
             "one octave up and down, then both hands separately in one exercise."),
        (17, "Dynamics Loud and Soft",
             "Playing piano and forte: weight from the arm, not poking. Use the theme from "
             "Haydn's 'Surprise' Symphony (soft phrase, sudden loud moment) to make "
             "dynamics fun, plus a gentle crescendo exercise."),
        (18, "Legato and Staccato",
             "Smooth connected legato versus light detached staccato. Use a simplified "
             "opening of Mozart's 'Eine kleine Nachtmusik' for the staccato side and a "
             "slow singing phrase for legato."),
        (19, "The A Minor Chord",
             "The A minor chord (A-C-E): how it differs from C major, its sad colour. "
             "Finding and playing it in the left hand, broken then as successive whole notes."),
        (20, "Playing in A Minor",
             "Simple melancholy playing in the A minor five-finger position with left-hand "
             "Am chords. Use a simplified 'Fur Elise' opening motif (E-D#-E-B-D-C-A, "
             "simplified for five-finger position) as the melody."),
        (21, "Waltz Rhythm in 3/4",
             "Three beats per bar, the um-pah-pah waltz feel: left hand bass note then "
             "chord-chord pattern (written as successive notes). Use Brahms' Lullaby as "
             "the gentle right-hand waltz melody."),
    ]),
    ("Growing independence", [
        (22, "The G Major Scale",
             "The G major scale with F sharp: introducing the sharp sign, right-hand "
             "fingering one octave. Use a simplified phrase from Bach's Minuet in G "
             "as the melody."),
        (23, "The D Minor and E Minor Chords",
             "Two more minor chords, Dm and Em, and the classic Am-Dm-Em colour palette. "
             "Left-hand drills moving between them."),
        (24, "Broken Chord Accompaniment",
             "Accompaniment patterns: gentle broken chords under a slow right-hand melody. "
             "Use Pachelbel's Canon chord progression transposed to C "
             "(C-G-Am-Em-F-C-F-G) — the most useful pop-piano pattern there is."),
        (25, "Meet the Sustain Pedal",
             "The right pedal: what it does, when to lift it, the simple 'change with the chord' "
             "rule. Short exercises with and without pedal to hear the difference."),
        (26, "Hands Doing Different Things",
             "Coordination training: 'Amazing Grace' as a right-hand melody while the left "
             "hand holds slow whole-note chords. Start very slowly; accuracy before speed."),
        (27, "Playing Expressively",
             "Phrasing: thinking in musical sentences, breathing at the ends of phrases. "
             "Use a simplified opening phrase of Schumann's 'Traumerei' (transposed to C) "
             "and shape it with small crescendos and diminuendos."),
        (28, "Your First Waltz",
             "A complete gentle waltz combining 3/4 time, broken-chord accompaniment and a "
             "singing melody: a simplified Brahms Waltz Op. 39 No. 15 (transposed to C). "
             "The first real performance piece."),
    ]),
    ("Review and recital", [
        (29, "Month One Review",
             "A tour of everything learned this month: five-finger positions, the C, F, G "
             "and Am chords, eighth notes, 3/4 and 4/4 time. Mixed warm-up exercises that "
             "briefly revisit the month's famous themes (Ode to Joy, the Fur Elise motif, "
             "Minuet in G)."),
        (30, "Month One Recital Piece",
             "The month-one recital goal: a simplified first section of Beethoven's "
             "'Fur Elise' in A minor — the famous opening motif with an easy broken-chord "
             "left hand, dynamics, and a calm ending. Tips for playing through without "
             "stopping."),
    ]),
]

# Days 1-7 already exist; used only to brief the AI on what the student knows.
EXISTING = ["Meet the Piano", "Both Hands Together", "Your First Chord (C major)",
            "The G Chord", "The F Chord", "Eighth Notes", "Melody with Chords",
            "Broken Chords Basics (bonus)"]

def all_days():
    out = []
    for week, days in WEEKS:
        for day, title, topic in days:
            out.append((day, week, title, topic))
    return sorted(out)

def slug(title):
    return re.sub(r"[^\w]+", "_", title).strip("_")

def prompt_for(day, week, title, topic):
    covered = EXISTING + [t for d, _, t, _ in all_days() if d < day]
    return (
        f'You are writing Day {day} of "Six Months to Piano", a daily self-study course '
        f"for a middle-aged absolute beginner who practices 20-30 minutes a day.\n"
        f"This week's theme: {week}. Today's lesson is \"{title}\": {topic}\n"
        f"The student has already covered: {'; '.join(covered)}. Build gently on that — "
        f"brief recall is welcome, but do not re-teach earlier material in depth, and do "
        f"not use any concept not yet introduced.\n"
        f"When a famous melody is named above, it is practice material, not a performance "
        f"edition: simplify it ruthlessly to the learner's current level. Five-finger "
        f"positions only, one note at a time per hand, only the note values and techniques "
        f"introduced up to this day, 8-16 bars total. Transpose, narrow the range, drop "
        f"ornaments, smooth out hard rhythms and shorten as needed — a recognizable "
        f"skeleton the learner can actually play this week is the goal, not fidelity to "
        f"the original.\n"
        f"Title the lesson exactly: Day {day}: {title}."
    )

def pdf_exists(day):
    return bool(glob.glob(os.path.join(LESSONS_DIR, f"Day_{day}_*.pdf")))

def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--composer", choices=("kimi", "codex"), default="kimi")
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--to", dest="end", type=int, default=999)
    ap.add_argument("--force", action="store_true",
                    help="regenerate days even if their PDF already exists")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    days = [(d, w, t, tp) for d, w, t, tp in all_days() if args.start <= d <= args.end]
    if args.dry_run:
        for d, w, t, _ in days:
            mark = "exists" if pdf_exists(d) else "MISSING"
            print(f"Day {d:>3} [{mark:>7}] ({w}) {t}")
        return

    failed = []
    for d, week, title, topic in days:
        if pdf_exists(d) and not args.force:
            log(f"Day {d} {title}: already exists, skipping")
            continue
        base = os.path.join(LESSONS_DIR, f"Day_{d}_{slug(title)}")
        cmd = [sys.executable, os.path.join(HERE, "lesson_gen.py"),
               prompt_for(d, week, title, topic),
               "--title", f"Day {d}: {title}",
               "--out", base, "--composer", args.composer]
        log(f"Day {d} {title}: generating with {args.composer}")
        proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=900)
        if proc.returncode == 0 and pdf_exists(d):
            log(f"Day {d} {title}: done")
        else:
            log(f"Day {d} {title}: FAILED rc={proc.returncode} "
                + (proc.stdout + proc.stderr)[-300:].replace("\n", " "))
            failed.append(d)
        time.sleep(5)
    log(f"Batch finished. Failed days: {failed or 'none'}")

if __name__ == "__main__":
    main()
