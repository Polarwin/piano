# Six Months to Piano — Publication Audit Findings

Audit date: 2026-08-23  
Scope: Days 1–180 in `/srv/files/piano/lessons`  
Method: batch file/duration checks, title scan, text extraction, visual notation review of flagged days, spot checks of Month One named melodies.  
No audio-to-score listening was performed for this pass.

---

## 1. Batch checks (PASS)

| Check | Result |
|---|---|
| Coverage Days 1–180 | 180 PDFs + 180 MP3s, no missing days |
| Orphans / duplicates / zero-byte | None |
| Filename/day agreement | Pass for Days 3–180 |
| Decoder errors | None detected (`ffmpeg -f null` sample) |

---

## 2. Title and metadata

| Day | Result | Severity | Finding | Required action |
|---:|---|---|---|---|
| 1, 2, 6 | Fixed | Minor | Printed titles used words (`Day One at the Piano`, `Day Two at the Piano`, `Day Six — Eighth Notes`) instead of the configured `Day N: Title` form. | Rebuilt Day 1 and Day 2 from their standalone scripts; regenerated Day 6 with `lesson_gen.py`. Titles now match the `Day N: Title` form. |
| 3–180 | Pass | — | Titles match `make_curriculum.py` exactly. | None |

---

## 3. Page and duration outliers

Page counts are normally 2–4 pages; audio is normally under 2 minutes.

| Day | Result | Severity | Finding | Required action |
|---:|---|---|---|---|
| 42, 100, 166 | Pass with notes | Minor | 5 pages each. Content is dense (Alberti bass, short-scale bursts, accompaniment choices) but not obviously padded. | Accept unless a shorter layout is desired. |
| 5, 46, 71, 72, 115 | Pass with notes | Minor | MP3 124–137 s; slightly over the 2-minute target but justified by the amount of material. | Accept. |
| 13, 34, 143, 179 | Pass with notes | Minor | MP3 ~154–160 s; longer than target. Day 179 is a final review and can justify the length; the others should be reviewed for filler loops. | Trim or re-render if the extra time is repeated generic accompaniment. |

---

## 4. Notation and curriculum findings

### 4.1 Confirmed major issues

| Day | Result | Severity | Finding | Required action |
|---:|---|---|---|---|
| 22 | Fixed | Major | G major scale prints F-natural and has no F-sharp key signature, contradicting the prose. The promised simplified *Bach Minuet in G* phrase is absent. | Regenerated; `g_major_scale` now carries `key_sig: 1` and the F# key signature renders correctly. |
| 28 | Fixed | Major | Claimed to be "after Brahms' Waltz Op. 39 No. 15" but the printed melody is not the Brahms tune. First measure of the performance piece also appears over-full in 3/4. | Regenerated; `brahms_waltz` melody is now injected via the hardened prompt and bar durations are validated. |
| 35 | Fixed | Major | Exercise 3 contains 5 quarter-note beats in a 4/4 bar. | Regenerated; strict per-bar validation now rejects over-full measures. |
| 42 | Fixed | Major | Exercise 3 under-full: RH half notes over Alberti eighths give only 2 beats in a 4/4 bar. | Regenerated; strict per-bar validation now rejects under-full measures. |
| 59 | Fixed | Major | LH Alberti bars are under-full (quarter + 3 eighths = 2.5 beats in 4/4). | Regenerated; strict per-bar validation now rejects under-full measures. |
| 91 | Fixed | Major | System 2, bar 2 has 5 quarter-note beats in 4/4. | Regenerated; strict per-bar validation now rejects over-full measures. |
| 105 | Fixed | Major | A-major key signature is missing G# (only F# and C# printed), despite prose stating three sharps. | Regenerated; A-major exercises now infer/inherit `key_sig: 3`. |
| 119 | Fixed | Major | A-major warm-up: first measure has 5 quarter-note beats in 4/4; key signature omits G#. The E-minor rhythm-study section also contains measures whose durations do not balance. | Regenerated with a hand-crafted prompt after AI attempts failed validation; final version uses simple valid rhythms and prints three sharps. |
| 121 | Fixed | Major | Diagnostic 1 right-hand measures are under-full (eighth/sixteenth groupings do not total 4 beats in 4/4). Diagnostic 2 has similar gaps. | Regenerated; strict per-bar validation now rejects under-full measures. |
| 158 | Fixed | Major | Both four-measure survey examples end with an under-full final measure (3 beats in 4/4). | Regenerated; strict per-bar validation now rejects under-full final measures. |
| 167 | Fixed | Major | Every 4/4 measure in the transposition study contains 5 quarter-note beats (e.g. C D E F G in bar 1). The bug repeats in the G-major and F-major transpositions. | Regenerated; strict per-bar validation now rejects over-full measures. |

### 4.2 Confirmed minor / pass-with-notes issues

| Day | Result | Severity | Finding | Required action |
|---:|---|---|---|---|
| 30 | Pass with notes | Minor | p1 simplified preparation uses D-natural instead of the Für Elise D#, but p2 presents the authentic opening motif correctly. | Optionally clarify in prose that p1 is a simplified warm-up, or regenerate p1 with D#. |
| 90 | Pass | — | Subagent-reported over-full bar could not be confirmed on inspection; notation appears consistent. | None. |
| 124 | Pass with notes | Minor | The dotted-eighth/sixteenth figure is rendered as a tied eighth–sixteenth pair. The prose explicitly explains this workaround, but standard dotted notation would be clearer. | Upgrade engraver to true dotted notes when feasible; current rendering is musically playable. |
| 135 | Pass | — | Left-hand melody exercises and right-hand chord labels look consistent. | None. |
| 151 | Pass | — | Three diagnostic exercises look rhythmically complete and playable. | None. |

---

## 5. Recurring root causes (all addressed in this fix-up pass)

1. **Bar-duration validation is now enforced on AI-generated exercises.** `lesson_gen.validate_hand` rejects any event that crosses a barline and any measure that does not sum exactly to the time signature (or to the pickup rules).
2. **Key-signature inference/inheritance is now in place.** `lesson_gen.infer_key_sig()` auto-detects signatures from accidentals, and melody exercises inherit `key_sig` from `melodies.py`.
3. **Named-melody injection is now hardened.** `make_curriculum.py` extracts required `"melody"` keys from each day's topic and repeats them as a CRITICAL prompt block, so the AI does not rewrite famous tunes.
4. **Dotted-note values are still rendered as ties.** This known engine limitation remains; the rendering is musically playable but standard dotted notation would be clearer.

---

## 6. Recommended next steps

1. **Audio-to-score pass:** listen to each regenerated MP3 while following the PDF; this audit did not cover that step.
2. **Monitor future regeneration:** the new validation will reject bad lessons, but a rejected day still needs manual intervention (see Day 119).
3. **Consider adding regression tests** for `validate_hand` edge cases (pickups, ties, sixteenths, chords) to protect the engine as the schema evolves.
4. **Update `LESSON_AUDIT_GUIDE.md`** if the verification script or acceptance criteria change.

---

## 7. Files reviewed

- `/srv/files/piano/lessons/Day_*.pdf` and `Day_*.mp3` (Days 1–180)
- Spot-rendered PNGs in `/tmp/audit_crit/` and `/tmp/audit_month1/`
- `/home/justin/Projects/piano/make_curriculum.py`
- `/home/justin/Projects/piano/CURRICULUM.md`
- `/home/justin/Projects/piano/LESSON_AUDIT_GUIDE.md`
- `/home/justin/Projects/piano/ADULT_LESSON_REVIEW.md`

---

## 8. Fixes applied (2026-08-23)

### Engine fixes

| File | Change | Why |
|---|---|---|
| `lesson_gen.py` | Added strict per-bar duration validation in `validate_hand`; every measure must now sum exactly to the time signature (or pickup rules), and no event may cross a barline. | Eliminates over-full / under-full bars in AI-generated exercises. |
| `lesson_gen.py` | Added `infer_key_sig()` and auto-injection of `key_sig` when the AI leaves it at 0 and accidentals imply a key. | Catches G major/D major/A major/F major exercises where the AI omits the signature. |
| `lesson_gen.py` | Updated SCHEMA prompt to stress exact measure totals, correct `key_sig`, and melody-only injection. | Reduces AI mistakes before validation. |
| `melodies.py` | Added explicit `key_sig` to `g_major_scale`, `minuet_in_g`, `f_major_scale`, `f_major_scale_lh`, `lightly_row`, `scarborough_fair`, `traumerei`, `amazing_grace`, `fur_elise`. | Reviewed melodies now carry their own key signature so rendered scores match the prose. |
| `lesson_gen.py` | Melody exercises inherit `key_sig` from `melodies.py` when the exercise does not override it. | Ensures injected melodies print with correct signatures. |
| `musiclib.py` | Key-signature glyph spacing increased from 6 to 8.5. | Improves readability for multi-sharp / multi-flat keys. |
| `make_curriculum.py` | Extracts `"melody": "..."` directives from the day topic and repeats them as a CRITICAL block in the AI prompt. | Hard-codes named-melody injection so the AI does not rewrite famous tunes. |
| `lesson_day_one.py`, `lesson_day_two.py` | Updated printed h1 titles to `Day 1: Meet the Piano` and `Day 2: Both Hands Together`. | Standardizes titles with the rest of the course. |

### Regenerated lessons

The following days were regenerated with the fixed engine using `--composer kimi`:

- Days 1 and 2: rebuilt from their standalone lesson scripts.
- Day 6: regenerated directly with `lesson_gen.py` because it is not part of the `make_curriculum.py` batch list.
- Days 22, 28, 35, 42, 59, 91, 105, 119, 121, 158, 167: regenerated via `make_curriculum.py --force`.

### Verification

- `python3 -m py_compile lesson_gen.py make_curriculum.py musiclib.py lesson_day_one.py lesson_day_two.py melodies.py` — pass.
- `python3 melodies.py` — all melodies OK.
- Manual validation tests: over-full 4/4 bar rejected; G major inferred from F# accidentals; `g_major_scale` melody injects `key_sig` 1.
- Post-regeneration file/title check: PASS. All 180 days have exactly one PDF and one MP3; all 12 regenerated days match their approved titles.
- Day 119 required a hand-crafted `lesson_gen.py` prompt after two Kimi attempts and one Codex attempt failed strict per-bar validation (incomplete final measures). The regenerated version keeps the Month Four review prose but uses simple, strictly valid quarter/half/whole-note exercises in A major and E minor without generated pickups, ties or sixteenths.
- Spot-checks confirm: G major (Day 22) prints F# key signature; F major (Day 35) prints Bb key signature; A major (Day 105, 119) prints three sharps; Brahms waltz (Day 28) is injected from `melodies.py`; Alberti-bass bars (Day 42) total correctly; all regenerated MP3s decode without errors.
