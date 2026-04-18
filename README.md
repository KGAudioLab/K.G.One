# K.G.One Studio

> **AI-native music creation. Compose, generate, and produce — right in your browser.**

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20CUDA-green.svg)

<!-- IMAGE: hero screenshot of K.G.Studio DAW with the K.G.One Music Generator panel open, showing a clip generation result loaded into a track -->

---

## What is K.G.One Studio?

**K.G.One Studio** is an AI-powered music production platform — think Cursor, but for making music. It pairs [K.G.Studio](https://github.com/KGAudioLab/K.G.Studio), a lightweight browser-based DAW, with **K.G.One**, a local AI backend that brings real generative AI capabilities to your workflow.

No heavy software to install. Open K.G.Studio in any modern browser, point it at your K.G.One server, and you can generate full songs from text, produce MIDI clips and WAV loops, or strip apart any track into clean stems — all without leaving the browser.

K.G.Studio ships with a built-in **AI Musician Assistant** for harmony, arrangement, and note editing through natural conversation. K.G.One extends the DAW with a dedicated **K.G.One Music Generator** panel — GPU-accelerated tools for generating full songs, producing MIDI clips, and separating stems, all accessible directly from the browser interface.

Both K.G.Studio and K.G.One are built by the same author.

---

## Platform Capabilities

| What you can do | Powered by | Output | Port |
|-----------------|-----------|--------|------|
| **Compose and edit in the browser DAW** | [K.G.Studio](https://github.com/KGAudioLab/K.G.Studio) | MIDI, Audio tracks, Project files | `/kgstudio/` |
| **Generate a full song from text** | [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | Full-length music (MP3/WAV/FLAC) | 8001 (internal) |
| **Generate MIDI clips + WAV loops from text** | [Foundation-1](https://huggingface.co/RoyalCities/Foundation-1) | WAV audio + MIDI transcription | 8002 (internal) |
| **Separate stems from any audio** | [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) | Vocals, Instrumental, and more (MP3) | CLI (no port) |
| **K.G.One Server** | FastAPI | Routes all AI requests | **8000** (public) |

> **Note:** All AI models require a GPU. Only one model can be active at a time — you switch explicitly via `POST /v1/models/load`.

---

## How It Works

<!-- IMAGE: architecture diagram showing browser → K.G.Studio UI → K.G.One server (port 8000) → AI models (ACE-Step 8001, Foundation-1 8002, audio-separator CLI) with GPU mutex illustrated -->

K.G.Studio runs entirely in the browser — it stores your projects locally and never requires a server to use as a standalone DAW. When you connect it to K.G.One, the **K.G.One Music Generator** panel unlocks inside K.G.Studio, letting you generate full songs, produce MIDI clips, and separate stems without leaving your session.

K.G.One manages a single NVIDIA GPU across all three AI services. When you switch models via the API, the active service is shut down before the next one loads. This keeps VRAM clean and prevents conflicts between the very different dependency stacks each model requires.

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | `init.bat` is Windows-only; Linux/macOS support can be added |
| NVIDIA GPU | CUDA required for all AI models |
| [Git](https://git-scm.com/downloads) | For cloning sub-projects |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python environment manager |
| [nvm-windows](https://github.com/coreybutler/nvm-windows/releases) | Node.js version manager (for building K.G.Studio) |
| Python 3.10 | Required by Foundation-1; ACE-Step works with 3.10+ |

---

## Setup

### 1. Initialize

Run `init.bat` from the project root. It will:

1. Read pinned commit hashes and URLs from `submodules.json`
2. Clone (or update) ACE-Step 1.5 → `ace-step/`
3. Clone (or update) Foundation-1 → `foundation1/`
4. Clone (or update) python-audio-separator → `separator/`
5. Clone (or update) K.G.Studio, install Node dependencies, and build the SPA → `kgstudio/dist/`
6. Clone (or update) soundfonts → `soundfonts/`
7. Create four isolated Python environments:
   - `.venv` — K.G.One server (fastapi, httpx)
   - `ace-step/.venv` — ACE-Step and its CUDA dependencies
   - `foundation1/.venv` — Foundation-1 (Python 3.10, scipy==1.8.1)
   - `separator/.venv` — python-audio-separator (GPU)
8. Create output and upload directories
9. Download ACE-Step and Foundation-1 model weights

```bat
init.bat
```

> **Note:** The first run downloads large runtime packages and model weights (several GB total). How long it takes depends on your network speed and machine — subsequent runs skip already-completed steps.

To use a local Foundation-1 checkpoint instead of downloading from HuggingFace:

```bat
set FOUNDATION1_CKPT_PATH=C:\path\to\foundation1.safetensors
set FOUNDATION1_CONFIG_PATH=C:\path\to\model_config.json
```

### 2. Start K.G.One Studio

```bat
uv run .\main.py
```

The server starts on `http://localhost:8000` and automatically opens K.G.Studio in your browser.

To allow access from other devices on your network:

```bat
uv run .\main.py --host 0.0.0.0
uv run .\main.py --host 0.0.0.0 --port 8080
```

### Upgrading a pinned dependency

Edit the `commit` field in `submodules.json`, delete the corresponding subfolder, then re-run `init.bat`.

---

## Using K.G.One Studio

<!-- IMAGE: screenshot of K.G.Studio showing the K.G.One Music Generator panel — loading a model and triggering a clip generation -->

**K.G.Studio is the recommended way to use K.G.One Studio.** It opens automatically in your browser when the server starts and covers every capability through a visual interface.

**K.G.One Music Generator panel** (requires K.G.One server):
- **Generate a full song** — describe the mood, genre, and style; get back a full-length audio track
- **Generate MIDI clips + WAV loops** — produce instrument loops that land directly on your tracks, ready to edit in the piano roll
- **Separate stems** — split any audio file into vocals, instrumentals, or individual instruments

**K.G.Studio Musician Assistant** (works standalone, no K.G.One needed):
- Arrange, edit, and compose using the AI chat panel — describe what you want and the assistant makes edits directly in the project

> AI generation tools (full song, clip, stem separation) will be integrated into the Musician Assistant in a future release.

> **First time?** Head to [K.G.Studio's Quick Start guide](https://github.com/KGAudioLab/K.G.Studio#quick-start) to set up the AI assistant, or read the full [K.G.Studio User Guide](https://github.com/KGAudioLab/K.G.Studio/blob/main/docs/USER_GUIDE.md) for a complete walkthrough.

---

## For Developers

If you want to call the AI features programmatically, integrate K.G.One into your own tooling, or explore what's under the hood:

- **[API Reference →](./docs/API.md)** — full REST API documentation with request/response examples for all endpoints
- **Interactive Swagger UI** — `http://localhost:8000/docs` (available while the server is running)

---

## Project Structure

```
K.G.One/
├── submodules.json          # Pinned commits — source of truth for dependency versions
├── init.bat                 # Windows bootstrap script
├── pyproject.toml           # K.G.One Python project
├── main.py                  # K.G.One FastAPI server (port 8000); serves K.G.Studio at /kgstudio/
├── services/
│   ├── model_manager.py     # GPU mutex — starts/stops AI model subprocesses
│   ├── acestep_client.py    # ACE-Step connection config
│   ├── foundation1_client.py# Foundation-1 connection config
│   └── separator_runner.py  # Runs audio-separator CLI per-request, manages tasks
├── foundation1_server/
│   └── server.py            # Foundation-1 FastAPI wrapper (port 8002)
├── kgstudio/                # K.G.Studio browser DAW — built as a static SPA, served at /kgstudio/
├── ace-step/                # Cloned by init.bat — ACE-Step 1.5 source
├── foundation1/             # Cloned by init.bat — RC-stable-audio-tools source
├── separator/               # Cloned by init.bat — python-audio-separator source + venv
├── soundfonts/              # Cloned by init.bat — soundfont samples for K.G.Studio
├── docs/
│   └── API.md               # Full REST API reference
├── outputs/
│   ├── clip/                # Foundation-1 generated WAV + MIDI files
│   ├── fullsong/            # (reserved for ACE-Step output references)
│   └── separator/           # Separated stem MP3 files
└── uploads/
    └── separator/           # Temporary upload storage (auto-deleted after processing)
```

---

## Contributing

K.G.One Studio is an experimental, actively evolving project — contributions are very welcome! Whether you're a developer, musician, or designer, your expertise can make a real difference.

### How You Can Help

**🎵 Musicians & Music Producers**
- Test the platform with real-world music production workflows
- Provide feedback on generation quality and integration with K.G.Studio
- Suggest AI models or features that would improve your creative process
- Help improve prompting guides for ACE-Step and Foundation-1

**💻 Developers**
- Implement new features from the roadmap
- Fix bugs and improve performance
- Add support for new AI models or stem separation models
- Improve Linux/macOS compatibility
- Work on K.G.Studio's AI Musician Assistant capabilities

**🎨 UI/UX Designers**
- Improve the K.G.Studio DAW interface and workflows
- Design better visual feedback for generation and separation tasks
- Create more intuitive interactions for AI-assisted music production

### Get Involved

- **Email:** [kgstudio@duck.com](mailto:kgstudio@duck.com)
- **Issues:** Browse open issues labeled `help wanted` or `good first issue`
- **Discussions:** Share ideas and feedback in GitHub Discussions

No contribution is too small — from reporting bugs to suggesting new features, every bit of help moves the project forward!

---

## License

K.G.One Studio is licensed under the [Apache License 2.0](./LICENSE) with two supplemental conditions:

- **No patents** — this software may not be used to file or support any patent application in any jurisdiction.
- **Attribution** — public or commercial deployments must display `Powered by K.G.One © 2026 Xiaohan Tian` in a prominent location visible to end users.

### Third-party component licenses

K.G.One Studio integrates or proxies the following projects. If you use the corresponding features, you are responsible for complying with their licenses.

| Component | Used for | License | Notes |
|-----------|----------|---------|-------|
| [K.G.Studio](https://github.com/KGAudioLab/K.G.Studio) | Browser DAW UI | Apache 2.0 + custom terms | Public/commercial use requires displaying `Powered by K.G.Studio © 2025 Xiaohan Tian`; no patent filing permitted |
| [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | Full-song generation (`/v1/fullsong/*`) | MIT | Permissive — attribution required |
| [stable-audio-open-1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0) | Clip generation (`/v1/clip/*`) via Foundation-1 | Stability AI Community License | **Non-commercial only.** Commercial use requires a separate license from Stability AI — see [stability.ai/license](https://stability.ai/license) |
| [python-audio-separator / UVR5](https://github.com/nomadkaraoke/python-audio-separator) | Stem separation (`/v1/separator/*`) | MIT | Permissive — attribution required |

> **Note:** The `clip` generation feature is powered by a model released under the Stability AI Community License, which **does not permit commercial use**. If you intend to use K.G.One Studio in a commercial product, you must obtain a commercial license from Stability AI before enabling or exposing the `/v1/clip/*` endpoints.

See [LICENSE](./LICENSE) for the full terms including third-party notices.
