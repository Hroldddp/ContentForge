# Contributing

Pull requests welcome. This project is built for Arch Linux / CachyOS with Python 3.13+.

## Bugs

Check existing issues first. Open a new one with:
- Your OS and Python version
- The full error output
- The command that triggered it
- What you expected to happen

## Feature ideas

Open an issue describing what you want and why. If you have implementation ideas, include them.

## Pull requests

1. Fork the repo
2. `git checkout -b fix/something` or `git checkout -b feat/something`
3. Make your changes
4. Test them (see below)
5. Push and open a PR

## Testing

```bash
# Quick smoke test (no stock, no GPU)
echo "This is a test. It works." > test_script.txt
python make_video.py test_script.txt --no-stock --bg-volume 0

# Full pipeline (needs internet)
echo "Testing ContentForge. Downloading stock footage." > test_script.txt
python make_video.py test_script.txt --bg-volume 30

# Import validation
python3 -c "
from src.topic import generate_stock_queries, kill_ollama;
from src.research import research_topic;
from src.tts import generate_voiceover;
from src.stock import download_stock_footage, separate_media_files;
from src.captions import generate_srt;
from src.video_builder import assemble_video;
from src.utils import run_ffmpeg_progress, check_ffmpeg, check_ytdlp;
print('All imports OK')
"
```

## Code style

- PEP 8-ish. Don't overthink it.
- No comments in code — use descriptive names
- One thing per function
- Wrap cleanup in try/finally always
