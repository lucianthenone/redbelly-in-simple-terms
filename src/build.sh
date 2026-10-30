#!/usr/bin/env bash
# Rebuilds every deliverable from source.
#   bash src/build.sh            reuse the chosen narration takes in build/voice if present
#   bash src/build.sh --voice    regenerate the narration too (slow on CPU, about 1 hour)
# Any other arguments go to the final check, for example: bash src/build.sh --online --asr
# Needs: Python 3.12+ with requirements.txt, Node 18+ with Playwright and Chromium, ffmpeg with librubberband.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
NAME=redbelly-in-simple-terms

step() { printf '\n== %s\n' "$1"; }

VOICE=0
if [[ "${1:-}" == "--voice" ]]; then VOICE=1; shift; fi
if [[ $VOICE == 1 || ! -f build/voice/manifest.json ]]; then
  step "Narration: 4 takes per line, transcribed, best exact take kept"
  $PY src/audio/voice.py --takes 4
fi

step "Timeline: pace, word timings, cues, captions"
$PY src/timeline.py

step "Music and sound effects"
$PY src/audio/music.py

step "Mix and master"
$PY src/audio/mix.py

step "Picture"
node src/video/build-icons.mjs
node src/video/render.mjs --workers "${WORKERS:-3}"

step "Encode MP4"
mkdir -p submission
ffmpeg -y -loglevel error -i build/video/picture.mkv -i build/audio/final.wav \
  -map 0:v -map 1:a -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 16 -tune animation -profile:v high -level 4.2 -g 120 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest \
  -metadata title="Redbelly in Simple Terms" "submission/$NAME.mp4"

step "Captions and transcript"
$PY src/captions.py

step "Site, sources, PDF, checks"
# The site and the PDF quote the check results, so they are built, checked, then rebuilt.
$PY src/docs/build_site.py
$PY src/docs/build_pdf.py
$PY src/checks/verify.py || true
$PY src/docs/build_site.py
$PY src/docs/build_pdf.py
$PY src/checks/verify.py "$@"
