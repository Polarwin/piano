# Six Months to Piano — Month Three Suggestions

Month Three should turn the learner from an advanced beginner following daily
instructions into a more independent early pianist. It should consolidate the
corrected Month Two skills before adding another large collection of concepts.

## Proposed outcome for Day 90

The learner can prepare and perform a short authentic two-hand piece by:

- identifying its key, meter, landmarks, intervals, repeated patterns and form
- practising hands separately and then combining short sections
- reading in C, G, F and D major and recognising their key signatures
- playing C, G, F and D major scales one octave, hands separately
- using I, IV, V and V7 chords with close-position inversions
- maintaining a steady pulse in 2/4, 3/4, 4/4 and simple 6/8
- recognising and playing pickups, ties and dotted rhythms accurately
- balancing a singing melody over chords or broken-chord accompaniment
- using articulation, dynamics and pedal intentionally
- recovering from a mistake without restarting the performance

The target is confident early-beginner musicianship, not speed or an
intermediate examination level.

## Engine work required first

Implementation status (2026-08-23): genuine 6/8 validation, display, timing,
audio and single-staff 3+3 beaming are implemented. Pickup and tied-event
engraving remain deferred, so Days 62–63 use honest listening/counting drills
and explicitly identify the notation limitation. They do not simulate a tie
with a repeated attack or disguise a padded full bar as an anacrusis.

Do not generate lessons that merely describe notation the software cannot
engrave or play. Before Month Three generation, add and test:

1. `[6, 8]` time signatures, with six eighth-note subdivisions per bar and
   correct beaming and MIDI timing.
2. Pickup/anacrusis measures without padding them into incorrect full bars.
3. Ties within and across barlines in the lesson schema, engraving and MIDI.
4. Sixteenth-note durations if they will be taught; otherwise postpone them.
5. Validation that understands partial pickup/final measures and tied events.

If these upgrades are postponed, replace Days 62–65 with consolidation in
supported meters and state the limitation honestly. Do not simulate 6/8 as 3/4
or represent ties as repeated attacks.

## Suggested daily plan

### Week 9 — Reading real musical phrases

| Day | Lesson | Main work | Level | Practice |
|---:|---|---|---:|---:|
| 61 | Month Three Orientation | Short Month Two diagnostic; choose two skills to revisit | 3 | 20 min |
| 62 | Ties You Can Play | Engraved and audible ties within a bar, then across a barline | 3 | 20 min |
| 63 | Pickup Notes | Feel and count an incomplete opening measure; short familiar examples | 3 | 20 min |
| 64 | Feeling 6/8 | Two large beats, each divided into three; clap before playing | 3 | 20 min |
| 65 | Playing in 6/8 | Simple two-hand melody over dotted-quarter bass notes | 4 | 20 min |
| 66 | Quiet Review Day | Ties, pickup and 6/8 reading without new material | 2 | 15 min |
| 67 | A Small 6/8 Song | Checked public-domain tune using only the week's skills | 4 | 20 min |

The 6/8 tune must genuinely be in compound meter and use a reviewed melody;
do not relabel a 3/4 waltz. A suitable traditional tune may be selected only
after checking its public-domain status, melodic accuracy and playable range.

### Week 10 — D major and dominant seventh harmony

| Day | Lesson | Main work | Level | Practice |
|---:|---|---|---:|---:|
| 68 | Meet D Major | Key signature with F-sharp and C-sharp; keyboard geography | 3 | 20 min |
| 69 | D Major Scale, Right Hand | One octave with reviewed standard fingering | 4 | 20 min |
| 70 | D Major Scale, Left Hand | One octave; compare crossings with earlier scales | 4 | 20 min |
| 71 | Chords in D | D, G and A as I, IV and V; genuine simultaneous chords | 3 | 20 min |
| 72 | The Dominant Seventh | A7 resolving to D; hear tension and release before naming it | 4 | 20 min |
| 73 | Smooth Changes in D | Close inversions of D, G and A7 with minimal movement | 4 | 20 min |
| 74 | Play Day in D | Guided improvisation over D–G–A7–D; optional and light | 2 | 15 min |

Do not introduce hands-together D-major scales this month. Secure separate
hands and musical use of the key first.

### Week 11 — Texture, balance and interpretation

| Day | Lesson | Main work | Level | Practice |
|---:|---|---|---:|---:|
| 75 | Month Three Checkpoint | Ties, 6/8, D scale and D-major harmony self-check | 4 | 20 min |
| 76 | Melody and Inner Voice | Bring out the top line while keeping repeated notes quiet | 4 | 20 min |
| 77 | Articulation with Purpose | Legato, staccato, accents and phrase endings in one short study | 3 | 20 min |
| 78 | Pedal by Ear | Half-length practice segments; clear pedal at every harmony change | 4 | 20 min |
| 79 | Arpeggio Shapes | Slow one-octave chord shapes, not fast concert arpeggios | 4 | 20 min |
| 80 | Sight-Reading in Four Keys | Four very short examples in C, G, F and D | 3 | 20 min |
| 81 | Ear and Chord Function | Hear home, away and tension: I, IV, V/V7 | 2 | 15 min |

Keep Day 79 modest. Month Three should not require rapid thumb-under arpeggios
or wide stretches.

### Week 12 — Preparing authentic repertoire

Use Schumann's **Soldier's March, Op. 68 No. 2**, already available in the
Music Library as an authentic two-hand Month Three piece. Do not rewrite its
notes. The daily lessons should teach the learner how to approach the original
score progressively.

| Day | Lesson | Main work | Level | Practice |
|---:|---|---|---:|---:|
| 82 | Meet Soldier's March | Survey key, 2/4 meter, form, repeated patterns and difficult spots | 3 | 20 min |
| 83 | March Rhythm and Chords | Practise its rhythm and chord attacks away from the full piece | 4 | 20 min |
| 84 | First Half, Hands Separately | Fingering, position changes and short practice loops | 4 | 25 min |
| 85 | Second Half, Hands Separately | Repeated patterns, rests and clean releases | 4 | 25 min |
| 86 | Put the Hands Together | Two-bar units at a deliberately slow tempo | 5 | 25 min |
| 87 | Dynamics and Character | Strong march character without tension or harshness | 4 | 20 min |
| 88 | Repair and Recovery Day | Isolate weak bars; practise continuing after a mistake | 3 | 20 min |

### Days 89–90 — Review and recital

| Day | Lesson | Main work | Level | Practice |
|---:|---|---|---:|---:|
| 89 | Month Three Review | Short review of 6/8, D major, V7, reading and interpretation; mock performance | 4 | 25 min |
| 90 | Month Three Recital | Perform Schumann's *Soldier's March* from the authentic library score | 5 | 25–30 min |

The recital should link directly to the existing library PDF, MIDI and MP3
rather than generating a conflicting AI edition. Provide a slower practice
audio option if technically practical.

## Pedagogical safeguards

- Include a lighter review or creative day every six to seven days.
- Introduce at most one substantial new notation or coordination concept per
  lesson.
- Keep most PDFs between two and four pages and most play-along audio under two
  minutes; explain any deliberate exception.
- Never test a skill before its teaching day.
- Verify every historical day reference against the curriculum.
- Use genuine chord events for simultaneous chords.
- Treat fingering as hand-specific; review standard fingering before publishing.
- Avoid describing dotted rhythm as swing unless swing rhythm is the lesson.
- Do not claim a melody is famous or authentic unless its reviewed notes have
  been compared with a reliable public-domain source.
- Include relaxation reminders but do not repeatedly pad every lesson with the
  same generic advice.
- Optional play and ear-training days should remain non-blocking.

## Validation before generation

Write the Month Three scope and verify its prerequisites before generating any
PDFs. Then generate representative Days 61, 67, 75 and 90 first. Inspect their
notation, extracted text and audio manually. Only after those pass should the
remaining lessons be generated.

Final validation must confirm exactly one PDF and MP3 for every Day 61–90,
correct titles, valid media, complete measures, accurate reviewed melodies,
chronological references, reasonable page/audio lengths and a gradual
difficulty curve. Do not commit or push until the audit passes.
