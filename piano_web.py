#!/usr/bin/env python3
"""Small LAN web application for the prompt-to-piano composer."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse
import json, mimetypes, os, re, subprocess, tempfile, threading, time, uuid
import musiclib

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OUTPUT = Path(os.environ.get("PIANO_OUTPUT_DIR", ROOT / "output"))
OUTPUT.mkdir(parents=True, exist_ok=True)
PUBLISHED = Path("/srv/files/piano")
JOBS = {}
LOCK = threading.Lock()
MAX_JOBS = 100
MEDIA_SUFFIXES = {".pdf", ".mid", ".mp3", ".m4a", ".wav", ".json"}

def progress_file():
    d = PUBLISHED / "lessons"
    return (d if d.is_dir() else OUTPUT) / "progress.json"

def load_progress():
    try:
        return json.loads(progress_file().read_text())
    except Exception:
        return {}

def save_progress(p):
    f = progress_file()
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, ensure_ascii=False))
    tmp.replace(f)

def job_event(job_id, message):
    print(f"piano job {job_id[:8]}: {message}", flush=True)

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

def prune_jobs():
    """Keep at most MAX_JOBS, removing the oldest finished jobs first."""
    finished=sorted((job.get("created",0),job_id) for job_id,job in JOBS.items()
                    if job.get("status") not in ("queued","composing"))
    while len(JOBS) >= MAX_JOBS and finished:
        _,job_id=finished.pop(0)
        JOBS.pop(job_id,None)

def library():
    groups = {}
    lesson_stems = set()
    folders = list(dict.fromkeys((OUTPUT, PUBLISHED, PUBLISHED / "lessons")))
    for folder in folders:
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES - {".json"}:
                groups.setdefault(p.stem, {})[p.suffix.lower().lstrip(".")] = p
                if folder.name == "lessons":
                    lesson_stems.add(p.stem)
    rows=[]
    for stem, files in groups.items():
        rows.append({"name": stem.replace("_", " "), "stem": stem,
                     "lesson": stem in lesson_stems,
                     "files": {k: f"files/{p.name}" for k,p in sorted(files.items())},
                     "mtime": max(p.stat().st_mtime for p in files.values())})
    rows.sort(key=lambda row: row["mtime"],reverse=True)
    for row in rows: row.pop("mtime")
    return rows

def canonical_user(p, user):
    """Case-insensitive identity: 'justin' and 'Justin' are the same person.
    Keeps the capitalization first used on the board."""
    for entry in p.values():
        for u in entry:
            if u.lower() == user.lower():
                return u
    return user

def find_existing_lesson(title, prompt):
    """A lesson matching the requested title (or clearly named in the prompt)."""
    def norm(s):
        return re.sub(r"[^a-z0-9]+", "", s.lower())
    rows = [r for r in library() if r.get("lesson")]
    t = norm(title or "")
    for r in rows:
        for n in (norm(r["name"]), norm(r["stem"])):
            if len(t) >= 4 and n and (t == n or t in n or n in t):
                return r
    if not t:
        p = norm(prompt)
        for r in rows:
            n = norm(r["name"])
            if len(p) >= 4 and n and (n in p or p in n):
                return r
    return None

def run_job(job_id, request):
    kind = request.get("kind", "piece")
    title = request.get("title", "").strip()
    if kind == "lesson":
        stem = safe_name(title or f"Piano_Lesson_{job_id[:6]}")
        base = PUBLISHED / "lessons" / stem
        cmd = [os.sys.executable, str(ROOT / "lesson_gen.py"), request["prompt"],
               "--out", str(base), "--composer", request["composer"]]
        if title: cmd += ["--title", title]
        exts = ("pdf", "mp3")
        expected = 150
        working = f"{request['composer'].title()} is writing your lesson…"
    else:
        stem = safe_name(title or f"Piano_Piece_{job_id[:6]}")
        base = OUTPUT / stem
        cmd = [os.sys.executable, str(ROOT / "compose.py"), request["prompt"],
               "--bars", str(request["bars"]), "--out", str(base), "--keep-json",
               "--composer", request["composer"]]
        if title: cmd += ["--title", title]
        if not request.get("audio", True): cmd.append("--no-audio")
        exts = ("pdf", "mid", "mp3", "wav", "json")
        expected = (120 if request["composer"] == "kimi" else 210) + request["bars"] * 2
        working = f"{request['composer'].title()} is writing melody and harmony…"
    with LOCK:
        JOBS[job_id].update(status="composing",
                            message=working,
                            progress=8, stage="AI composition",
                            diagnostic="The selected AI is creating and validating the content.")
    job_event(job_id, f"started kind={kind} composer={request['composer']}")
    try:
        started=time.time()
        with tempfile.TemporaryFile(mode="w+") as log:
            proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,text=True)
            while proc.poll() is None:
                elapsed=time.time()-started
                progress=min(88,8+int(80*elapsed/expected))
                with LOCK:
                    JOBS[job_id].update(progress=progress,
                        diagnostic=f"{request['composer'].title()} is still working; {int(elapsed)} seconds elapsed. Longer pieces and audio take more time.")
                if elapsed >= 720:
                    proc.kill(); proc.wait()
                    raise subprocess.TimeoutExpired(cmd,720)
                time.sleep(2)
            log.seek(0); command_output=log.read()
        if proc.returncode:
            if kind == "lesson":
                raise RuntimeError(f"{request['composer'].title()} exited with status {proc.returncode}. "
                                   "Please try again or simplify the request.")
            job_event(job_id, f"AI command exited status={proc.returncode}; starting fallback")
            with LOCK:
                JOBS[job_id].update(message="The AI composer failed; using the built-in composer…",
                                    progress=90,stage="Built-in fallback",
                                    diagnostic=f"{request['composer'].title()} exited with status {proc.returncode}. Rendering a deterministic fallback score.")
            score=fallback_score(request)
            musiclib.render_all(score,str(base),audio=request.get("audio",True))
        else:
            with LOCK:
                JOBS[job_id].update(message="Finalizing your files…",progress=94,
                                    stage="Final checks",diagnostic="Generation and rendering completed; checking output files.")
        made={}
        for ext in exts:
            p=Path(f"{base}.{ext}")
            if p.exists(): made[ext]=f"files/{p.name}"
        with LOCK:
            JOBS[job_id].update(status="complete",
                                message="Your lesson is ready." if kind == "lesson" else "Your piece is ready.",
                                files=made,
                                progress=100,stage="Complete",finished=time.time(),
                                diagnostic=f"Created {len(made)} file format(s): {', '.join(sorted(made)) or 'none'}.")
        job_event(job_id, f"complete files={','.join(sorted(made)) or 'none'}")
    except subprocess.TimeoutExpired:
        with LOCK: JOBS[job_id].update(status="error", message="Composition timed out. Please try fewer measures.",
                                      progress=100,stage="Timed out",finished=time.time(),
                                      diagnostic="The AI/render process exceeded the 12-minute safety limit and was stopped.")
        job_event(job_id, "timed out after 720 seconds")
    except Exception as exc:
        with LOCK: JOBS[job_id].update(status="error", message="Composition failed.",progress=100,
                                      stage="Error",finished=time.time(),
                                      diagnostic=f"{type(exc).__name__}: {str(exc)[:300]}")
        job_event(job_id, f"error {type(exc).__name__}: {str(exc)[:160]}")

class Handler(SimpleHTTPRequestHandler):
    server_version = "PianoStudio/1.0"
    def log_message(self, fmt, *args): print("piano:", fmt % args, flush=True)
    def send_json(self, obj, status=200):
        body=json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=unquote(urlparse(self.path).path)
        if path == "/api/library": return self.send_json({"pieces":library()})
        if path == "/api/progress": return self.send_json(load_progress())
        if path.startswith("/api/jobs/"):
            with LOCK:
                stored=JOBS.get(path.rsplit("/",1)[-1])
                job=dict(stored) if stored else None
            if job:
                job["elapsed"]=round((job.get("finished") or time.time())-job["created"])
            return self.send_json(job or {"error":"Job not found"}, 200 if job else 404)
        if path.startswith("/files/"):
            name=Path(path).name
            if Path(name).suffix.lower() not in MEDIA_SUFFIXES: return self.send_error(404)
            candidates=[OUTPUT/name, PUBLISHED/name, PUBLISHED/"lessons"/name]
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
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-cache")
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/progress":
            try:
                size=int(self.headers.get("Content-Length","0"))
                if size>4000: return self.send_json({"error":"Request too large"},413)
                req=json.loads(self.rfile.read(size))
                user=str(req.get("user","")).strip()
                stem=str(req.get("stem","")).strip()
                done=bool(req.get("done"))
                if not 1<=len(user)<=24: raise ValueError("Name must be 1–24 characters.")
                if not re.fullmatch(r"[\w \-]{1,80}", stem): raise ValueError("Bad lesson name.")
                if not (progress_file().parent / f"{stem}.pdf").is_file():
                    raise ValueError("Unknown lesson.")
                with LOCK:
                    p=load_progress()
                    user=canonical_user(p,user)
                    entry=p.setdefault(stem,{})
                    if done: entry[user]=time.time()
                    else: entry.pop(user,None)
                    if not entry: p.pop(stem,None)
                    save_progress(p)
                return self.send_json(p)
            except (ValueError,TypeError,json.JSONDecodeError) as exc:
                return self.send_json({"error":str(exc)},400)
        if path not in ("/api/compose", "/api/lesson"): return self.send_error(404)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size>16000: return self.send_json({"error":"Request too large"},413)
            req=json.loads(self.rfile.read(size))
            prompt=str(req.get("prompt","")).strip()
            composer=str(req.get("composer","kimi")).lower()
            if not 5<=len(prompt)<=1000: raise ValueError("Describe it in 5–1000 characters.")
            if composer not in ("kimi","codex"): raise ValueError("Choose Kimi or Codex.")
            if path == "/api/lesson":
                kind="lesson"; bars=None
            else:
                kind="piece"
                bars=int(req.get("bars",32))
                if bars not in (16,24,32,48,64): raise ValueError("Choose a supported length.")
            clean={"kind":kind,"prompt":prompt,"title":str(req.get("title", ""))[:100],
                   "bars":bars,"audio":bool(req.get("audio",True)),"composer":composer}
            if kind == "lesson":
                existing = find_existing_lesson(clean["title"], prompt)
                if existing:
                    return self.send_json({"status":"exists",
                        "message":f'"{existing["name"]}" already exists — find it in the list above.',
                        "lesson":existing})
            with LOCK:
                if any(j["status"] in ("queued","composing") for j in JOBS.values()):
                    return self.send_json({"error":"Another composition is in progress. Please wait."},429)
                prune_jobs()
                job_id=uuid.uuid4().hex
                JOBS[job_id]={"id":job_id,"status":"queued",
                              "message":"Preparing your lesson…" if kind=="lesson" else "Preparing your composition…",
                              "created":time.time(),"progress":2,"stage":"Queued","composer":composer,
                              "bars":bars,"diagnostic":"The request was accepted and the worker thread is starting."}
            job_event(job_id, f"accepted kind={kind} composer={composer} bars={bars}")
            threading.Thread(target=run_job,args=(job_id,clean),daemon=True).start()
            return self.send_json(JOBS[job_id],202)
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            print(f"piano compose rejected: {type(exc).__name__}: {exc}",flush=True)
            return self.send_json({"error":str(exc)},400)

if __name__ == "__main__":
    host=os.environ.get("PIANO_HOST","0.0.0.0"); port=int(os.environ.get("PIANO_PORT","8940"))
    print(f"Piano Studio listening on http://{host}:{port}",flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
