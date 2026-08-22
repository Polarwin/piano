# Kimi prompt: correct and revalidate Month Two

Review and correct the existing Month Two curriculum, Days 31–60. Preserve
good material and do not change Month One or begin Month Three. Inspect
`AGENTS.md`, `CURRICULUM.md`, `make_curriculum.py`, `melodies.py`, the lesson
generator/renderers, and the existing Month Two PDFs before editing anything.

## Confirmed problems to fix

1. Day 35 says the right-hand C-major scale was learned on Day 16. It was Day
   15; Day 16 was the left hand.
2. Day 35 says legato was learned on Day 19. It was introduced on Day 18.
3. The Month Two scope promises the F-major scale with both hands separately,
   but `f_major_scale` currently contains only the right hand. Add a reviewed,
   playable left-hand F-major scale with correct standard fingering, or change
   the scope consistently if there is a strong pedagogical reason not to add it.
4. Day 45 tests dotted-quarter rhythms before they are introduced on Day 47.
   Move the introduction earlier or remove dotted-quarter rhythm from the
   checkpoint. Do not test a skill before teaching it.
5. Day 47 incorrectly describes a dotted quarter followed by an eighth as a
   dotted quarter "tied to an eighth." A dot and a tie are different notation.
   Explain and notate the rhythm correctly, count subdivisions accurately, and
   avoid calling ordinary dotted rhythm "swing" unless swing is actually being
   taught.
6. Days 48 and 59 say the reviewed `scarborough_fair` melody uses the new
   dotted-quarter/eighth rhythm, but its notes do not. Correct the reviewed
   melody and harmony so the tune is recognisable and genuinely demonstrates
   the rhythm, with complete 3/4 bars.
7. The reviewed `lightly_row` melody is not sufficiently faithful to the
   familiar traditional tune. Replace it with a checked, recognisable melody,
   appropriate fingering, harmony, meter, and complete bars.
8. Day 42 is excessive for a 20–30 minute adult-beginner lesson: eight PDF
   pages and almost three minutes of exercise audio. Reduce it to a focused
   introduction to Alberti bass, normally two to four PDF pages, with a small
   number of progressive exercises.
9. The stated Month Two outcome says the recital demonstrates playing in C, G,
   or F major, but Day 60 uses A-minor `greensleeves`. Make the stated outcome
   and recital agree. Prefer a recital that genuinely demonstrates the month's
   new F-major, reading, inversion, accompaniment, balance, and phrasing skills;
   alternatively revise the outcome with a clear pedagogical justification.
10. The current eight-bar `greensleeves` adaptation is weak and harmonically
    sparse. If retained, replace it with a reviewed, recognisable two-hand
    version with correct melodic contour, rhythm, harmony, playable range,
    fingering, and complete bars. Do not pretend the engine supports pickups or
    ties if it does not.
11. Day 59 repeats the inaccurate claim that the current `scarborough_fair`
    exercise demonstrated dotted rhythm. Update the review after correcting the
    underlying melody and chronology.

## Required workflow

- Correct `CURRICULUM.md`, `make_curriculum.py`, and `melodies.py` consistently.
- Run Python compilation and `python3 melodies.py` before regeneration.
- Regenerate affected Days 35, 36, 42, 45, 47, 48, 59, and 60 with Kimi using
  `--force`. Regenerate another day only if your corrections truly affect it.
- Verify every regenerated PDF and MP3, not merely the process exit status.
- Extract the PDF text and confirm all day-number references and music-theory
  statements are correct.
- Confirm one PDF and one MP3 still exist for every Day 31–60.
- Check that every reviewed melody has the declared meter, complete bars,
  sensible fingering, playable two-hand texture, and recognisable notes.
- Report exact changes, regeneration results, media validation, and any
  remaining compromises. Do not commit or push unless explicitly asked.
