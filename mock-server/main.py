"""KGOne Mock Gateway — same API surface as the real server, no ML models required.

Place sample files in ./samples/ before starting:
  sample.mp3
  clip.wav
  clip.mid
  separator_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3
  separator_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.mp3

Run:
  uv sync
  .venv/Scripts/python.exe main.py        # Windows
  .venv/bin/python main.py                # Linux / macOS
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
SAMPLES_DIR = BASE_DIR / "samples"

ALLOWED_MODELS = {
    "UVR-MDX-NET-Inst_HQ_3.onnx",
    "MDX23C-8KFFT-InstVoc_HQ.ckpt",
    "htdemucs_6s.yaml",
}

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

_active_model: Optional[str] = None
_tasks: dict[str, float] = {}  # task_id -> unix timestamp of creation

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KGOne Gateway",
    description="Unified REST API for ACE-Step 1.5 (full-song music) and Foundation-1 (clip MIDI/WAV).",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require(model_name: str) -> None:
    """Raise 503 if the requested model is not the active one."""
    if _active_model != model_name:
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Model '{model_name}' is not loaded. POST /v1/models/load first.",
                "active_model": _active_model,
            },
        )


def _sample(filename: str) -> Path:
    """Return path to a sample file, raising 500 if it is missing."""
    path = SAMPLES_DIR / filename
    if not path.is_file():
        raise HTTPException(500, f"Mock sample file not found: samples/{filename}")
    return path


def _task_age(task_id: str) -> float:
    """Return seconds since this task was created, or raise 404 if unknown."""
    created_at = _tasks.get(task_id)
    if created_at is None:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return time.time() - created_at


# ---------------------------------------------------------------------------
# Health & model management
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "active_model": _active_model}


class LoadModelRequest(BaseModel):
    model: str  # "fullsong" | "clip"

    model_config = ConfigDict(json_schema_extra={"example": {"model": "fullsong"}})


@app.post("/v1/models/load", tags=["system"])
async def load_model(req: LoadModelRequest):
    """Load a model onto the GPU, unloading the currently active one first.

    - `model`: `"fullsong"` (ACE-Step 1.5), `"clip"` (Foundation-1), or `"separator"` (UVR stem separation)

    For `"fullsong"` and `"clip"` this blocks until the sub-service reports healthy.
    For `"separator"` it only terminates the currently running model subprocess to free VRAM —
    no persistent process is started. After loading `"separator"`, call `POST /v1/separator/separate`.
    """
    global _active_model
    if req.model not in ("fullsong", "clip", "separator"):
        raise HTTPException(400, f"Unknown model '{req.model}'. Must be 'fullsong', 'clip', or 'separator'.")
    await asyncio.sleep(5)
    _active_model = req.model
    return {"active_model": _active_model, "status": "ready"}


@app.get("/v1/models/status", tags=["system"])
async def model_status():
    return {"active_model": _active_model}


# ---------------------------------------------------------------------------
# /v1/fullsong — ACE-Step 1.5
# ---------------------------------------------------------------------------


class FullsongGenerateRequest(BaseModel):
    """ACE-Step 1.5 generation request. All listed fields are forwarded as-is;
    any additional ACE-Step fields are also accepted and forwarded."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "caption": "Genre: Eurodance, 90s dance-pop, upbeat electronic. Style: Catchy, energetic, nostalgic 90s Eurodance with a strong four-on-the-floor beat. Bright synth leads, punchy bassline, and rhythmic chord stabs. Mix of melodic female vocals for chorus and rhythmic male spoken/rap-style verses. Mood: Uplifting, euphoric, nostalgic club vibe. Tempo: ~130 BPM. Instrumentation: driving kick drum, eurodance bassline, bright saw synth leads, pads, dance piano accents, light vocal chops. Structure: Intro → Verse (male rap) → Pre-Chorus → Chorus (female melodic hook) → Verse → Chorus → Bridge → Final Chorus. Production: clean, polished, wide stereo, club-ready mix.",
                "lyrics": "[Intro]\nFeel the rhythm, feel the light\nWe come alive in neon night\n\n[Verse 1 – Male]\nStep in the scene, yeah the bassline drops\nHeartbeat racing when the strobe light pops\nHands up high, let the pressure go\nMove your body to the radio\n\n[Pre-Chorus – Female]\nTake me higher, don't let go\nWe're electric, feel the flow\n\n[Chorus – Female]\nWe are dancing in the neon in the night\nShining brighter than the stars in the sky\nFeel the fire, let it take you away\nWe will never fade",
                "instrumental": False,
                "inference_steps": 8,
                "guidance_scale": 7.0,
                "use_random_seed": False,
                "seed": -1,
                "thinking": True,
                "batch_size": 1,
                "audio_format": "mp3",
            }
        },
    )

    caption: Optional[str] = None
    lyrics: Optional[str] = None
    instrumental: Optional[bool] = None
    inference_steps: Optional[int] = None
    guidance_scale: Optional[float] = None
    use_random_seed: Optional[bool] = None
    seed: Optional[int] = None
    thinking: Optional[bool] = None
    batch_size: Optional[int] = None
    audio_format: Optional[str] = None


@app.post(
    "/v1/fullsong/generate",
    tags=["fullsong"],
    summary="Submit a full-song generation task (ACE-Step 1.5)",
)
async def fullsong_generate(req: FullsongGenerateRequest):
    """Proxy to ACE-Step's `/release_task`.

    Forwards the exact JSON body you send (only fields you include are forwarded —
    no defaults are injected). Extra ACE-Step fields beyond those listed are also passed through.

    Returns `{"data": {"task_id": "...", "status": "queued", ...}}`.
    """
    _require("fullsong")
    task_id = str(uuid.uuid4())
    _tasks[task_id] = time.time()
    return {
        "data": {
            "task_id": task_id,
            "status": "queued",
            "queue_position": 1,
        },
        "code": 200,
        "error": None,
        "timestamp": int(time.time() * 1000),
        "extra": None,
    }


@app.get(
    "/v1/fullsong/result/{task_id}",
    tags=["fullsong"],
    summary="Poll a fullsong generation task result",
)
async def fullsong_result(task_id: str):
    """Query the result of a generation task.

    Returns ACE-Step's raw result payload. Poll until `status` is `1` (succeeded),
    then call `GET /v1/fullsong/audio/{task_id}` to download the audio.
    """
    _require("fullsong")
    age = _task_age(task_id)
    ts = int(time.time() * 1000)

    if age < 10:
        result_inner = json.dumps([{
            "file": "",
            "wave": "",
            "status": 0,
            "create_time": int(_tasks[task_id]),
            "env": "development",
            "progress": min(0.9, age / 10),
            "stage": "Phase 1: Generating CoT metadata (once for all items)...",
        }])
        return {
            "data": [{
                "task_id": task_id,
                "result": result_inner,
                "status": 0,
                "progress_text": "Generating...",
            }],
            "code": 200,
            "error": None,
            "timestamp": ts,
            "extra": None,
        }

    result_inner = json.dumps([{
        "file": "/v1/audio?path=mock",
        "wave": "",
        "status": 1,
        "create_time": int(_tasks[task_id]),
        "env": "development",
        "progress": 1.0,
        "stage": "succeeded",
    }])
    return {
        "data": [{
            "task_id": task_id,
            "result": result_inner,
            "status": 1,
            "progress_text": "Done.",
        }],
        "code": 200,
        "error": None,
        "timestamp": ts,
        "extra": None,
    }


@app.get(
    "/v1/fullsong/audio/{task_id}",
    tags=["fullsong"],
    summary="Download generated audio for a completed fullsong task",
)
async def fullsong_audio(task_id: str, index: int = 0):
    """Download the generated audio file for a completed task.

    Internally queries ACE-Step for the task result, extracts the audio path,
    and streams the file back. Only works once the task `status` is `1` (succeeded).

    Use `index` (0-based) to select a specific file when `batch_size > 1`.
    """
    _require("fullsong")
    if _task_age(task_id) < 10:
        raise HTTPException(409, "Task is not yet complete — poll /v1/fullsong/result/{task_id} until status is 1")
    path = _sample("sample.mp3")
    return FileResponse(
        str(path),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{task_id}.mp3"'},
    )


# ---------------------------------------------------------------------------
# /v1/clip — Foundation-1
# ---------------------------------------------------------------------------


class ClipGenerateRequest(BaseModel):
    """Foundation-1 clip generation request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Gritty, Acid, Bassline, 303, Synth Lead, FM, Sub, Upper Mids, High Phaser, High Reverb, Pitch Bend, 8 Bars, 140 BPM, E minor",
                "negative_prompt": "",
                "bars": 8,
                "bpm": 140,
                "note": "C",
                "scale": "minor",
                "steps": 75,
                "cfg_scale": 7,
                "seed": -1,
                "sampler_type": "dpmpp-2m-sde",
                "sigma_min": 0.03,
                "sigma_max": 500,
                "cfg_rescale": 0,
            }
        }
    )

    prompt: str
    negative_prompt: str = ""
    bars: int = 4
    bpm: int = 140
    note: str = "C"
    scale: str = "minor"
    steps: int = 75
    cfg_scale: float = 7.0
    seed: int = -1
    sampler_type: str = "dpmpp-2m-sde"
    sigma_min: float = 0.03
    sigma_max: float = 500.0
    cfg_rescale: float = 0.0


@app.post(
    "/v1/clip/generate",
    tags=["clip"],
    summary="Submit a clip generation task (Foundation-1)",
)
async def clip_generate(req: ClipGenerateRequest):
    """Submit a MIDI + WAV generation task to Foundation-1.

    Returns `{"task_id": "..."}`. Poll `/v1/clip/result/{task_id}` for completion.
    """
    _require("clip")
    task_id = str(uuid.uuid4())
    _tasks[task_id] = time.time()
    return {"task_id": task_id}


@app.get(
    "/v1/clip/result/{task_id}",
    tags=["clip"],
    summary="Poll a clip generation task result",
)
async def clip_result(task_id: str):
    """Returns task status. When `status == "complete"`, the generation is done.
    Download the output files using the same `task_id`:
    - `GET /v1/clip/audio/{task_id}` → WAV
    - `GET /v1/clip/midi/{task_id}` → MIDI
    """
    _require("clip")
    age = _task_age(task_id)
    status = "complete" if age >= 10 else "pending"
    return {"task_id": task_id, "status": status}


@app.get(
    "/v1/clip/audio/{task_id}",
    tags=["clip"],
    summary="Download a generated WAV clip",
)
async def clip_audio(task_id: str):
    _require("clip")
    _task_age(task_id)  # raises 404 if unknown
    path = _sample("clip.wav")
    return FileResponse(str(path), media_type="audio/wav")


@app.get(
    "/v1/clip/midi/{task_id}",
    tags=["clip"],
    summary="Download a generated MIDI clip",
)
async def clip_midi(task_id: str):
    _require("clip")
    _task_age(task_id)  # raises 404 if unknown
    path = _sample("clip.mid")
    return FileResponse(str(path), media_type="audio/midi")


# ---------------------------------------------------------------------------
# /v1/separator — UVR stem separation
# ---------------------------------------------------------------------------


@app.post(
    "/v1/separator/separate",
    tags=["separator"],
    summary="Submit a stem separation task",
)
async def separator_separate(
    file: UploadFile = File(...),
    model_filename: str = Form(...),
):
    """Upload an audio file and separate its stems using the chosen UVR model.

    - `file`: audio file (MP3, WAV, FLAC, …)
    - `model_filename`: one of `UVR-MDX-NET-Inst_HQ_3.onnx`, `MDX23C-8KFFT-InstVoc_HQ.ckpt`,
      `htdemucs_6s.yaml`

    Returns `{"task_id": "..."}`. Poll `/v1/separator/result/{task_id}` for completion.
    The number of output files depends on the model (2 for MDX models, 6 for htdemucs_6s).
    """
    if model_filename not in ALLOWED_MODELS:
        raise HTTPException(
            400,
            f"Unknown model '{model_filename}'. Must be one of: {sorted(ALLOWED_MODELS)}",
        )
    if _active_model != "separator":
        raise HTTPException(
            503,
            {
                "error": "Separator is not loaded. POST /v1/models/load first.",
                "hint": '{"model": "separator"}',
                "active_model": _active_model,
            },
        )
    task_id = str(uuid.uuid4())
    _tasks[task_id] = time.time()
    return {"task_id": task_id}


@app.get(
    "/v1/separator/result/{task_id}",
    tags=["separator"],
    summary="Poll a stem separation task result",
)
async def separator_result(task_id: str):
    """Returns task status.

    - `pending` / `running` while in progress
    - `complete` — includes `files`: list of output filenames (download via `/v1/separator/download/{filename}`)
    - `error` — includes `error` message
    """
    age = _task_age(task_id)
    if age < 10:
        return {"task_id": task_id, "status": "running"}
    return {
        "task_id": task_id,
        "status": "complete",
        "files": [
            f"{task_id}_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.mp3",
            f"{task_id}_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3",
        ],
    }


@app.get(
    "/v1/separator/download/{filename}",
    tags=["separator"],
    summary="Download a separated stem file",
)
async def separator_download(filename: str):
    """Download a stem MP3 file produced by a completed separation task.

    `filename` is one of the entries from the `files` list in the result response.
    """
    if "Vocals" in filename:
        sample_name = "separator_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3"
    else:
        sample_name = "separator_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.mp3"
    path = _sample(sample_name)
    safe_name = Path(filename).name
    return FileResponse(
        str(path),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
