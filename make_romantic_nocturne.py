#!/usr/bin/env python3
"""Create an original five-minute romantic piano score (PDF + MIDI).

The PDF is engraved directly with ReportLab so this project has no external
notation-program dependency.  MIDI writing uses only Python's standard library.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import math, os, random, struct

OUT = "/srv/files/piano" if os.path.isdir("/srv/files/piano") and os.access("/srv/files/piano", os.W_OK) else os.path.dirname(os.path.abspath(__file__))
PPQ = 480

NOTE_PC = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
def midi_note(name):
    letter=name[0]; i=1; accidental=0
    while i < len(name) and name[i] in "#b":
        accidental += 1 if name[i]=="#" else -1; i+=1
    octave=int(name[i:])
    return 12*(octave+1)+NOTE_PC[letter]+accidental

def note_name(n, prefer_flat=False):
    sharp=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    flat =["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"]
    return (flat if prefer_flat else sharp)[n%12]+str(n//12-1)

# Harmony: intimate E-minor opening, warm G-major middle, darker climax, return.
CHORDS = {
 "Em":(52,[0,3,7]), "C":(48,[0,4,7]), "G":(43,[0,4,7]), "D":(50,[0,4,7]),
 "Am":(45,[0,3,7]), "B7":(47,[0,4,7,10]), "Em/B":(47,[0,5,9]), "G/B":(47,[0,3,8]),
 "D/F#":(42,[0,3,8]), "Cmaj7":(48,[0,4,7,11]), "A7":(45,[0,4,7,10]),
 "F#dim":(42,[0,3,6]), "Bm":(47,[0,3,7]), "Eb":(39,[0,4,7]), "Cm":(48,[0,3,7]),
}

sections = [
 ("A — Andante, con tenerezza", ["Em","Cmaj7","G/B","B7","Em","Am","D","G","C","Am","B7","Em/B","C","F#dim","B7","Em"]),
 ("B — Un poco più mosso", ["G","D/F#","Em","Bm","C","G/B","Am","D","G","D/F#","Em","B7","Cmaj7","G/B","D","G"]),
 ("C — Appassionato", ["Cm","Eb","G","B7","Em","C","A7","D","Bm","G","Am","B7","Em","F#dim","B7","Em"]),
 ("D — Cantabile", ["G","Cmaj7","G/B","D","Em","Bm","C","D","G","D/F#","Em","C","Am","D","G","B7"]),
 ("A' — Tempo I, morendo", ["Em","Cmaj7","G/B","B7","Em","Am","D","G","Cmaj7","Am","B7","Em/B","C","F#dim","B7","Em"]),
]
progression=[]; section_marks={}
for title, seq in sections:
    section_marks[len(progression)] = title
    progression += seq

SCALE = [0,2,3,5,7,9,10]  # E natural minor relative pitch classes
RHYTHMS = [
 [1,0.5,0.5,1,1], [0.5,0.5,1,0.5,0.5,1], [1.5,0.5,1,1],
 [0.5,0.5,0.5,0.5,1,1], [1,1,0.5,0.5,1], [0.5,0.5,1,1.5,0.5],
]

random.seed(1827)
measures=[]
previous=76
for bar,ch in enumerate(progression):
    root, intervals=CHORDS[ch]
    chord_pcs={(root+i)%12 for i in intervals}
    rhythm=RHYTHMS[(bar + bar//8)%len(RHYTHMS)]
    if bar in (15,31,47,63,79): rhythm=[1,1,2]
    contour=[0,2,4,3,1,-1,-2,0][bar%8]
    rh=[]
    for j,dur in enumerate(rhythm):
        target=72 + contour + [0,2,-1,3,-2,1][j%6]
        candidates=[n for n in range(67,85) if n%12 in (chord_pcs if (j==0 or dur>=1) else {(4+s)%12 for s in SCALE})]
        n=min(candidates, key=lambda x: abs(x-target)+0.18*abs(x-previous))
        if bar//16==2 and 6 <= bar%16 <= 12: n=min(88,n+5)
        rh.append((n,dur)); previous=n
    # Final cadences resolve to E; penultimate bar leans on B.
    if bar==78: rh=[(71,1),(72,1),(74,1),(71,1)]
    if bar==79: rh=[(76,1),(71,1),(76,2)]
    tones=[root+i for i in intervals[:3]]
    # Flowing broken-chord left hand, always within a comfortable bass register.
    arp=[tones[0], tones[1]+12, tones[2]+12, tones[1]+12,
         tones[0]+12, tones[1]+12, tones[2]+12, tones[1]+12]
    lh=[(n,0.5) for n in arp]
    if bar==79: lh=[(40,1),(47,1),(52,2)]
    measures.append({"chord":ch,"rh":rh,"lh":lh})

def vlq(v):
    out=[v&127]; v >>= 7
    while v: out.append((v&127)|128); v >>= 7
    return bytes(reversed(out))

def make_track(events):
    events.sort(key=lambda e:(e[0],e[1]))
    data=b""; last=0
    for tick,order,msg in events:
        data += vlq(tick-last)+msg; last=tick
    data += b"\x00\xff\x2f\x00"
    return b"MTrk"+struct.pack(">I",len(data))+data

def write_midi(path):
    meta=[]
    meta.append((0,0,b"\xff\x03\x1eWhispers at Dusk - Piano Solo"))
    meta.append((0,1,b"\xff\x58\x04\x04\x02\x18\x08"))
    meta.append((0,1,b"\xff\x59\x02\x01\x01")) # one sharp, minor
    # Expressive tempo map; average duration remains approximately five minutes.
    for bar in range(80):
        bpm=64
        if 16<=bar<32: bpm=68
        elif 32<=bar<48: bpm=61
        elif 48<=bar<64: bpm=66
        if bar%16 >= 13: bpm-= (bar%16-12)*2
        us=round(60_000_000/bpm)
        meta.append((bar*4*PPQ,2,b"\xff\x51\x03"+us.to_bytes(3,"big")))
    notes=[]
    for bar,m in enumerate(measures):
        base=bar*4*PPQ
        # Pedal by measure, released just before the next harmony.
        notes += [(base,0,bytes([0xB0,64,92])),(base+4*PPQ-30,0,bytes([0xB0,64,0]))]
        for hand, channel, vel0 in [(m["rh"],0,66),(m["lh"],1,49)]:
            t=base
            for k,(n,d) in enumerate(hand):
                vel=vel0 + int(8*math.sin((bar%16)/15*math.pi)) + (5 if bar//16==2 else 0)
                vel += (k%3)-1
                length=max(60,int(d*PPQ*0.88))
                notes += [(t,2,bytes([0x90|channel,n,max(30,min(94,vel))])),
                          (t+length,1,bytes([0x80|channel,n,35]))]
                t += int(d*PPQ)
    header=b"MThd"+struct.pack(">IHHH",6,1,2,PPQ)
    open(path,"wb").write(header+make_track(meta)+make_track(notes))

def staff_y_for(note, middle_y, clef):
    # Diatonic steps; treble center line B4, bass center line D3.
    names=["C","D","E","F","G","A","B"]
    nn=note_name(note); letter=nn[0]; octave=int(nn[-1])
    idx=octave*7+names.index(letter)
    ref=4*7+names.index("B") if clef=="treble" else 3*7+names.index("D")
    return middle_y+(idx-ref)*3.15

def draw_staff(c,y,x0,x1,label):
    for k in range(5): c.line(x0,y+k*6.3,x1,y+k*6.3)
    c.setFont("DejaVu",8); c.drawRightString(x0-7,y+8,label)

def draw_note(c,x,y,dur,up=True):
    c.saveState(); c.translate(x,y); c.rotate(13)
    c.setFillColor(HexColor("#171717")); c.ellipse(-3,-2,3,2,fill=1,stroke=0); c.restoreState()
    if dur < 2:
        stemx=x+2.6 if up else x-2.6; end=y+(19 if up else -19)
        c.line(stemx,y,stemx,end)
        if dur<=0.5:
            c.bezier(stemx,end,stemx+(7 if up else -7),end-3*(1 if up else -1),stemx+(6 if up else -6),end-9*(1 if up else -1),stemx+(2 if up else -2),end-11*(1 if up else -1))
    if dur>=2:
        c.setFillColorRGB(1,1,1); c.ellipse(x-1.7,y-1.1,x+1.7,y+1.1,fill=1,stroke=0)

def draw_measure(c,m,x0,x1,yt,yb,bar):
    c.setStrokeColor(HexColor("#222222")); c.setLineWidth(.55)
    for y in (yt,yb):
        c.line(x0,y,x0,y+25.2); c.line(x1,y,x1,y+25.2)
    c.setFont("DejaVu",7); c.setFillColor(HexColor("#333333")); c.drawString(x0+2,yt+28,str(bar+1))
    c.setFont("DejaVu",7.5); c.setFillColor(HexColor("#555555")); c.drawCentredString((x0+x1)/2,yt+28,m["chord"])
    for hand,ymid,clef in [(m["rh"],yt+12.6,"treble"),(m["lh"],yb+12.6,"bass")]:
        beat=0
        for n,d in hand:
            x=x0+8+(x1-x0-16)*(beat/4)
            y=staff_y_for(n,ymid,clef)
            # Ledger lines.
            while y < (yb if clef=="bass" else yt)-.5:
                break
            accidental=note_name(n)[1:2]
            if accidental in "#b":
                c.setFont("DejaVu",7); c.drawRightString(x-4,y-2,accidental)
            draw_note(c,x,y,d,up=(y<ymid+5))
            beat += d

def write_pdf(path):
    W,H=A4; c=canvas.Canvas(path,pagesize=A4)
    c.setTitle("Whispers at Dusk — Romantic Piano Nocturne")
    margin=42; systems_per_page=5; measures_per_system=4
    for page in range(4):
        c.setFillColor(HexColor("#171717"))
        if page==0:
            c.setFont("DejaVu",22); c.drawCentredString(W/2,H-40,"Whispers at Dusk")
            c.setFont("DejaVuOblique",10); c.drawCentredString(W/2,H-57,"A Romantic Nocturne for Piano")
            top=H-108
        else:
            c.setFont("DejaVu",8); c.drawString(margin,H-27,"WHISPERS AT DUSK")
            c.drawRightString(W-margin,H-27,"Romantic Nocturne")
            top=H-62
        gap=143 if page==0 else 148
        start=page*20
        for s in range(systems_per_page):
            first=start+s*4
            yt=top-s*gap; yb=yt-58
            if first in section_marks:
                c.setFont("DejaVuOblique",8.5); c.drawString(margin+22,yt+42,section_marks[first])
            draw_staff(c,yt,margin+24,W-margin,"RH")
            draw_staff(c,yb,margin+24,W-margin,"LH")
            c.setLineWidth(.9); c.line(margin+24,yb,margin+24,yt+25.2)
            if first==0:
                c.setFont("DejaVu",8); c.drawString(margin+31,yt+30,"Andante, con tenerezza  ♩ = 64")
                c.setFont("DejaVu",11); c.drawString(margin+27,yt+8,"𝄞")
                c.drawString(margin+27,yb+8,"𝄢")
                c.setFont("DejaVu",8); c.drawString(margin+40,yt+8,"4/4")
                c.drawString(margin+40,yb+8,"4/4")
            left=margin+55; width=W-margin-left
            for j in range(4):
                x0=left+j*width/4; x1=left+(j+1)*width/4
                draw_measure(c,measures[first+j],x0,x1,yt,yb,first+j)
            # Dynamic shaping and pedal indication.
            dyn=["p dolce","cresc.","mf espress.","dim.","pp morendo"][first//16]
            c.setFont("DejaVuOblique",8); c.drawString(left+3,yb-14,dyn)
            c.setFont("DejaVu",7); c.drawRightString(W-margin,yb-14,"Ped. simile")
        c.setFont("DejaVu",7); c.drawCentredString(W/2,18,str(page+1))
        c.showPage()
    c.save()

if __name__=="__main__":
    font="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    italic="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
    pdfmetrics.registerFont(TTFont("DejaVu",font))
    pdfmetrics.registerFont(TTFont("DejaVuOblique",italic))
    write_pdf(os.path.join(OUT,"Whispers_at_Dusk.pdf"))
    write_midi(os.path.join(OUT,"Whispers_at_Dusk.mid"))
    print("Created Whispers_at_Dusk.pdf and Whispers_at_Dusk.mid")
