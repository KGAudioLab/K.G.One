"""Stem separator runner — invokes audio-separator CLI per-request.

Uses a single-worker ThreadPoolExecutor to serialize GPU use.
Coordinates with model_manager: callers should check model_manager.active_model
before submitting, and model load routes should check separator_runner.active.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent
SEPARATOR_DIR = ROOT_DIR / "separator"
OUTPUT_DIR = ROOT_DIR / "outputs" / "separator"
UPLOAD_DIR = ROOT_DIR / "uploads" / "separator"

ALLOWED_MODELS = frozenset([
    "UVR-MDX-NET-Inst_HQ_3.onnx",
    "MDX23C-8KFFT-InstVoc_HQ.ckpt",
    "htdemucs_6s.yaml",
])

logger = logging.getLogger(__name__)


class SeparatorRunner:
    def __init__(self) -> None:
        self._tasks: dict[str, dict] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._running_count = 0
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        with self._lock:
            return self._running_count > 0

    def submit(self, task_id: str, file_path: Path, model_filename: str) -> None:
        """Schedule a separation task. Returns immediately; poll get_task() for status."""
        self._tasks[task_id] = {"status": "pending", "created_at": time.time()}
        with self._lock:
            self._running_count += 1
        self._executor.submit(self._run, task_id, file_path, model_filename)

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def _run(self, task_id: str, file_path: Path, model_filename: str) -> None:
        self._tasks[task_id]["status"] = "running"
        try:
            cmd = [
                "uv", "run", "audio-separator",
                str(file_path),
                "--model_filename", model_filename,
                "--output_dir", str(OUTPUT_DIR),
                "--output_format", "MP3",
            ]
            logger.info("Running separator: %s", " ".join(cmd))
            proc = subprocess.Popen(
                cmd,
                cwd=str(SEPARATOR_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge stderr into stdout
                text=True,
                bufsize=1,
            )
            output_lines: list[str] = []

            def _read_output() -> None:
                for line in proc.stdout:
                    stripped = line.rstrip()
                    logger.info("[separator] %s", stripped)
                    output_lines.append(stripped)

            reader = threading.Thread(target=_read_output, daemon=True)
            reader.start()
            try:
                proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise RuntimeError("audio-separator timed out after 600s")
            finally:
                reader.join(timeout=5)

            if proc.returncode != 0:
                detail = "\n".join(output_lines[-20:]) or "unknown error"
                raise RuntimeError(f"audio-separator exited {proc.returncode}: {detail}")

            # Collect output files — named {input_stem}_{stem_type}_{model_base}.mp3
            stem = file_path.stem
            files = sorted(p.name for p in OUTPUT_DIR.glob(f"{stem}_*"))
            if not files:
                raise RuntimeError("audio-separator completed but produced no output files")

            self._tasks[task_id].update({"status": "complete", "files": files})
            logger.info("Separation complete for task %s: %s", task_id, files)
        except Exception:
            logger.exception("Separation failed for task %s", task_id)
            self._tasks[task_id].update({
                "status": "error",
                "error": "Separation failed — check server logs.",
            })
        finally:
            with self._lock:
                self._running_count -= 1
            # Clean up upload file after processing
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass


separator_runner = SeparatorRunner()
