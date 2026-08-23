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
ADVANCED_SCOPE = os.path.join(HERE, "MONTHS_4_TO_6_SCOPE.md")

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
    # ---- Month Three (Days 61-90) -----------------------------------------
    ("Reading real musical phrases", [
        (61, "Month Three Orientation", "A short Month Two diagnostic covering F major, inversions, dotted rhythms and steady two-hand playing. Help the learner choose two skills to revisit; no new notation."),
        (62, "Ties You Can Play", "Teach ties within a bar and across a barline: hold one key without a second attack. Because tied-event engraving is not yet available in generated exercises, show supported long-note listening exercises and explain the printed curve honestly; do not fake a tie with repeated notes."),
        (63, "Pickup Notes", "Teach anacrusis by counting an incomplete opening measure before beat one. Use spoken and keyboard drills, but state honestly that the generated exercise begins at a full bar because partial-measure engraving is not yet available."),
        (64, "Feeling 6/8", "Introduce genuine 6/8: six eighth notes grouped 3+3, felt as two large dotted-quarter beats. Every exercise MUST use [6,8], with eighth notes grouped musically; clap before playing."),
        (65, "Playing in 6/8", "Genuine [6,8] two-hand playing: a simple melody in six eighth-note subdivisions over two dotted-quarter bass notes per bar. Count ONE-and-a TWO-and-a."),
        (66, "Quiet Review Day", "A short relaxed review of ties, pickup counting and genuine [6,8]. All notated exercises use [6,8]; no new skill."),
        (67, "A Small 6/8 Song", "A short original public-domain-style song in genuine [6,8], not a relabelled 3/4 waltz. Use two dotted-quarter pulses, clear 3+3 grouping, and a simple two-hand texture."),
    ]),
    ("D major and dominant seventh harmony", [
        (68, "Meet D Major", "Introduce the D-major key signature, F sharp and C sharp, and keyboard geography. Short original exercises only."),
        (69, "D Major Scale Right Hand", "One-octave D major scale, right hand separately, standard fingering 1-2-3-1-2-3-4-5 ascending and reverse descending."),
        (70, "D Major Scale Left Hand", "One-octave D major scale, left hand separately, standard fingering 5-4-3-2-1-3-2-1 ascending and reverse descending. Do not ask for hands together."),
        (71, "Chords in D", "D, G and A major as I, IV and V in D. Use genuine simultaneous chord events, slow enough for an adult beginner."),
        (72, "The Dominant Seventh", "Introduce A7 resolving to D by sound first, then name V7. Use genuine simultaneous chord events and explain the G natural in A7."),
        (73, "Smooth Changes in D", "Close-position inversions of D, G and A7 with minimal hand movement. Genuine chord events, then a simple right-hand melody."),
        (74, "Play Day in D", "Optional guided improvisation over D-G-A7-D. Keep it light and non-blocking, with one short notated example."),
    ]),
    ("Texture balance and interpretation", [
        (75, "Month Three Checkpoint", "Self-check ties concept, genuine 6/8, D-major scales hands separately, and D-major harmony. Never test a skill not yet taught."),
        (76, "Melody and Inner Voice", "Bring out a singing top line while repeated inner notes stay quiet. Use modest spans and slow two-hand exercises."),
        (77, "Articulation with Purpose", "Combine legato, staccato, accents and breathing at phrase endings in one short original study. Explain the musical reason for each."),
        (78, "Pedal by Ear", "Clear sustain pedal at every harmony change, using half-length practice segments and listening for blur. Keep notation simple."),
        (79, "Arpeggio Shapes", "Slow one-octave chord shapes and broken chords, not rapid concert arpeggios or wide stretches."),
        (80, "Sight Reading in Four Keys", "Four very short reading examples in C, G, F and D, using only learned notes and rhythms. Explain key-signature preparation before playing."),
        (81, "Ear and Chord Function", "Hear home, away and tension as I, IV and V or V7. A light listening day with one short notated example."),
    ]),
    ("Preparing Schumann's Soldier's March", [
        (82, "Meet Soldier's March", "Prepare Schumann's authentic Soldier's March Op. 68 No. 2 from the Music Library: survey key, 2/4 meter, form, repeated patterns and hard spots. Do not rewrite or claim to reproduce its score; generated notation is only a separate preparatory drill."),
        (83, "March Rhythm and Chords", "Preparatory rhythm and chord-attack drills for Soldier's March, away from the authentic score. Use 2/4 and genuine chord events."),
        (84, "First Half Hands Separately", "A practice plan for the first half of the authentic library score: fingering choices, position changes, hands separately, short loops. Generated notes are generic drills, not the piece."),
        (85, "Second Half Hands Separately", "A practice plan for the second half of the authentic library score: repeated patterns, rests and clean releases. Generated notes are generic drills, not the piece."),
        (86, "Put the Hands Together", "Combine the authentic piece in two-bar units at a deliberately slow tempo. Include only a generic coordination drill and direct the learner back to the library score."),
        (87, "Dynamics and Character", "Build a strong but unforced march character with planned dynamics, accents and relaxed arms while practising the authentic library score."),
        (88, "Repair and Recovery Day", "Isolate weak bars, use stop-before-start-after loops, and practise continuing after a mistake in the authentic library score."),
    ]),
    ("Month Three review and recital", [
        (89, "Month Three Review", "Review genuine 6/8, D major, V7, four-key reading, balance and interpretation, then plan a mock performance of Soldier's March."),
        (90, "Month Three Recital Soldier's March", "Perform Schumann's authentic Soldier's March Op. 68 No. 2 using the existing Music Library PDF, MIDI and MP3. Do not generate or imply a replacement edition; the exercise is only a brief warm-up and the lesson must direct the learner to the library score."),
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
    if os.path.exists(ADVANCED_SCOPE):
        theme = "Months Four to Six"
        row_re = re.compile(
            r"^\|\s*(\d{2,3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\d+\s*\|\s*[^|]+\|")
        with open(ADVANCED_SCOPE) as scope:
            for line in scope:
                if line.startswith("## Week ") or line.startswith("## Days "):
                    theme = line[3:].strip()
                match = row_re.match(line)
                if match and 91 <= int(match.group(1)) <= 180:
                    out.append((int(match.group(1)), theme,
                                match.group(2).strip(), match.group(3).strip()))
    days = sorted(out)
    numbers = [day for day, _, _, _ in days]
    if len(numbers) != len(set(numbers)):
        raise RuntimeError("duplicate curriculum day in configured scopes")
    return days

def slug(title):
    return re.sub(r"[^\w]+", "_", title).strip("_")

def prompt_for(day, week, title, topic):
    covered = ([f"Day {d} {t}" for d, t in sorted(EXISTING.items()) if d < day]
               + [f"Day {d} {t}" for d, _, t, _ in all_days() if d < day])
    level_rule = (
        "five-finger positions, only the note values and techniques introduced up to this day"
        if day <= 60 else
        "the hand positions, keys, rhythms and techniques introduced up to this day; keep spans comfortable and avoid virtuoso writing"
    )
    advanced = ""
    if day >= 91:
        advanced = (
            " The lesson engine supports key_sig (-7..7 fifths), pickup durations, "
            "sixteenth-note duration 0.25, and a fifth boolean on a note to tie it "
            "to the immediately following same-pitch note. Use these only when today's "
            "scope requires them. Authentic repertoire named in the topic must be studied "
            "from the Music Library; generated exercises are preparatory and must not claim "
            "to reproduce the historical score."
        )
    # Extract any hard melody directives from the topic and repeat them explicitly.
    melodies_required = re.findall(r'"melody"\s*:\s*"([^"]+)"', topic)
    melody_block = ""
    if melodies_required:
        melody_block = (
            "CRITICAL: today's topic requires the following reviewed melody exercise(s). "
            "You MUST set the exact JSON \"melody\" field(s) shown and you MUST omit "
            "\"rh\" and \"lh\" for each such exercise; the exact notes are injected automatically. "
            "Never write the notes of these melodies yourself:\n"
            + "\n".join(f'  - "melody": "{m}"' for m in melodies_required)
            + "\n"
        )
    return (
        f'You are writing Day {day} of "Six Months to Piano", a daily self-study course '
        f"for a middle-aged absolute beginner who practices 20-30 minutes a day.\n"
        f"This week's theme: {week}. Today's lesson is \"{title}\": {topic}\n"
        f"The student has already covered: {'; '.join(covered)}. Build gently on that — "
        f"brief recall is welcome, but do not re-teach earlier material in depth, and do "
        f"not use any concept not yet introduced. When naming an earlier day, verify its "
        f"number against this sequence; if unsure, omit the day number.\n"
        f"{melody_block}"
        f"Any exercises you invent yourself must fit the learner's level: {level_rule}, "
        f"8-16 bars total.{advanced}\n"
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
