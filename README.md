<p align="center">
  <h1 align="center">ContentForge</h1>
  <p align="center"><strong>Turn text scripts into videos automatically</strong></p>
  <p align="center">
    Write a script. Get a finished video with AI voiceover, captions, and real stock footage.
    <br/>No video editing skills needed. <strong>No gradients. No looping.</strong>
  </p>
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/arch-linux-blue?logo=arch-linux&logoColor=white" alt="Arch Linux"></a>
  <a href="https://github.com/Hroldddp/ContentForge/actions/workflows/ci.yml"><img src="https://github.com/Hroldddp/ContentForge/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/Hroldddp/ContentForge/releases"><img src="https://img.shields.io/github/v/release/Hroldddp/ContentForge" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Hroldddp/ContentForge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.13+-blue?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Hroldddp/ContentForge/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome"></a>
  <a href="https://github.com/Hroldddp/ContentForge/issues"><img src="https://img.shields.io/github/issues/Hroldddp/ContentForge" alt="Issues"></a>
  <a href="https://github.com/Hroldddp/ContentForge/stargazers"><img src="https://img.shields.io/github/stars/Hroldddp/ContentForge?style=flat" alt="Stars"></a>
  <img src="https://img.shields.io/badge/status-active-success" alt="Active">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Platform">
</p>

---

## What is this?

You write a plain text script. ContentForge reads it with a local AI, finds matching stock footage on YouTube, generates a natural-sounding voiceover, syncs captions to the speech, and stitches it all into a finished video. Everything runs on your machine — no cloud services, no API keys, no credit card.

### How it works

```
Script.txt → Ollama (local AI) → Stock search (yt-dlp) → TTS (edge-tts) → Assembly (FFmpeg) → final_video.mp4
```

---

## Features

- **Local AI** — Ollama runs on your machine and understands your script. No API keys.
- **Real stock footage** — Downloaded from YouTube. No gradients, no looping.
- **Natural voiceover** — Microsoft's neural TTS via edge-tts. Multiple voices.
- **Auto captions** — Synced per-sentence from the TTS engine.
- **Your clips** add to the video first, then stock fills the rest. Never looped.
- **Web research** — Optional: enriches your script with real facts.
- **Modular code** — Each component in its own file. Easy to hack on.

---

## Requirements

| Thing | Version | Why |
|-------|---------|-----|
| Python | 3.13+ | Runtime |
| FFmpeg | latest | Video/audio processing |
| yt-dlp | latest | YouTube downloads |
| Ollama | 0.30+ | Local AI |
| llama3.2:3b | ~2GB | AI model |
| edge-tts | (pip) | Voiceover |

Tested on Arch Linux / CachyOS. Should work on any distro with these packages.

---

## Installation

```bash
git clone https://github.com/Hroldddp/ContentForge.git
cd ContentForge
bash setup.sh                 # installs everything
source venv/bin/activate      # enter venv for every session
```

### What setup.sh does

1. Installs system packages (FFmpeg, yt-dlp, DejaVu Sans, Ollama)
2. Downloads the AI model (~2GB first time)
3. Sets up passwordless sudo for Ollama (so it can auto-start/stop)
4. Creates a Python virtualenv
5. Installs pip packages
6. Creates clips/, output/, temp/ dirs
7. Copies .env.example to .env

---

## Quick start

```bash
echo "Welcome to ContentForge. This is a test video." > script.txt
python make_video.py script.txt --no-stock --bg-volume 0
```

That generates a video with just voiceover and captions, no stock footage.

For the full experience:

```bash
python wizard.py     # interactive mode
# or
python make_video.py script.txt --voice af_bella --resolution 1920x1080
```

### CLI options

| Flag | Default | What it does |
|------|---------|--------------|
| `--clips [DIR]` | (none) | Folder with your video clips |
| `--voice` | af_bella | TTS voice name |
| `--bg-volume` | 30 | Background audio volume (0-100) |
| `--research` | off | Research topic on the web |
| `--no-stock` | off | Skip stock footage download |
| `--resolution` | 1080x1920 | 1080x1920 (vertical) or 1920x1080 (horizontal) |
| `-o` / `--output` | output/final_video.mp4 | Output file path |

### Voices

| Name | Style |
|------|-------|
| af_bella | Female, warm (US) |
| af_sky | Female, soft (US) |
| af_sarah | Female, calm (UK) |
| af_nicole | Female, energetic (US) |
| am_adam | Male, deep (US) |
| am_michael | Male, natural (US) |
| am_multi | Male, versatile (UK) |

---

## Stock footage pipeline

The AI generates 12 multi-word search queries from your script. These feed into:

YouTube (yt-dlp, no API key) → Pexels (optional key) → Pixabay (optional key) → broader YouTube search → generic fallback (nature, city, tech)

If the first round doesn't find enough clips, it tries again with broader terms. If _that_ fails, it falls back to generic keywords. One of these will always produce results.

---

## Project structure

```
src/
├── tts.py           # Voiceover via edge-tts
├── captions.py      # SRT subtitle generation
├── stock.py         # Stock footage download from multiple sources
├── topic.py         # AI query generation via Ollama
├── research.py      # Web research
├── video_builder.py # FFmpeg pipeline
├── generator.py     # Image slideshow fallback
├── timer.py         # Progress/ETA display
└── utils.py         # Shared FFmpeg helpers
```

The rest: `make_video.py` (CLI), `wizard.py` (interactive), `setup.sh` (installer).

---

## Configuration

Optional API keys go in `.env`:

```
# PEXELS_API_KEY=...    # Better stock footage (200/mo free)
# PIXABAY_API_KEY=...   # Better stock footage (100/day free)
# FREEAI_API_KEY=...    # Cloud AI fallback
# BRAVE_API_KEY=...     # Web search fallback
```

All optional. The program works without any of them.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ffmpeg not found` | `sudo pacman -S ffmpeg` or run setup.sh |
| `yt-dlp not found` | `sudo pacman -S yt-dlp` |
| `ollama not found` | `sudo pacman -S ollama` |
| `model not found` | `ollama pull llama3.2:3b` |
| `edge-tts import error` | `source venv/bin/activate && pip install edge-tts` |
| corrupted output | Use `--preset veryfast` (it's the default) |
| no stock footage | Check internet, verify yt-dlp works |

See [docs/troubleshooting.md](docs/troubleshooting.md) for more.

---

## License

MIT — do what you want with it.
