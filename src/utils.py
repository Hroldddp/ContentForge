import os
import re
import shutil
import subprocess
import threading
import time
import warnings
from pathlib import Path

warnings.filterwarnings('ignore', message='line buffering.*binary mode')


def check_ffmpeg():
    return shutil.which('ffmpeg') is not None


def check_ytdlp():
    return shutil.which('yt-dlp') is not None


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def get_video_files(directory):
    valid_ext = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    files = []
    for f in sorted(os.listdir(directory)):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_ext:
            files.append(os.path.join(directory, f))
    return files


def run_ffmpeg(args):
    cmd = ['ffmpeg', '-y'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error (return code {result.returncode}):\n{result.stderr}")
    return result


def run_ffmpeg_progress(args, total_duration=None, label="Encoding"):
    cmd = ['ffmpeg', '-y'] + args
    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
        universal_newlines=False, bufsize=1
    )

    last_report = -10
    error_lines = []

    def read_stderr(proc, err_lines):
        for line_bytes in iter(proc.stderr.readline, b''):
            err_lines.append(line_bytes)

    reader = threading.Thread(target=read_stderr, args=(process, error_lines), daemon=True)
    reader.start()

    # TODO: parsing time= from ffmpeg output is fragile — fails on edge cases
    # with weird pixel formats or filters that don't produce time lines
    while process.poll() is None:
        time.sleep(0.5)
        raw = b''.join(error_lines[-20:])
        try:
            text = raw.decode('utf-8', errors='replace')
        except Exception:
            text = ''

        m = re.search(r'time=(\d+):(\d+):(\d+)\.(\d+)', text)
        if m and total_duration:
            h, mn, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            cur = h * 3600 + mn * 60 + s + ms / 100
            if cur - last_report >= 3:
                pct = min(99, (cur / total_duration) * 100)
                rem = max(0, total_duration - cur)
                print(f"    {label}: {pct:.0f}% ({rem:.0f}s remaining)")
                last_report = cur

    process.wait()

    all_stderr = b''.join(error_lines).decode('utf-8', errors='replace')
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg {label.lower()} failed (code {process.returncode}):\n{all_stderr[-500:]}")


def get_media_duration(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def get_media_resolution(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height',
         '-of', 'csv=p=0', path],
        capture_output=True, text=True
    )
    parts = result.stdout.strip().split(',')
    if len(parts) == 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            pass
    return None


def has_audio_stream(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
         '-show_entries', 'stream=index', '-of', 'csv=p=0', path],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())
