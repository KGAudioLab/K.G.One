# K.G.One API Reference

K.G.One exposes a REST API on port **8000**. These endpoints are consumed by K.G.Studio's AI Musician Assistant and are also directly callable for programmatic or headless use.

> **Interactive docs (Swagger UI):** `http://localhost:8000/docs`

---

## System

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/health` | Server health check |
| `POST` | `/v1/models/load` | Load a model onto the GPU (unloads the active one first) |
| `GET` | `/v1/models/status` | Return the currently active model |

---

### `GET /health`

**Response**
```json
{
  "status": "ok",
  "active_model": "clip"
}
```

`active_model` is `null` when no model is loaded.

---

### `POST /v1/models/load`

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

### `GET /v1/models/status`

**Response**
```json
{
  "active_model": "fullsong"
}
```

---

## Full-song generation (ACE-Step 1.5)

> All `/v1/fullsong/*` endpoints return HTTP 503 if `fullsong` is not the active model.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/fullsong/generate` | Submit a full-song generation task |
| `GET` | `/v1/fullsong/result/{task_id}` | Poll task status and retrieve result |
| `GET` | `/v1/fullsong/audio/{task_id}` | Download a generated audio file |

---

### `POST /v1/fullsong/generate`

Proxied to ACE-Step's `/release_task`. All listed fields are forwarded as-is; any additional ACE-Step fields are also accepted and passed through.

See [ACE-Step API docs](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md) for the complete parameter spec.

**Request**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caption` | string | required | Musical style/description |
| `lyrics` | string | `null` | Song lyrics (`[verse]`, `[chorus]` tags supported) |
| `instrumental` | boolean | `null` | Generate without vocals |
| `inference_steps` | integer | `null` | Diffusion steps (8 = turbo, 50 = full quality) |
| `guidance_scale` | number | `null` | Classifier-free guidance scale |
| `use_random_seed` | boolean | `null` | Use a random seed |
| `seed` | integer | `null` | Fixed seed value (used when `use_random_seed` is false) |
| `thinking` | boolean | `null` | Enable ACE-Step thinking mode |
| `batch_size` | integer | `null` | Number of outputs to generate |
| `audio_format` | string | `null` | `"mp3"`, `"wav"`, `"flac"`, `"opus"` |

**Example request**

```bash
curl -X POST 'http://127.0.0.1:8000/v1/fullsong/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "caption": "Genre: Eurodance, 90s dance-pop, upbeat electronic. Catchy, energetic, nostalgic 90s Eurodance with a strong four-on-the-floor beat. Bright synth leads, punchy bassline. Tempo: ~130 BPM.",
    "lyrics": "[verse]\nStep in the scene, yeah the bassline drops\n[chorus]\nWe are dancing in the neon in the night",
    "instrumental": false,
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "use_random_seed": true,
    "thinking": true,
    "batch_size": 1,
    "audio_format": "mp3"
  }'
```

**Response**
```json
{
  "data": {
    "task_id": "58e15e57-3022-4f43-8ada-64ea52a9064a",
    "status": "queued",
    "queue_position": 1
  },
  "code": 200,
  "error": null,
  "timestamp": 1776227065582,
  "extra": null
}
```

---

### `GET /v1/fullsong/result/{task_id}`

Poll until `status` is `1` (succeeded). Recommended interval: 2–5 seconds.

**Response — pending / running**
```json
{
  "data": [
    {
      "task_id": "58e15e57-3022-4f43-8ada-64ea52a9064a",
      "status": 0,
      "progress": 0.1,
      "stage": "Phase 1: Generating CoT metadata..."
    }
  ],
  "code": 200
}
```

**Response — succeeded**
```json
{
  "data": [
    {
      "task_id": "58e15e57-3022-4f43-8ada-64ea52a9064a",
      "status": 1,
      "progress": 1.0,
      "stage": "succeeded"
    }
  ],
  "code": 200
}
```

Once `status` is `1`, download the audio with `GET /v1/fullsong/audio/{task_id}`.

---

### `GET /v1/fullsong/audio/{task_id}`

Download the generated audio file. Only works once the task has succeeded (`status == 1`).

**Query parameter:** `index` (optional, default `0`) — selects a specific file when `batch_size > 1`.

**Example**

```bash
curl -X GET \
  'http://127.0.0.1:8000/v1/fullsong/audio/58e15e57-3022-4f43-8ada-64ea52a9064a?index=0' \
  --output song.mp3
```

**Response headers**
```
content-disposition: attachment; filename="58e15e57-3022-4f43-8ada-64ea52a9064a.mp3"
content-type: audio/mpeg
```

---

## Clip generation (Foundation-1)

> All `/v1/clip/*` endpoints return HTTP 503 if `clip` is not the active model.

Foundation-1 generates short instrument clips (4 or 8 bars) from a structured text prompt, producing both a WAV audio file and a MIDI transcription simultaneously.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/clip/generate` | Submit a clip generation task |
| `GET` | `/v1/clip/result/{task_id}` | Poll task status |
| `GET` | `/v1/clip/audio/{task_id}` | Download the generated WAV file |
| `GET` | `/v1/clip/midi/{task_id}` | Download the generated MIDI file |

---

### `POST /v1/clip/generate`

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

Foundation-1 prompts are structured tag lists:

```
[Instrument family], [Sub-type], [Timbre descriptors], [FX], [Bars], [BPM], [Key]
```

Examples:
- `"Piano, Rhodes Piano, Warm, Bright, Lush, 8 Bars, 120 BPM, C major"`
- `"Bass, FM Bass, Acid, Gritty, Thick, 8 Bars, 140 BPM, E minor"`
- `"Synth, Wavetable Synth, Pad, Wide, Silky, 4 Bars, 128 BPM, A minor"`

**Example request**

```bash
curl -X POST 'http://127.0.0.1:8000/v1/clip/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Gritty, Acid, Bassline, 303, Synth Lead, FM, Sub, Upper Mids, High Phaser, High Reverb, Pitch Bend, 8 Bars, 140 BPM, E minor",
    "bars": 8,
    "bpm": 140,
    "note": "E",
    "scale": "minor",
    "steps": 75,
    "cfg_scale": 7,
    "seed": -1,
    "sampler_type": "dpmpp-2m-sde",
    "sigma_min": 0.03,
    "sigma_max": 500,
    "cfg_rescale": 0
  }'
```

**Response**
```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d"
}
```

---

### `GET /v1/clip/result/{task_id}`

Poll until `status` is `"complete"`. Recommended interval: 2–5 seconds.

**Response — pending / running**
```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d",
  "status": "running",
  "error": null
}
```

**Response — complete**
```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d",
  "status": "complete"
}
```

Once complete, download the files using the same `task_id`:
- `GET /v1/clip/audio/{task_id}` → WAV
- `GET /v1/clip/midi/{task_id}` → MIDI

**Response — error**
```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d",
  "status": "error",
  "error": "Generation failed — check server logs."
}
```

---

### `GET /v1/clip/audio/{task_id}`

Download the generated WAV file (32 kHz stereo).

```bash
curl -X GET \
  'http://127.0.0.1:8000/v1/clip/audio/7ab55a6a-c478-45a0-bab7-1fd9cbd8597d' \
  --output clip.wav
```

**Response headers**
```
content-type: audio/wav
content-length: 2419244
```

---

### `GET /v1/clip/midi/{task_id}`

Download the MIDI transcription (via [basic-pitch](https://github.com/spotify/basic-pitch)).

```bash
curl -X GET \
  'http://127.0.0.1:8000/v1/clip/midi/7ab55a6a-c478-45a0-bab7-1fd9cbd8597d' \
  --output clip.mid
```

**Response headers**
```
content-type: audio/midi
content-length: 1458
```

---

## Stem separation (python-audio-separator)

> All `/v1/separator/*` endpoints return HTTP 503 if `separator` is not the active model.

Separates an uploaded audio file into individual stems using UVR models. Outputs are always MP3.

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/separator/separate` | Upload audio + select model → task ID |
| `GET` | `/v1/separator/result/{task_id}` | Poll task status and retrieve output filenames |
| `GET` | `/v1/separator/download/{filename}` | Download a separated stem file |

---

### `POST /v1/separator/separate`

Accepts `multipart/form-data`.

**Form fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | Audio file to separate (MP3, WAV, FLAC, …) |
| `model_filename` | string | yes | One of the supported models below |

**Supported models**

| `model_filename` | Stems produced |
|-----------------|----------------|
| `UVR-MDX-NET-Inst_HQ_3.onnx` | 2 — Vocals, Instrumental |
| `MDX23C-8KFFT-InstVoc_HQ.ckpt` | 2 — Vocals, Instrumental |
| `htdemucs_6s.yaml` | 6 — bass, drums, guitar, other, piano, vocals |

Models are downloaded automatically by `audio-separator` on first use.

**Example request**

```bash
curl -X POST 'http://127.0.0.1:8000/v1/separator/separate' \
  -H 'accept: application/json' \
  -F 'file=@song.mp3;type=audio/mpeg' \
  -F 'model_filename=MDX23C-8KFFT-InstVoc_HQ.ckpt'
```

**Response**
```json
{ "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76" }
```

---

### `GET /v1/separator/result/{task_id}`

Poll until `status` is `"complete"`. Separation typically takes 10–60 seconds.

**Response — running**
```json
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76",
  "status": "running"
}
```

**Response — complete**
```json
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76",
  "status": "complete",
  "files": [
    "0b93cb76-616d-45f0-9580-61d615cd6a76_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.mp3",
    "0b93cb76-616d-45f0-9580-61d615cd6a76_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3"
  ]
}
```

**Response — error**
```json
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76",
  "status": "error",
  "error": "Separation failed — check server logs."
}
```

---

### `GET /v1/separator/download/{filename}`

Download a stem MP3 file. `filename` is one of the entries from the `files` list above.

```bash
curl -X GET \
  'http://127.0.0.1:8000/v1/separator/download/0b93cb76-616d-45f0-9580-61d615cd6a76_%28Vocals%29_MDX23C-8KFFT-InstVoc_HQ.mp3' \
  --output vocals.mp3
```

**Response headers**
```
content-disposition: attachment; filename="0b93cb76-...(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3"
content-type: audio/mpeg
```

---

## Typical Workflows

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
    "instrumental": true,
    "inference_steps": 8,
    "use_random_seed": true,
    "audio_format": "mp3"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['data']['task_id'])")

# 3. Poll until status == 1
curl http://localhost:8000/v1/fullsong/result/$TASK

# 4. Download
curl "http://localhost:8000/v1/fullsong/audio/$TASK" --output song.mp3
```

### Generate a MIDI + WAV clip

```bash
# 1. Load Foundation-1
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "clip"}'

# 2. Submit generation
TASK=$(curl -s -X POST http://localhost:8000/v1/clip/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Keys, Rhodes Piano, Warm, Lush, 8 Bars, 90 BPM, D major",
    "bars": 8, "bpm": 90, "note": "D", "scale": "major", "steps": 75
  }' | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# 3. Poll until status == "complete"
curl http://localhost:8000/v1/clip/result/$TASK

# 4. Download both files
curl "http://localhost:8000/v1/clip/audio/$TASK" --output clip.wav
curl "http://localhost:8000/v1/clip/midi/$TASK"  --output clip.mid
```

### Separate stems from an audio file

```bash
# 1. Load separator (frees VRAM from any active model)
curl -X POST http://localhost:8000/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "separator"}'

# 2. Submit separation
TASK=$(curl -s -X POST http://localhost:8000/v1/separator/separate \
  -F "file=@song.mp3" \
  -F "model_filename=UVR-MDX-NET-Inst_HQ_3.onnx" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# 3. Poll until complete
curl http://localhost:8000/v1/separator/result/$TASK

# 4. Download stems (use filenames from the result response)
curl "http://localhost:8000/v1/separator/download/...(Vocals)....mp3" --output vocals.mp3
curl "http://localhost:8000/v1/separator/download/...(Instrumental)....mp3" --output instrumental.mp3
```

---

## Error Reference

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
