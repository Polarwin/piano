#!/usr/bin/env python3
"""Convert a song into a simplified two-hand piano-solo arrangement (v2).

This is an improved version of song_to_piano.py. It keeps the same CLI and
output schema, but replaces the analysis core with:

- grid-search over tempo, meter, subdivision and swing on short clips,
- cross-validation of the winning grid on a held-out clip,
- key detection from the quantized melody,
- key-aware chord selection with smooth root movement,
- explicit rest handling and a continuity-biased melody extraction.

MIDI input works without additional Python packages. MP3/WAV/M4A/FLAC input
uses Spotify Basic Pitch when its `basic-pitch` command is installed.

Usage:
    python3 song_to_piano_v2.py song.mid --out My_Piano_Solo
    python3 song_to_piano_v2.py song.mp3 --out My_Piano_Solo --time 4/4
"""
import argparse
from collections import Counter, defaultdict
import copy
import html
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import os
import unicodedata
from urllib.parse import quote_plus, urljoin
from urllib.request import Request, urlopen

import musiclib
from render_library_midi import parse_midi, tick_converter


AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".webm", ".mp4", ".mkv", ".mov",
}
DEFAULT_BASIC_PITCH = Path("/home/justin/.local/share/piano-basic-pitch/bin/basic-pitch")
LIBRARY = Path("/srv/files/piano/library")
MUTOPIA = "https://www.mutopiaproject.org"
ROOT_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")

# Simple triads used for key-aware chord inference.
CHORDS = {
    name + suffix: (pc, (pc + third) % 12, (pc + 7) % 12)
    for pc, name in enumerate(ROOT_NAMES)
    for suffix, third in (("", 4), ("m", 3))
}
# Diminished triads are needed for the leading-tone chord in major keys.
CHORDS.update({
    name + "dim": (pc, (pc + 3) % 12, (pc + 6) % 12)
    for pc, name in enumerate(ROOT_NAMES)
})

KEY_SIGS = {
    "C": (0, False), "Am": (0, True), "G": (1, False), "Em": (1, True),
    "D": (2, False), "Bm": (2, True), "A": (3, False),
    "F": (-1, False), "Dm": (-1, True), "Bb": (-2, False),
    "F#m": (3, True), "E": (4, False), "C#m": (4, True),
    "B": (5, False), "G#m": (5, True), "Eb": (-3, False), "Cm": (-3, True),
}

TITLE_STOPWORDS = {
    "performed", "performance", "official", "video", "audio", "live",
    "remaster", "remastered", "piano", "solo", "the", "by", "hd",
}

# Krumhansl-Kessler probe-tone profiles (major / minor), normalised roughly.
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

METERS = [(2, 4), (3, 4), (4, 4), (6, 8)]
# Keep subdivisions to quarter/eighth notes: the current renderer cannot
# notate 16th-note durations (smallest allowed duration is 0.5 beats).
SUBDIVISIONS = (1, 2)
CLIP_LENGTH = 10.0


def title_words(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", value.lower())
    return {word for word in words if len(word) > 1 and word not in TITLE_STOPWORDS}


def title_similarity(left, right):
    a, b = title_words(left), title_words(right)
    if not a or not b:
        return 0.0, 0
    shared = len(a & b)
    return max(shared / len(a | b), shared / min(len(a), len(b))), shared


def chroma_profile(notes, start=0.0, length=None):
    values = [0.0] * 12
    finish = float("inf") if length is None else start + length
    for note_start, note_end, note, velocity in notes:
        overlap = max(0.0, min(finish, note_end) - max(start, note_start))
        if overlap:
            values[note % 12] += overlap * (.35 + velocity / 127)
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values] if norm else values


def musical_similarity(source_notes, candidate_notes):
    source_end = max(end for _, end, _, _ in source_notes)
    candidate_end = max(end for _, end, _, _ in candidate_notes)
    positions = (0.04, .35, .68)
    source_profiles = [chroma_profile(source_notes, source_end * part, 10)
                       for part in positions]
    candidate_profiles = [chroma_profile(candidate_notes, candidate_end * part, 10)
                          for part in positions]
    best = (0.0, 0)
    for shift in range(12):
        scores = []
        for source, candidate in zip(source_profiles, candidate_profiles):
            shifted = [candidate[(pc - shift) % 12] for pc in range(12)]
            scores.append(sum(a * b for a, b in zip(source, candidate)))
        score = sum(scores) / len(scores)
        if score > best[0]:
            best = score, shift
    signed_shift = best[1] if best[1] <= 6 else best[1] - 12
    return best[0], signed_shift


def candidate_notes(path):
    notes, _ = midi_notes(path)
    return notes


def local_score_candidates():
    if not LIBRARY.is_dir():
        return []
    candidates = []
    for midi in LIBRARY.glob("*.mid"):
        pdf, mp3 = midi.with_suffix(".pdf"), midi.with_suffix(".mp3")
        if pdf.is_file():
            candidates.append({"title": midi.stem.replace("_", " "),
                               "midi": midi, "pdf": pdf,
                               "mp3": mp3 if mp3.is_file() else None,
                               "source": "local music library"})
    return candidates


def mutopia_candidates(title, directory):
    words = list(title_words(title))
    if len(words) < 2:
        return []
    ordered = sorted(words, key=lambda word: (-len(word), word))
    queries = ([" ".join(ordered[:4]), " ".join(ordered[:2])]
               + [word for word in ordered if len(word) >= 4])
    ids = []
    headers = {"User-Agent": "PianoStudio/1.0 score matcher"}
    for query in queries:
        url = f"{MUTOPIA}/cgibin/make-table.cgi?searchingfor={quote_plus(query)}"
        try:
            page = urlopen(Request(url, headers=headers), timeout=10).read().decode("utf-8", "replace")
        except OSError:
            continue
        for piece_id in re.findall(r"piece-info\.cgi\?id=(\d+)", page):
            if piece_id not in ids:
                ids.append(piece_id)
        if ids:
            break
    results = []
    for piece_id in ids[:3]:
        page_url = f"{MUTOPIA}/cgibin/piece-info.cgi?id={piece_id}"
        try:
            page = urlopen(Request(page_url, headers=headers), timeout=10).read().decode("utf-8", "replace")
            heading = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
            found_title = re.sub(r"<[^>]+>", " ", heading.group(1)) if heading else title
            found_title = html.unescape(" ".join(found_title.split()))
            midi_url = re.search(r'href="([^"]+\.(?:mid|midi))"', page, re.I)
            pdf_url = re.search(r'href="([^"]+-a4\.pdf)"', page, re.I)
            if not midi_url or not pdf_url:
                continue
            midi = directory / f"mutopia-{piece_id}.mid"
            pdf = directory / f"mutopia-{piece_id}.pdf"
            for remote, target in ((midi_url.group(1), midi), (pdf_url.group(1), pdf)):
                data = urlopen(Request(urljoin(page_url, remote), headers=headers), timeout=15).read()
                target.write_bytes(data)
            results.append({"title": found_title, "midi": midi, "pdf": pdf,
                            "mp3": None, "source": page_url})
        except (OSError, ValueError):
            continue
    return results


def find_matching_score(title, source_notes, directory):
    ranked = []
    for item in local_score_candidates():
        name_score, shared = title_similarity(title, item["title"])
        if shared < 2:
            continue
        try:
            music_score, shift = musical_similarity(source_notes, candidate_notes(item["midi"]))
        except (OSError, ValueError):
            continue
        confidence = .58 * name_score + .42 * music_score
        ranked.append((confidence, name_score, music_score, shift, item))
    if not ranked or max(row[0] for row in ranked) < .57:
        for item in mutopia_candidates(title, directory):
            name_score, shared = title_similarity(title, item["title"])
            if shared < 2:
                continue
            try:
                music_score, shift = musical_similarity(source_notes, candidate_notes(item["midi"]))
            except (OSError, ValueError):
                continue
            confidence = .58 * name_score + .42 * music_score
            ranked.append((confidence, name_score, music_score, shift, item))
    if not ranked:
        return None
    confidence, name_score, music_score, shift, item = max(ranked, key=lambda row: row[0])
    if confidence < .57 or music_score < .64:
        return None
    item.update(confidence=confidence, name_score=name_score,
                music_score=music_score, pitch_shift=shift)
    return item


def publish_matching_score(match, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    midi_out, pdf_out, mp3_out = (output.with_suffix(ext) for ext in (".mid", ".pdf", ".mp3"))
    shutil.copy2(match["midi"], midi_out)
    shutil.copy2(match["pdf"], pdf_out)
    if match.get("mp3"):
        shutil.copy2(match["mp3"], mp3_out)
    else:
        from render_library_midi import render
        temp_stem = "matched_score"
        temp_midi = output.parent / f"{temp_stem}.mid"
        shutil.copy2(match["midi"], temp_midi)
        try:
            rendered, _, _ = render(temp_stem, output.parent)
            rendered.replace(mp3_out)
        finally:
            temp_midi.unlink(missing_ok=True)
    return [pdf_out, midi_out, mp3_out]


def audio_to_midi(source, directory):
    configured = os.environ.get("PIANO_BASIC_PITCH")
    command = configured or shutil.which("basic-pitch")
    if not command and DEFAULT_BASIC_PITCH.is_file():
        command = str(DEFAULT_BASIC_PITCH)
    if not command:
        raise RuntimeError(
            "Audio transcription requires Spotify Basic Pitch. Install it with "
            "`python3 -m pip install basic-pitch`, or provide a MIDI file instead.")
    decoded = directory / "source_audio.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
                    "-vn", "-ac", "1", "-ar", "22050", str(decoded)], check=True)
    subprocess.run([command, str(directory), str(decoded)], check=True)
    candidates = sorted(directory.glob("*.mid")) + sorted(directory.glob("*.midi"))
    if not candidates:
        raise RuntimeError("Basic Pitch finished without producing a MIDI file")
    return candidates[0]


def midi_notes(path):
    division, tempos, notes, metadata = parse_midi(path, include_metadata=True)
    convert = tick_converter(division, tempos)
    converted = [(convert(start), convert(end), note, velocity)
                 for start, end, note, velocity in notes if end > start]
    if not converted:
        raise ValueError("The MIDI file contains no playable notes")
    return converted, metadata


def estimate_bpm(notes):
    starts = sorted({round(start, 3) for start, _, _, _ in notes})
    gaps = [b - a for a, b in zip(starts, starts[1:]) if .15 <= b - a <= 1.5]
    if not gaps:
        return 72
    gaps.sort()
    beat = gaps[len(gaps) // 2]
    while beat < .4:
        beat *= 2
    while beat > 1.0:
        beat /= 2
    return max(40, min(120, round(60 / beat)))


def bar_beats(time):
    num, den = time
    return num * 4 / den


def grid_positions(start, end, bpm, time, subdivision, swing=False):
    """Yield (time_seconds, is_downbeat) for every grid line in [start, end]."""
    spb = 60.0 / bpm
    step = spb / subdivision
    bar_sec = bar_beats(time) * spb
    bar0 = math.floor(start / bar_sec)
    t = bar0 * bar_sec
    idx = 0
    while t < end:
        offset = t - (bar0 * bar_sec)
        is_down = offset < 1e-9
        if swing and subdivision == 2:
            # swing eighths: long-short within the beat
            beat_phase = idx % 2
            if beat_phase == 0:
                pos = t
            else:
                pos = t - step + (spb * 1 / 3)
        else:
            pos = t
        if pos >= start - 1e-9:
            yield pos, is_down
        idx += 1
        t += step


def score_grid(notes, bpm, time, subdivision, swing, clip_start, clip_end):
    """Return a float: higher means notes align better to the candidate grid."""
    spb = 60.0 / bpm
    step = spb / subdivision
    total_weight = 0.0
    score = 0.0
    grid = list(grid_positions(clip_start, clip_end, bpm, time, subdivision, swing))
    if len(grid) < 2:
        return 0.0
    grid_times = [g[0] for g in grid]
    for note_start, note_end, note, velocity in notes:
        if note_end <= clip_start or note_start >= clip_end:
            continue
        # Weight the onset most strongly; also consider mid-note if it is long.
        points = [note_start]
        if note_end - note_start > spb:
            points.append(note_start + spb * 0.5)
        for pt in points:
            if not (clip_start <= pt < clip_end):
                continue
            weight = (.35 + velocity / 127)
            total_weight += weight
            distances = [abs(pt - gt) for gt in grid_times]
            nearest = min(distances)
            # Gaussian-ish alignment score
            align = math.exp(-(nearest / (step * 0.45)) ** 2)
            # Downbeat bonus
            downbeat_bonus = 1.0
            if nearest < step * 0.3:
                grid_idx = distances.index(nearest)
                if grid[grid_idx][1]:
                    downbeat_bonus = 1.35
            score += weight * align * downbeat_bonus
    if total_weight == 0:
        return 0.0
    return score / total_weight


def candidate_bpms(seed_bpm):
    candidates = {seed_bpm}
    for factor in (0.5, 0.667, 0.75, 1.0, 1.333, 1.5, 2.0):
        b = round(seed_bpm * factor)
        if 40 <= b <= 160:
            candidates.add(b)
    for delta in (-12, -6, -3, 3, 6, 12):
        b = seed_bpm + delta
        if 40 <= b <= 160:
            candidates.add(b)
    return sorted(candidates)


def choose_clips(total_length, clip_len=CLIP_LENGTH, count=3):
    if total_length <= clip_len * (count + 1):
        # Not enough room; take one clip in the middle.
        mid = total_length / 2
        return [(max(0.0, mid - clip_len / 2), min(total_length, mid + clip_len / 2))]
    clips = []
    margin = clip_len
    usable = total_length - 2 * margin
    for i in range(count):
        start = margin + usable * i / max(1, count - 1)
        clips.append((start, start + clip_len))
    return clips


def grid_search(notes, accompaniment, declared_time=None):
    """Return (bpm, time_signature, subdivision, swing, source) with best clip fit."""
    if not notes:
        return 72, (4, 4), 2, False, "fallback"
    end_time = max(end for _, end, _, _ in notes)
    seed = estimate_bpm(notes)
    bpms = candidate_bpms(seed)
    times = [tuple(map(int, declared_time.split("/")))] if declared_time else METERS
    if accompaniment == "waltz":
        times = [(3, 4)]
    clips = choose_clips(end_time)
    best = (0.0, None)
    for bpm in bpms:
        for time in times:
            if time not in ((2, 4), (3, 4), (4, 4), (6, 8)):
                continue
            if accompaniment == "waltz" and time != (3, 4):
                continue
            for subdivision in SUBDIVISIONS:
                for swing in (False, True):
                    if swing and time[1] != 4:
                        continue
                    if swing and subdivision != 2:
                        continue
                    scores = [score_grid(notes, bpm, time, subdivision, swing, s, e)
                              for s, e in clips]
                    avg = sum(scores) / len(scores)
                    if avg > best[0]:
                        best = (avg, (bpm, time, subdivision, swing, "grid-search"))
    if best[1] is None:
        return seed, (4, 4), 2, False, "fallback"
    bpm, time, subdivision, swing, source = best[1]
    # Cross-validate on a held-out clip.
    val_start = max(0.0, end_time / 2 - CLIP_LENGTH / 2)
    val_end = min(end_time, val_start + CLIP_LENGTH)
    if val_end - val_start < 3:
        return bpm, time, subdivision, swing, source
    val_score = score_grid(notes, bpm, time, subdivision, swing, val_start, val_end)
    if val_score < best[0] * 0.70:
        # Validation failed; fall back to a conservative 4/4 straight-eighths grid.
        return seed, (4, 4), 2, False, "fallback"
    return bpm, time, subdivision, swing, source


def transpose_note(note, shift):
    return max(48, min(84, note + shift))


def fit_melody_register(note, mode):
    if mode == "lower":
        return transpose_note(note, -12)
    if mode == "original":
        return transpose_note(note, 0)
    while note > 76:
        note -= 12
    while note < 55:
        note += 12
    return transpose_note(note, 0)


def melody_at(notes, moment, previous=None, register="auto"):
    sounding = [(note, velocity) for start, end, note, velocity in notes
                if start <= moment < end and note >= 48]
    if not sounding:
        return previous
    if previous is None:
        chosen = max(sounding, key=lambda item: (item[0], item[1]))[0]
    else:
        chosen = max(sounding, key=lambda item:
                     item[1] - abs(item[0] - previous) * 3 + item[0] * .08)[0]
    return fit_melody_register(chosen, register)


def detect_key(melody_notes):
    """Return (root_pc, is_minor) from a list of (pitch, duration)."""
    if not melody_notes:
        return 0, False
    profile = [0.0] * 12
    for pitch, dur in melody_notes:
        profile[pitch % 12] += dur
    norm = math.sqrt(sum(v * v for v in profile))
    if norm == 0:
        return 0, False
    profile = [v / norm for v in profile]
    best = (0.0, 0, False)
    for shift in range(12):
        shifted = [profile[(i + shift) % 12] for i in range(12)]
        major = sum(a * b for a, b in zip(shifted, MAJOR_PROFILE))
        minor = sum(a * b for a, b in zip(shifted, MINOR_PROFILE))
        if major > best[0]:
            best = (major, (-shift) % 12, False)
        if minor > best[0]:
            best = (minor, (-shift) % 12, True)
    return best[1], best[2]


def diatonic_chords(root_pc, minor):
    """Return list of (chord_symbol, root_pc, chord_tones) for the detected key."""
    names = ROOT_NAMES
    if minor:
        # Natural minor scale degrees: i, ii°, III, iv, v, VI, VII
        intervals = [0, 2, 3, 5, 7, 8, 10]
        qualities = ["m", "dim", "", "m", "m", "", ""]
    else:
        intervals = [0, 2, 4, 5, 7, 9, 11]
        qualities = ["", "m", "m", "", "", "m", "dim"]
    chords = []
    for deg, qual in zip(intervals, qualities):
        pc = (root_pc + deg) % 12
        name = names[pc] + qual
        tones = CHORDS[name]
        chords.append((name, pc, tones))
    return chords


def chord_name_from_root(root_pc, minor):
    return ROOT_NAMES[root_pc] + ("m" if minor else "")


def chord_distance(prev_root, root):
    diff = abs((root - prev_root + 6) % 12 - 6)
    return diff


def choose_chord(notes_in_bar, key_root, minor, previous_root=None):
    """Key-aware chord choice for one bar."""
    if not notes_in_bar:
        if previous_root is not None:
            return chord_name_from_root(previous_root, minor), previous_root
        return chord_name_from_root(key_root, minor), key_root
    weights = defaultdict(float)
    for pitch, dur in notes_in_bar:
        weights[pitch % 12] += dur
    chords = diatonic_chords(key_root, minor)
    best = None
    for name, root, tones in chords:
        covered = sum(weights[t] for t in tones)
        outside = sum(v for pc, v in weights.items() if pc not in tones)
        root_bonus = weights[root] * .3
        movement = 0
        if previous_root is not None:
            dist = chord_distance(previous_root, root)
            if dist == 0:
                movement = 0.15
            elif dist in (5, 7):
                movement = 0.25  # prefer V-I and IV-I movement
            elif dist == 2:
                movement = 0.10
        score = covered - outside * .25 + root_bonus + movement
        if best is None or score > best[0]:
            best = (score, name, root)
    return best[1], best[2]


def compress_steps(steps, step_beats):
    events = []
    for note in steps:
        if note is None:
            continue
        if events and events[-1][0] == note:
            events[-1][1] += step_beats
        else:
            events.append([note, step_beats])
    result = []
    allowed = sorted(musiclib.ALLOWED_DURS, reverse=True)
    min_dur = min(allowed)
    for note, duration in events:
        while duration > 1e-9:
            part = next((value for value in allowed if value <= duration + 1e-9), None)
            if part is None:
                # Tiny remainder: round up to the smallest notatable duration.
                if duration + 1e-9 < min_dur:
                    if result and result[-1][0] == musiclib.SHARP[note % 12] + str(note // 12 - 1):
                        result[-1][1] += min_dur
                    else:
                        result.append([musiclib.SHARP[note % 12] + str(note // 12 - 1), min_dur])
                    break
                raise ValueError(f"cannot represent a {duration}-beat remainder")
            name = musiclib.SHARP[note % 12] + str(note // 12 - 1)
            result.append([name, part])
            duration -= part
    return result


def arrange(notes, title, bpm, time, subdivision, swing, max_bars,
            accompaniment, melody_register="auto"):
    numerator, denominator = time
    beats_per_bar = numerator * 4 / denominator
    if beats_per_bar not in (2, 3, 4):
        raise ValueError("Use a meter equivalent to 2, 3, or 4 quarter-note beats")
    spb = 60 / bpm
    bar_seconds = beats_per_bar * spb
    end_time = max(end for _, end, _, _ in notes)
    natural_bars = math.ceil(end_time / bar_seconds)
    bar_count = max(8, min(max_bars or 256, natural_bars))
    step_beats = 1 / subdivision
    steps_per_bar = round(beats_per_bar / step_beats)
    last_note = 60
    bars = []
    previous_root = None
    all_melody = []  # for key detection
    raw_bars = []
    for bar in range(bar_count):
        start = bar * bar_seconds
        sampled = []
        for step in range(steps_per_bar):
            moment = start + (step + .15) * step_beats * spb
            if swing and subdivision == 2:
                # Adjust sampling moment for swing feel.
                if step % 2 == 1:
                    moment += spb * (1 / 6)
            note = melody_at(notes, moment, last_note, melody_register)
            if note is not None:
                all_melody.append((note, step_beats))
            sampled.append(note)
            if note is not None:
                last_note = note
        raw_bars.append(sampled)
    key_root, minor = detect_key(all_melody)
    for bar, sampled in enumerate(raw_bars):
        start = bar * bar_seconds
        # Collect melody notes and durations for chord choice.
        bar_melody = [(n, step_beats) for n in sampled if n is not None]
        chord_name, root = choose_chord(bar_melody, key_root, minor, previous_root)
        previous_root = root
        bars.append({"chord": chord_name, "melody": compress_steps(sampled, step_beats)})
    key_sig, _ = KEY_SIGS.get(chord_name_from_root(key_root, minor), (0, minor))
    return {
        "title": title,
        "subtitle": "Simplified two-hand piano-solo arrangement",
        "key_sig": key_sig,
        "minor": minor,
        "time": list(time),
        "bpm": bpm,
        "tempo_mark": "Moderato",
        "accompaniment": accompaniment,
        "sections": [{"bar": 0, "name": "Piano solo", "dynamic": "mp"}],
        "bars": bars,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song", type=Path, help="source MIDI or audio file")
    parser.add_argument("--out", type=Path, help="output basename")
    parser.add_argument("--title", help="printed title")
    parser.add_argument("--bpm", type=int, help="override detected tempo")
    parser.add_argument("--time", choices=("auto", "2/4", "3/4", "4/4", "6/8"), default="auto")
    parser.add_argument("--subdivision", type=int, choices=(1, 2),
                        help="melody samples per beat (default: auto from grid search)")
    parser.add_argument("--max-bars", type=int,
                        help="truncate at this many bars (default: detect, capped at 256)")
    parser.add_argument("--accompaniment", choices=("flowing", "alberti", "waltz", "chords"),
                        default="flowing")
    parser.add_argument("--melody-register", choices=("auto", "lower", "original"),
                        default="auto", help="octave placement for the right-hand melody")
    parser.add_argument("--no-score-match", action="store_true",
                        help="skip local-library and Mutopia score matching")
    args = parser.parse_args()
    if args.max_bars is not None and not 8 <= args.max_bars <= 256:
        parser.error("--max-bars must be between 8 and 256")
    source = args.song.resolve()
    if not source.is_file():
        parser.error(f"file not found: {source}")
    title = args.title or source.stem.replace("_", " ").title()
    output = args.out or Path(source.stem + "_Piano_Solo")
    if args.accompaniment == "waltz" and args.time not in ("auto", "3/4"):
        parser.error("waltz accompaniment requires --time 3/4")
    with tempfile.TemporaryDirectory() as temp:
        midi = source
        from_audio = source.suffix.lower() in AUDIO_EXTENSIONS
        if from_audio:
            midi = audio_to_midi(source, Path(temp))
        elif source.suffix.lower() not in {".mid", ".midi"}:
            parser.error("input must be MIDI or a supported audio file")
        notes, metadata = midi_notes(midi)
        if from_audio and not args.no_score_match:
            match = find_matching_score(title, notes, Path(temp))
            if match:
                made = publish_matching_score(match, output)
                print(f"matched reviewed score: {match['title']} from {match['source']} "
                      f"(confidence={match['confidence']:.3f}, "
                      f"music={match['music_score']:.3f}, "
                      f"detected_shift={match['pitch_shift']:+d})")
                for path in made:
                    print("created:", path)
                return
        if from_audio:
            metadata = {"time_signatures": []}
        declared_time = None if args.time == "auto" else args.time
        bpm, time, subdivision, swing, time_source = grid_search(notes, args.accompaniment, declared_time)
        if args.bpm:
            bpm = args.bpm
            time_source = "manual override"
        if args.subdivision:
            subdivision = args.subdivision
        data = arrange(notes, title, bpm, time, subdivision, swing,
                       args.max_bars, args.accompaniment, args.melody_register)
        score = musiclib.build_score(copy.deepcopy(data))
        made = musiclib.render_all(score, str(output), audio=True)
    print(f"arranged {len(data['bars'])} bars in {time[0]}/{time[1]} "
          f"({time_source}) at {bpm} BPM, subdivision={subdivision}")
    for path in made:
        print("created:", path)


if __name__ == "__main__":
    main()
