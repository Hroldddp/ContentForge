import os
from .utils import run_ffmpeg, ensure_dir


def create_slideshow(image_files, output_path, resolution, duration):
    if not image_files:
        raise RuntimeError(
            "No images available for slideshow. "
            "Stock footage download must provide images or videos."
        )

    temp_dir = 'temp'
    ensure_dir(temp_dir)
    width, height = (int(x) for x in resolution.split('x'))

    images = image_files[:15]
    secs_per_image = max(3.0, duration / len(images))

    segment_files = []
    for i, img in enumerate(images):
        segment = os.path.join(temp_dir, f"slide_seg_{i:03d}.mp4")
        run_ffmpeg([
            '-loop', '1', '-i', img,
            '-vf', (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
            ),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
            '-t', str(secs_per_image),
            '-pix_fmt', 'yuv420p',
            '-y', segment,
        ])
        segment_files.append(segment)

    if len(segment_files) == 1:
        run_ffmpeg([
            '-i', segment_files[0],
            '-t', str(duration),
            '-c', 'copy',
            '-y', output_path,
        ])
    else:
        list_path = os.path.join(temp_dir, 'slideshow_list.txt')
        with open(list_path, 'w') as f:
            for seg in segment_files:
                f.write(f"file '{os.path.abspath(seg)}'\n")
        # fallback: re-encode if concat copy fails (codec mismatch between generated segments)
        try:
            run_ffmpeg([
                '-f', 'concat', '-safe', '0', '-i', list_path,
                '-c', 'copy',
                '-y', output_path,
            ])
        except RuntimeError:
            run_ffmpeg([
                '-f', 'concat', '-safe', '0', '-i', list_path,
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                '-pix_fmt', 'yuv420p',
                '-y', output_path,
            ])

    return output_path
