#!/usr/bin/env python3
"""Render Standard MIDI library files to MP3 with a lightweight piano sound.

This pure-standard-library renderer is intentionally modest, but makes the
downloaded public-domain piano MIDI files playable without FluidSynth or a
system soundfont. It supports PPQ MIDI, tempo changes, running status, and
note-on/note-off events.
"""
import argparse
from array import array
import math
from pathlib import Path
import struct
import subprocess
import sys
import wave


LIBRARY = Path("/srv/files/piano/library")
PIANO_SOLOS = (
    "Bach_Minuet_in_G",
    "Bach_Little_Prelude_BWV939",
    "Beethoven_Fur_Elise",
    "Beethoven_Moonlight_Sonata",
    "Beethoven_Ode_to_Joy",
    "Beethoven_Symphony5",
    "Brahms_Lullaby",
    "Brahms_Waltz_Op39_No15",
    "Burgmuller_Arabesque_Op100_No2",
    "Clementi_Sonatina_Op36_No1",
    "Debussy_Clair_de_Lune",
    "Pachelbel_Canon_in_D",
    "Schumann_Traumerei",
    "Schumann_Little_Piece_Op68_No5",
    "Schumann_Melody_Op68_No1",
    "Schumann_Soldiers_March_Op68_No2",
)


def vlq(data, pos):
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7f)
        if not byte & 0x80:
            return value, pos


def parse_midi(path, include_metadata=False):
    data = path.read_bytes()
    if data[:4] != b"MThd":
        raise ValueError(f"{path}: not a Standard MIDI file")
    header_len = struct.unpack(">I", data[4:8])[0]
    _, tracks, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError(f"{path}: SMPTE timing is not supported")
    pos = 8 + header_len
    tempos = [(0, 500000)]
    time_signatures = []
    notes = []
    for track_no in range(tracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError(f"{path}: missing track {track_no}")
        size = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        chunk, pos = data[pos + 8:pos + 8 + size], pos + 8 + size
        p = tick = 0
        running = None
        active = {}
        while p < len(chunk):
            delta, p = vlq(chunk, p)
            tick += delta
            status = chunk[p]
            if status & 0x80:
                p += 1
                if status < 0xf0:
                    running = status
            elif running is not None:
                status = running
            else:
                raise ValueError(f"{path}: invalid running status")
            if status == 0xff:
                kind = chunk[p]; p += 1
                length, p = vlq(chunk, p)
                payload = chunk[p:p + length]; p += length
                if kind == 0x51 and length == 3:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                elif kind == 0x58 and length >= 2:
                    time_signatures.append((tick, payload[0], 2 ** payload[1]))
                continue
            if status in (0xf0, 0xf7):
                length, p = vlq(chunk, p)
                p += length
                continue
            kind, channel = status & 0xf0, status & 0x0f
            if kind in (0xc0, 0xd0):
                p += 1
                continue
            a, b = chunk[p], chunk[p + 1]
            p += 2
            key = (channel, a)
            if kind == 0x90 and b:
                active.setdefault(key, []).append((tick, b))
            elif kind == 0x80 or (kind == 0x90 and not b):
                starts = active.get(key)
                if starts:
                    start, velocity = starts.pop(0)
                    notes.append((start, tick, a, velocity))
        for (_, note), starts in active.items():
            notes.extend((start, tick, note, velocity) for start, velocity in starts)
    result = (division, sorted(set(tempos)), notes)
    return result + ({"time_signatures": sorted(set(time_signatures))},) if include_metadata else result


def tick_converter(division, tempos):
    segments = []
    last_tick = 0
    seconds = 0.0
    tempo = 500000
    for tick, new_tempo in sorted(tempos):
        if tick > last_tick:
            segments.append((last_tick, tick, seconds, tempo))
            seconds += (tick - last_tick) * tempo / division / 1_000_000
            last_tick = tick
        tempo = new_tempo
    segments.append((last_tick, float("inf"), seconds, tempo))

    def convert(tick):
        for start, end, base, usec in segments:
            if tick < end:
                return base + (tick - start) * usec / division / 1_000_000
        raise AssertionError
    return convert


def render_wav(midi_path, wav_path, sample_rate=16000):
    division, tempos, raw_notes = parse_midi(midi_path)
    to_seconds = tick_converter(division, tempos)
    notes = [(to_seconds(a), to_seconds(b), note, velocity)
             for a, b, note, velocity in raw_notes if b > a]
    if not notes:
        raise ValueError(f"{midi_path}: no notes")
    duration = max(end for _, end, _, _ in notes) + 2.5
    mix = array("f", [0.0]) * int(duration * sample_rate)
    table_size = 4096
    sine = [math.sin(2 * math.pi * i / table_size) for i in range(table_size)]
    mask = table_size - 1
    for start, end, midi, velocity in notes:
        frequency = 440 * 2 ** ((midi - 69) / 12)
        held = max(0.06, end - start)
        decay = min(2.4, 1.25 * 2 ** ((60 - midi) / 44))
        count = int(min(held + decay, 3.0) * sample_rate)
        base = int(start * sample_rate)
        step = frequency * table_size / sample_rate
        amplitude = (velocity / 127) ** 1.5 * 0.17
        phase = 0.0
        for i in range(min(count, len(mix) - base)):
            t = i / sample_rate
            envelope = min(1.0, t / .008) * math.exp(-t / decay)
            if t > held:
                envelope *= math.exp(-(t - held) * 4.0)
            p = int(phase) & mask
            mix[base + i] += amplitude * envelope * (
                sine[p] + .28 * sine[int(phase * 2.003) & mask]
                + .09 * sine[int(phase * 3.007) & mask])
            phase += step
    peak = max(max(mix), -min(mix), .001)
    gain = .92 / peak
    pcm = array("h", (max(-32767, min(32767, int(v * gain * 32767))) for v in mix))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(wav_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())
    return duration, len(notes)


def render(stem, directory):
    midi = directory / f"{stem}.mid"
    mp3 = directory / f"{stem}.mp3"
    wav = directory / f".{stem}.rendering.wav"
    duration, count = render_wav(midi, wav)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                        "-codec:a", "libmp3lame", "-q:a", "4", str(mp3)], check=True)
    finally:
        wav.unlink(missing_ok=True)
    return mp3, duration, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pieces", nargs="*", choices=PIANO_SOLOS,
                        default=list(PIANO_SOLOS))
    parser.add_argument("--directory", type=Path, default=LIBRARY)
    args = parser.parse_args()
    for stem in args.pieces:
        output, duration, notes = render(stem, args.directory)
        print(f"created: {output} ({duration:.0f}s, {notes} notes)", flush=True)


if __name__ == "__main__":
    main()
