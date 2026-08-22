#!/usr/bin/env python3
"""Convert a song into a simplified two-hand piano-solo arrangement.

MIDI input works without additional Python packages. MP3/WAV/M4A/FLAC input
uses Spotify Basic Pitch when its `basic-pitch` command is installed:

    python3 song_to_piano.py song.mid --out My_Piano_Solo
    python3 song_to_piano.py song.mp3 --out My_Piano_Solo

The arranger extracts a monophonic upper melody, infers one simple chord per
bar, and renders PDF, MIDI, WAV and MP3 through musiclib. The result is an
editable first draft rather than a note-perfect transcription.
"""
import argparse
from collections import defaultdict
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
CHORDS = {
    name + suffix: (pc, (pc + third) % 12, (pc + 7) % 12)
    for pc, name in enumerate(ROOT_NAMES)
    for suffix, third in (("", 4), ("m", 3))
}
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


def title_words(value):
    """Comparable title words, independent of accents and upload decoration."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", value.lower())
    return {word for word in words if len(word) > 1 and word not in TITLE_STOPWORDS}


def title_similarity(left, right):
    a, b = title_words(left), title_words(right)
    if not a or not b:
        return 0.0, 0
    shared = len(a & b)
    # Upload names often append performer/channel text. Reward a candidate
    # whose identifying words are contained in that longer source name.
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
    """Compare multiple short windows, allowing a transposed performance."""
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
            scores.append(sum(a * b for a, b in zip(source, shifted)))
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
    """Fetch at most three explicitly licensed Mutopia MIDI/PDF candidates."""
    words = list(title_words(title))
    if len(words) < 2:
        return []
    # Short queries survive performer/channel text better than the full upload name.
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
    """Return a reviewed score only when name and musical evidence agree."""
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
    # Two shared title words plus musical agreement avoids matching generic names.
    if confidence < .57 or music_score < .64:
        return None
    item.update(confidence=confidence, name_score=name_score,
                music_score=music_score, pitch_shift=shift)
    return item


def publish_matching_score(match, output):
    """Publish the authoritative notation and MIDI, rendering audio if needed."""
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
    # Decode through FFmpeg first so video containers and compressed audio all
    # reach the transcription model in the same predictable WAV format.
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


def estimate_time_signature(notes, bpm, metadata, accompaniment):
    """Prefer embedded MIDI meter; otherwise compare 3- and 4-beat accents."""
    declared = metadata.get("time_signatures", [])
    for _, numerator, denominator in declared:
        if (numerator, denominator) in ((2, 4), (3, 4), (4, 4)):
            return numerator, denominator, "MIDI metadata"
    if accompaniment == "waltz":
        return 3, 4, "waltz accompaniment"
    seconds_per_beat = 60 / bpm
    onsets = [(start / seconds_per_beat, velocity) for start, _, _, velocity in notes]

    def accent_score(beats):
        best = 0.0
        for phase in range(beats):
            down, other = [], []
            for beat, velocity in onsets:
                nearest = round(beat)
                if abs(beat - nearest) > .22:
                    continue
                (down if (nearest - phase) % beats == 0 else other).append(velocity)
            if down and other:
                best = max(best, sum(down) / len(down) - sum(other) / len(other))
        return best
    three, four = accent_score(3), accent_score(4)
    if three > max(3.0, four * 1.15):
        return 3, 4, "rhythmic accent estimate"
    return 4, 4, "conservative rhythm estimate"


def transpose_note(note, shift):
    return max(48, min(84, note + shift))


def fit_melody_register(note, mode):
    if mode == "lower":
        return transpose_note(note, -12)
    if mode == "original":
        return transpose_note(note, 0)
    # Keep the melody centred where an adult beginner can read and play it,
    # folding transcription overtones down rather than merely clipping them.
    while note > 76:  # E5
        note -= 12
    while note < 55:  # G3
        note += 12
    return transpose_note(note, 0)


def melody_at(notes, moment, previous=None, register="auto"):
    sounding = [(note, velocity) for start, end, note, velocity in notes
                if start <= moment < end and note >= 48]
    if not sounding:
        return None
    if previous is None:
        chosen = max(sounding, key=lambda item: (item[0], item[1]))[0]
    else:
        # A singable line usually moves locally. Velocity preserves prominent
        # notes while the continuity penalty avoids grabbing isolated upper
        # accompaniment tones merely because they are highest.
        chosen = max(sounding, key=lambda item:
                     item[1] - abs(item[0] - previous) * 3 + item[0] * .08)[0]
    return fit_melody_register(chosen, register)


def choose_chord(notes, start, end, previous="C"):
    weights = defaultdict(float)
    for note_start, note_end, note, velocity in notes:
        overlap = max(0.0, min(end, note_end) - max(start, note_start))
        if overlap:
            weights[note % 12] += overlap * (.5 + velocity / 127)
    if not weights:
        return previous
    best = None
    for name, tones in CHORDS.items():
        covered = sum(weights[tone] for tone in tones)
        outside = sum(value for pc, value in weights.items() if pc not in tones)
        root_bonus = weights[tones[0]] * .25
        score = covered - outside * .18 + root_bonus + (0.08 if name == previous else 0)
        if best is None or score > best[0]:
            best = score, name
    return best[1]


def compress_steps(steps, step_beats):
    events = []
    for note in steps:
        if events and events[-1][0] == note:
            events[-1][1] += step_beats
        else:
            events.append([note, step_beats])
    # Split sustained notes into duration values accepted by musiclib.
    result = []
    allowed = sorted(musiclib.ALLOWED_DURS, reverse=True)
    for note, duration in events:
        name = musiclib.SHARP[note % 12] + str(note // 12 - 1)
        while duration > 1e-9:
            part = next((value for value in allowed if value <= duration + 1e-9), None)
            if part is None:
                raise ValueError(f"cannot represent a {duration}-beat remainder")
            result.append([name, part])
            duration -= part
    return result


def arrange(notes, title, bpm, time, subdivision, max_bars, accompaniment,
            melody_register="auto"):
    numerator, denominator = time
    beats_per_bar = numerator * 4 / denominator
    if beats_per_bar not in (2, 3, 4):
        raise ValueError("Use a meter equivalent to 2, 3, or 4 quarter-note beats")
    seconds_per_beat = 60 / bpm
    bar_seconds = beats_per_bar * seconds_per_beat
    end_time = max(end for _, end, _, _ in notes)
    natural_bars = math.ceil(end_time / bar_seconds)
    bar_count = max(8, min(max_bars or 256, natural_bars))
    step_beats = 1 / subdivision
    steps_per_bar = round(beats_per_bar / step_beats)
    last_note = 60
    bars = []
    previous_chord = "C"
    for bar in range(bar_count):
        start = bar * bar_seconds
        sampled = []
        for step in range(steps_per_bar):
            moment = start + (step + .15) * step_beats * seconds_per_beat
            note = melody_at(notes, moment, last_note, melody_register)
            if note is None:
                note = last_note
            last_note = note
            sampled.append(note)
        chord = choose_chord(notes, start, start + bar_seconds, previous_chord)
        previous_chord = chord
        bars.append({"chord": chord, "melody": compress_steps(sampled, step_beats)})
    key = max(CHORDS, key=lambda name: sum(1 for bar in bars if bar["chord"] == name))
    key_sig, minor = KEY_SIGS.get(key, (0, key.endswith("m")))
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
    parser.add_argument("--time", choices=("auto", "2/4", "3/4", "4/4"), default="auto")
    parser.add_argument("--subdivision", type=int, choices=(1, 2), default=2,
                        help="melody samples per beat (default: 2)")
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
            # Basic Pitch writes a generic 4/4 header; it is not a measurement
            # of the source meter, so let the rhythm estimator decide instead.
            metadata = {"time_signatures": []}
        bpm = args.bpm or estimate_bpm(notes)
        if args.time == "auto":
            numerator, denominator, time_source = estimate_time_signature(
                notes, bpm, metadata, args.accompaniment)
            time = (numerator, denominator)
        else:
            time = tuple(map(int, args.time.split("/")))
            time_source = "manual override"
        data = arrange(notes, title, bpm, time, args.subdivision,
                       args.max_bars, args.accompaniment, args.melody_register)
        score = musiclib.build_score(copy.deepcopy(data))
        made = musiclib.render_all(score, str(output), audio=True)
    print(f"arranged {len(data['bars'])} bars in {time[0]}/{time[1]} "
          f"({time_source}) at {bpm} BPM")
    for path in made:
        print("created:", path)


if __name__ == "__main__":
    main()
