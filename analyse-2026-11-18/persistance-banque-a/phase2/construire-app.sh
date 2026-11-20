#!/bin/bash
# Construit l'archive d'application CTAPP1 a partir des sources de phase2 (meme chaine que l'image).
# Usage (WSL) : bash construire-app.sh <sortie.ctapp>
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
project=$(realpath "$here/../../..")
output=$(realpath -m "$1")
old_service=$project/analyse-2026-11-17/buildroot-ram/variante-service-20261118/overlay/usr/share/cozytouch/mqtt
tree=$(mktemp -d)
trap 'rm -rf "$tree"' EXIT
python3 "$here/prepare-lua.py" "$old_service" "$here/src" "$tree"
python3 "$here/build-app.py" "$tree" "$output"
