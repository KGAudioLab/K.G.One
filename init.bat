@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   KGOne Initialization Script (Windows)
echo ==========================================
echo.

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo Checking prerequisites...

where git >nul 2>&1
if errorlevel 1 (
    echo   ERROR: git not found. Install from https://git-scm.com/downloads
    exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
    echo   ERROR: uv not found. Install from https://docs.astral.sh/uv/
    exit /b 1
)

echo   git ... OK
echo   uv  ... OK
echo.

:: ---------------------------------------------------------
echo [1/6] Reading submodules.json...
:: ---------------------------------------------------------

powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.'ace-step'.url | Out-File -Encoding ASCII '%TEMP%\kg_acestep_url.txt' -NoNewline"
if errorlevel 1 (
    echo   ERROR: Failed to read submodules.json
    exit /b 1
)
powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.'ace-step'.commit | Out-File -Encoding ASCII '%TEMP%\kg_acestep_commit.txt' -NoNewline"
powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.foundation1.url | Out-File -Encoding ASCII '%TEMP%\kg_f1_url.txt' -NoNewline"
powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.foundation1.commit | Out-File -Encoding ASCII '%TEMP%\kg_f1_commit.txt' -NoNewline"
powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.'python-audio-separator'.url | Out-File -Encoding ASCII '%TEMP%\kg_sep_url.txt' -NoNewline"
powershell -NoProfile -Command "$j = Get-Content 'submodules.json' | ConvertFrom-Json; $j.'python-audio-separator'.commit | Out-File -Encoding ASCII '%TEMP%\kg_sep_commit.txt' -NoNewline"

set /p ACESTEP_URL=<"%TEMP%\kg_acestep_url.txt"
set /p ACESTEP_COMMIT=<"%TEMP%\kg_acestep_commit.txt"
set /p FOUNDATION1_URL=<"%TEMP%\kg_f1_url.txt"
set /p FOUNDATION1_COMMIT=<"%TEMP%\kg_f1_commit.txt"
set /p SEP_URL=<"%TEMP%\kg_sep_url.txt"
set /p SEP_COMMIT=<"%TEMP%\kg_sep_commit.txt"
del "%TEMP%\kg_acestep_url.txt" "%TEMP%\kg_acestep_commit.txt" "%TEMP%\kg_f1_url.txt" "%TEMP%\kg_f1_commit.txt" "%TEMP%\kg_sep_url.txt" "%TEMP%\kg_sep_commit.txt" >nul 2>&1

if "%ACESTEP_URL%"=="" (
    echo   ERROR: Could not read from submodules.json
    exit /b 1
)

echo   ACE-Step          URL   : %ACESTEP_URL%
echo   ACE-Step          commit: %ACESTEP_COMMIT%
echo   Foundation-1      URL   : %FOUNDATION1_URL%
echo   Foundation-1      commit: %FOUNDATION1_COMMIT%
echo   audio-separator   URL   : %SEP_URL%
echo   audio-separator   commit: %SEP_COMMIT%
echo.

:: ---------------------------------------------------------
echo [2/6] Setting up ACE-Step...
:: ---------------------------------------------------------

if exist "ace-step\.git" goto :acestep_fetch
echo   Cloning ACE-Step (may take several minutes)...
git clone "%ACESTEP_URL%" ace-step
if errorlevel 1 (
    echo   ERROR: Failed to clone ACE-Step
    exit /b 1
)
goto :acestep_checkout

:acestep_fetch
echo   Repository exists. Fetching refs...
git -C ace-step fetch --quiet origin

:acestep_checkout
echo   Checking out pinned commit %ACESTEP_COMMIT%...
git -C ace-step checkout %ACESTEP_COMMIT% --quiet
if errorlevel 1 (
    echo   ERROR: Could not checkout ACE-Step commit %ACESTEP_COMMIT%
    exit /b 1
)
echo   ACE-Step OK.
echo.

:: ---------------------------------------------------------
echo [3/6] Setting up Foundation-1...
:: ---------------------------------------------------------

if exist "foundation1\.git" goto :f1_fetch
echo   Cloning Foundation-1...
git clone "%FOUNDATION1_URL%" foundation1
if errorlevel 1 (
    echo   ERROR: Failed to clone Foundation-1
    exit /b 1
)
goto :f1_checkout

:f1_fetch
echo   Repository exists. Fetching refs...
git -C foundation1 fetch --quiet origin

:f1_checkout
echo   Checking out pinned commit %FOUNDATION1_COMMIT%...
git -C foundation1 checkout %FOUNDATION1_COMMIT% --quiet
if errorlevel 1 (
    echo   ERROR: Could not checkout Foundation-1 commit %FOUNDATION1_COMMIT%
    exit /b 1
)
echo   Foundation-1 OK.
echo.

:: ---------------------------------------------------------
echo Setting up python-audio-separator...
:: ---------------------------------------------------------

if exist "separator\.git" goto :sep_fetch
echo   Cloning python-audio-separator...
git clone "%SEP_URL%" separator
if errorlevel 1 (
    echo   ERROR: Failed to clone python-audio-separator
    exit /b 1
)
goto :sep_checkout

:sep_fetch
echo   Repository exists. Fetching refs...
git -C separator fetch --quiet origin

:sep_checkout
echo   Checking out pinned commit %SEP_COMMIT%...
git -C separator checkout %SEP_COMMIT% --quiet
if errorlevel 1 (
    echo   ERROR: Could not checkout python-audio-separator commit %SEP_COMMIT%
    exit /b 1
)
echo   python-audio-separator OK.
echo.

:: ---------------------------------------------------------
echo [4/6] Setting up Python environments...
:: ---------------------------------------------------------

:: Gateway venv
if exist ".venv\Scripts\python.exe" goto :gateway_venv_done
echo   Creating gateway venv...
uv venv .venv
if errorlevel 1 (
    echo   ERROR: Failed to create gateway venv
    exit /b 1
)
uv pip install --python .venv "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0" "httpx>=0.27.0" "python-multipart>=0.0.9"
if errorlevel 1 (
    echo   ERROR: Failed to install gateway dependencies
    exit /b 1
)
echo   Gateway venv OK.
goto :acestep_venv_start
:gateway_venv_done
echo   Gateway venv already exists, skipping.

:: ACE-Step venv
:acestep_venv_start
if exist "ace-step\.venv\Scripts\python.exe" goto :acestep_venv_done
echo   Creating ACE-Step venv...
echo   NOTE: Downloads large CUDA packages. May take 10-20 minutes.
pushd ace-step
uv venv .venv
if errorlevel 1 (
    popd
    echo   ERROR: Failed to create ACE-Step venv
    exit /b 1
)
uv pip install --python .venv -e .
if errorlevel 1 (
    popd
    echo   ERROR: Failed to install ACE-Step dependencies
    exit /b 1
)
popd
echo   ACE-Step venv OK.
goto :f1_venv_start
:acestep_venv_done
echo   ACE-Step venv already exists, skipping.

:: Foundation-1 venv
:f1_venv_start
if exist "foundation1\.venv\Scripts\python.exe" goto :f1_venv_done
echo   Creating Foundation-1 venv (requires Python 3.10)...
uv venv --python 3.10 foundation1\.venv
if errorlevel 1 (
    echo   WARNING: Python 3.10 not found. Falling back to default Python.
    uv venv foundation1\.venv
    if errorlevel 1 (
        echo   ERROR: Failed to create Foundation-1 venv
        exit /b 1
    )
)
echo   Installing PyTorch 2.5.1 (CUDA 12.1 wheels)...
echo   NOTE: This downloads ~2 GB. May take several minutes.
uv pip install --python foundation1\.venv torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo   ERROR: Failed to install PyTorch
    exit /b 1
)
echo   Installing pinned numpy...
uv pip install --python foundation1\.venv "numpy==1.23.5"
if errorlevel 1 (
    echo   ERROR: Failed to install numpy
    exit /b 1
)
echo   Installing Foundation-1 dependencies...
uv pip install --python foundation1\.venv -e foundation1
if errorlevel 1 (
    echo   ERROR: Failed to install Foundation-1 dependencies
    exit /b 1
)
uv pip install --python foundation1\.venv "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0"
if errorlevel 1 (
    echo   ERROR: Failed to install Foundation-1 server dependencies
    exit /b 1
)
echo   Pinning setuptools for pkg_resources compatibility...
uv pip install --python foundation1\.venv "setuptools<70"
if errorlevel 1 (
    echo   ERROR: Failed to pin setuptools
    exit /b 1
)
echo   Foundation-1 venv OK.
goto :sep_venv_start
:f1_venv_done
echo   Foundation-1 venv already exists, skipping.

:: Separator venv
:sep_venv_start
if exist "separator\.venv\pyvenv.cfg" goto :sep_venv_done
echo   Creating separator venv...
echo   NOTE: Downloads CUDA packages. May take several minutes.
uv venv separator\.venv
if errorlevel 1 (
    echo   ERROR: Failed to create separator venv
    exit /b 1
)
uv pip install --python separator\.venv -e "separator[gpu]"
if errorlevel 1 (
    echo   ERROR: Failed to install audio-separator
    exit /b 1
)
uv pip uninstall --python separator\.venv torch torchvision
uv pip install --python separator\.venv torch==2.11.0+cu126 torchvision==0.26.0+cu126 --index-url https://download.pytorch.org/whl/cu126
if errorlevel 1 (
    echo   ERROR: Failed to install PyTorch for separator
    exit /b 1
)
uv pip install --python separator\.venv --force-reinstall onnxruntime-gpu
if errorlevel 1 (
    echo   ERROR: Failed to install onnxruntime-gpu
    exit /b 1
)
echo   Separator venv OK.
goto :venvs_done
:sep_venv_done
echo   Separator venv already exists, skipping.

:venvs_done
echo.

:: ---------------------------------------------------------
echo [5/6] Creating output directories...
:: ---------------------------------------------------------
if not exist "outputs\clip"            mkdir "outputs\clip"
if not exist "outputs\fullsong"        mkdir "outputs\fullsong"
if not exist "outputs\separator"       mkdir "outputs\separator"
if not exist "uploads\separator"       mkdir "uploads\separator"
if not exist "foundation1\generations" mkdir "foundation1\generations"
if not exist "foundation1\models"      mkdir "foundation1\models"
echo   Done.
echo.

:: ---------------------------------------------------------
echo [6/6] Downloading model weights...
:: ---------------------------------------------------------

:: ACE-Step weights - mirrors what the API server does on first initialize:
::   ensure_model_downloaded('acestep-v15-turbo', checkpoints/)
::   ensure_model_downloaded('vae', checkpoints/)
:: Auto-selects HuggingFace vs ModelScope by pinging Google (or ACESTEP_DOWNLOAD_SOURCE env var).
if exist "ace-step\checkpoints\acestep-v15-turbo\model.safetensors" goto :acestep_weights_done
echo   Downloading ACE-Step checkpoints (may take several minutes)...
ace-step\.venv\Scripts\python.exe -c "from acestep.api.model_download import ensure_model_downloaded; import os; ckpt=os.path.join(os.getcwd(),'ace-step','checkpoints'); ensure_model_downloaded('acestep-v15-turbo', ckpt); ensure_model_downloaded('vae', ckpt)"
if errorlevel 1 (
    echo   ERROR: ACE-Step weight download failed
    exit /b 1
)
:acestep_weights_done
echo   ACE-Step weights OK.
echo.

:: Foundation-1 weights (huggingface_hub is already installed as a dep of stable_audio_tools)
if exist "foundation1\models\RoyalCities-Foundation-1\Foundation_1.safetensors" goto :f1_weights_done
echo   Downloading Foundation-1 weights (approx 1.7 GB)...
foundation1\.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('RoyalCities/Foundation-1', local_dir='foundation1/models/RoyalCities-Foundation-1')"
if errorlevel 1 (
    echo   ERROR: Foundation-1 weight download failed
    exit /b 1
)
:f1_weights_done
echo   Foundation-1 weights OK.
echo.

:: Separator models are downloaded automatically by audio-separator on first use.
echo   Separator models will be downloaded on first use (handled by audio-separator).
echo.

echo ==========================================
echo   Initialization complete!
echo ==========================================
echo.
echo Start the gateway:
echo   .venv\Scripts\python.exe main.py
echo.
echo Then load a model:
echo   POST http://localhost:8000/v1/models/load
echo   Body: {"model": "clip"}     -- Foundation-1 (MIDI + WAV)
echo   Body: {"model": "fullsong"} -- ACE-Step 1.5 (full songs)
echo.
echo Or separate stems (no model load needed):
echo   POST http://localhost:8000/v1/separator/separate
echo   Body: multipart/form-data  file=<audio> model_filename=<model>
echo.
echo API docs: http://localhost:8000/docs
echo.
