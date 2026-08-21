#!/usr/bin/env python3
"""Render Lettre d'Amour to audio (WAV) with a soft piano-like synthesis.

Pure standard library: additive sine tones with per-note decay envelopes.
Follows the score in make_lettre_d_amour.py (Andantino, q = 69, with a
ritardando over the last four bars).
"""
from array import array
import math, os, wave
from make_lettre_d_amour import MEASURES, OUT

SR = 32000

def bpm_for_bar(bar):
    if bar >= 36:  # rit. e morendo over the coda's last phrase
        return [69, 69, 69, 69, 65, 60, 54, 46][min(7, bar - 33)] if bar >= 33 else 69
    return 69

# Phrase dynamics (peak velocity) matching the score's markings.
def base_vel(bar):
    if bar < 8:  return 58   # p dolce
    if bar < 16: return 64   # mp espressivo
    if bar < 24: return 73   # mf appassionato
    if bar < 32: return 64   # mp dolce
    if bar < 36: return 57   # p
    return 50                # pp morendo

bar_starts = [0.0]
for bar in range(len(MEASURES)):
    bar_starts.append(bar_starts[-1] + 240 / bpm_for_bar(bar))

duration = bar_starts[-1] + 4.0
mix = array('f', [0.0]) * int(duration * SR)
TBL = 8192
sines = [math.sin(2 * math.pi * i / TBL) for i in range(TBL)]

def add_note(start, midi, beats, velocity, hand, bpm):
    freq = 440.0 * 2 ** ((midi - 69) / 12)
    decay = (2.8 if hand == 'lh' else 2.2) * 2 ** ((60 - midi) / 40)
    sustain = beats * 60 / bpm
    length = min(4.5, sustain + decay)
    count = int(length * SR); base = int(start * SR)
    amp = (velocity / 127) ** 1.65 * (0.25 if hand == 'rh' else 0.20)
    phase = 0.0; step = freq * TBL / SR
    for i in range(count):
        idx = base + i
        if idx >= len(mix):
            break
        t = i / SR
        attack = min(1.0, t / 0.009)
        env = attack * math.exp(-t / decay)
        if t > sustain + 0.25:
            env *= math.exp(-(t - sustain - 0.25) * 2.8)
        p = int(phase) & (TBL - 1)
        p2 = int(phase * 2.003) & (TBL - 1)
        p3 = int(phase * 3.008) & (TBL - 1)
        mix[idx] += amp * env * (sines[p] + 0.34 * sines[p2] + 0.13 * sines[p3])
        phase += step

for bar, m in enumerate(MEASURES):
    bpm = bpm_for_bar(bar)
    spb = 60 / bpm
    # Gentle phrasing swell inside each 8-bar phrase.
    swell = int(6 * math.sin((bar % 8) / 7 * math.pi))
    for hand_name, notes, vscale in [('rh', m['rh'], 1.0), ('lh', m['lh'], 0.74)]:
        beat = 0.0
        for midi, beats in notes:
            vel = int((base_vel(bar) + swell) * vscale)
            add_note(bar_starts[bar] + beat * spb, midi, beats, vel, hand_name, bpm)
            beat += beats

peak = max(max(mix), -min(mix), 0.001)
gain = 0.92 / peak
pcm = array('h', (max(-32767, min(32767, int(v * gain * 32767))) for v in mix))
if os.sys.byteorder != 'little':
    pcm.byteswap()
out = os.path.join(OUT, 'Lettre_d_Amour.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'Rendered {out}: {duration:.1f} seconds')
