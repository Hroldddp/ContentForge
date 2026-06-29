# Troubleshooting

## Python / system

**"python3 not found"**
  sudo pacman -S python
  bash setup.sh

**"FFmpeg not found"**
  sudo pacman -S ffmpeg
  # or just re-run: bash setup.sh

**"yt-dlp not found"**
  sudo pacman -S yt-dlp

**"edge-tts: No module named edge-tts"**
  source venv/bin/activate
  pip install edge-tts

## Ollama

**"Ollama not found"**
  sudo pacman -S ollama
  bash setup.sh

**"Could not connect to Ollama server"**
  sudo systemctl start ollama
  curl http://localhost:11434/api/tags   # should respond

**"Model 'llama3.2:3b' not found"**
  ollama pull llama3.2:3b   # ~2GB download

**"Ollama connection refused" in program output**
  The auto-start failed. Check:
  sudo cat /etc/sudoers.d/ollama
  # Should have your username with NOPASSWD for systemctl start/stop ollama
  # If missing: bash setup.sh

**AI generates poor search queries**
  Make sure Ollama is running with llama3.2:3b
  Short scripts (< 200 chars) get less context — write more
  Check logs: journalctl -u ollama --no-pager -n 50

## Stock footage

**"No stock footage found"**
  Shouldn't happen (YouTube always works). Check:
  1. Internet connection
  2. yt-dlp --version
  3. yt-dlp "ytsearch3:test" --dump-json
  4. Script might be too niche — try something generic

**YouTube downloads slow**
  Format 18 (360p) for speed. Longer scripts = more clips = more time.
  Use --no-stock for quick tests.

**Pexels API key not working**
  Check usage limit (200/mo) or remove the key from .env to fall back to YouTube.

## Video output

**Corrupted output file**
  Always use -preset veryfast (default). Re-run if interrupted.

**No audio in video**
  Check --bg-volume isn't 0 (set to e.g. 30)
  Check TTS completed: look for "Voiceover generated" in output
  Test: python make_video.py script.txt --no-stock --bg-volume 50

**Black screen instead of video**
  Stock download may have failed silently. Test without stock:
  python make_video.py script.txt --no-stock --bg-volume 0

**Captions don't fit**
  DejaVu Sans is auto-sized. Very long lines wrap. Split long sentences.

**"Font not found" in FFmpeg output**
  sudo pacman -S ttf-dejavu

## Getting help

Search existing issues: https://github.com/Hroldddp/ContentForge/issues
Or start a discussion: https://github.com/Hroldddp/ContentForge/discussions
Include: OS, Python version, command used, full error output.
