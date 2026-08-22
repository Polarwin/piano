# Changelog

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

### Documentation

- Added `ADULT_LESSON_REVIEW.md` with the Month One curriculum review, adult
  learning recommendations, UI guidance, and suggested remediation work.
