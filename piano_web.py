#!/usr/bin/env python3
"""Small LAN web application for the prompt-to-piano composer."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse
import json, mimetypes, os, re, subprocess, threading, time, uuid
import musiclib

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OUTPUT = Path(os.environ.get("PIANO_OUTPUT_DIR", ROOT / "output"))
OUTPUT.mkdir(parents=True, exist_ok=True)
PUBLISHED = Path("/srv/files/piano")
JOBS = {}
LOCK = threading.Lock()

def fallback_score(request):
    """Create a musical, deterministic score when the external composer is offline."""
    text=request["prompt"].lower(); bars=request["bars"]
    waltz="waltz" in text or "3/4" in text
    minor=any(w in text for w in ("minor","sad","dark","melancholy","wistful","nocturne"))
    beats=3 if waltz else 4
    progressions=(["Am","F","C","G","Am","Dm","E7","Am"] if minor else
                  ["C","G/B","Am","Em","F","C/E","Dm7","G7"])
    scale=([69,71,72,74,76,77,79] if minor else [72,74,76,77,79,81,83])
    rhythm=[1,1,1] if waltz else [1,0.5,0.5,1,1]
    data={"title":request.get("title") or "A New Piano Story","subtitle":"for piano solo",
          "key_sig":0,"minor":minor,"time":[beats,4],"bpm":58 if "slow" in text else 68,
          "tempo_mark":"Andantino espressivo","accompaniment":"waltz" if waltz else "flowing",
          "sections":[],"bars":[]}
    for bar in range(bars):
        if bar in (0,bars//4,bars//2,3*bars//4):
            data["sections"].append({"bar":bar,"name":["A","A′","B","Coda"][len(data["sections"])],
                                     "dynamic":["p dolce","mp cantabile","mf espressivo","p morendo"][len(data["sections"])]})
        contour=[0,1,2,3,2,1,-1,0][bar%8]; melody=[]
        for i,d in enumerate(rhythm):
            idx=max(0,min(len(scale)-1,2+contour+[0,1,-1,2,-1][i%5]))
            n=min(84,scale[idx] + (12 if bars//2<=bar<3*bars//4 and i==0 else 0))
            melody.append([musiclib.SHARP[n%12]+str(n//12-1),d])
        if bar==bars-1:
            tonic="A4" if minor else "C5"; melody=[[tonic,beats]]
        data["bars"].append({"chord":progressions[bar%len(progressions)],"melody":melody})
    return musiclib.build_score(data)

def safe_name(value):
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip()
    return re.sub(r"[\s_]+", "_", value)[:80] or "composition"

def library():
    groups = {}
    folders = list(dict.fromkeys((OUTPUT, PUBLISHED, ROOT)))
    for folder in folders:
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in {".pdf", ".mid", ".mp3", ".m4a", ".wav"}:
                groups.setdefault(p.stem, {})[p.suffix.lower().lstrip(".")] = p
    rows=[]
    for stem, files in groups.items():
        rows.append({"name": stem.replace("_", " "), "stem": stem,
                     "files": {k: f"files/{p.name}" for k,p in sorted(files.items())}})
    return sorted(rows, key=lambda x: max((ROOT / Path(v).name).stat().st_mtime if (ROOT / Path(v).name).exists() else 0 for v in x["files"].values()), reverse=True)

def run_job(job_id, request):
    title = request.get("title", "").strip()
    stem = safe_name(title or f"Piano_Piece_{job_id[:6]}")
    base = OUTPUT / stem
    cmd = [os.sys.executable, str(ROOT / "compose.py"), request["prompt"],
           "--bars", str(request["bars"]), "--out", str(base), "--keep-json"]
    if title: cmd += ["--title", title]
    if not request.get("audio", True): cmd.append("--no-audio")
    with LOCK:
        JOBS[job_id].update(status="composing", message="Writing melody and harmony…")
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=720)
        if proc.returncode:
            with LOCK: JOBS[job_id]["message"]="Using the built-in composer…"
            score=fallback_score(request)
            musiclib.render_all(score,str(base),audio=request.get("audio",True))
        made={}
        for ext in ("pdf","mid","mp3","wav","json"):
            p=Path(f"{base}.{ext}")
            if p.exists(): made[ext]=f"files/{p.name}"
        with LOCK:
            JOBS[job_id].update(status="complete", message="Your piece is ready.", files=made)
    except subprocess.TimeoutExpired:
        with LOCK: JOBS[job_id].update(status="error", message="Composition timed out. Please try fewer measures.")
    except Exception as exc:
        with LOCK: JOBS[job_id].update(status="error", message=str(exc))

class Handler(SimpleHTTPRequestHandler):
    server_version = "PianoStudio/1.0"
    def log_message(self, fmt, *args): print("piano:", fmt % args)
    def send_json(self, obj, status=200):
        body=json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path == "/api/library": return self.send_json({"pieces":library()})
        if path.startswith("/api/jobs/"):
            with LOCK: job=JOBS.get(path.rsplit("/",1)[-1])
            return self.send_json(job or {"error":"Job not found"}, 200 if job else 404)
        if path.startswith("/files/"):
            name=Path(path).name
            candidates=[OUTPUT/name, PUBLISHED/name, ROOT/name]
            p=next((x for x in candidates if x.is_file()),None)
            if not p: return self.send_error(404)
            self.send_response(200); self.send_header("Content-Type",mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            self.send_header("Content-Length",str(p.stat().st_size)); self.send_header("Content-Disposition",f'inline; filename="{p.name}"')
            self.end_headers()
            with p.open("rb") as f:
                while chunk:=f.read(1024*256): self.wfile.write(chunk)
            return
        target=WEB/("index.html" if path in ("/","/piano/") else path.lstrip("/"))
        if not target.is_file() or WEB not in target.resolve().parents: return self.send_error(404)
        body=target.read_bytes(); self.send_response(200)
        self.send_header("Content-Type",mimetypes.guess_type(target.name)[0] or "text/plain")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if urlparse(self.path).path != "/api/compose": return self.send_error(404)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size>16000: return self.send_json({"error":"Request too large"},413)
            req=json.loads(self.rfile.read(size))
            prompt=str(req.get("prompt","")).strip()
            bars=int(req.get("bars",32))
            if not 5<=len(prompt)<=1000: raise ValueError("Describe the piece in 5–1000 characters.")
            if bars not in (16,24,32,48,64): raise ValueError("Choose a supported length.")
            with LOCK:
                if any(j["status"] in ("queued","composing") for j in JOBS.values()):
                    return self.send_json({"error":"Another composition is in progress. Please wait."},429)
                job_id=uuid.uuid4().hex
                JOBS[job_id]={"id":job_id,"status":"queued","message":"Preparing your composition…","created":time.time()}
            clean={"prompt":prompt,"title":str(req.get("title", ""))[:100],"bars":bars,"audio":bool(req.get("audio",True))}
            threading.Thread(target=run_job,args=(job_id,clean),daemon=True).start()
            return self.send_json(JOBS[job_id],202)
        except (ValueError,TypeError,json.JSONDecodeError) as exc: return self.send_json({"error":str(exc)},400)

if __name__ == "__main__":
    host=os.environ.get("PIANO_HOST","0.0.0.0"); port=int(os.environ.get("PIANO_PORT","8940"))
    print(f"Piano Studio listening on http://{host}:{port}",flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
