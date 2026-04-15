"""GPU model manager — ensures only one model subprocess runs at a time."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx

ROOT_DIR = Path(__file__).parent.parent

ACESTEP_PORT = 8001
FOUNDATION1_PORT = 8002
HEALTH_POLL_INTERVAL = 2.0
HEALTH_TIMEOUT_SECONDS = 180  # model loading can be slow on first run

logger = logging.getLogger(__name__)


def _python_exe(venv_dir: Path) -> Path:
    """Return the Python executable for a given venv directory."""
    win = venv_dir / "Scripts" / "python.exe"
    if win.exists():
        return win
    return venv_dir / "bin" / "python"


class ModelNotActiveError(Exception):
    def __init__(self, requested: str, active: Optional[str]) -> None:
        self.requested = requested
        self.active = active
        super().__init__(f"Model '{requested}' is not loaded (active: {active!r})")


class ModelManager:
    def __init__(self) -> None:
        self.active_model: Optional[str] = None
        self._lock = asyncio.Lock()
        self._process: Optional[subprocess.Popen] = None

    async def load(self, model: str) -> None:
        """Load a model, unloading the currently active one first if needed."""
        async with self._lock:
            if self.active_model == model:
                logger.info("Model '%s' is already active.", model)
                return
            if self.active_model is not None:
                logger.info("Unloading model '%s'...", self.active_model)
                await asyncio.get_event_loop().run_in_executor(None, self._stop_process)
            logger.info("Starting model '%s'...", model)
            await asyncio.get_event_loop().run_in_executor(None, self._start_process, model)
            self.active_model = model
            logger.info("Model '%s' is ready.", model)

    async def unload(self) -> None:
        """Unload the active model."""
        async with self._lock:
            if self.active_model is None:
                return
            logger.info("Unloading model '%s'...", self.active_model)
            await asyncio.get_event_loop().run_in_executor(None, self._stop_process)

    def _stop_process(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully, killing.")
            self._process.kill()
            self._process.wait()
        except Exception as exc:
            logger.error("Error stopping process: %s", exc)
        finally:
            self._process = None
        self.active_model = None

    def _start_process(self, model: str) -> None:
        if model == "fullsong":
            self._process = self._launch_acestep()
            self._wait_healthy(f"http://127.0.0.1:{ACESTEP_PORT}/health")
        elif model == "clip":
            self._process = self._launch_foundation1()
            self._wait_healthy(f"http://127.0.0.1:{FOUNDATION1_PORT}/health")
        elif model == "separator":
            pass  # no persistent process; previous model already stopped by load(), VRAM is free
        else:
            raise ValueError(f"Unknown model: '{model}'. Must be 'fullsong', 'clip', or 'separator'.")

    def _launch_acestep(self) -> subprocess.Popen:
        venv_python = _python_exe(ROOT_DIR / "ace-step" / ".venv")
        cmd = [str(venv_python), "-c", "from acestep.api_server import main; main()"]
        logger.info("Launching ACE-Step: %s", " ".join(cmd))
        return subprocess.Popen(cmd, cwd=str(ROOT_DIR / "ace-step"))

    def _launch_foundation1(self) -> subprocess.Popen:
        venv_python = _python_exe(ROOT_DIR / "foundation1" / ".venv")
        server_script = str(ROOT_DIR / "foundation1_server" / "server.py")
        cmd = [str(venv_python), server_script]
        logger.info("Launching Foundation-1 server: %s", " ".join(cmd))
        return subprocess.Popen(cmd, cwd=str(ROOT_DIR))

    def _wait_healthy(self, url: str) -> None:
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        logger.info("Waiting for service at %s ...", url)
        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        logger.info("Service healthy: %s", url)
                        return
            except Exception:
                pass
            time.sleep(HEALTH_POLL_INTERVAL)
        raise TimeoutError(
            f"Service at {url} did not become healthy within {HEALTH_TIMEOUT_SECONDS}s"
        )


model_manager = ModelManager()
