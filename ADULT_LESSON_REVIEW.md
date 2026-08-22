# Adult Piano Lesson Review

## Current status

Month One of **Six Months to Piano** contains 30 daily lessons in
`/srv/files/piano/lessons/`. Every day currently has a printable PDF and an
MP3 play-along. Curriculum generation has finished, and no batch generator is
still running.

The material is aimed at an adult absolute beginner practising for 20–30
minutes per day. Its tone is generally welcoming, patient, and easy to read.

## Improvements already made

The lesson format now supports:

- 2/4, 3/4, and 4/4 time signatures
- rests and accidentals
- genuine simultaneous chords
- tempo, dynamic, and BPM markings
- single-staff and grand-staff exercises
- matching PDF and MP3 rendering

Day 21, **Waltz Rhythm in 3/4**, was regenerated successfully. Its exercises
are now printed in 3/4 and its MP3 is present and valid.

## Issues still to address

### 1. Day 22 has the wrong scale in its score and audio

The prose correctly describes the G major scale with F-sharp, but the existing
score prints F-natural. The lesson was generated before accidental support was
added and should be regenerated.

### 2. Older lessons do not use genuine chords

Many early lessons describe a chord while displaying its notes one after
another, sometimes as whole notes in separate bars. That is useful as an
arpeggio exercise, but it is not the same as playing a chord. Lessons about
chords should use the newer simultaneous-chord representation where suitable.

### 3. Promised famous themes are often absent

Several generated lessons do not contain the recognizable melody promised by
the curriculum:

- Day 27: Schumann's *Träumerei*
- Day 28: Brahms Waltz Op. 39 No. 15
- Day 29: review of the month's named themes
- Day 30: Beethoven's *Für Elise*

The same problem should be checked in earlier lessons that promise *Ode to
Joy*, *Twinkle, Twinkle*, Beethoven's Fifth, and other named material.

### 4. Cross-references need proofreading

Some generated text refers to the wrong lesson numbers. For example, Day 28
says waltz rhythm was introduced on Day 22 and broken-chord accompaniment on
Day 25; the intended references are Days 21 and 24.

### 5. The recital plan is inconsistent

The curriculum describes Day 30 as a simplified *Für Elise* recital piece,
but Day 29 asks the student to choose an earlier song or waltz instead. The
course should choose one clear recital plan and prepare for it consistently.

## Recommendations for adult learners

Each lesson should use a predictable 20–30 minute structure:

1. Two to five minutes reviewing an earlier skill.
2. A short explanation of one new concept.
3. Hands-separate practice at a stated tempo.
4. Hands-together practice where appropriate.
5. A musical application or short piece.
6. A clear self-check before finishing.

Useful success criteria include statements such as:

- Play four correct repetitions without stopping.
- Begin at 50 BPM and increase only when relaxed.
- Count aloud while maintaining an even pulse.
- Stop if there is pain or persistent tension.

The course should also provide an easier option and a gentle challenge in each
lesson. Adults differ greatly in available practice time, coordination, prior
musical experience, hand mobility, and comfort with notation.

## UI and user-experience recommendations

The current page provides a lesson list, PDF and MP3 links, per-user completion
tracking, and a form for generating additional lessons. For a course, the main
screen should feel more like a guided practice space than a file library.

### Use three top-level tabs

Split the current single page into three clear areas:

1. **Piano Lessons** — the structured adult course, progress, next lesson,
   lesson PDFs, and practice audio.
2. **AI Composition** — prompt-based creation of original music and custom
   lessons, including the Kimi/Codex advanced option and generation progress.
3. **Music Library** — the curated public-domain sheet-music collection, with
   search and filtering.

**Piano Lessons** should be the default tab because guided learning is the
main recurring activity. Remember the last selected tab for returning users,
but let a direct URL such as `#lessons`, `#compose`, or `#library` open a
specific tab. This also makes links bookmarkable and browser Back/Forward
navigation predictable.

On narrow screens, keep the three labels short enough to remain visible in one
row, or use a clearly labelled navigation menu rather than a horizontally
scrolling tab bar. Implement the tabs as accessible controls with keyboard
navigation, a visible selected state, and appropriate ARIA attributes.

Suggested contents:

| Tab | Primary content | Primary action |
| --- | --- | --- |
| Piano Lessons | Next lesson, course weeks, progress, PDF and audio | Continue lesson |
| AI Composition | Music prompt, generation status, and generated pieces | Compose music |
| Music Library | Curated public-domain scores | Open or play |

The custom **Create piano lesson** tool could live under an advanced section
inside **AI Composition**, while the reviewed Day 1–30 curriculum remains in
**Piano Lessons**. This prevents experimental AI material from looking like
part of the reviewed course.

### Make the next lesson the primary action

At the top of the lesson area, show one prominent **Continue with Day N** card
containing:

- lesson title and estimated practice time;
- the skill being learned today;
- **Open lesson** and **Play audio** buttons;
- completion state and a **Mark complete** button;
- a small indication of what comes next.

Keep the complete lesson list underneath as a secondary course overview. This
reduces choice overload while preserving easy access to earlier material.

### Group lessons by week

Display Days 1–30 in collapsible weekly sections using the themes from
`CURRICULUM.md`. Each week should show a compact completion summary, such as
**5 of 7 lessons complete**. Bonus lessons should be visibly marked as optional
instead of appearing to interrupt the numbered sequence.

### Add a useful progress view

A simple month progress indicator should show:

- completed lessons out of 30;
- current week and next recommended day;
- recent practice activity;
- review lessons that are due.

Progress should never imply that the student has failed for missing a day.
Prefer **Lesson 12 of 30** over streak pressure. Adult learners often have
irregular schedules.

### Improve lesson playback

Instead of opening the MP3 in another browser tab, provide an inline player
with:

- play, pause, restart, and a clear time display;
- playback speed controls such as 0.5×, 0.75×, and 1×;
- a one-bar count-in option;
- repeat exercise and repeat lesson controls;
- labels separating individual exercises in the combined audio;
- separate-hands audio when a lesson uses both hands.

The PDF should open in an embedded viewer where practical, with clear
**Download PDF** and **Print** actions still available.

### Show the practice plan before opening the PDF

Each lesson card can summarize the session:

> 25 minutes · C major scale · right hand · 50 BPM · three exercises

Also show prerequisites and a brief success check. This lets an adult learner
decide whether to start now or return when enough practice time is available.

### Separate learning from content creation

The **Create piano lesson** form is useful for experimentation, but it should
not compete visually with the structured course. Put it under an **Advanced**
or **Create a custom lesson** section after the curriculum. Clearly label
custom lessons as AI-generated and separate them from reviewed course lessons.

The Kimi/Codex choice is an implementation detail for most learners. It can be
hidden under advanced options while retaining the existing default.

### Make completion more meaningful

Replace the small text-only completion link with a proper button or checkbox.
Before marking a lesson complete, optionally ask the learner to confirm simple
self-checks:

- I can play the exercise slowly without stopping.
- I can keep a steady count.
- My hands and shoulders remain comfortable.

These should guide reflection, not block progress. A learner must always be
able to mark a lesson complete or return it to practice.

### Add notes and difficulty feedback

Allow a short private note for each lesson, for example **left-hand change is
still difficult**. A three-choice difficulty control—**comfortable**, **needs
practice**, or **too difficult**—would support better review suggestions and
help identify lessons that need curriculum revision.

### Improve accessibility

The interface should support:

- a comfortable default font size and a larger-text option;
- strong contrast and visible keyboard focus states;
- controls with descriptive text rather than colour alone;
- sufficiently large touch targets for tablets near a piano;
- complete keyboard navigation and screen-reader labels;
- no essential interaction that depends on hover;
- an option to prevent the screen from sleeping during practice.

The layout should work especially well in landscape orientation on a tablet,
with the score occupying most of the screen and playback controls remaining
reachable.

### Keep technical details out of the normal practice flow

Detailed job diagnostics are valuable when generation fails, but they should
remain collapsed by default. During lesson creation, show plain-language stages
such as **Writing lesson**, **Engraving exercises**, and **Creating audio**.
Offer the technical log only through a secondary disclosure control.

## Recommended generation strategy

Use AI to write welcoming explanations, practice advice, and troubleshooting
text. Do not rely on AI alone to reconstruct established melodies.

For named music, keep reviewed note data in the project and inject it into the
lesson deterministically. Then validate that:

- the score uses the intended notes, rhythm, key, and time signature;
- the MP3 matches the printed score;
- both hands contain the same number of beats when combined;
- accidentals are printed and played correctly;
- lesson references agree with `CURRICULUM.md`;
- every promised theme is recognizable at the intended beginner level.

## Suggested next pass

1. Regenerate Day 22 with the corrected G major scale.
2. Add reviewed source melodies for the named public-domain themes.
3. Regenerate Days 27–30 using those fixed melodies.
4. Review Days 1–26 for genuine chord usage and correct references.
5. Have a pianist play every PDF while listening to its MP3.
6. Only then use Month One as the foundation for Months Two through Six.
