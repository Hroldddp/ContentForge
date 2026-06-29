import os
from .utils import (
    run_ffmpeg, run_ffmpeg_progress, get_media_duration, has_audio_stream,
    ensure_dir,
)
from .generator import create_slideshow


def assemble_video(clip_files, audio_path, srt_path, output_path,
                   duration=None, bg_volume=0.3, resolution='1080x1920',
                   image_files=None, stock_videos=None):
    temp_dir = 'temp'
    ensure_dir(temp_dir)

    width, height = (int(x) for x in resolution.split('x'))
    has_user_clips = bool(clip_files)

    timeline = _build_timeline(clip_files, stock_videos, image_files,
                                duration, resolution, temp_dir)

    video_source = timeline.get('video_path')
    has_bg_audio = timeline.get('has_audio', False)

    if not video_source or not os.path.exists(video_source):
        raise RuntimeError("No video source could be built for the final video.")

    bg_pct = int(bg_volume * 100)
    print(f"  Adding voiceover (and background audio at {bg_pct}% volume if available)...")

    fs = max(14, int(min(width, height) / 50))
    margin_h = int(width * 0.06)
    margin_v = int(height * 0.04)

    # DejaVu Sans is guaranteed on Arch from the ttf-dejavu package
    # setup.sh installs it, but if you skip setup you'll get "[generic] sans-serif"
    subtitle_filter = (
        f"subtitles={srt_path}:"
        f"force_style="
        f"'FontName=DejaVu Sans,FontSize={fs},PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
        f"MarginV={margin_v},MarginL={margin_h},MarginR={margin_h},"
        f"Alignment=2,WrapStyle=1'"
    )

    duration_opt = ['-t', str(duration)] if duration else ['-shortest']

    if has_user_clips and has_bg_audio:
        filter_complex = (
            f"[0:a:0]volume={bg_volume}[bg];"
            f"[1:a:0]volume=1.0[vo];"
            f"[bg][vo]amix=inputs=2:duration=first[outa]"
        )
        ffmpeg_args = [
            '-i', video_source,
            '-i', audio_path,
            '-filter_complex', filter_complex,
            '-vf', subtitle_filter,
            '-map', '0:v:0',
            '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            *duration_opt,
            output_path,
        ]
    else:
        ffmpeg_args = [
            '-i', video_source,
            '-i', audio_path,
            '-vf', subtitle_filter,
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            *duration_opt,
            output_path,
        ]

    run_ffmpeg_progress(ffmpeg_args, total_duration=duration, label="Assembly")

    if not os.path.exists(output_path):
        raise RuntimeError(f"Output file was not created: {output_path}")

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    vid_dur = get_media_duration(output_path)
    print(f"  Final video: {vid_dur:.1f}s, {file_size:.1f}MB")
    print(f"  Saved to: {output_path}")

    return output_path


def _build_timeline(clip_files, stock_videos, image_files, duration, resolution, temp_dir):
    width, height = (int(x) for x in resolution.split('x'))
    segments = []

    if clip_files:
        print(f"  Building timeline: {len(clip_files)} user clip(s) + stock footage")
        for clip in clip_files:
            segments.append({'path': clip, 'type': 'user'})
    elif stock_videos:
        print(f"  Building timeline: {len(stock_videos)} stock video(s)")
        for sv in stock_videos:
            segments.append({'path': sv, 'type': 'stock'})
    elif image_files and len(image_files) >= 1:
        print(f"  Building timeline: slideshow from {len(image_files)} image(s)")
        slideshow_path = os.path.join(temp_dir, 'slideshow_video.mp4')
        create_slideshow(image_files, slideshow_path, resolution, duration)
        return {'video_path': slideshow_path, 'has_audio': False}

    if not segments:
        raise RuntimeError(
            "No video sources available. "
            "Stock footage download should have provided videos or images."
        )

    if duration is None:
        concat_path = _concat_segments(segments, resolution, temp_dir)
        has_audio = any(
            has_audio_stream(s['path']) for s in segments if s['type'] == 'user'
        )
        return {'video_path': concat_path, 'has_audio': has_audio}

    user_duration = 0.0
    for seg in segments:
        if seg['type'] == 'user':
            user_duration += get_media_duration(seg['path'])

    if clip_files and user_duration >= duration - 0.5:
        timing_segments = _adjust_to_duration(segments, duration, resolution, temp_dir)
        concat_path = _concat_segments(timing_segments, resolution, temp_dir)
        has_audio = any(
            has_audio_stream(s['path']) for s in timing_segments if s['type'] == 'user'
        )
        return {'video_path': concat_path, 'has_audio': has_audio}

    if clip_files and user_duration < duration - 0.5:
        remaining = duration - user_duration
        print(f"  User clips: {user_duration:.1f}s, need {remaining:.1f}s of stock footage")

        if stock_videos:
            remaining = _add_stock_segments(stock_videos, remaining, segments, resolution, temp_dir)

        if remaining > 1.0:
            if image_files and len(image_files) >= 1:
                print(f"  Filling remaining {remaining:.1f}s with image slideshow...")
                fill_path = os.path.join(temp_dir, 'fill_slideshow.mp4')
                create_slideshow(image_files, fill_path, resolution, remaining)
                segments.append({'path': fill_path, 'type': 'fill'})
                remaining = 0

        if remaining > 1.0:
            print(f"  WARNING: Still {remaining:.1f}s short of target. Final -t will handle this.")

        concat_path = _concat_segments(segments, resolution, temp_dir)
        has_audio = any(
            has_audio_stream(s['path']) for s in segments if s['type'] == 'user'
        )
        return {'video_path': concat_path, 'has_audio': has_audio}

    if not clip_files and stock_videos:
        remaining = duration
        all_segments = []
        remaining = _add_stock_segments(stock_videos, remaining, all_segments, resolution, temp_dir)

        if remaining > 1.0 and image_files and len(image_files) >= 1:
            fill_path = os.path.join(temp_dir, 'fill_slideshow.mp4')
            create_slideshow(image_files, fill_path, resolution, remaining)
            all_segments.append({'path': fill_path, 'type': 'fill'})
            remaining = 0

        if remaining > 1.0:
            print(f"  WARNING: Still {remaining:.1f}s short. Stock download was insufficient.")

        if not all_segments:
            raise RuntimeError("No video segments could be built.")
        concat_path = _concat_segments(all_segments, resolution, temp_dir)
        return {'video_path': concat_path, 'has_audio': False}

    raise RuntimeError("Could not build video timeline (no valid segments).")


def _adjust_to_duration(segments, target_dur, resolution, temp_dir):
    total = sum(get_media_duration(s['path']) for s in segments)
    if abs(total - target_dur) < 0.5:
        return segments

    result = []
    accumulated = 0.0
    for s in segments:
        dur = get_media_duration(s['path'])
        if accumulated + dur <= target_dur + 0.5:
            result.append(s)
            accumulated += dur
        else:
            needed = target_dur - accumulated
            if needed > 0.5:
                trim_path = os.path.join(temp_dir, f"trim_{len(result):03d}.mp4")
                run_ffmpeg([
                    '-i', s['path'],
                    '-t', str(needed),
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                    '-c:a', 'aac',
                    trim_path,
                ])
                result.append({'path': trim_path, 'type': 'trimmed'})
                accumulated += needed
            break
    return result


def _add_stock_segments(stock_videos, remaining, segments, resolution, temp_dir):
    stock_videos = sorted(stock_videos, key=get_media_duration)
    for sv in stock_videos:
        if remaining <= 0.5:
            break
        dur = get_media_duration(sv)
        if dur <= remaining + 0.5:
            segments.append({'path': sv, 'type': 'stock'})
            remaining -= dur
        else:
            trim_path = os.path.join(temp_dir, f"stock_trim_{len(segments):03d}.mp4")
            run_ffmpeg([
                '-i', sv,
                '-t', str(remaining),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                '-c:a', 'aac',
                trim_path,
            ])
            segments.append({'path': trim_path, 'type': 'stock'})
            remaining = 0
    return remaining


def _concat_segments(segments, resolution, temp_dir):
    if not segments:
        raise RuntimeError("No segments to concatenate")
    if len(segments) == 1:
        return segments[0]['path']

    width, height = (int(x) for x in resolution.split('x'))
    concat_path = os.path.join(temp_dir, 'timeline.mp4')

    # Scale + centre-crop every segment to target res so they all match
    scaled_segments = []
    for i, seg in enumerate(segments):
        scaled = os.path.join(temp_dir, f"scaled_{i:03d}.mp4")
        run_ffmpeg([
            '-i', seg['path'],
            '-vf', (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1"
            ),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
            '-c:a', 'aac', '-b:a', '128k',
            '-ar', '44100', '-ac', '2',
            '-pix_fmt', 'yuv420p',
            '-y', scaled,
        ])
        scaled_segments.append(scaled)

    if len(scaled_segments) == 1:
        run_ffmpeg(['-i', scaled_segments[0], '-c', 'copy', '-y', concat_path])
        return concat_path

    list_path = os.path.join(temp_dir, 'timeline_list.txt')
    with open(list_path, 'w') as f:
        for seg in scaled_segments:
            f.write(f"file '{os.path.abspath(seg)}'\n")

    # Concat with re-encode to avoid codec mismatch crashes
    run_ffmpeg([
        '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
        '-c:a', 'aac',
        '-y', concat_path,
    ])

    return concat_path
