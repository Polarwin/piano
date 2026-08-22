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
    # ---- Month Two (Days 31-60) -------------------------------------------
    ("Reading fluency and F major", [
        (31, "Welcome to Month Two",
             "A friendly look back at Month One and a mixed warm-up tour: five-finger "
             "positions, the C and G scales, the C F G Am chords, eighth notes, 3/4 and "
             "4/4. Short original exercises that re-awaken each skill, plus what this "
             "month will add (F major, inversions, new accompaniment patterns)."),
        (32, "Landmark Notes",
             "Reading without naming every note: landmark notes treble G, middle C and "
             "bass F, and judging notes by their distance from them. Short original "
             "reading exercises for each hand."),
        (33, "Steps and Skips",
             "Intervals: steps (2nds) and skips (3rds); reading by shape instead of "
             "letter-by-letter. Original exercises mixing steps and skips in C position."),
        (34, "Fourths and Fifths",
             "The bigger intervals, fourths and fifths, and how they look on the staff "
             "(line-to-line, space-to-space); recognizing chord shapes. Original exercises."),
        (35, "The F Major Scale",
             "F major and the flat sign: B flat. Two scale exercises: the first MUST "
             "set \"melody\": \"f_major_scale\" (right hand, one octave, fingering "
             "1234 1234) and the second MUST set \"melody\": \"f_major_scale_lh\" "
             "(left hand, standard fingering 54321 321). Follow with a short "
             "original melody in F major that uses B flat. Get recall references "
             "right: the right-hand C major scale was Day 15, the left hand was "
             "Day 16, and legato was introduced on Day 18."),
        (36, "Lightly Row",
             "A first Month Two song putting steps and skips to work: the piece MUST "
             "set \"melody\": \"lightly_row\" (G major, with chord accompaniment; the "
             "left-hand D major chord contains the F sharp from Day 22)."),
        (37, "Quiet Review Day",
             "A lighter consolidation day: the sight-reading habit (skim first, look "
             "ahead, never stop), then gentle review exercises mixing this week's "
             "intervals. Keep it short and relaxed."),
    ]),
    ("Chords, inversions and accompaniment", [
        (38, "Chord Checkup and I IV V",
             "Review the C, F and G chords with genuine chord events, and learn their "
             "other names: I, IV and V in the key of C. Keep the Roman numerals "
             "optional and friendly."),
        (39, "Chord Inversions",
             "Chord inversions in C: root position, first and second inversion, played "
             "as genuine chord events, and how inversions keep the left hand from "
             "jumping. Slow whole-note and half-note changes."),
        (40, "Inversions in G and F",
             "The same inversion idea in G major and F major (recall the F sharp and "
             "B flat). Genuine chord events, gentle progressions like I-IV-V-I using "
             "smooth inversions."),
        (41, "When the Saints",
             "A cheerful chord song: the piece MUST set \"melody\": \"saints\" (C major "
             "with C, F and G chord accompaniment). Steady march pulse."),
        (42, "Alberti Bass",
             "The Alberti bass: breaking a chord into a gentle low-high-middle-high "
             "eighth-note rocking pattern (e.g. C-G-E-G) under a slow right-hand "
             "melody. Keep the lesson compact — two to four PDF pages, at most "
             "three short progressive original exercises of 4-8 bars each: the "
             "pattern alone on C, the pattern through C-F-G chord changes, then "
             "the pattern under a slow simple right-hand melody."),
        (43, "Melody Above the Waves",
             "Balance between the hands: the melody sings louder while the "
             "accompaniment stays soft. Recall the Day 21 waltz pattern and Day 24 "
             "broken chords; original exercises practising melody-over-accompaniment."),
        (44, "Play Day Make Your Own",
             "A light creative day: guided improvisation using only the five notes of "
             "the C position over simple C-F-G chord loops. Mark it clearly as "
             "optional play, not a test. One short notated example exercise is enough."),
    ]),
    ("Checkpoint and independence", [
        (45, "Month Two Checkpoint",
             "Mid-month review and self-check: the F major scale with B flat, chord "
             "inversions, Alberti bass, and landmark/interval reading. Mixed "
             "original warm-up exercises and simple self-test questions (can I "
             "play it four times without stopping?). Do not test dotted rhythms "
             "here — they are only introduced on Day 47."),
        (46, "Steady Bass Singing Top",
             "Hand independence, a step further than Day 26: a busier right-hand "
             "melody over held whole-note and half-note chords. Original exercises, "
             "very slow practice."),
        (47, "The Long Short Rhythm",
             "The dotted-quarter-plus-eighth rhythm figure. Explain it correctly: "
             "a dot after a note lengthens it by half its value, so a dotted "
             "quarter equals a quarter plus an eighth — count it 1-and-2, with "
             "the eighth arriving on the 'and' of 2. A dot is not a tie: never "
             "describe the rhythm as a dotted quarter 'tied to' an eighth, and "
             "do not call it swing (swing is a different, uneven performance "
             "style that this course does not teach). Original rhythm exercises "
             "in 4/4, one hand then both."),
        (48, "Scarborough Fair",
             "A haunting minor melody using the new dotted rhythm from Day 47: the "
             "piece MUST set \"melody\": \"scarborough_fair\" (E minor, 3/4, chord "
             "accompaniment). Point out how the dotted quarter + eighth figure "
             "opens almost every bar, and the two five-finger positions (low "
             "E-B, high A-E). Recall the F sharp from Day 22."),
        (49, "Ear Training Day",
             "A lighter listening day: major versus minor, high versus low, same "
             "versus different. The text gives listen-then-play games; one short "
             "notated exercise is enough."),
        (50, "Sight-Reading Practice",
             "Sight-reading strategy: skim the shape, set the pulse, play slowly, "
             "never stop. Two short original reading exercises to try the method on."),
        (51, "Play Day Chord Colors",
             "A light creative day with the minor chords Am, Dm and Em: build a "
             "two-chord loop, make it sound sad then hopeful. Optional play, clearly "
             "marked. One short notated example is enough."),
    ]),
    ("Expression and the recital piece", [
        (52, "Pedal with Care",
             "Sustain pedal changes coordinated with chord changes (recall Day 25): "
             "press after the chord, lift cleanly on the change, listen for smears. "
             "Original slow chord exercises."),
        (53, "House of the Rising Sun",
             "Arpeggio accompaniment: the piece MUST set \"melody\": \"rising_sun\" "
             "(A minor, 3/4, rolling left-hand arpeggios). Keep it slow and even."),
        (54, "Yankee Doodle",
             "A complete two-hand piece in C major: the piece MUST set "
             "\"melody\": \"yankee_doodle\". Bright march tempo, steady left-hand "
             "chords."),
        (55, "Beyond the Staff",
             "Reading one and two ledger lines above and below each staff (low bass A "
             "and F, high treble A and B). Original exercises that step just outside "
             "the five-finger positions."),
        (56, "About Ties",
             "Concept day: explain that printed music often holds a note over a "
             "barline using a tie (two noteheads joined by a curve), and that in this "
             "course's exercises we simply write one long note instead. Exercises "
             "practise reading half, dotted-half and whole notes with confidence."),
        (57, "Play Day Canon Jam",
             "A light creative day: improvise a gentle right-hand melody over the "
             "Pachelbel chord loop from Day 24 (C-G-Am-Em-F-C-F-G). Optional play, "
             "clearly marked; include one notated example using \"melody\": "
             "\"canon_in_c\" as the backing."),
        (58, "Quiet Review Day",
             "A lighter day: mixed warm-ups from the month, then choose one favourite "
             "piece from the course so far and polish it. Short original exercises."),
    ]),
    ("Month Two review and recital", [
        (59, "Month Two Review",
             "A tour of the month: F major scale with B flat (right and left "
             "hands separately; do not ask for hands together), "
             "inversions, Alberti bass, the dotted quarter + eighth rhythm "
             "(introduced on Day 47 and genuinely used in the Scarborough Fair "
             "piece of Day 48), landmarks and intervals. One warm-up exercise "
             "MUST set \"melody\": \"f_major_scale\" (4/4), and a separate "
             "left-hand scale exercise MUST set \"melody\": "
             "\"f_major_scale_lh\". Mention that "
             "tomorrow's recital piece is Greensleeves (Day 60)."),
        (60, "Month Two Recital Greensleeves",
             "The month-two recital piece: the piece MUST set \"melody\": "
             "\"greensleeves\" (A minor, 3/4, a full 12-bar first verse with "
             "gentle waltz accompaniment). Explain the one new reading skill in "
             "it: the G sharp, the raised 7th that points home to A (and the F "
             "sharp in the final line, recalled from Day 22). Note how the "
             "dotted quarter + eighth rhythm of Day 47 gives the tune its "
             "lilt. Tips for a calm performance; recall the Day 30 recital "
             "advice."),
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
    covered = ([f"Day {d} {t}" for d, t in sorted(EXISTING.items()) if d < day]
               + [f"Day {d} {t}" for d, _, t, _ in all_days() if d < day])
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
