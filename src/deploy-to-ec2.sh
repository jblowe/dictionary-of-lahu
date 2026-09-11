#!/usr/bin/env bash
# deploy-to-ec2.sh -- copy docs/ (the static website) and generated/ (the
# PDF, TEI, HTML, and every intermediate pipeline artifact) to the EC2 box,
# continuing the manual `scp -r generated ...` you'd already started.
#
# Uses rsync instead of plain scp when it's available: generated/ is ~65MB
# and docs/ ~21MB (mostly one sqlite3 file), and rsync only re-transfers
# what changed on repeat runs instead of the whole tree every time. Falls
# back to scp -r if rsync isn't installed locally or on the remote box.
#
# Edit the four variables below for your setup, or override them on the
# command line, e.g.:
#   EC2_HOST=1.2.3.4 src/deploy-to-ec2.sh
#
# Usage: src/deploy-to-ec2.sh
# Run from the project root (same convention as the other src/ scripts).

set -euo pipefail
cd "$(dirname "$0")/.."

PEM_KEY="${PEM_KEY:-$HOME/Downloads/jblowe.pem}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-54.71.209.160}"
REMOTE_DIR="${REMOTE_DIR:-/var/www/html/lahu_dico}"

if [ ! -f "$PEM_KEY" ]; then
  echo "error: PEM key not found at $PEM_KEY (set PEM_KEY=... to override)" >&2
  exit 1
fi
if [ ! -d docs ] || [ ! -d generated ]; then
  echo "error: run this from the project root -- docs/ and/or generated/ not found here" >&2
  exit 1
fi

echo "==> Ensuring $REMOTE_DIR exists on $EC2_HOST"
ssh -i "$PEM_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p '$REMOTE_DIR'"

if command -v rsync >/dev/null 2>&1; then
  echo "==> Syncing docs/ and generated/ via rsync (only changed files after the first run)"
  rsync -avz --progress -e "ssh -i $PEM_KEY" docs generated "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"
else
  echo "==> rsync not found locally -- falling back to scp (copies everything, every time)"
  scp -r -i "$PEM_KEY" docs generated "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"
fi

echo "==> Done. Remote layout: $REMOTE_DIR/docs/, $REMOTE_DIR/generated/"
