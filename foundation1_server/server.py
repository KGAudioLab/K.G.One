"""Foundation-1 REST API wrapper server.

Wraps RC-stable-audio-tools' generate_cond() behind FastAPI endpoints.
Runs on port 8002. Managed as a subprocess by the KGOne gateway.

Environment variables:
  FOUNDATION1_PRETRAINED_NAME  HuggingFace model name (default: RoyalCities/Foundation-1)
  FOUNDATION1_CKPT_PATH        Path to local .safetensors checkpoint (overrides pretrained name)
  FOUNDATION1_CONFIG_PATH      Path to local model_config.json (required if CKPT_PATH is set)
  FOUNDATION1_SERVER_PORT      Port to listen on (default: 8002)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── path setup ──────────────────────��──────────────────────────────��──────────
# Must happen BEFORE importing stable_audio_tools — gradio.py opens config.json
# relative to CWD at import time.

ROOT_DIR = Path(__file__).parent.parent.resolve()
FOUNDATION1_DIR = ROOT_DIR / "foundation1"
OUTPUT_DIR = ROOT_DIR / "outputs" / "clip"

if not FOUNDATION1_DIR.exists():
    raise RuntimeError(
        f"Foundation-1 repo not found at {FOUNDATION1_DIR}. "
        "Run init.bat first to clone the submodules."
    )

os.chdir(FOUNDATION1_DIR)
sys.path.insert(0, str(FOUNDATION1_DIR))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── imports from stable_audio_tools (CWD is now FOUNDATION1_DIR) ─────────────
import stable_audio_tools.interface.gradio as _gradio_module  # noqa: E402
from stable_audio_tools.interface.gradio import generate_cond, load_model  # noqa: E402

# Override the output directory from the one baked into config.json
_gradio_module.output_directory = str(OUTPUT_DIR)

# ── logging ────────────────────────────────────────────────────────────────���──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── configuration ─────────────────────────────────────────────────────────────
PRETRAINED_NAME = os.environ.get("FOUNDATION1_PRETRAINED_NAME", "RoyalCities/Foundation-1")
CKPT_PATH = os.environ.get("FOUNDATION1_CKPT_PATH")
CONFIG_PATH = os.environ.get("FOUNDATION1_CONFIG_PATH")
PORT = int(os.environ.get("FOUNDATION1_SERVER_PORT", "8002"))

# Default local paths written by init.bat's snapshot_download step.
# The HuggingFace repo names the file Foundation_1.safetensors (not model.safetensors),
# so get_pretrained_model() would fail — we bypass it by using the local path directly.
_DEFAULT_LOCAL_DIR = ROOT_DIR / "foundation1" / "models" / "RoyalCities-Foundation-1"
_DEFAULT_CKPT = _DEFAULT_LOCAL_DIR / "Foundation_1.safetensors"
_DEFAULT_CONFIG = _DEFAULT_LOCAL_DIR / "model_config.json"

# ── in-memory task store ──────────────────────────────────────────────────────
_tasks: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=1)  # one generation at a time (single GPU)


# ── app lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading Foundation-1 model...")
    _load_foundation1_model()
    logger.info("Foundation-1 model ready.")
    yield
    logger.info("Shutting down Foundation-1 server.")
    _gradio_module.model = None


def _load_foundation1_model() -> None:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Using device: %s", device)

    # Resolve checkpoint: env var override > local download > pretrained_name fallback
    ckpt = Path(CKPT_PATH) if CKPT_PATH else (_DEFAULT_CKPT if _DEFAULT_CKPT.exists() else None)
    config = Path(CONFIG_PATH) if CONFIG_PATH else (_DEFAULT_CONFIG if _DEFAULT_CONFIG.exists() else None)

    if ckpt and config:
        with open(config) as f:
            model_config = json.load(f)
        load_model(model_config=model_config, model_ckpt_path=str(ckpt), device=device)
        logger.info("Loaded local checkpoint: %s", ckpt)
    else:
        # Last resort: let stable_audio_tools attempt its own download.
        # Note: get_pretrained_model() expects model.safetensors; this will fail unless
        # the upstream repo is updated to match that name.
        logger.warning(
            "Local weights not found at %s — falling back to pretrained_name download. "
            "Run init.bat to pre-download weights.",
            _DEFAULT_CKPT,
        )
        load_model(pretrained_name=PRETRAINED_NAME, device=device)
        logger.info("Loaded pretrained model: %s", PRETRAINED_NAME)


app = FastAPI(
    title="Foundation-1 Server",
    description="Wraps Foundation-1 (RC-stable-audio-tools) for REST API use.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── request model ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
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


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _gradio_module.model is not None}


@app.post("/generate")
async def generate(req: GenerateRequest):
    if _gradio_module.model is None:
        raise HTTPException(503, "Model not loaded")

    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending", "created_at": time.time()}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_generate, task_id, req)

    return {"task_id": task_id}


def _run_generate(task_id: str, req: GenerateRequest) -> None:
    _tasks[task_id]["status"] = "running"
    try:
        wav_path, _spectrograms, _piano_roll, midi_path = generate_cond(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt or None,
            bars=req.bars,
            bpm=req.bpm,
            note=req.note,
            scale=req.scale,
            steps=req.steps,
            cfg_scale=req.cfg_scale,
            seed=req.seed,
            sampler_type=req.sampler_type,
            sigma_min=req.sigma_min,
            sigma_max=req.sigma_max,
            cfg_rescale=req.cfg_rescale,
        )
        _tasks[task_id].update(
            {
                "status": "complete",
                "wav_filename": Path(wav_path).name if wav_path else None,
                "midi_filename": Path(midi_path).name if midi_path else None,
            }
        )
    except Exception:
        logger.exception("Generation failed for task %s", task_id)
        _tasks[task_id]["status"] = "error"
        _tasks[task_id]["error"] = "Generation failed — check server logs."


@app.get("/result/{task_id}")
async def get_result(task_id: str):
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")

    status = task["status"]
    if status != "complete":
        return {"task_id": task_id, "status": status, "error": task.get("error")}

    return {"task_id": task_id, "status": "complete"}


@app.get("/audio/{task_id}")
async def serve_audio(task_id: str):
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    filename = task.get("wav_filename")
    if not filename:
        raise HTTPException(404, "No audio file for this task")
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Audio file not found on disk")
    return FileResponse(str(path), media_type="audio/wav")


@app.get("/midi/{task_id}")
async def serve_midi(task_id: str):
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    filename = task.get("midi_filename")
    if not filename:
        raise HTTPException(404, "No MIDI file for this task")
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "MIDI file not found on disk")
    return FileResponse(str(path), media_type="audio/midi")


# ── entry point ────────────────────────────��────────────────────────────────���─

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
