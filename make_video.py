#!/usr/bin/env python3
import argparse
import os
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(
        prog='make_video.py',
        description='ContentForge - Turn text scripts into videos automatically.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('script', help='Path to your script text file (.txt)')
    parser.add_argument('--clips', nargs='?', const='./clips', default=None,
                        help='Folder containing your video clips (defaults to ./clips if flag given without path)')
    parser.add_argument('--voice', default='af_bella',
                        help='TTS voice (default: af_bella). '
                             'Choices: af_bella, af_nicole, af_sarah, af_sky, am_adam, am_michael, am_multi')
    parser.add_argument('--research', action='store_true',
                        help='Research the topic on the web before generating')
    parser.add_argument('--output', '-o', default=None,
                        help='Output video file path (default: output/final_video.mp4)')
    parser.add_argument('--no-stock', action='store_true',
                        help='Skip stock footage download (use your clips only)')
    parser.add_argument('--bg-volume', type=int, default=30, choices=range(0, 101), metavar='0-100',
                        help='Background video audio volume percentage (default: 30)')
    parser.add_argument('--resolution', default='1080x1920', choices=['1080x1920', '1920x1080'],
                        help='Video resolution (default: 1080x1920 for 9:16 vertical). '
                             'Use 1920x1080 for 16:9 horizontal')

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"Error: Script file not found: {args.script}")
        sys.exit(1)

    if args.clips and not os.path.isdir(args.clips):
        print(f"Error: Clips folder not found: {args.clips}")
        sys.exit(1)

    from src.timer import Progress
    from src.utils import (
        check_ffmpeg, ensure_dir, clean_text,
        get_video_files,
    )
    from src.tts import generate_voiceover
    from src.captions import generate_srt
    from src.video_builder import assemble_video
    from src.stock import download_stock_footage, separate_media_files
    from src.topic import generate_stock_queries, kill_ollama
    from src.research import research_topic

    if not check_ffmpeg():
        print("Error: FFmpeg is required but not found.")
        print("Install it with: sudo pacman -S ffmpeg")
        sys.exit(1)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    with open(args.script, 'r', encoding='utf-8') as f:
        script_text = f.read()
    script_text = clean_text(script_text)

    print(f"\n{'='*55}")
    print("  ContentForge Pipeline")
    print(f"{'='*55}")
    print(f"  Script: {args.script}")
    print(f"  Voice:  {args.voice}")
    print(f"  Research: {'On' if args.research else 'Off'}")
    print(f"  Stock footage: {'Off' if args.no_stock else 'On'}")
    print(f"{'='*55}")
    print()

    progress = Progress(5)
    temp_dir = 'temp'
    output_file = None

    progress.step(1, "Researching topic on the web..." if args.research else "Skipping research")
    if args.research:
        script_text = research_topic(script_text)

    progress.step(2, "Generating AI voiceover...")
    try:
        audio_path, sentences_timed = generate_voiceover(script_text, voice=args.voice)
    except ImportError as e:
        print(f"  {e}")
        print("  Run: source venv/bin/activate && pip install edge-tts")
        sys.exit(1)
    except Exception as e:
        print(f"  Voiceover generation failed: {e}")
        sys.exit(1)

        # edge-tts gives us sentence-level timing for SRT sync
        total_duration = sentences_timed[-1][1] if sentences_timed else 0
        if total_duration <= 0:
            print("  Error: Voiceover duration is zero. Check your script content.")
            sys.exit(1)

        progress.step(3, "Gathering video clips...")
        all_clips = []
        image_files = []
        stock_videos = []

        if args.clips:
            user_clips = get_video_files(args.clips)
            all_clips.extend(user_clips)
            print(f"  Found {len(user_clips)} user clip(s) in '{args.clips}'")
            for clip in all_clips:
                print(f"    {os.path.basename(clip)}")

        if not args.no_stock:
            phrases = generate_stock_queries(script_text)
            stock_files = download_stock_footage(
                phrases, resolution=args.resolution,
                target_duration=total_duration,
            )
            sv, si = separate_media_files(stock_files)
            stock_videos.extend(sv)
            image_files.extend(si)
            if sv:
                print(f"  Stock videos ready: {len(sv)}")
            if si:
                print(f"  Stock images ready: {len(si)} (for slideshow fill)")

        # Retry with broader terms if we got nothing
        total_videos = len(all_clips) + len(stock_videos) + (1 if args.clips is None and not stock_videos and image_files else 0)
        if total_videos == 0 and not args.no_stock:
            print("  WARNING: No stock footage found. Retrying with broader search...")
            stock_files = download_stock_footage(
                phrases + ['footage', 'video', 'background', 'nature', 'city', 'technology'],
                resolution=args.resolution,
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
        # rough estimate for progress display
        asm_eta = total_duration * 2.0 if all_clips else total_duration * 0.5
        progress.step(5, "Assembling final video...", estimate=asm_eta)
        output_file = args.output or os.path.join('output', 'final_video.mp4')
        ensure_dir(os.path.dirname(output_file) or '.')

        bg_vol = args.bg_volume / 100.0
        final_path = assemble_video(
            all_clips, audio_path, srt_path, output_file,
            duration=total_duration, bg_volume=bg_vol,
            resolution=args.resolution, image_files=image_files,
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
    # Nuke temp dir contents without touching the dir itself.
    # Must be called in finally so we never leave trash.
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
