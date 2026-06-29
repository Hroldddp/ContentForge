#!/usr/bin/env python3
import os
import shutil
import sys

from src.timer import Progress
from src.utils import check_ffmpeg, ensure_dir, clean_text, get_video_files
from src.tts import generate_voiceover
from src.captions import generate_srt
from src.video_builder import assemble_video
from src.stock import download_stock_footage, separate_media_files
from src.topic import generate_stock_queries, kill_ollama
from src.research import research_topic

VOICE_OPTIONS = [
    ('af_bella', 'Female, warm (US)'),
    ('af_sky', 'Female, soft (US)'),
    ('af_sarah', 'Female, calm (UK)'),
    ('af_nicole', 'Female, energetic (US)'),
    ('am_adam', 'Male, deep (US)'),
    ('am_michael', 'Male, natural (US)'),
    ('am_multi', 'Male, versatile (UK)'),
]


def ask(question, default=None):
    if default is not None:
        result = input(f"  {question} [{default}]: ").strip()
        return result if result else default
    return input(f"  {question}: ").strip()


def ask_yes_no(question, default=False):
    suffix = " (Y/n)" if default else " (y/N)"
    result = input(f"  {question}{suffix}: ").strip().lower()
    if not result:
        return default
    return result == 'y'


def ask_choice(question, options):
    print(f"  {question}")
    for i, (name, desc) in enumerate(options, 1):
        print(f"    [{i}] {name:12s} - {desc}")
    while True:
        try:
            choice = input(f"  Choose (1-{len(options)}): ").strip()
            if not choice:
                return options[0][0]
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(options)}")


def ask_int(question, default, lo, hi):
    while True:
        try:
            result = input(f"  {question} ({lo}-{hi}, default {default}): ").strip()
            if not result:
                return default
            val = int(result)
            if lo <= val <= hi:
                return val
        except ValueError:
            pass
        print(f"  Please enter a number between {lo} and {hi}")


def main():
    print()
    print("=" * 55)
    print("  ContentForge Wizard")
    print("  Answer the prompts to create your video.")
    print("=" * 55)
    print()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if not check_ffmpeg():
        print("Error: FFmpeg is required but not found.")
        print("Install it with: sudo pacman -S ffmpeg")
        sys.exit(1)

    script_path = ask("Script file", "script.txt")
    if not os.path.exists(script_path):
        print(f"  Error: File not found: {script_path}")
        sys.exit(1)

    use_clips = ask_yes_no("Use video clips")
    clips_dir = None
    if use_clips:
        clips_dir = "./clips"
        if not os.path.isdir(clips_dir):
            print(f"  Error: Folder not found: {clips_dir}")
            sys.exit(1)

    bg_volume_pct = ask_int("Background audio volume", 30, 0, 100)
    bg_volume = bg_volume_pct / 100.0

    voice = ask_choice("Voice", VOICE_OPTIONS)

    resolution_options = [
        ('1080x1920', '9:16 vertical (portrait, for TikTok/Shorts/Reels)'),
        ('1920x1080', '16:9 horizontal (landscape, for YouTube)'),
    ]
    resolution = ask_choice("Video resolution", resolution_options)

    use_research = ask_yes_no("Enable web research")

    use_stock = ask_yes_no("Download stock footage")

    output = ask("Output file", "output/final_video.mp4")

    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()
    script_text = clean_text(script_text)

    print()
    print(f"{'='*55}")
    print("  ContentForge Pipeline")
    print(f"{'='*55}")
    print(f"  Script:         {script_path}")
    print(f"  Voice:          {voice}")
    print(f"  Resolution:     {resolution}")
    print(f"  Clips:          {clips_dir or 'None (stock footage only)'}")
    print(f"  BG volume:      {bg_volume_pct}%")
    print(f"  Research:       {'On' if use_research else 'Off'}")
    print(f"  Stock footage:  {'On' if use_stock else 'Off'}")
    print(f"  Output:         {output}")
    print(f"{'='*55}")

    progress = Progress(5)
    temp_dir = 'temp'
    final_path = None

    try:
        progress.step(1, "Researching topic on the web..." if use_research else "Skipping research")
        if use_research:
            script_text = research_topic(script_text)

        progress.step(2, "Generating AI voiceover...")
        try:
            audio_path, sentences_timed = generate_voiceover(script_text, voice=voice)
        except Exception as e:
            print(f"  Voiceover generation failed: {e}")
            sys.exit(1)

        total_duration = sentences_timed[-1][1] if sentences_timed else 0
        if total_duration <= 0:
            print("  Error: Voiceover duration is zero. Check your script content.")
            sys.exit(1)

        progress.step(3, "Gathering video clips...")
        all_clips = []
        image_files = []
        stock_videos = []

        if clips_dir:
            user_clips = get_video_files(clips_dir)
            all_clips.extend(user_clips)
            print(f"  Found {len(user_clips)} user clip(s) in '{clips_dir}'")

        if use_stock:
            phrases = generate_stock_queries(script_text)
            stock_files = download_stock_footage(
                phrases, resolution=resolution,
                target_duration=total_duration,
            )
            sv, si = separate_media_files(stock_files)
            stock_videos.extend(sv)
            image_files.extend(si)
            if sv:
                print(f"  Stock videos ready: {len(sv)}")
            if si:
                print(f"  Stock images ready: {len(si)}")

        total_videos = len(all_clips) + len(stock_videos)
        # try broader terms if the AI queries returned nothing useful
        if total_videos == 0 and use_stock:
            print("  Retrying with broader search...")
            stock_files = download_stock_footage(
                phrases + ['footage', 'video', 'background', 'nature', 'city', 'technology'],
                resolution=resolution,
                target_duration=total_duration,
            )
            sv, si = separate_media_files(stock_files)
            stock_videos.extend(sv)
            image_files.extend(si)

        progress.step(4, "Generating captions...")
        ensure_dir(temp_dir)
        srt_path = os.path.join(temp_dir, 'captions.srt')
        generate_srt(sentences_timed, srt_path)
        print(f"  SRT file created: {srt_path}")

        progress.step(5, "Assembling final video...")
        asm_eta = total_duration * 2.0 if all_clips else total_duration * 0.5
        progress.step(5, "Assembling final video...", estimate=asm_eta)
        ensure_dir(os.path.dirname(output) or '.')
        final_path = assemble_video(
            all_clips, audio_path, srt_path, output,
            duration=total_duration, bg_volume=bg_volume,
            resolution=resolution, image_files=image_files,
            stock_videos=stock_videos,
        )

        progress.done()
        print(f"\n  Video: {final_path}  ({total_duration:.1f}s / {total_duration/60:.1f}m)")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    finally:
        _clean_temp(temp_dir)
        kill_ollama()


def _clean_temp(temp_dir):
    if os.path.isdir(temp_dir):
        for entry in os.listdir(temp_dir):
            path = os.path.join(temp_dir, entry)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception:
                pass
        print("\n  Cleaned up temporary build files")


if __name__ == '__main__':
    main()
