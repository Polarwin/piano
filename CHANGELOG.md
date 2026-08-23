# Changelog

## 2026-08-23 — Month Three curriculum

- Added the complete Days 61–90 adult curriculum: musical phrases and 6/8,
  D major and dominant seventh harmony, texture and interpretation, and a
  progressive preparation path for Schumann's *Soldier's March*.
- Added genuine `[6,8]` validation, engraving timing, 3+3 eighth-note beaming
  on single staves, MIDI metadata, and play-along timing to the lesson engine.
- Kept Days 62–63 explicit about the current pickup/tie engraving limitation;
  their listening and counting drills do not fake ties as repeated attacks or
  pad a pickup into misleading notation.
- Generated and audited one PDF and MP3 for every Day 61–90. All PDFs are two
  to four pages; most audio is under two minutes, with three D-major harmony
  lessons lasting about 124 seconds.
- Days 82–90 prepare the authentic Music Library edition of Schumann's
  *Soldier's March, Op. 68 No. 2* without generating a conflicting rewrite.

## 2026-08-22 — Reviewed-score matching before transcription

- Song conversion now compares several ten-second windows with local-library
  MIDI while allowing transposed performances during matching.
- Strong title and musical matches publish the reviewed PDF, MIDI and MP3
  instead of rebuilding a lossy generic arrangement.
- When the local library has no confident match, conversion searches Mutopia
  for explicitly licensed MIDI/PDF candidates and applies the same confidence
  checks before using one.
- Low-confidence results still fall back to Basic Pitch transcription and the
  existing two-hand arranger; `--no-score-match` disables lookup explicitly.
- Job details now identify when a reviewed score was matched and report its
  confidence, musical similarity and detected pitch shift.

Notable changes to Piano Studio are recorded here.

## 2026-08-22

### Changed

- Split the web interface into three focused tabs: **Piano Lessons**,
  **AI Composition**, and **Music Library**.
- Made Piano Lessons the default first-time view and remembered the most
  recently selected tab for returning users.
- Added bookmarkable `#lessons`, `#compose`, and `#library` navigation with
  browser Back and Forward support.
- Added keyboard-accessible tab navigation using Left, Right, Home, and End.
- Moved custom AI lesson generation into a collapsed advanced section under
  AI Composition so it is clearly separated from the reviewed curriculum.
- Placed generated pieces directly in AI Composition, beside the tools that
  created them, and kept Music Library focused on curated public-domain scores.
- Reworked headings and introductory text around the three main user tasks.
- Improved narrow-screen tab sizing, keyboard focus visibility, and external
  link safety.
- Replaced the visible Amazing Grace melody-line edition with a simplified
  two-hand piano-solo course arrangement in F major, including PDF, MIDI, and
  MP3 files.
- Added simplified two-hand course editions of Twinkle, Eine kleine
  Nachtmusik, and the Surprise Symphony theme in place of melody-only,
  orchestral, and duet library editions.

### Added

- Added `make_library_arrangements.py` as a reproducible home for reviewed
  two-hand library arrangements, beginning with Amazing Grace.
- Added `render_library_midi.py` to create playable MP3 files from existing
  piano-solo MIDI scores without requiring a system MIDI synthesizer.
- Added `song_to_piano.py` to turn MIDI—and MP3, WAV, M4A, WebM, MP4, MKV and
  other audio formats when Basic Pitch is available—into a simplified
  two-hand piano-solo PDF, MIDI, WAV, and MP3.
- Integrated song-to-piano conversion into AI Composition with file upload,
  meter, accompaniment, tempo and length controls, background progress, and
  automatic publication in Your AI Compositions.
- Added public or intranet shared-link input with redirect validation,
  supported-extension checks, dangerous-address blocking, and a 100 MB limit.
- Song conversion now detects embedded MIDI time signatures, estimates meter
  from rhythmic accents when metadata is absent, and derives arrangement
  length from the source duration with a 64-measure safety cap.
- Installed Spotify Basic Pitch in an isolated Python 3.11 environment and
  connected it to the converter, enabling MP3/M4A/WebM/MP4/MKV transcription
  without changing Piano Studio's system Python 3.14 runtime.
- Improved converted-song naming from uploaded or URL-encoded source names,
  removed trailing video IDs, expanded chord recognition to all chromatic
  major/minor roots, made melody tracking favour a continuous line, and raised
  automatic full-song arrangements from 64 to 256 bars.
- Added automatic right-hand register normalization plus lower/original octave
  overrides, and fixed UTF-8 MIDI title lengths for non-Latin song names.
- Added protected, intranet-only delete buttons for generated AI compositions.
  Public-host requests, curated scores, and course lessons cannot delete files.
- Stopped retaining WAV files after successful MP3 encoding and removed WAV
  links from newly generated prompt compositions and song conversions.

### Documentation

- Added `ADULT_LESSON_REVIEW.md` with the Month One curriculum review, adult
  learning recommendations, UI guidance, and suggested remediation work.
