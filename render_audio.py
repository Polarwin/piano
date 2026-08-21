#!/usr/bin/env python3
"""Render Whispers at Dusk to audio without an external MIDI synthesizer."""
from array import array
import math, os, wave
import make_romantic_nocturne as score

SR = 32000

def bpm_for_bar(bar):
    bpm=64
    if 16<=bar<32: bpm=68
    elif 32<=bar<48: bpm=61
    elif 48<=bar<64: bpm=66
    if bar%16>=13: bpm -= (bar%16-12)*2
    return bpm

bar_starts=[0.0]
for bar in range(80):
    bar_starts.append(bar_starts[-1]+240/bpm_for_bar(bar))

duration=bar_starts[-1]+3.0
mix=array('f',[0.0])*int(duration*SR)
table_size=8192
sines=[math.sin(2*math.pi*i/table_size) for i in range(table_size)]

def add_note(start, midi, beats, velocity, hand):
    freq=440.0*2**((midi-69)/12)
    # Higher notes decay more quickly; bass is allowed to bloom under the pedal.
    decay=(2.7 if hand=='lh' else 2.15)*2**((60-midi)/40)
    sustain=beats*60/bpm_for_bar(min(79,int(start/3.5)))
    length=min(4.2,sustain+decay)
    count=int(length*SR); base=int(start*SR)
    amp=(velocity/127)**1.65 * (0.25 if hand=='rh' else 0.21)
    phase=0.0; step=freq*table_size/SR
    # A mellow piano spectrum: fundamental plus octave and twelfth.
    for i in range(count):
        idx=base+i
        if idx>=len(mix): break
        t=i/SR
        attack=min(1.0,t/0.009)
        env=attack*math.exp(-t/decay)
        if t>sustain+0.25: env*=math.exp(-(t-sustain-0.25)*2.8)
        p=int(phase)&(table_size-1)
        p2=int(phase*2.003)&(table_size-1)
        p3=int(phase*3.008)&(table_size-1)
        tone=sines[p]+0.34*sines[p2]+0.13*sines[p3]
        mix[idx]+=amp*env*tone
        phase+=step

for bar,m in enumerate(score.measures):
    sec_per_beat=60/bpm_for_bar(bar)
    for hand_name, notes, vel in [('rh',m['rh'],67),('lh',m['lh'],50)]:
        beat=0.0
        for midi,beats in notes:
            expressive=vel+int(9*math.sin((bar%16)/15*math.pi))+(5 if 32<=bar<48 else 0)
            add_note(bar_starts[bar]+beat*sec_per_beat,midi,beats,expressive,hand_name)
            beat+=beats

peak=max(max(mix),-min(mix),0.001)
gain=0.92/peak
pcm=array('h',(max(-32767,min(32767,int(v*gain*32767))) for v in mix))
if os.sys.byteorder!='little': pcm.byteswap()
_OUTDIR = "/srv/files/piano" if os.path.isdir("/srv/files/piano") and os.access("/srv/files/piano", os.W_OK) else os.path.dirname(__file__)
out=os.path.join(_OUTDIR,'Whispers_at_Dusk.wav')
with wave.open(out,'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f'Rendered {out}: {duration:.1f} seconds')
