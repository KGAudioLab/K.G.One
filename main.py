"""KGOne — unified REST API gateway for ACE-Step 1.5 (fullsong), Foundation-1 (clip), and UVR separator."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import threading
import urllib.parse
import uuid
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from services.model_manager import ModelManager, ModelNotActiveError, model_manager
from services.acestep_client import ACESTEP_BASE_URL
from services.foundation1_client import FOUNDATION1_BASE_URL
from services.separator_runner import ALLOWED_MODELS, OUTPUT_DIR, UPLOAD_DIR, separator_runner

_KGSTUDIO_DIST = Path(__file__).parent / "kgstudio" / "dist"
_SOUNDFONTS_DIR = Path(__file__).parent / "soundfonts"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    display_host = getattr(app.state, "display_host", "127.0.0.1")
    port = getattr(app.state, "port", 8000)
    url = f"http://{display_host}:{port}/kgstudio/"
    threading.Timer(1.5, webbrowser.open, args=[url]).start()
    async with httpx.AsyncClient(timeout=300.0) as client:
        app.state.http_client = client
        yield
    await model_manager.unload()


app = FastAPI(
    title="KGOne Gateway",
    description="Unified REST API for ACE-Step 1.5 (full-song music) and Foundation-1 (clip MIDI/WAV).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if _SOUNDFONTS_DIR.is_dir():
    app.mount("/soundfont-for-samplers", StaticFiles(directory=str(_SOUNDFONTS_DIR)), name="soundfonts")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _proxy(client: httpx.AsyncClient, method: str, url: str, request: Request) -> Response:
    """Forward a request body + headers to a sub-service and return its response."""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    try:
        resp = await client.request(method, url, content=body, headers=headers)
    except httpx.ConnectError:
        raise HTTPException(503, "Sub-service unreachable — is the model loaded?")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding",)},
        media_type=resp.headers.get("content-type"),
    )


def _require(model_name: str) -> None:
    """Raise 503 if the requested model is not the active one."""
    if model_manager.active_model != model_name:
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Model '{model_name}' is not loaded. POST /v1/models/load first.",
                "active_model": model_manager.active_model,
            },
        )


# ---------------------------------------------------------------------------
# Health & model management
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "active_model": model_manager.active_model}


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
    if req.model not in ("fullsong", "clip", "separator"):
        raise HTTPException(400, f"Unknown model '{req.model}'. Must be 'fullsong', 'clip', or 'separator'.")
    if separator_runner.active:
        raise HTTPException(503, "A stem separation task is currently running. Wait for it to complete first.")
    await model_manager.load(req.model)
    return {"active_model": model_manager.active_model, "status": "ready"}


@app.get("/v1/models/status", tags=["system"])
async def model_status():
    return {"active_model": model_manager.active_model}


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
async def fullsong_generate(req: FullsongGenerateRequest, request: Request):
    """Proxy to ACE-Step's `/release_task`.

    Forwards the exact JSON body you send (only fields you include are forwarded —
    no defaults are injected). Extra ACE-Step fields beyond those listed are also passed through.

    Returns `{"data": {"task_id": "...", "status": "queued", ...}}`.
    """
    _require("fullsong")
    body = req.model_dump_json(exclude_unset=True).encode()
    try:
        resp = await request.app.state.http_client.post(
            f"{ACESTEP_BASE_URL}/release_task",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    except httpx.ConnectError:
        raise HTTPException(503, "Sub-service unreachable — is the model loaded?")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding",)},
        media_type=resp.headers.get("content-type"),
    )


@app.get(
    "/v1/fullsong/result/{task_id}",
    tags=["fullsong"],
    summary="Poll a fullsong generation task result",
)
async def fullsong_result(task_id: str, request: Request):
    """Query the result of a generation task.

    Returns ACE-Step's raw result payload. Poll until `status` is `1` (succeeded),
    then call `GET /v1/fullsong/audio/{task_id}` to download the audio.
    """
    _require("fullsong")
    payload = json.dumps({"task_id_list": [task_id]}).encode()
    try:
        resp = await request.app.state.http_client.post(
            f"{ACESTEP_BASE_URL}/query_result",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    except httpx.ConnectError:
        raise HTTPException(503, "ACE-Step service unreachable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get(
    "/v1/fullsong/audio/{task_id}",
    tags=["fullsong"],
    summary="Download generated audio for a completed fullsong task",
)
async def fullsong_audio(task_id: str, request: Request, index: int = 0):
    """Download the generated audio file for a completed task.

    Internally queries ACE-Step for the task result, extracts the audio path,
    and streams the file back. Only works once the task `status` is `1` (succeeded).

    Use `index` (0-based) to select a specific file when `batch_size > 1`.
    """
    _require("fullsong")
    client: httpx.AsyncClient = request.app.state.http_client

    # Step 1: fetch the task result from ACE-Step
    try:
        result_resp = await client.post(
            f"{ACESTEP_BASE_URL}/query_result",
            content=json.dumps({"task_id_list": [task_id]}).encode(),
            headers={"Content-Type": "application/json"},
        )
    except httpx.ConnectError:
        raise HTTPException(503, "ACE-Step service unreachable")

    try:
        result_data = result_resp.json()
    except Exception:
        raise HTTPException(502, "Invalid response from ACE-Step")

    items = result_data.get("data", [])
    task_item = next((item for item in items if item.get("task_id") == task_id), None)
    if task_item is None:
        raise HTTPException(404, f"Task '{task_id}' not found")
    if task_item.get("status") != 1:
        raise HTTPException(409, "Task is not yet complete — poll /v1/fullsong/result/{task_id} until status is 1")

    # Step 2: parse the nested result JSON string and extract the file path
    raw_result = task_item.get("result")
    if not isinstance(raw_result, str):
        raise HTTPException(502, "Unexpected result format from ACE-Step")
    try:
        results = json.loads(raw_result)
    except json.JSONDecodeError:
        raise HTTPException(502, "Could not parse ACE-Step result JSON")

    if not results or index >= len(results):
        raise HTTPException(404, f"No audio at index {index} (batch contains {len(results)} file(s))")

    file_url = results[index].get("file", "")
    if not file_url or "path=" not in file_url:
        raise HTTPException(502, "No audio file path in ACE-Step result")

    # parse_qs handles URL-decoding, giving us the raw filesystem path
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(file_url).query)
    fs_path = qs.get("path", [""])[0]
    if not fs_path:
        raise HTTPException(502, "Could not extract audio path from ACE-Step result")

    # Step 3: proxy the audio from ACE-Step — httpx re-encodes the path correctly
    try:
        audio_resp = await client.get(f"{ACESTEP_BASE_URL}/v1/audio", params={"path": fs_path})
    except httpx.ConnectError:
        raise HTTPException(503, "ACE-Step service unreachable")

    if audio_resp.status_code == 404:
        raise HTTPException(404, "Audio file not found on ACE-Step server")
    if audio_resp.status_code != 200:
        raise HTTPException(502, f"ACE-Step returned {audio_resp.status_code} for audio download")

    ext = Path(fs_path).suffix  # e.g. ".mp3" — taken from the actual saved file
    return Response(
        content=audio_resp.content,
        status_code=200,
        media_type=audio_resp.headers.get("content-type", "audio/mpeg"),
        headers={"Content-Disposition": f'attachment; filename="{task_id}{ext}"'},
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
async def clip_generate(req: ClipGenerateRequest, request: Request):
    """Submit a MIDI + WAV generation task to Foundation-1.

    Returns `{"task_id": "..."}`. Poll `/v1/clip/result/{task_id}` for completion.
    """
    _require("clip")
    body = req.model_dump_json(exclude_unset=True).encode()
    try:
        resp = await request.app.state.http_client.post(
            f"{FOUNDATION1_BASE_URL}/generate",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    except httpx.ConnectError:
        raise HTTPException(503, "Sub-service unreachable — is the model loaded?")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding",)},
        media_type=resp.headers.get("content-type"),
    )


@app.get(
    "/v1/clip/result/{task_id}",
    tags=["clip"],
    summary="Poll a clip generation task result",
)
async def clip_result(task_id: str, request: Request):
    """Returns task status. When `status == "complete"`, the generation is done.
    Download the output files using the same `task_id`:
    - `GET /v1/clip/audio/{task_id}` → WAV
    - `GET /v1/clip/midi/{task_id}` → MIDI
    """
    _require("clip")
    try:
        resp = await request.app.state.http_client.get(f"{FOUNDATION1_BASE_URL}/result/{task_id}")
    except httpx.ConnectError:
        raise HTTPException(503, "Foundation-1 service unreachable")

    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get(
    "/v1/clip/audio/{task_id}",
    tags=["clip"],
    summary="Download a generated WAV clip",
)
async def clip_audio(task_id: str, request: Request):
    _require("clip")
    try:
        resp = await request.app.state.http_client.get(f"{FOUNDATION1_BASE_URL}/audio/{task_id}")
    except httpx.ConnectError:
        raise HTTPException(503, "Foundation-1 service unreachable")
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "audio/wav"))


@app.get(
    "/v1/clip/midi/{task_id}",
    tags=["clip"],
    summary="Download a generated MIDI clip",
)
async def clip_midi(task_id: str, request: Request):
    _require("clip")
    try:
        resp = await request.app.state.http_client.get(f"{FOUNDATION1_BASE_URL}/midi/{task_id}")
    except httpx.ConnectError:
        raise HTTPException(503, "Foundation-1 service unreachable")
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "audio/midi"))


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
    if model_manager.active_model != "separator":
        raise HTTPException(
            503,
            {
                "error": "Separator is not loaded. POST /v1/models/load first.",
                "hint": '{"model": "separator"}',
                "active_model": model_manager.active_model,
            },
        )

    task_id = str(uuid.uuid4())

    # Preserve the original file extension so audio-separator names outputs correctly
    suffix = Path(file.filename or "audio").suffix or ".mp3"
    upload_path = UPLOAD_DIR / f"{task_id}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with upload_path.open("wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    separator_runner.submit(task_id, upload_path, model_filename)
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
    task = separator_runner.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return {"task_id": task_id, **{k: v for k, v in task.items() if k != "created_at"}}


@app.get(
    "/v1/separator/download/{filename}",
    tags=["separator"],
    summary="Download a separated stem file",
)
async def separator_download(filename: str):
    """Download a stem MP3 file produced by a completed separation task.

    `filename` is one of the entries from the `files` list in the result response.
    """
    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.is_file():
        raise HTTPException(404, f"File '{safe_name}' not found")
    return FileResponse(
        str(file_path),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


# ---------------------------------------------------------------------------
# /kgstudio — K.G.Studio static SPA
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def kgstudio_root_redirect():
    return RedirectResponse(url="/kgstudio/", status_code=302)


@app.get("/kgstudio/{full_path:path}", include_in_schema=False)
async def kgstudio_spa(full_path: str):
    candidate = _KGSTUDIO_DIST / full_path
    if candidate.is_file():
        return FileResponse(str(candidate))
    return FileResponse(str(_KGSTUDIO_DIST / "index.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _write_server_config(port: int) -> None:
    """Copy kgone-server.json to kgstudio/dist/ with {port} replaced by the actual port."""
    src = Path(__file__).parent / "kgone-server.json"
    dst = _KGSTUDIO_DIST / "kgone-server.json"
    if not src.is_file():
        logger.warning("kgone-server.json not found — skipping KGStudio config injection")
        return
    content = src.read_text(encoding="utf-8").replace("{port}", str(port))
    dst.write_text(content, encoding="utf-8")
    logger.info("Wrote %s", dst)


def main():
    parser = argparse.ArgumentParser(description="KGOne Gateway")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind (default: 127.0.0.1; use 0.0.0.0 for remote access)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to bind (default: 8000)")
    args = parser.parse_args()

    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    app.state.host = args.host
    app.state.port = args.port
    app.state.display_host = display_host

    _write_server_config(args.port)

    print(f"\nK.G.Studio: http://{display_host}:{args.port}/kgstudio/")
    print(f"API docs:   http://{display_host}:{args.port}/docs\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
