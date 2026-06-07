#!/usr/bin/env bash

echo "=========================================="
echo "  KGOne Cleanup Script (Linux/macOS)"
echo "=========================================="
echo ""
echo "This will permanently delete:"
echo "  .venv/       (gateway Python environment)"
echo "  ace-step/    (submodule + venv + model checkpoints)"
echo "  foundation1/ (submodule + venv + model weights)"
echo "  separator/   (submodule + venv)"
echo "  kgstudio/    (frontend repo + node_modules + dist)"
echo "  soundfonts/  (soundfont-for-samplers MP3 samples, ~150 MB)"
echo "  outputs/     (all generated audio and MIDI files)"
echo "  uploads/     (all uploaded audio files)"
echo ""
echo "Re-run init.sh or init-macos.sh to restore everything except outputs and uploads."
echo ""

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

read -r -p "Type YES to confirm: " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi
echo ""

remove_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        echo "Removing $dir ..."
        rm -rf "$dir"
        echo "  Done."
    else
        echo "$dir not found, skipping."
    fi
}

remove_dir ".venv"
remove_dir "ace-step"
remove_dir "foundation1"
remove_dir "separator"
remove_dir "kgstudio"
remove_dir "soundfonts"
remove_dir "outputs"
remove_dir "uploads"

echo ""
echo "=========================================="
echo "  Cleanup complete."
echo "  Run init.sh or init-macos.sh to set up again."
echo "=========================================="
echo ""
