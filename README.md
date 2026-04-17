# K.G.One

A unified REST API gateway that exposes two AI music-generation models behind a single consistent interface.

| Service | Model | Output | Port |
|---------|-------|--------|------|
| **Full-song** | [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | Full-length music (MP3/WAV/FLAC) | 8001 (internal) |
| **Clip** | [Foundation-1](https://huggingface.co/RoyalCities/Foundation-1) | Short instrument clips — WAV **and** MIDI | 8002 (internal) |
| **Separator** | [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) | Separated stems (Vocals, Instrumental, etc.) as MP3 | CLI (no port) |
| **Gateway** | K.G.One | Routes all requests, enforces GPU mutex | **8000** (public) |

Because all services require a GPU, only one is active at a time. You explicitly switch via `POST /v1/models/load` before generating or separating.

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | `init.bat` is Windows-only; Linux/macOS support can be added |
| NVIDIA GPU | CUDA required for both models |
| [Git](https://git-scm.com/downloads) | For cloning sub-projects |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python environment manager |
| Python 3.10 | Required by Foundation-1; ACE-Step works with 3.10+ |

---

## Setup

### 1. Initialize

Run `init.bat` from the project root. It will:

1. Read pinned commit hashes from `submodules.json`
2. Clone ACE-Step 1.5 into `ace-step/`
3. Clone Foundation-1 into `foundation1/`
4. Create three isolated Python environments:
   - `.venv` — the gateway (fastapi, httpx)
   - `ace-step/.venv` — ACE-Step and its CUDA dependencies
   - `foundation1/.venv` — Foundation-1 and its dependencies (scipy==1.8.1)
5. Create output directories under `outputs/`

```bat
init.bat
```

> **Note:** ACE-Step downloads large CUDA packages. Expect 10–20 minutes on the first run.

### 2. Download model weights

**ACE-Step** downloads weights automatically on first start via its built-in model downloader.

**Foundation-1** downloads from HuggingFace on first start (handled by `get_pretrained_model`). Alternatively, set environment variables to point to a local checkpoint:

```bat
set FOUNDATION1_CKPT_PATH=C:\path\to\foundation1.safetensors
set FOUNDATION1_CONFIG_PATH=C:\path\to\model_config.json
```

### 3. Start the gateway

```bat
.venv\Scripts\python.exe main.py
```

The gateway starts on `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### 4. Load a model and generate

```bash
# Load Foundation-1
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "clip"}'

# Submit a generation
curl -X POST http://localhost:8000/v1/clip/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Piano, Rhodes, Warm, 8 Bars, 120 BPM, C major", "bars": 8, "bpm": 120}'
```

### Upgrading a pinned dependency

Edit the `commit` field in `submodules.json`, delete the corresponding subfolder, then re-run `init.bat`.

---

## Project structure

```
K.G.One/
├── submodules.json          # Pinned commits — source of truth for dependency versions
├── init.bat                 # Windows bootstrap script
├── pyproject.toml           # Gateway Python project
├── main.py                  # Gateway FastAPI application (port 8000)
├── services/
│   ├── model_manager.py     # GPU mutex — starts/stops sub-service subprocesses
│   ├── acestep_client.py    # ACE-Step connection config
│   ├── foundation1_client.py# Foundation-1 connection config
│   └── separator_runner.py  # Runs audio-separator CLI per-request, manages tasks
├── foundation1_server/
│   └── server.py            # Foundation-1 FastAPI wrapper (port 8002)
├── ace-step/                # Cloned by init.bat — ACE-Step 1.5 source
├── foundation1/             # Cloned by init.bat — RC-stable-audio-tools source
├── separator/               # Cloned by init.bat — python-audio-separator source + venv
├── outputs/
│   ├── clip/                # Foundation-1 generated WAV + MIDI files
│   ├── fullsong/            # (reserved for ACE-Step output references)
│   └── separator/           # Separated stem MP3 files
└── uploads/
    └── separator/           # Temporary upload storage (auto-deleted after processing)
```

---

## API Reference

### System

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/health` | Gateway health check |
| `POST` | `/v1/models/load` | Load a model onto the GPU (unloads the active one first) |
| `GET` | `/v1/models/status` | Return the currently active model |

---

#### `GET /health`

**Response**
```json
{
  "status": "ok",
  "active_model": "clip"
}
```

`active_model` is `null` when no model is loaded.

---

#### `POST /v1/models/load`

Loads a model onto the GPU. If a different model is currently active, it is shut down first.

For `"fullsong"` and `"clip"` this call **blocks** until the sub-service reports healthy (model weights loaded). Expect 30–120 seconds on first run.

For `"separator"` it only terminates the currently running model to free VRAM — no persistent process is started. Returns immediately.

**Request**

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `model` | string | yes | `"clip"`, `"fullsong"`, or `"separator"` |

```json
{ "model": "separator" }
```

**Response**
```json
{
  "active_model": "separator",
  "status": "ready"
}
```

**Error — unknown model (400)**
```json
{ "detail": "Unknown model 'foo'. Must be 'fullsong', 'clip', or 'separator'." }
```

---

#### `GET /v1/models/status`

**Response**
```json
{
  "active_model": "fullsong"
}
```

---

### Full-song generation (ACE-Step 1.5)

> All `/v1/fullsong/*` endpoints return HTTP 503 if `fullsong` is not the active model.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/fullsong/generate` | Submit a full-song generation task |
| `GET` | `/v1/fullsong/result/{task_id}` | Poll task status and retrieve result |
| `GET` | `/v1/fullsong/audio?path={path}` | Download a generated audio file |

---

#### `POST /v1/fullsong/generate`

Proxied to ACE-Step's `/release_task`. Accepts the full ACE-Step generation parameter set.

**Request** (key fields — see [ACE-Step API docs](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md) for the complete spec)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caption` | string | required | Musical style/description |
| `lyrics` | string | `""` | Song lyrics (`[verse]`, `[chorus]` tags supported) |
| `duration` | number | `60` | Duration in seconds |
| `instrumental` | boolean | `false` | Generate without vocals |
| `bpm` | number | `null` | Target BPM (null = auto) |
| `inference_steps` | integer | `8` | Diffusion steps (8 = turbo, 50 = full quality) |
| `guidance_scale` | number | `7.0` | Classifier-free guidance scale |
| `seed` | integer | `-1` | `-1` for random |
| `audio_format` | string | `"mp3"` | `"mp3"`, `"wav"`, `"flac"`, `"opus"` |

```json
{
  "caption": "upbeat electronic dance, synthesizer, four-on-the-floor kick, 128 BPM",
  "lyrics": "[verse]\nLights are flashing\nBeats are crashing\n[chorus]\nDance all night",
  "duration": 90,
  "instrumental": false,
  "inference_steps": 8,
  "guidance_scale": 7.0,
  "seed": -1,
  "audio_format": "mp3"
}
```

**Response**
```json
{
  "data": {
    "task_id": "a3f2c1d8-9e4b-4a7f-b012-3c5d6e7f8a9b",
    "status": "queued",
    "queue_position": 1
  },
  "code": 200,
  "error": null,
  "timestamp": 1744300000000
}
```

---

#### `GET /v1/fullsong/result/{task_id}`

Poll until `status` is `"finished"`. Recommended interval: 2–5 seconds.

**Path parameter:** `task_id` from the generate response.

**Response — pending**
```json
{
  "data": [
    {
      "task_id": "a3f2c1d8-9e4b-4a7f-b012-3c5d6e7f8a9b",
      "status": "running",
      "progress": 0.4
    }
  ],
  "code": 200
}
```

**Response — finished**
```json
{
  "data": [
    {
      "task_id": "a3f2c1d8-9e4b-4a7f-b012-3c5d6e7f8a9b",
      "status": "finished",
      "audio_path": "/tmp/acestep/outputs/a3f2c1d8.mp3",
      "duration": 90.2,
      "bpm": 128
    }
  ],
  "code": 200
}
```

Use `audio_path` as the `path` query parameter when calling `/v1/fullsong/audio`.

---

#### `GET /v1/fullsong/audio?path={path}`

Download the generated audio file. Returns binary audio data.

**Query parameter:** `path` — the `audio_path` value from the result response.

**Response:** Binary audio file (`audio/mpeg`, `audio/wav`, etc. depending on format).

---

### Clip generation (Foundation-1)

> All `/v1/clip/*` endpoints return HTTP 503 if `clip` is not the active model.

Foundation-1 generates short instrument clips (4 or 8 bars) from a structured text prompt, producing both a WAV audio file and a MIDI transcription simultaneously.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/clip/generate` | Submit a clip generation task |
| `GET` | `/v1/clip/result/{task_id}` | Poll task status and retrieve file URLs |
| `GET` | `/v1/clip/audio/{filename}` | Download the generated WAV file |
| `GET` | `/v1/clip/midi/{filename}` | Download the generated MIDI file |

---

#### `POST /v1/clip/generate`

**Request**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | required | Comma-separated descriptor tags (see prompt guide below) |
| `negative_prompt` | string | `""` | Tags to avoid |
| `bars` | integer | `4` | Clip length: `4` or `8` |
| `bpm` | integer | `140` | Tempo in BPM (e.g. 100, 110, 120, 128, 130, 140, 150) |
| `note` | string | `"C"` | Root note: `A` through `G#` |
| `scale` | string | `"minor"` | `"major"` or `"minor"` |
| `steps` | integer | `75` | Diffusion steps (1–500; 75 is a good balance) |
| `cfg_scale` | number | `7.0` | Classifier-free guidance (0–25) |
| `seed` | integer | `-1` | `-1` for random |
| `sampler_type` | string | `"dpmpp-2m-sde"` | Sampler algorithm |
| `sigma_min` | number | `0.03` | Minimum noise sigma |
| `sigma_max` | number | `500.0` | Maximum noise sigma |
| `cfg_rescale` | number | `0.0` | CFG rescale factor (0–1) |

**Prompt format**

Foundation-1 prompts are structured tag lists. Key components:

```
[Instrument family], [Sub-type], [Timbre descriptors], [FX], [Bars], [BPM], [Key]
```

Example prompts:
- `"Piano, Rhodes Piano, Warm, Bright, Lush, 8 Bars, 120 BPM, C major"`
- `"Bass, FM Bass, Acid, Gritty, Thick, 8 Bars, 140 BPM, E minor"`
- `"Synth, Wavetable Synth, Pad, Wide, Silky, 4 Bars, 128 BPM, A minor"`

```json
{
  "prompt": "Bass, FM Bass, Acid, Gritty, Wide, Thick, 8 Bars, 140 BPM, E minor",
  "bars": 8,
  "bpm": 140,
  "note": "E",
  "scale": "minor",
  "steps": 75,
  "cfg_scale": 7.0,
  "seed": -1,
  "sampler_type": "dpmpp-2m-sde"
}
```

**Response**
```json
{
  "task_id": "b7e3a921-4f1c-4d8e-a023-9d6c5e8f1b2a"
}
```

---

#### `GET /v1/clip/result/{task_id}`

Poll until `status` is `"complete"`. Recommended interval: 2–5 seconds.

**Path parameter:** `task_id` from the generate response.

**Response — pending / running**
```json
{
  "task_id": "b7e3a921-4f1c-4d8e-a023-9d6c5e8f1b2a",
  "status": "running",
  "error": null
}
```

**Response — complete**
```json
{
  "task_id": "b7e3a921-4f1c-4d8e-a023-9d6c5e8f1b2a",
  "status": "complete",
  "wav_url": "/v1/clip/audio/Bass_FM_Bass_Acid_140BPM_E_minor_42.wav",
  "midi_url": "/v1/clip/midi/Bass_FM_Bass_Acid_140BPM_E_minor_42.mid"
}
```

**Response — error**
```json
{
  "task_id": "b7e3a921-4f1c-4d8e-a023-9d6c5e8f1b2a",
  "status": "error",
  "error": "Generation failed — check server logs."
}
```

---

#### `GET /v1/clip/audio/{filename}`

Download the generated WAV file (32 kHz stereo).

**Path parameter:** `filename` — the filename portion of `wav_url` from the result response.

**Response:** Binary WAV file (`audio/wav`).

```bash
curl http://localhost:8000/v1/clip/audio/Bass_FM_Bass_Acid_140BPM_E_minor_42.wav \
  --output clip.wav
```

---

#### `GET /v1/clip/midi/{filename}`

Download the MIDI transcription derived from the generated audio (via [basic-pitch](https://github.com/spotify/basic-pitch)).

**Path parameter:** `filename` — the filename portion of `midi_url` from the result response.

**Response:** Binary MIDI file (`audio/midi`).

```bash
curl http://localhost:8000/v1/clip/midi/Bass_FM_Bass_Acid_140BPM_E_minor_42.mid \
  --output clip.mid
```

---

### Stem separation (python-audio-separator)

> All `/v1/separator/*` endpoints return HTTP 503 if `separator` is not the active model.

Separates an uploaded audio file into individual stems (vocals, instrumental, etc.) using UVR models. Outputs are always MP3.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/separator/separate` | Upload audio + select model → task ID |
| `GET` | `/v1/separator/result/{task_id}` | Poll task status and retrieve output filenames |
| `GET` | `/v1/separator/download/{filename}` | Download a separated stem file |

---

#### `POST /v1/separator/separate`

Accepts a `multipart/form-data` body.

**Form fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | Audio file to separate (MP3, WAV, FLAC, …) |
| `model_filename` | string | yes | One of the three supported models (see below) |

**Supported models**

| `model_filename` | Stems produced |
|-----------------|----------------|
| `UVR-MDX-NET-Inst_HQ_3.onnx` | 2 — Vocals, Instrumental |
| `MDX23C-8KFFT-InstVoc_HQ.ckpt` | 2 — Vocals, Instrumental |
| `htdemucs_6s.yaml` | 6 — bass, drums, guitar, other, piano, vocals |

Models are downloaded automatically by `audio-separator` on first use.

```bash
curl -X POST http://localhost:8000/v1/separator/separate \
  -F "file=@song.mp3" \
  -F "model_filename=UVR-MDX-NET-Inst_HQ_3.onnx"
```

**Response**
```json
{ "task_id": "c4e2f891-3b1a-4d7e-b023-8e5f6a9c2d1b" }
```

---

#### `GET /v1/separator/result/{task_id}`

Poll until `status` is `"complete"`. Recommended interval: 2–5 seconds. Separation typically takes 10–60 seconds depending on file length and model.

**Response — running**
```json
{
  "task_id": "c4e2f891-3b1a-4d7e-b023-8e5f6a9c2d1b",
  "status": "running"
}
```

**Response — complete**
```json
{
  "task_id": "c4e2f891-3b1a-4d7e-b023-8e5f6a9c2d1b",
  "status": "complete",
  "files": [
    "c4e2f891_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.mp3",
    "c4e2f891_(Vocals)_UVR-MDX-NET-Inst_HQ_3.mp3"
  ]
}
```

**Response — error**
```json
{
  "task_id": "c4e2f891-3b1a-4d7e-b023-8e5f6a9c2d1b",
  "status": "error",
  "error": "Separation failed — check server logs."
}
```

---

#### `GET /v1/separator/download/{filename}`

Download a stem MP3 file. `filename` is one of the entries from the `files` list in the result response.

**Response:** Binary MP3 file (`audio/mpeg`) with `Content-Disposition: attachment`.

```bash
curl "http://localhost:8000/v1/separator/download/c4e2f891_(Vocals)_UVR-MDX-NET-Inst_HQ_3.mp3" \
  --output vocals.mp3
```

---

## Typical workflows

### Generate a full song

```bash
# 1. Load ACE-Step
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "fullsong"}'

# 2. Submit generation
TASK=$(curl -s -X POST http://localhost:8000/v1/fullsong/generate \
  -H "Content-Type: application/json" \
  -d '{
    "caption": "lo-fi hip hop, mellow piano, soft drums, vinyl crackle",
    "duration": 120,
    "instrumental": true,
    "inference_steps": 8,
    "audio_format": "mp3"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['data']['task_id'])")

# 3. Poll until finished
curl http://localhost:8000/v1/fullsong/result/$TASK

# 4. Download (using audio_path from step 3 result)
curl "http://localhost:8000/v1/fullsong/audio?path=/tmp/acestep/outputs/$TASK.mp3" \
  --output song.mp3
```

### Generate a MIDI + WAV clip

```bash
# 1. Load Foundation-1
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "clip"}'

# 2. Submit generation
curl -s -X POST http://localhost:8000/v1/clip/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Keys, Rhodes Piano, Warm, Lush, 8 Bars, 90 BPM, D major",
    "bars": 8, "bpm": 90, "note": "D", "scale": "major", "steps": 75
  }'
# => {"task_id": "b7e3a921-..."}

# 3. Poll
curl http://localhost:8000/v1/clip/result/b7e3a921-...
# => {"status": "complete", "wav_url": "/v1/clip/audio/Keys_Rhodes_...", "midi_url": "..."}

# 4. Download both files
curl http://localhost:8000/v1/clip/audio/Keys_Rhodes_Piano_Warm_Lush_42.wav --output clip.wav
curl http://localhost:8000/v1/clip/midi/Keys_Rhodes_Piano_Warm_Lush_42.mid  --output clip.mid
```

### Separate stems from an audio file

```bash
# 1. Load separator (terminates any active model, frees VRAM)
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "separator"}'

# 2. Upload file and submit separation
TASK=$(curl -s -X POST http://localhost:8000/v1/separator/separate \
  -F "file=@song.mp3" \
  -F "model_filename=UVR-MDX-NET-Inst_HQ_3.onnx" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# 3. Poll until complete
curl http://localhost:8000/v1/separator/result/$TASK
# => {"status": "complete", "files": ["...(Vocals)...", "...(Instrumental)..."]}

# 4. Download stems
curl "http://localhost:8000/v1/separator/download/...(Vocals)....mp3" --output vocals.mp3
curl "http://localhost:8000/v1/separator/download/...(Instrumental)....mp3" --output instrumental.mp3
```

### Switch between models

```bash
# Foundation-1 is active — switch to ACE-Step
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "fullsong"}'
# Foundation-1 subprocess is terminated, ACE-Step starts. Blocks until healthy.
```

---

## Error reference

| HTTP Status | Meaning |
|-------------|---------|
| `400` | Bad request (e.g. unknown model name) |
| `404` | Task ID or file not found |
| `503` | Requested model is not currently loaded, or sub-service is unreachable |

**503 body when wrong model is active:**
```json
{
  "detail": {
    "error": "Model 'clip' is not loaded. POST /v1/models/load first.",
    "active_model": "fullsong"
  }
}
```

---

## License

K.G.One is licensed under the [Apache License 2.0](./LICENSE) with two supplemental conditions:

- **No patents** — this software may not be used to file or support any patent application in any jurisdiction.
- **Attribution** — public or commercial deployments must display `Powered by K.G.One © 2026 Xiaohan Tian` in a prominent location visible to end users.

### Third-party component licenses

K.G.One integrates or proxies the following projects. If you use the corresponding features, you are responsible for complying with their licenses.

| Component | Used for | License | Notes |
|-----------|----------|---------|-------|
| [K.G.Studio](https://github.com/KGAudioLab/K.G.Studio) | Browser DAW UI | Apache 2.0 + custom terms | Public/commercial use requires displaying `Powered by K.G.Studio © 2025 Xiaohan Tian`; no patent filing permitted |
| [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | Full-song generation (`/v1/fullsong/*`) | MIT | Permissive — attribution required |
| [stable-audio-open-1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0) | Clip generation (`/v1/clip/*`) via Foundation-1 | Stability AI Community License | **Non-commercial only.** Commercial use requires a separate license from Stability AI — see [stability.ai/license](https://stability.ai/license) |
| [python-audio-separator / UVR5](https://github.com/nomadkaraoke/python-audio-separator) | Stem separation (`/v1/separator/*`) | MIT | Permissive — attribution required |

> **Note:** The `clip` generation feature is powered by a model released under the Stability AI Community License, which **does not permit commercial use**. If you intend to use K.G.One in a commercial product, you must obtain a commercial license from Stability AI before enabling or exposing the `/v1/clip/*` endpoints.

See [LICENSE](./LICENSE) for the full terms including third-party notices.
