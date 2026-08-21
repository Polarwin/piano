#!/usr/bin/env bash
# install_piano.sh — set up the piano file server safely.
#
#   sudo bash install_piano.sh [port]
#
# What it does (and nothing more):
#   1. creates /srv/files/piano, owned by the invoking user
#   2. adds ONE new nginx config: /etc/nginx/conf.d/piano-files.conf
#      (its own server block on its own port — existing sites/apps untouched)
#   3. validates with `nginx -t`; on any failure it removes its own config
#      and reloads, leaving nginx exactly as it was
#   4. snapshots listening ports before/after and reports if anything else changed
# Default port: 8930 (falls back to the next free port in 8000-9000).
set -euo pipefail

SHARE_DIR=/srv/files/piano
CONF=/etc/nginx/conf.d/piano-files.conf
WANTED_PORT="${1:-8930}"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run with sudo:  sudo bash $0 [port]" >&2
    exit 1
fi
REAL_USER="${SUDO_USER:-root}"

# --- preconditions ---------------------------------------------------------
command -v nginx >/dev/null || { echo "nginx is not installed." >&2; exit 1; }
command -v ss    >/dev/null || { echo "iproute2 (ss) is not installed." >&2; exit 1; }
systemctl is-active --quiet nginx || { echo "nginx is not running." >&2; exit 1; }

# true when nothing listens on the port on ANY interface
port_free() { ! ss -tlnH "sport = :$1" | grep -q .; }

PORT=""
if port_free "$WANTED_PORT"; then
    PORT=$WANTED_PORT
else
    echo "Port $WANTED_PORT is busy, looking for a free one in 8000-9000..."
    for p in $(seq 8000 9000); do
        if port_free "$p"; then PORT=$p; break; fi
    done
fi
[ -n "$PORT" ] || { echo "No free port in 8000-9000." >&2; exit 1; }

echo "==> Snapshot of current listeners (before)"
ss -tln | awk 'NR>1{print $4}' | sort > /tmp/piano_before.ports

# NFS note: root_squash maps root to nobody, so anything touching the share
# directory must run as the real user, not as root.
as_user() { runuser -u "$REAL_USER" -- "$@"; }

echo "==> Creating $SHARE_DIR (as $REAL_USER)"
as_user mkdir -p "$SHARE_DIR"

echo "==> Copying existing pieces from $SCRIPT_DIR"
copied=0
for f in "$SCRIPT_DIR"/*.pdf "$SCRIPT_DIR"/*.mid "$SCRIPT_DIR"/*.mp3 "$SCRIPT_DIR"/*.wav; do
    [ -e "$f" ] || continue
    as_user cp -n "$f" "$SHARE_DIR/" && copied=$((copied+1))
done
echo "    $copied file(s) copied (existing files in the share are never overwritten)"
if runuser -u www-data -- test -r "$SHARE_DIR" -a -x "$SHARE_DIR" 2>/dev/null; then
    echo "    nginx (www-data) can read the share"
else
    echo "    WARNING: www-data cannot read $SHARE_DIR — check the NFS export permissions" >&2
fi

echo "==> Writing $CONF (port $PORT)"
cat > "$CONF" <<EOF
server {
    listen $PORT;
    server_name _;
    root $SHARE_DIR;
    autoindex on;
}
EOF

rollback() {
    echo "Rolling back: removing $CONF" >&2
    rm -f "$CONF"
    nginx -t && systemctl reload nginx || true
    exit 1
}

echo "==> Validating nginx configuration"
nginx -t || rollback
# Graceful reload: other sites keep their connections, nothing restarts.
systemctl reload nginx || rollback

echo "==> Snapshot of current listeners (after)"
ss -tln | awk 'NR>1{print $4}' | sort > /tmp/piano_after.ports
if diff /tmp/piano_before.ports /tmp/piano_after.ports | grep '^<' ; then
    echo "WARNING: a pre-existing listener disappeared (see above)." >&2
else
    echo "OK: all pre-existing apps are still listening — nothing else was affected."
fi

# --- optional dependency report (nothing is installed automatically) -------
echo "==> Dependency check (report only)"
command -v python3 >/dev/null && echo "    python3: ok" || echo "    python3: MISSING"
python3 -c "import reportlab" 2>/dev/null && echo "    reportlab: ok" || echo "    reportlab: MISSING (pip install reportlab)"
command -v ffmpeg >/dev/null && echo "    ffmpeg: ok" || echo "    ffmpeg: missing (only affects MP3 output)"
command -v kimi >/dev/null && echo "    kimi CLI: ok" || echo "    kimi CLI: missing (only affects AI composition)"

LAN_IP=$(ip -4 addr show | grep -oE 'inet (192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9.]+' | awk '{print $2}' | head -1)
echo
echo "Done. From your phone (same Wi-Fi):  http://${LAN_IP:-<this-pc>}:$PORT/"
echo "Files in $SHARE_DIR are listed and downloadable there."
echo "To uninstall: sudo rm $CONF && sudo systemctl reload nginx"
