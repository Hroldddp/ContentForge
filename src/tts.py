import os
import asyncio


VOICE_MAP = {
    'af_bella': 'en-US-JennyNeural',
    'af_nicole': 'en-US-AriaNeural',
    'af_sarah': 'en-GB-SoniaNeural',
    'af_sky': 'en-US-JennyNeural',
    'am_adam': 'en-US-GuyNeural',
    'am_michael': 'en-US-BrianNeural',
    'am_multi': 'en-GB-RyanNeural',
}


def generate_voiceover(text, voice='af_bella', output_dir='temp'):
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        raise ImportError(
            "edge-tts is required. Install it with: pip install edge-tts"
        )

    edge_voice = VOICE_MAP.get(voice, voice)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        audio_data, sentence_timings = loop.run_until_complete(
            _generate_text_with_timing(text, edge_voice)
        )
    finally:
        loop.close()

    if not audio_data:
        raise RuntimeError("No audio was generated.")

    captions = []
    for st in sentence_timings:
        start = st['offset'] / 10_000_000
        end = (st['offset'] + st['duration']) / 10_000_000
        captions.append((start, end, st['text']))

    if not captions:
        raise RuntimeError("No sentence boundaries returned from TTS.")

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, 'voiceover.mp3')
    with open(audio_path, 'wb') as f:
        f.write(audio_data)

    total_duration = captions[-1][1]
    print(f"  Voiceover generated: {len(captions)} sentences, {total_duration:.1f}s total")
    print(f"  Saved to: {audio_path}")

    return audio_path, captions


async def _generate_text_with_timing(text, voice):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)

    audio_bytes = bytearray()
    sentence_timings = []

    # edge-tts fires SentenceBoundary events with offset/duration in 100ns units
    # we divide by 10_000_000 to get seconds for SRT timing
    async for chunk in communicate.stream():
        if chunk["type"] == "SentenceBoundary":
            sentence_timings.append({
                'offset': chunk['offset'],
                'duration': chunk['duration'],
                'text': chunk.get('text', ''),
            })
        elif chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])

    return bytes(audio_bytes), sentence_timings
