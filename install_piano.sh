#!/usr/bin/env bash
# install_piano.sh — install Piano Studio on the home server.
#
#   sudo bash install_piano.sh [port]
#
# What it does:
#   1. creates /srv/files/piano (as the invoking user — the share is NFS,
#      root is squashed to nobody and cannot write there)
#   2. adds ONE new nginx config: /etc/nginx/conf.d/piano-files.conf
#      (standalone server on its own port, default 8930; re-running reuses
#      the existing port instead of allocating a new one)
#   3. integrates with the homeserver site (port 80/443): adds a marked
#      /piano/ location block and a link on the /srv/www/index.html dashboard,
#      following the same pattern as the other apps (ytwatcher etc.)
#   4. every nginx change is gated on `nginx -t` with automatic rollback;
#      a before/after listener snapshot proves nothing else was affected
set -euo pipefail

# Log everything to /tmp so the output can be reviewed/shared afterwards.
LOG=/tmp/piano_install.log
exec > >(tee -a "$LOG") 2>&1
echo "=== install run $(date '+%Y-%m-%d %H:%M:%S') ==="

SHARE_DIR=/srv/files/piano
CONF=/etc/nginx/conf.d/piano-files.conf
SITE=/etc/nginx/sites-enabled/homeserver
INDEX=/srv/www/index.html
SERVICE=/etc/systemd/system/piano-studio.service
APP_PORT=8943
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run with sudo:  sudo bash $0 [port]" >&2
    exit 1
fi
REAL_USER="${SUDO_USER:-root}"
# NFS root_squash: anything touching /srv must run as the real user.
as_user() { runuser -u "$REAL_USER" -- "$@"; }

command -v nginx >/dev/null || { echo "nginx is not installed." >&2; exit 1; }
command -v ss    >/dev/null || { echo "iproute2 (ss) is not installed." >&2; exit 1; }
systemctl is-active --quiet nginx || { echo "nginx is not running." >&2; exit 1; }

# --- choose port -----------------------------------------------------------
port_free() { ! ss -tlnH "sport = :$1" | grep -q .; }
if [ $# -ge 1 ]; then
    PORT="$1"
    port_free "$PORT" || { echo "Port $PORT is busy." >&2; exit 1; }
elif [ -f "$CONF" ]; then
    PORT=$(grep -oE 'listen [0-9]+' "$CONF" | head -1 | awk '{print $2}')
    echo "==> Reusing existing port $PORT from $CONF"
else
    PORT=""
    for p in 8930 $(seq 8000 9000); do
        if port_free "$p"; then PORT=$p; break; fi
    done
    [ -n "$PORT" ] || { echo "No free port in 8000-9000." >&2; exit 1; }
fi

echo "==> Snapshot of current listeners (before)"
ss -tln | awk 'NR>1{print $4}' | sort > /tmp/piano_before.ports

# --- share directory -------------------------------------------------------
echo "==> Creating $SHARE_DIR (as $REAL_USER)"
as_user mkdir -p "$SHARE_DIR"
# Only copy media when the script actually lives in the piano project —
# running from /tmp (or anywhere else) must not scoop up unrelated files.
copied=0
if [ -f "$SCRIPT_DIR/compose.py" ] && [ -f "$SCRIPT_DIR/musiclib.py" ]; then
    for f in "$SCRIPT_DIR"/*.pdf "$SCRIPT_DIR"/*.mid "$SCRIPT_DIR"/*.mp3 "$SCRIPT_DIR"/*.wav "$SCRIPT_DIR"/*.m4a; do
        [ -e "$f" ] || continue
        as_user cp -n "$f" "$SHARE_DIR/" && copied=$((copied+1))
    done
fi
echo "    $copied file(s) copied (never overwrites)"
if runuser -u www-data -- test -r "$SHARE_DIR" -a -x "$SHARE_DIR" 2>/dev/null; then
    echo "    nginx (www-data) can read the share"
else
    echo "    WARNING: www-data cannot read $SHARE_DIR — check the NFS export permissions" >&2
fi

# --- application service --------------------------------------------------
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
echo "==> Installing Piano Studio composition service"
cat > "$SERVICE" <<EOF
[Unit]
Description=Piano Studio web composer
After=network.target

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$SCRIPT_DIR
Environment=HOME=$REAL_HOME
Environment=PATH=$REAL_HOME/.kimi-code/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PIANO_HOST=127.0.0.1
Environment=PIANO_PORT=$APP_PORT
Environment=PIANO_OUTPUT_DIR=$SHARE_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/piano_web.py
Restart=on-failure
RestartSec=3
UMask=0022

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now piano-studio.service

# --- nginx changes, all gated on nginx -t ----------------------------------
# NOTE: backups must NOT go into sites-enabled/ — nginx includes every file
# there, so a *.bak copy of a site would be loaded as a duplicate server.
SITE_REAL=$(readlink -f "$SITE")
BACKUP="$SITE_REAL.bak.piano"
NGINX_CHANGED=0
rollback() {
    echo "Rolling back nginx changes..." >&2
    [ "$NGINX_CHANGED" = 1 ] && [ -f "$BACKUP" ] && cp "$BACKUP" "$SITE_REAL"
    rm -f "$CONF.new"
    nginx -t && systemctl reload nginx || true
    exit 1
}

echo "==> Writing $CONF (port $PORT)"
# clean up a misplaced backup from a previous run, if any (it breaks nginx -t)
rm -f /etc/nginx/sites-enabled/homeserver.bak.piano
cat > "$CONF.new" <<EOF
server {
    listen $PORT;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 900s;
    }
}
EOF
mv "$CONF.new" "$CONF"

if [ -f "$SITE" ]; then
    if grep -q '# piano-begin' "$SITE"; then
        echo "==> Upgrading existing /piano/ file route to the composer app"
        cp "$SITE" "$BACKUP"
        NGINX_CHANGED=1
        sed -i '/# piano-begin/,/# piano-end/d' "$SITE_REAL"
    fi
    if [ "$(tail -n 1 "$SITE")" != "}" ]; then
        echo "WARNING: $SITE does not end with '}' — skipping homeserver integration" >&2
    else
        echo "==> Adding /piano/ location to $SITE (backup: $BACKUP)"
        cp "$SITE" "$BACKUP"
        NGINX_CHANGED=1
        TMP=$(mktemp)
        head -n -1 "$SITE" > "$TMP"
        cat >> "$TMP" <<'EOF'
    # piano-begin (piano sheet music / MIDI / audio from /srv/files/piano)
    location = /piano { return 301 /piano/; }
    location /piano/ {
        proxy_pass http://127.0.0.1:8943/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Prefix /piano;
        proxy_read_timeout 900s;
    }
    # piano-end
EOF
        tail -n 1 "$SITE" >> "$TMP"
        cat "$TMP" > "$SITE_REAL"
        rm -f "$TMP"
    fi
fi

echo "==> Validating nginx configuration"
nginx -t || rollback
systemctl reload nginx || rollback   # graceful: other sites keep connections

# --- dashboard link --------------------------------------------------------
if [ -f "$INDEX" ] && grep -q '</ul>' "$INDEX"; then
    if grep -q 'piano-link' "$INDEX"; then
        echo "==> Dashboard already has the piano link"
    else
        echo "==> Adding piano entry to $INDEX (as $REAL_USER)"
        # /srv/www is root-owned: sed -i cannot create its temp file there,
        # so render to /tmp and write back into the file (which is writable).
        as_user sed 's|</ul>|      <!-- piano-link -->\n      <li><a class="app" href="/piano/">piano<small>Sheet music, MIDI \&amp; audio — prompt-composed piano pieces</small></a></li>\n    </ul>|' "$INDEX" > /tmp/piano_index.html
        as_user bash -c 'cat /tmp/piano_index.html > "$1" && rm -f /tmp/piano_index.html' _ "$INDEX"
    fi
else
    echo "==> No dashboard at $INDEX; skipping index link"
fi

# --- verification ----------------------------------------------------------
echo "==> Snapshot of current listeners (after)"
ss -tln | awk 'NR>1{print $4}' | sort > /tmp/piano_after.ports
if diff /tmp/piano_before.ports /tmp/piano_after.ports | grep '^<'; then
    echo "WARNING: a pre-existing listener disappeared (see above)." >&2
else
    echo "OK: all pre-existing apps are still listening — nothing else was affected."
fi

LAN_IP=$(ip -4 addr show | grep -oE 'inet (192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9.]+' | awk '{print $2}' | head -1)
echo
echo "Done. Entry points:"
echo "  dashboard:  http://${LAN_IP:-<this-pc>}/        (piano link on the index page)"
echo "  direct:     http://${LAN_IP:-<this-pc>}/piano/  or  http://${LAN_IP:-<this-pc>}:$PORT/"
echo "To uninstall: sudo sed -i '/# piano-begin/,/# piano-end/d' $SITE;"
echo "              sudo systemctl disable --now piano-studio; sudo rm $SERVICE $CONF"
echo "              sudo systemctl daemon-reload; sudo systemctl reload nginx"
echo "              and remove the piano-link lines from $INDEX"
