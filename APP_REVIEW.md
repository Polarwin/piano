# Piano Composer App Review

Reviewed: 21 August 2026

## Overview

This project contains a command-line AI piano-composition application:

- `compose.py` asks the Kimi CLI to generate a structured piano score from a
  plain-language prompt.
- `musiclib.py` validates the score and renders sheet music (PDF), MIDI, WAV,
  and MP3 files.
- `install_piano.sh` configures an nginx file listing so generated files can be
  downloaded by devices on the same local network.

It is currently a command-line application with an nginx file browser, not a
graphical web application.

## Checks performed

- Python compilation of `compose.py` and `musiclib.py`: passed.
- Command-line argument/help generation: passed.
- Existing JSON score to PDF and MIDI smoke test: passed.
- Shell syntax validation of `install_piano.sh`: passed.
- Required executables found: Kimi CLI, FFmpeg, and nginx.

The installer was not executed, no service configuration was changed, and no
external Kimi composition job was started during this review.

## Issues found

### 1. PDF spacing assumes 4/4 time

`musiclib.py` calculates horizontal note positions using `beat / 4`. In 3/4 or
2/4 music, notes occupy only part of each measure instead of using its full
width.

Location: `musiclib.py`, function `draw_hand`, around line 366.

Recommended fix: pass the measure length into `draw_hand` and divide by the
actual number of beats.

### 2. Non-ASCII MIDI titles may corrupt the metadata track

The MIDI track-name event uses the number of Python characters as its byte
length. Accented and non-Latin characters use multiple UTF-8 bytes, so the
declared event length can be wrong.

Location: `musiclib.py`, function `write_midi`, around line 206.

Recommended fix: encode the title first and use the length of the encoded byte
string. The event length should also use MIDI variable-length encoding.

### 3. Slash-bass notes are ignored by some accompaniments

Chord symbols such as `G/B` are parsed correctly, but the `flowing` and
`alberti` accompaniment generators start from the chord root rather than the
requested slash bass. The `waltz` and `chords` patterns do use the slash bass.

Location: `musiclib.py`, left-hand generation around lines 141–156.

Recommended fix: use the parsed bass note as the first/lowest note in all
accompaniment patterns.

### 4. Installer changes home-directory permissions

The installer runs `chmod o+x` on the invoking user's home directory. This is
a persistent permission change and is not reversed by the documented uninstall
command. It is also unnecessary when normal files are copied directly into
`/srv/files/piano`.

Location: `install_piano.sh`, around line 48.

Recommended fix: remove this permission change. If symlink support is required,
document it separately and request explicit permission before changing a home
directory.

### 5. Existing nginx configuration can be overwritten

The installer writes directly to
`/etc/nginx/conf.d/piano-files.conf`. If that file already exists, it is
replaced without a backup. A later failure or uninstall could therefore remove
pre-existing configuration.

Location: `install_piano.sh`, around lines 50–64.

Recommended fix: stop if the target configuration already exists, or create a
backup and restore it during rollback.

## Suggested priority

1. Protect existing nginx configuration and remove the home-directory
   permission change before running the installer.
2. Correct MIDI title encoding before generating pieces with international
   titles.
3. Correct time-signature spacing and slash-bass accompaniment behavior.
4. Add automated tests for 3/4 spacing, Unicode MIDI titles, slash chords, and
   installer rollback behavior.
