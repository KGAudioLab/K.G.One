#!/usr/bin/env bash

echo "=========================================="
echo "  KGOne Initialization Script (Linux)"
echo "=========================================="
echo ""

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "Checking prerequisites..."

if ! command -v git &>/dev/null; then
    echo "  ERROR: git not found. Install via your package manager (e.g. sudo apt install git)"
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo "  ERROR: uv not found. Install from https://docs.astral.sh/uv/"
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "  ERROR: jq not found. Install via your package manager (e.g. sudo apt install jq)"
    exit 1
fi

# nvm is a shell function — it must be sourced, not found on PATH
if ! command -v nvm &>/dev/null; then
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        # shellcheck source=/dev/null
        source "$HOME/.nvm/nvm.sh"
    fi
fi
if ! command -v nvm &>/dev/null; then
    echo "  ERROR: nvm not found. Install from https://github.com/nvm-sh/nvm"
    exit 1
fi

echo "  git ... OK"
echo "  uv  ... OK"
echo "  jq  ... OK"
echo "  nvm ... OK"
echo ""

# ---------------------------------------------------------
echo "[1/9] Reading submodules.json..."
# ---------------------------------------------------------

ACESTEP_URL=$(jq -r '."ace-step".url' submodules.json)
ACESTEP_COMMIT=$(jq -r '."ace-step".commit' submodules.json)
FOUNDATION1_URL=$(jq -r '.foundation1.url' submodules.json)
FOUNDATION1_COMMIT=$(jq -r '.foundation1.commit' submodules.json)
SEP_URL=$(jq -r '."python-audio-separator".url' submodules.json)
SEP_COMMIT=$(jq -r '."python-audio-separator".commit' submodules.json)
KGSTUDIO_URL=$(jq -r '.kgstudio.url' submodules.json)
SOUNDFONTS_URL=$(jq -r '."soundfont-for-samplers".url' submodules.json)
SOUNDFONTS_COMMIT=$(jq -r '."soundfont-for-samplers".commit' submodules.json)

if [ -z "$ACESTEP_URL" ] || [ "$ACESTEP_URL" = "null" ]; then
    echo "  ERROR: Could not read from submodules.json"
    exit 1
fi

echo "  ACE-Step          URL   : $ACESTEP_URL"
echo "  ACE-Step          commit: $ACESTEP_COMMIT"
echo "  Foundation-1      URL   : $FOUNDATION1_URL"
echo "  Foundation-1      commit: $FOUNDATION1_COMMIT"
echo "  audio-separator   URL   : $SEP_URL"
echo "  audio-separator   commit: $SEP_COMMIT"
echo "  KGStudio          URL   : $KGSTUDIO_URL"
echo "  soundfont-for-samplers URL   : $SOUNDFONTS_URL"
echo "  soundfont-for-samplers commit: $SOUNDFONTS_COMMIT"
echo ""

# ---------------------------------------------------------
echo "[2/9] Setting up ACE-Step..."
# ---------------------------------------------------------

if [ -d "ace-step/.git" ]; then
    echo "  Repository exists. Fetching refs..."
    git -C ace-step fetch --quiet origin
else
    echo "  Cloning ACE-Step (may take several minutes)..."
    git clone "$ACESTEP_URL" ace-step || { echo "  ERROR: Failed to clone ACE-Step"; exit 1; }
fi

echo "  Checking out pinned commit $ACESTEP_COMMIT..."
git -C ace-step checkout "$ACESTEP_COMMIT" --quiet || { echo "  ERROR: Could not checkout ACE-Step commit $ACESTEP_COMMIT"; exit 1; }
echo "  ACE-Step OK."
echo ""

# ---------------------------------------------------------
echo "[3/9] Setting up Foundation-1..."
# ---------------------------------------------------------

if [ -d "foundation1/.git" ]; then
    echo "  Repository exists. Fetching refs..."
    git -C foundation1 fetch --quiet origin
else
    echo "  Cloning Foundation-1..."
    git clone "$FOUNDATION1_URL" foundation1 || { echo "  ERROR: Failed to clone Foundation-1"; exit 1; }
fi

echo "  Checking out pinned commit $FOUNDATION1_COMMIT..."
git -C foundation1 checkout "$FOUNDATION1_COMMIT" --quiet || { echo "  ERROR: Could not checkout Foundation-1 commit $FOUNDATION1_COMMIT"; exit 1; }
echo "  Foundation-1 OK."
echo ""

# ---------------------------------------------------------
echo "[4/9] Setting up python-audio-separator..."
# ---------------------------------------------------------

if [ -d "separator/.git" ]; then
    echo "  Repository exists. Fetching refs..."
    git -C separator fetch --quiet origin
else
    echo "  Cloning python-audio-separator..."
    git clone "$SEP_URL" separator || { echo "  ERROR: Failed to clone python-audio-separator"; exit 1; }
fi

echo "  Checking out pinned commit $SEP_COMMIT..."
git -C separator checkout "$SEP_COMMIT" --quiet || { echo "  ERROR: Could not checkout python-audio-separator commit $SEP_COMMIT"; exit 1; }
echo "  python-audio-separator OK."
echo ""

# ---------------------------------------------------------
echo "[5/9] Setting up KGStudio..."
# ---------------------------------------------------------

if [ -d "kgstudio/.git" ]; then
    echo "  Repository exists. Pulling latest..."
    git -C kgstudio pull --quiet origin
else
    echo "  Cloning KGStudio..."
    git clone "$KGSTUDIO_URL" kgstudio || { echo "  ERROR: Failed to clone KGStudio"; exit 1; }
fi

echo "  Installing Node.js 20.19 (latest patch)..."
nvm install 20.19 || { echo "  ERROR: Failed to install Node.js 20.19"; exit 1; }
nvm use 20.19 || { echo "  ERROR: Failed to activate Node.js 20.19"; exit 1; }

echo "  Installing npm dependencies..."
pushd kgstudio >/dev/null
npm install --no-audit --no-fund
_EC=$?
echo "  [debug] npm install exit code: $_EC"
if [ "$_EC" -ne 0 ]; then
    popd >/dev/null
    echo "  ERROR: npm install failed (exit code $_EC)"
    exit 1
fi

echo "  Building KGStudio (tsc + vite build)..."
npm run build
_EC=$?
echo "  [debug] npm run build exit code: $_EC"
if [ "$_EC" -ne 0 ]; then
    popd >/dev/null
    echo "  ERROR: npm run build failed (exit code $_EC)"
    exit 1
fi
popd >/dev/null

if [ ! -f "kgstudio/dist/index.html" ]; then
    echo "  ERROR: Build succeeded but dist/index.html not found"
    exit 1
fi
echo "  KGStudio OK."
echo ""

# ---------------------------------------------------------
echo "[6/9] Setting up soundfonts..."
# ---------------------------------------------------------

if [ -d "soundfonts/.git" ]; then
    echo "  Repository exists. Fetching refs..."
    git -C soundfonts fetch --quiet origin
else
    echo "  Cloning soundfont-for-samplers (may take several minutes, ~150 MB)..."
    git clone "$SOUNDFONTS_URL" soundfonts || { echo "  ERROR: Failed to clone soundfont-for-samplers"; exit 1; }
fi

echo "  Checking out pinned commit $SOUNDFONTS_COMMIT..."
git -C soundfonts checkout "$SOUNDFONTS_COMMIT" --quiet || { echo "  ERROR: Could not checkout soundfont-for-samplers commit $SOUNDFONTS_COMMIT"; exit 1; }
echo "  soundfont-for-samplers OK."
echo ""

# ---------------------------------------------------------
echo "[7/9] Setting up Python environments..."
# ---------------------------------------------------------

# Gateway venv
if [ -f ".venv/bin/python" ]; then
    echo "  Gateway venv already exists, skipping."
else
    echo "  Creating gateway venv..."
    uv venv .venv || { echo "  ERROR: Failed to create gateway venv"; exit 1; }
    uv pip install --python .venv "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0" "httpx>=0.27.0" "python-multipart>=0.0.9" || { echo "  ERROR: Failed to install gateway dependencies"; exit 1; }
    echo "  Gateway venv OK."
fi

# ACE-Step venv
if [ -f "ace-step/.venv/bin/python" ]; then
    echo "  ACE-Step venv already exists, skipping."
else
    echo "  Creating ACE-Step venv..."
    echo "  NOTE: Downloads large CUDA packages. May take 10-20 minutes."
    pushd ace-step >/dev/null
    uv venv .venv || { popd >/dev/null; echo "  ERROR: Failed to create ACE-Step venv"; exit 1; }
    uv pip install --python .venv -e . || { popd >/dev/null; echo "  ERROR: Failed to install ACE-Step dependencies"; exit 1; }
    popd >/dev/null
    echo "  ACE-Step venv OK."
fi

# Foundation-1 venv
if [ -f "foundation1/.venv/bin/python" ]; then
    echo "  Foundation-1 venv already exists, skipping."
else
    echo "  Creating Foundation-1 venv (requires Python 3.10)..."
    if ! uv venv --python 3.10 foundation1/.venv 2>/dev/null; then
        echo "  WARNING: Python 3.10 not found. Falling back to default Python."
        uv venv foundation1/.venv || { echo "  ERROR: Failed to create Foundation-1 venv"; exit 1; }
    fi
    echo "  Installing PyTorch 2.5.1 (CUDA 12.1 wheels)..."
    echo "  NOTE: This downloads ~2 GB. May take several minutes."
    uv pip install --python foundation1/.venv torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121 || { echo "  ERROR: Failed to install PyTorch"; exit 1; }
    echo "  Installing pinned numpy..."
    uv pip install --python foundation1/.venv "numpy==1.23.5" || { echo "  ERROR: Failed to install numpy"; exit 1; }
    echo "  Installing Foundation-1 dependencies..."
    uv pip install --python foundation1/.venv -e foundation1 || { echo "  ERROR: Failed to install Foundation-1 dependencies"; exit 1; }
    uv pip install --python foundation1/.venv "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0" || { echo "  ERROR: Failed to install Foundation-1 server dependencies"; exit 1; }
    echo "  Pinning setuptools for pkg_resources compatibility..."
    uv pip install --python foundation1/.venv "setuptools<70" || { echo "  ERROR: Failed to pin setuptools"; exit 1; }
    echo "  Foundation-1 venv OK."
fi

# Separator venv
if [ -f "separator/.venv/pyvenv.cfg" ]; then
    echo "  Separator venv already exists, skipping."
else
    echo "  Creating separator venv..."
    echo "  NOTE: Downloads CUDA packages. May take several minutes."
    uv venv separator/.venv || { echo "  ERROR: Failed to create separator venv"; exit 1; }
    uv pip install --python separator/.venv -e "separator[gpu]" || { echo "  ERROR: Failed to install audio-separator"; exit 1; }
    uv pip uninstall --python separator/.venv torch torchvision
    uv pip install --python separator/.venv torch==2.11.0+cu126 torchvision==0.26.0+cu126 --index-url https://download.pytorch.org/whl/cu126 || { echo "  ERROR: Failed to install PyTorch for separator"; exit 1; }
    uv pip install --python separator/.venv --force-reinstall onnxruntime-gpu || { echo "  ERROR: Failed to install onnxruntime-gpu"; exit 1; }
    echo "  Separator venv OK."
fi

echo ""

# ---------------------------------------------------------
echo "[8/9] Creating output directories..."
# ---------------------------------------------------------
mkdir -p "outputs/clip"
mkdir -p "outputs/fullsong"
mkdir -p "outputs/separator"
mkdir -p "uploads/separator"
mkdir -p "foundation1/generations"
mkdir -p "foundation1/models"
echo "  Done."
echo ""

# ---------------------------------------------------------
echo "[9/9] Downloading model weights..."
# ---------------------------------------------------------

if [ -f "ace-step/checkpoints/acestep-v15-turbo/model.safetensors" ]; then
    echo "  ACE-Step weights OK."
else
    echo "  Downloading ACE-Step checkpoints (may take several minutes)..."
    ace-step/.venv/bin/python -c "from acestep.api.model_download import ensure_model_downloaded; import os; ckpt=os.path.join(os.getcwd(),'ace-step','checkpoints'); ensure_model_downloaded('acestep-v15-turbo', ckpt); ensure_model_downloaded('vae', ckpt)" || { echo "  ERROR: ACE-Step weight download failed"; exit 1; }
    echo "  ACE-Step weights OK."
fi
echo ""

if [ -f "foundation1/models/RoyalCities-Foundation-1/Foundation_1.safetensors" ]; then
    echo "  Foundation-1 weights OK."
else
    echo "  Downloading Foundation-1 weights (approx 1.7 GB)..."
    foundation1/.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('RoyalCities/Foundation-1', local_dir='foundation1/models/RoyalCities-Foundation-1')" || { echo "  ERROR: Foundation-1 weight download failed"; exit 1; }
    echo "  Foundation-1 weights OK."
fi
echo ""

echo "  Separator models will be downloaded on first use (handled by audio-separator)."
echo ""

echo "=========================================="
echo "  Initialization complete!"
echo "=========================================="
echo ""
echo "Start the gateway:"
echo "  uv run ./main.py"
echo "  uv run ./main.py --host 0.0.0.0          (allow remote access)"
echo "  uv run ./main.py --host 0.0.0.0 --port 8080  (custom port)"
echo ""
echo "The default browser will open automatically once the server starts."
echo ""
echo "Then load a model:"
echo "  POST http://127.0.0.1:8000/v1/models/load"
echo '  Body: {"model": "clip"}     -- Foundation-1 (MIDI + WAV)'
echo '  Body: {"model": "fullsong"} -- ACE-Step 1.5 (full songs)'
echo ""
echo "Or separate stems (no model load needed):"
echo "  POST http://127.0.0.1:8000/v1/separator/separate"
echo "  Body: multipart/form-data  file=<audio> model_filename=<model>"
echo ""
echo "K.G.Studio DAW:"
echo "  http://127.0.0.1:8000  (redirects to /kgstudio/)"
echo ""
echo "API docs: http://127.0.0.1:8000/docs"
echo ""
