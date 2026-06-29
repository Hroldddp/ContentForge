import os
import json
import re
import requests
import subprocess
import shutil
from .utils import run_ffmpeg, ensure_dir


def _get_topic_terms(phrases):
    words = ' '.join(phrases).split()
    meaningful = [w for w in words if len(w) > 3]
    if not meaningful:
        return ['footage', 'video', 'background', 'nature', 'city', 'technology']
    top_category = meaningful[0]
    return [
        f'{top_category} footage',
        f'{top_category} background',
        f'{top_category} video',
        'technology concept',
        'abstract background',
        'free stock video',
        'motion background',
    ]


def download_stock_footage(phrases, output_dir='temp/stock', resolution='1080x1920', target_duration=None):
    orientation = 'portrait' if resolution == '1080x1920' else 'landscape'
    ensure_dir(output_dir)
    all_files = []

    print(f"  Searching stock footage (orientation: {orientation})...")
    # This whole function is a mess of nested fallbacks but it works.
    # Keep adding sources at the top and let it cascade down.

    pexels_key = os.getenv('PEXELS_API_KEY', '')
    pixabay_key = os.getenv('PIXABAY_API_KEY', '')

    for phrase in phrases:
        if len(all_files) >= 30:
            break
        if pexels_key:
            clips = _download_pexels(phrase, pexels_key, output_dir, 2, orientation)
            all_files.extend(clips)
        if len(all_files) < 25 and pixabay_key:
            clips = _download_pixabay(phrase, pixabay_key, output_dir, 2)
            all_files.extend(clips)

    videos, _ = _split_files(all_files)
    target_videos = max(10, int((target_duration or 120) / 16))
    videos_needed = max(3, target_videos - len(videos))

    if videos_needed > 0:
        print(f"  Need ~{videos_needed} video clips (target ~{target_videos}). Searching YouTube...")
        yt_clips = _download_youtube(phrases, output_dir, max_clips=videos_needed + 3)
        all_files.extend(yt_clips)

    videos, _ = _split_files(all_files)
    if len(videos) < target_videos:
        topic_terms = _get_topic_terms(phrases)
        print(f"  Have {len(videos)} videos, need ~{target_videos}. Searching with broader terms...")
        yt_clips = _download_youtube(topic_terms, output_dir, max_clips=16)
        all_files.extend(yt_clips)

    videos, _ = _split_files(all_files)
    if len(videos) < target_videos:
        base_extra = ['video background', 'free stock video', 'motion background',
                       'abstract background', 'drone footage', 'time lapse',
                       'background loop', 'visual effects', 'animated background']
        topic_terms = _get_topic_terms(phrases)
        extra_terms = topic_terms + base_extra
        print(f"  Still {len(videos)} videos. Trying broader search...")
        yt_clips = _download_youtube(extra_terms, output_dir, max_clips=14)
        all_files.extend(yt_clips)

    videos, images = _split_files(all_files)
    print(f"  Stock results: {len(videos)} video(s), {len(images)} image(s)")

    if not videos and not images:
        raise RuntimeError(
            "Could not find any stock footage from any source. "
            "Check internet connection or install yt-dlp (sudo pacman -S yt-dlp)."
        )

    return all_files


def _download_pexels(query, api_key, output_dir, max_per_query, orientation):
    downloaded = []
    try:
        resp = requests.get(
            'https://api.pexels.com/videos/search',
            params={'query': query, 'per_page': max_per_query + 2, 'orientation': orientation},
            headers={'Authorization': api_key},
            timeout=15,
        )
        if resp.status_code != 200:
            return downloaded

        data = resp.json()
        for video_data in data.get('videos', []):
            if len(downloaded) >= max_per_query:
                break
            for vf in video_data.get('video_files', []):
                dl_url = vf.get('link')
                if dl_url and vf.get('width', 0) >= 480:
                    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', query)[:25]
                    fname = f"pex_{safe}_{video_data['id']}_{vf.get('id', '0')}.mp4"
                    fpath = os.path.join(output_dir, fname)
                    try:
                        dl = requests.get(dl_url, timeout=60)
                        if dl.status_code == 200 and len(dl.content) > 10240:
                            with open(fpath, 'wb') as f:
                                f.write(dl.content)
                            downloaded.append(fpath)
                        break
                    except Exception:
                        continue
    except Exception:
        pass
    return downloaded


def _download_pixabay(query, api_key, output_dir, max_per_query):
    downloaded = []
    try:
        resp = requests.get(
            'https://pixabay.com/api/videos/',
            params={'key': api_key, 'q': query, 'per_page': max_per_query + 2, 'safesearch': 'true'},
            timeout=15,
        )
        if resp.status_code != 200:
            return downloaded

        data = resp.json()
        for hit in data.get('hits', []):
            if len(downloaded) >= max_per_query:
                break
            videos = hit.get('videos', {})
            for quality in ['large', 'medium', 'small']:
                vf = videos.get(quality, {})
                dl_url = vf.get('url')
                if dl_url:
                    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', query)[:25]
                    fname = f"pix_{safe}_{hit['id']}_{quality}.mp4"
                    fpath = os.path.join(output_dir, fname)
                    try:
                        dl = requests.get(dl_url, timeout=60)
                        if dl.status_code == 200 and len(dl.content) > 10240:
                            with open(fpath, 'wb') as f:
                                f.write(dl.content)
                            downloaded.append(fpath)
                        break
                    except Exception:
                        continue
    except Exception:
        pass
    return downloaded


def _download_commons(phrases, output_dir, max_clips=10):
    headers = {'User-Agent': 'ContentForge/1.0 (https://github.com/Hroldddp/ContentForge)'}
    downloaded = []
    for keyword in phrases[:3]:
        if len(downloaded) >= max_clips:
            break
        try:
            api = 'https://commons.wikimedia.org/w/api.php'
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': keyword,
                'format': 'json',
                'srlimit': max_clips,
                'srnamespace': '6',
            }
            resp = requests.get(api, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            titles = [r['title'] for r in data.get('query', {}).get('search', [])]
            if not titles:
                continue

            img_params = {
                'action': 'query',
                'titles': '|'.join(titles[:max_clips]),
                'prop': 'imageinfo',
                'iiprop': 'url|mime',
                'format': 'json',
            }
            resp2 = requests.get(api, params=img_params, headers=headers, timeout=15)
            if resp2.status_code != 200:
                continue
            pages = resp2.json().get('query', {}).get('pages', {})
            for page in pages.values():
                if len(downloaded) >= max_clips:
                    break
                if 'imageinfo' not in page:
                    continue
                for info in page['imageinfo']:
                    img_url = info.get('url', '')
                    mime = info.get('mime', '')
                    if not img_url:
                        continue
                    is_video = mime.startswith('video/')
                    ext = '.mp4' if is_video else '.jpg'
                    if not (is_video or mime.startswith('image/')):
                        continue
                    title = page.get('title', '')
                    base = re.sub(r'^[^:]+:', '', title)
                    base = re.sub(r'\.[^.]+$', '', base)
                    safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', f"com_{keyword[:20]}_{base}{ext}")
                    fpath = os.path.join(output_dir, safe)
                    try:
                        dl = requests.get(img_url, headers=headers, timeout=60)
                        if dl.status_code == 200 and len(dl.content) > 1024:
                            with open(fpath, 'wb') as f:
                                f.write(dl.content)
                            downloaded.append(fpath)
                        break
                    except Exception:
                        continue
        except Exception:
            continue
    return downloaded


def _download_youtube(phrases, output_dir, max_clips=6):
    if not shutil.which('yt-dlp'):
        print("    yt-dlp not found. Install: sudo pacman -S yt-dlp")
        return []

    downloaded = []
    seen_urls = set()

    for phrase in phrases:
        if len(downloaded) >= max_clips:
            break
        try:
            result = subprocess.run(
                ['yt-dlp', f'ytsearch{3}:{phrase}',
                 '--dump-json', '--no-download'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                continue

            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    info = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if len(downloaded) >= max_clips:
                    break

                url = info.get('webpage_url', '')
                if not url or url in seen_urls:
                    continue
                dur = info.get('duration', 0)
                if dur < 8 or dur > 900:
                    continue
                seen_urls.add(url)

                vid_id = info.get('id', 'unknown')
                safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', vid_id)
                idx = len(downloaded)
                output_path = os.path.join(output_dir, f"yt_{safe_id}_{idx}.mp4")
                trimmed_path = os.path.join(output_dir, f"yt_{safe_id}_{idx}_trim.mp4")

                try:
                    subprocess.run([
                        'yt-dlp', '-f', '18',
                        '--no-warnings',
                        '-o', output_path,
                        url,
                    ], capture_output=True, text=True, timeout=120, check=True)

                    if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                        try:
                            run_ffmpeg([
                                '-i', output_path,
                                '-t', '25',
                                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                                '-c:a', 'aac',
                                trimmed_path,
                            ])
                            os.remove(output_path)
                            downloaded.append(trimmed_path)
                        except Exception:
                            continue
                        title = info.get('title', 'Unknown')[:60]
                        print(f"      YouTube: {title}")
                except Exception:
                    continue
        except Exception:
            continue

    return downloaded


def _split_files(file_list):
    videos = []
    images = []
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    for f in file_list:
        ext = os.path.splitext(f)[1].lower()
        if ext in video_exts:
            videos.append(f)
        elif ext in image_exts:
            images.append(f)
    return videos, images


def separate_media_files(file_list):
    return _split_files(file_list)
