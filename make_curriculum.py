#!/usr/bin/env python3
"""Batch-generate the daily lesson curriculum via lesson_gen.py.

Resumable: any day whose PDF already exists in the lessons folder is skipped,
so re-running the script only fills in the gaps. Use --force to regenerate
days that already exist (e.g. after changing the curriculum).

Usage:
    python3 make_curriculum.py --dry-run            # show the plan
    python3 make_curriculum.py                      # generate missing days
    python3 make_curriculum.py --from 8 --to 30     # a range of days
    python3 make_curriculum.py --force --skip 15 16 --from 3 --to 30
"""
import argparse, glob, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS_DIR = "/srv/files/piano/lessons"
LOG = os.path.join(HERE, "curriculum_build.log")

# (week theme, [(day, title, topic), ...])
# Days that promise a famous theme name a reviewed melody key from melodies.py —
# the exact notes are injected at render time, never written by the AI.
WEEKS = [
    ("First steps — chord days refreshed", [
        (3,  "Your First Chord",
             "The C major chord (C-E-G): what a chord is, and playing its three notes "
             "TOGETHER as a genuine simultaneous chord (use chord events, whole notes), "
             "left hand then right hand. Finish with gentle broken-chord practice."),
        (4,  "The G Chord",
             "The G major chord (G-B-D) played as a genuine simultaneous chord (chord "
             "events, whole notes), and moving between the C and G chords in the left "
             "hand, one chord per bar, slow and steady."),
        (5,  "The F Chord",
             "The F major chord (F-A-C) as a genuine simultaneous chord (chord events); "
             "then C-F-G progressions in the left hand, one chord per bar. Do not use "
             "or mention Ode to Joy here: its reading lesson is not introduced until Day 8."),
        (7,  "Melody with Chords",
             "A simple right-hand melody accompanied by genuine left-hand chords "
             "(chord events, one per bar, whole or half notes) using C, F and G."),
    ]),
    ("Reading music and steady rhythm", [
        (8,  "Reading the Treble Staff",
             "Reading notes on the treble staff: lines and spaces, middle C to G. "
             "Simple right-hand reading exercises in the C five-finger position. "
             "The main reading melody is Beethoven's 'Ode to Joy': that exercise MUST "
             "set \"melody\": \"ode_to_joy\" (reviewed notes are injected; do not "
             "write the notes yourself)."),
        (9,  "Reading the Bass Staff",
             "Reading notes on the bass staff: lines and spaces, C2 to G2 area. "
             "Simple left-hand reading exercises in the bass C five-finger position. "
             "The main reading melody is 'Ode to Joy' in the bass: that exercise MUST "
             "set \"melody\": \"ode_to_joy_bass\"."),
        (10, "Note Values and Counting",
             "Quarter, half, dotted half and whole notes; counting aloud while playing. "
             "The rhythm exercise is 'Twinkle, Twinkle' (Mozart's theme) and MUST set "
             "\"melody\": \"twinkle\"."),
        (11, "Rests and Silence",
             "Whole, half and quarter rests; learning to lift the hands and feel the silence. "
             "The exercise is the four-note 'fate' motif from Beethoven's Fifth Symphony "
             "(adapted in C, no flats) and MUST set \"melody\": \"beethoven_fifth\"."),
        (12, "Smooth Chord Changes C to G",
             "Moving between the C and G chords without stopping: prepare the hand early, "
             "look ahead, keep a slow steady beat. Left-hand chord change drills using "
             "genuine chord events (whole or half notes)."),
        (13, "Chord Changes C F and G",
             "Three-chord progressions (C-F-G) in the left hand using genuine chord "
             "events; one chord per bar, then two bars each. Keep the pulse rock steady."),
        (14, "Your First Song",
             "Put it together: Beethoven's 'Ode to Joy' with chord accompaniment — the "
             "song exercise MUST set \"melody\": \"ode_to_joy_chords\". Playing a "
             "complete famous song from start to finish."),
    ]),
    ("Scales, touch and minor colours", [
        (15, "The C Major Scale Right Hand",
             "The C major scale right hand: fingering, the thumb-under crossing, "
             "one octave up and down, slow and even."),
        (16, "The C Major Scale Left Hand",
             "The C major scale left hand: fingering, the third-finger-over crossing, "
             "one octave up and down, then both hands separately in one exercise."),
        (17, "Dynamics Loud and Soft",
             "Playing piano and forte: weight from the arm, not poking. The exercise is "
             "the theme from Haydn's 'Surprise' Symphony (soft phrase, sudden loud "
             "moment) and MUST set \"melody\": \"surprise\"."),
        (18, "Legato and Staccato",
             "Smooth connected legato versus light detached staccato. The exercise is "
             "after Mozart's 'Eine kleine Nachtmusik' and MUST set "
             "\"melody\": \"eine_kleine\"."),
        (19, "The A Minor Chord",
             "The A minor chord (A-C-E): how it differs from C major, its sad colour. "
             "Play it as a genuine simultaneous chord (chord events) in the left hand, "
             "then broken, then C-Am changes."),
        (20, "Playing in A Minor",
             "Simple melancholy playing in A minor. The exercise is the famous opening "
             "motif of Beethoven's 'Fur Elise' and MUST set \"melody\": \"fur_elise\". "
             "If referring to legato, say it was introduced on Day 18, not Day 19."),
        (21, "Waltz Rhythm in 3/4",
             "Three beats per bar, the um-pah-pah waltz feel: left hand bass note then "
             "chord-chord pattern. Use Brahms' Lullaby as the gentle right-hand melody."),
        (22, "The G Major Scale",
             "The G major scale with F sharp: introducing the sharp sign and right-hand "
             "scale fingering over one octave. The scale exercise MUST set "
             "\"melody\": \"g_major_scale\". Follow it with a short original melody in "
             "G major that uses F sharp."),
    ]),
    ("Growing independence", [
        (23, "The D Minor and E Minor Chords",
             "Two more minor chords, Dm and Em, played as genuine simultaneous chords "
             "(chord events), and the classic Am-Dm-Em colour palette. Left-hand drills "
             "moving between them."),
        (24, "Broken Chord Accompaniment",
             "Accompaniment patterns on Pachelbel's Canon progression in C: the exercise "
             "MUST set \"melody\": \"canon_in_c\". Explain how these chord tones can be "
             "broken into the most useful pop-piano pattern there is."),
        (25, "Meet the Sustain Pedal",
             "The right pedal: what it does, when to lift it, the simple 'change with the chord' "
             "rule. Short exercises with and without pedal to hear the difference."),
        (26, "Hands Doing Different Things",
             "Coordination training: the melody of 'Amazing Grace' in the right hand while "
             "the left hand holds slow whole-note chords. The exercise MUST set "
             "\"melody\": \"amazing_grace\". Start very slowly; accuracy before speed."),
        (27, "Playing Expressively",
             "Phrasing: thinking in musical sentences, breathing at the ends of phrases. "
             "The exercise is after Schumann's 'Traumerei' and MUST set "
             "\"melody\": \"traumerei\"; shape it with small crescendos and diminuendos. "
             "Dynamics were introduced on Day 17 (not Day 18)."),
        (28, "Your First Waltz",
             "A complete gentle waltz combining 3/4 time, broken-chord accompaniment and a "
             "singing melody, after Brahms' Waltz Op. 39 No. 15. The exercise MUST set "
             "\"melody\": \"brahms_waltz\". The first real performance piece. (Recall: "
             "3/4 waltz rhythm was Day 21, broken chords Day 24.)"),
    ]),
    ("Review and recital", [
        (29, "Month One Review",
             "A tour of everything learned this month: five-finger positions, the C, F, G "
             "and Am chords, eighth notes, 3/4 and 4/4 time. One warm-up exercise MUST set "
             "\"melody\": \"ode_to_joy\" (4/4) to revisit the month's first famous tune. "
             "Mention that tomorrow's recital piece is the simplified Fur Elise (Day 30), "
             "so the student can look forward to it."),
        (30, "Month One Recital Piece",
             "The month-one recital goal: the famous opening of Beethoven's 'Fur Elise' "
             "in A minor with a gentle chord accompaniment. The recital exercise MUST set "
             "\"melody\": \"fur_elise\". Tips for playing through without stopping, and "
             "ideas for performing it for family and friends. Keep historical references "
             "accurate: dynamics were introduced on Day 17, legato/staccato on Day 18, "
             "and eighth notes on Day 6. Do not claim that hands-separate practice was "
             "introduced on Day 27; simply advise practising each hand separately."),
    ]),
]

# Days 1, 2 and 6 plus the bonus exist and are not regenerated; used only to
# brief the AI on what the student knows.
EXISTING = {1: "Meet the Piano", 2: "Both Hands Together", 6: "Eighth Notes",
            0: "Broken Chords Basics (bonus)"}

def all_days():
    out = []
    for week, days in WEEKS:
        for day, title, topic in days:
            out.append((day, week, title, topic))
    return sorted(out)

def slug(title):
    return re.sub(r"[^\w]+", "_", title).strip("_")

def prompt_for(day, week, title, topic):
    covered = ([t for d, t in sorted(EXISTING.items()) if d < day]
               + [t for d, _, t, _ in all_days() if d < day])
    return (
        f'You are writing Day {day} of "Six Months to Piano", a daily self-study course '
        f"for a middle-aged absolute beginner who practices 20-30 minutes a day.\n"
        f"This week's theme: {week}. Today's lesson is \"{title}\": {topic}\n"
        f"The student has already covered: {'; '.join(covered)}. Build gently on that — "
        f"brief recall is welcome, but do not re-teach earlier material in depth, and do "
        f"not use any concept not yet introduced. When naming an earlier day, verify its "
        f"number against this sequence; if unsure, omit the day number.\n"
        f"If the topic says an exercise MUST set \"melody\" to a key, do exactly that and "
        f"omit rh/lh for that exercise — reviewed notes are injected automatically; never "
        f"write those notes yourself. Any exercises you invent yourself must fit the "
        f"learner's level: five-finger positions, only the note values and techniques "
        f"introduced up to this day, 8-16 bars total.\n"
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
    ap.add_argument("--skip", type=int, nargs="*", default=[],
                    help="day numbers to leave untouched")
    ap.add_argument("--force", action="store_true",
                    help="regenerate days even if their PDF already exists")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    days = [(d, w, t, tp) for d, w, t, tp in all_days()
            if args.start <= d <= args.end and d not in args.skip]
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
