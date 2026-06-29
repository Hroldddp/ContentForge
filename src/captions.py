def generate_srt(captions_data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, (start, end, text) in enumerate(captions_data, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_time(start)} --> {_format_time(end)}\n")
            f.write(f"{text}\n\n")
    return output_path


def _format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
