# GPU Acceleration for Ollama

Ollama can leverage NVIDIA GPUs via CUDA for faster inference. The RTX 2050 (4GB VRAM) works well for the `llama3.2:3b` model used by ContentForge.

## Prerequisites

- NVIDIA GPU with CUDA compute capability 5.0+
- NVIDIA proprietary drivers installed
- Arch Linux (CachyOS) or any system with `pacman`

## Setup

1. Install CUDA:
   ```bash
   sudo pacman -S cuda
   ```

2. Add your user to the `video` group (if not already):
   ```bash
   sudo usermod -aG video $USER
   ```

3. Verify CUDA installation:
   ```bash
   nvidia-smi
   nvcc --version
   ```

4. Install Ollama with CUDA support:
   ```bash
   sudo pacman -S ollama
   sudo systemctl enable --now ollama
   ```

5. Ollama auto-detects CUDA on startup. Check the logs:
   ```bash
   journalctl -u ollama --since "5 minutes ago" | grep -i cuda
   ```
   You should see lines like `CUDA available` or `GPU detected`.

6. Pull the model:
   ```bash
   ollama pull llama3.2:3b
   ```

## Verification

Run a quick test:
```bash
ollama run llama3.2:3b "Hello, are you using my GPU?"
```

Monitor GPU usage in another terminal:
```bash
watch -n 1 nvidia-smi
```

You should see VRAM usage (~2GB) and GPU utilization >0% during inference.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Ollama starts but uses CPU | Ensure `cuda` package is installed, restart `ollama` service |
| `CUDA error: out of memory` | Use a smaller model (`llama3.2:1b`) or close other GPU apps |
| No GPU detected in logs | Check `nvidia-smi` works; reinstall `cuda` and `ollama` |
| Slow first response | First inference loads the model into VRAM; subsequent calls are faster |

## Performance

For `llama3.2:3b` on RTX 2050 (4GB):
- **Prompt evaluation**: ~50 tokens/s
- **Text generation**: ~15 tokens/s
- **Cold start** (first query): ~3s (model load)
- **Subsequent queries**: <1s for short prompts

CPU-only performance is roughly 5-10x slower on the same hardware.

## References

- [Ollama GPU docs](https://github.com/ollama/ollama/blob/main/docs/gpu.md)
- [CUDA installation guide](https://wiki.archlinux.org/title/CUDA)
- [ContentForge AI integration](../src/topic.py)
