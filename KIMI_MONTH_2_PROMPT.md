# Kimi prompt: build Month Two only

You are extending the existing **Six Months to Piano** course for a middle-aged
adult absolute beginner who practises for 20–30 minutes each day. Work only on
**Month Two, Days 31–60**. Do not rewrite or regenerate Days 1–30.

First inspect `AGENTS.md`, `CURRICULUM.md`, `make_curriculum.py`,
`lesson_gen.py`, `lesson_audio.py`, `melodies.py`, and several existing lesson
PDFs in `/srv/files/piano/lessons/`. Treat Month One as the prerequisite and
continue from what the learner genuinely knows at Day 30.

## Goal for Month Two

By Day 60, the learner should be able to read and play a short two-hand piece
in C, G, or F major with a steady pulse, basic phrasing, simple chord or broken-
chord accompaniment, and sensible fingering. The month should strengthen
Month One rather than suddenly becoming intermediate-level.

Develop these areas gradually:

- fluent treble- and bass-staff reading without writing every note name
- landmark-note and interval reading: steps, skips, repeated notes, thirds,
  fourths, and fifths
- secure C and G major scales, then introduce F major and B-flat carefully
- primary chords and inversions in C, G, and F; introduce I, IV, and V as
  optional labels alongside ordinary chord names
- left-hand accompaniment patterns: held chords, broken chords, Alberti bass,
  and simple waltz patterns
- hand independence, balance between melody and accompaniment, legato,
  staccato, dynamics, phrasing, and careful pedal changes
- rhythm through eighth notes, dotted-quarter plus eighth, ties, pickup notes,
  and 2/4, 3/4, and 4/4; introduce only one new rhythmic idea at a time
- small amounts of sight-reading, ear training, improvisation, and chord-based
  creativity suitable for an adult beginner
- relaxed posture and injury prevention; never encourage practising through
  pain or tension

## Course structure

Design exactly 30 daily lessons, Days 31–60. Use a sustainable rhythm:

- four or five teaching/practice days followed by a lighter consolidation,
  musical-play, or review day
- a clear review or checkpoint near Day 45
- Days 59–60 as Month Two review and a realistic recital piece
- each day should fit 20–30 minutes, including approximately 5 minutes of
  warm-up/review and a short enjoyable play-through
- recycle earlier skills frequently instead of presenting a new concept daily
- identify optional challenge material clearly so it does not block progress

Use simplified public-domain melodies only where they fit the skills already
learned. Do not force a famous tune into every lesson. Verify that each tune is
public domain and that its rhythm, range, key, and hand coordination are
appropriate at that exact point. Any factual reference to an earlier lesson
must use the correct day number; if uncertain, omit the number.

## Required project changes

1. Extend `CURRICULUM.md` with a complete Month Two scope table for Days 31–60.
   For every day include the title, core skill, exercise or repertoire, expected
   length, difficulty, and practice time. Also state the Month Two entry skills,
   end-of-month outcomes, review criteria, and recital goal.
2. Extend `make_curriculum.py` for Days 31–60 without changing the established
   Month One definitions. Keep `--from`, `--to`, `--skip`, `--force`,
   `--dry-run`, and composer selection working across both months.
3. Add reviewed melodies to `melodies.py` only when needed. Never ask the model
   to invent notes for a named famous melody. Validate every reviewed melody's
   meter, bar lengths, range, rhythm, and harmony.
4. Keep lesson JSON compatible with the existing v2 schema and renderers. Use
   genuine chord events for simultaneous chords. All exercises must have
   complete bars in the declared time signature.
5. Add concise documentation or validation code where necessary, but do not
   redesign the website or change AI Composition/Music Library functionality.

## Workflow and validation

Start by writing the Month Two plan and checking its pedagogical sequence.
Resolve duplication, prerequisite, workload, and difficulty problems before
generating any lessons. Then implement the scope and generator changes.

Before bulk generation, generate and inspect representative Days 31, 45, and
60. Confirm their PDFs are readable, their notation matches the lesson text,
their MP3 files are valid, and no exercise has incomplete bars. After those
checks pass, generate the remaining Month Two lessons with Kimi, resuming safely
when a lesson already exists.

Finally verify that:

- exactly one PDF and one MP3 exist for every Day 31–60
- all media files open successfully
- lesson titles and day numbers match the Month Two scope
- concepts never appear before they are introduced
- prior-day references are correct
- difficulty rises gradually and includes consolidation days
- Days 59–60 accurately review and demonstrate Month Two outcomes
- `git diff --check` and relevant Python compilation/tests pass

Report the curriculum decisions, files changed, generated lesson status, any
failed/retried days, validation results, and remaining pedagogical concerns.
Do not commit or push unless explicitly asked.
