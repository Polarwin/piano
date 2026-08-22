# Piano Project

Prompt-to-piano-music app: describe a piece in plain words, get sheet music
(PDF), MIDI, and audio (WAV/MP3).

## The app is live (Piano Studio web app)

- **Public URL: https://justinmusic.duckdns.org** — served at the domain root.
  Chain: duckdns name -> 8.211.26.86 (Alibaba Cloud VPS, Caddy TLS) -> tunnel
  through the 192.168.0.103 FRP gateway -> home nginx -> backend. China reachability: duckdns.org HTTPS passed
  GreatFire's last test (2026-06), but the zone has a mixed GFW history.
- **LAN URL: http://192.168.0.9/piano/** (dashboard entry on http://192.168.0.9/)
- Port 8930 serves the same app: http://192.168.0.9:8930/
- Backend: `piano_web.py` (stdlib ThreadingHTTPServer + `musiclib`, with an
  offline fallback composer) listening on **127.0.0.1:8943**, run as user
  justin from the project folder. Web UI files in `web/`, API: `api/library`,
  `api/compose` (long-running; nginx proxy_read_timeout is 900s).
- nginx: both `/piano/` (homeserver `# piano-begin`..`# piano-end` block) and
  port 8930 (`/etc/nginx/conf.d/piano-files.conf`) **proxy** to 127.0.0.1:8943.
- Pieces are published to `/srv/files/piano` (served by the app under
  `files/...`); compose.py and the older generators also write there when the
  directory exists (fallback: project folder). Subfolders: `lessons/`
  (generated course lessons + `progress.json`) and `library/` (public-domain
  famous sheet music + `levels.json` with suggested course month per piece,
  shown in the app's "Sheet music library" section).

## Lessons (Six Months to Piano)

- `lesson_gen.py` — prompt-to-lesson CLI (PDF + MP3). Lesson JSON v2 supports
  time signatures ([2,4]/[3,4]/[4,4], one per lesson), rests `["R", dur]`,
  genuine chords `{"chord": [["C",3],...], "dur": d, "fingers": "1-3-5"}`,
  accidentals (letter may carry #/b), and per-exercise tempo/dynamic/bpm marks.
  Engravers: `lesson_day_one.exercise()` (single staff) and
  `lesson_day_two.grand_exercise()` — both accept v1 4-tuples and v2 events,
  and wrap long exercises onto multiple systems automatically.
  `lesson_audio.py` builds the play-along score (one time signature per lesson).
- `make_curriculum.py` — batch-generates the course; resumable (skips days
  whose PDF exists), `--force` regenerates, `--dry-run` shows the plan.
  Curriculum + practice lengths/levels documented in `CURRICULUM.md`.
  Month One (Days 1-30) lives in `/srv/files/piano/lessons/`.
- After editing `web/index.html`, always `node --check` the extracted script —
  a single missing brace once blanked the whole page.

## Usage (CLI)

    python3 compose.py "a dreamy waltz in F major, slow"   # AI-composes + renders all
    python3 compose.py "sad nocturne" --bars 40 --keep-json
    python3 musiclib.py score.json outname                 # re-render from edited JSON

- `compose.py` — CLI; uses either `kimi -p` or `codex exec` to compose the score
  as JSON, then renders. Options: --composer --title --bars --out --constraints
  --no-audio --keep-json --timeout.
- `musiclib.py` — engine: score schema validation, chord parsing, grand-staff
  PDF engraving (ReportLab + NotoMusic-Regular.ttf for clefs), MIDI writer,
  pure-stdlib audio synth. Score JSON schema documented in its docstring.
- Older one-off generators: `make_lettre_d_amour.py`, `render_lettre_d_amour.py`,
  `make_romantic_nocturne.py`, `render_audio.py`.

## Infrastructure

- nginx integration (two parts, both marked for clean removal):
  - `/etc/nginx/conf.d/piano-files.conf` — standalone server on port 8930
  - `/etc/nginx/sites-enabled/homeserver` — `# piano-begin`..`# piano-end`
    block, plus a `<!-- piano-link -->` entry in `/srv/www/index.html`
- Setup/reinstall: `sudo bash /tmp/install_piano.sh` (copy it to /tmp first —
  see NFS note). Logs to `/tmp/piano_install.log`. NOTE: installer writes the
  8930 config as a file server — the current proxy version was added later
  by the web-app work; don't blindly overwrite it.
- Git: github.com/Polarwin/piano (private), branch `main`.

## Gotchas (learned the hard way)

- **NFS root_squash**: `/srv` and `/home` are NFS; root is mapped to nobody.
  Never do file work under /srv or ~ as root/sudo — use `runuser -u justin`.
  Running sudo from an NFS cwd can fail; run scripts from /tmp instead.
- **nginx backups**: never put backup files in `sites-enabled/` — nginx loads
  every file there, a `.bak` of a site becomes a duplicate default server.
- `/srv/www` is root-owned but `index.html` is justin-writable: `sed -i` fails
  (needs dir write); render to /tmp and `cat >` the file instead.
- **install_piano.sh copy step**: only copies media when the script lives in
  the piano project (checks for compose.py + musiclib.py). Running it from
  /tmp once scooped unrelated media into the share — cleaned up 2026-08-21.
- Port 8930 chosen because 8000-9000 has other apps (8010, 8011, 8293, 8347,
  8473, 8791, 8799 are taken); 8943 is the app backend (loopback only).
