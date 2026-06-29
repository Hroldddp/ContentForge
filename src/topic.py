import os
import re
import json
import time
import subprocess
import requests

OLLAMA_MODEL = 'llama3.2:3b'


def kill_ollama():
    subprocess.run(['sudo', 'systemctl', 'stop', 'ollama'],
                   capture_output=True, timeout=10)
    subprocess.run(['sudo', 'pkill', '-f', 'ollama'],
                   capture_output=True, timeout=5)


def _start_ollama():
    result = subprocess.run(['sudo', 'systemctl', 'start', 'ollama'],
                            capture_output=True, timeout=30)
    if result.returncode != 0:
        result = subprocess.run(['ollama', 'serve'],
                                capture_output=True, timeout=5)
    for _ in range(10):
        try:
            r = requests.get('http://localhost:11434/api/tags', timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(1)
    return False


def generate_stock_queries(script_text, max_queries=12):
    print("  AI reading your script to find relevant stock footage...")

    queries = _via_ollama(script_text, max_queries)
    if queries:
        return queries

    # Fallback chain: free API -> brave search -> hardcoded defaults
    # TODO: this if/elif chain is ugly, should refactor into a list of handlers
    freeai_key = os.getenv('FREEAI_API_KEY', '')
    if freeai_key:
        queries = _via_freeai(script_text, freeai_key, max_queries)
        if queries:
            return queries

    brave_key = os.getenv('BRAVE_API_KEY', '')
    if brave_key:
        queries = _via_brave(script_text, brave_key, max_queries)
        if queries:
            return queries

    print("    No AI available. Install Ollama (sudo pacman -S ollama && sudo systemctl start ollama && ollama pull llama3.2:3b)")
    print("    Or set FREEAI_API_KEY or BRAVE_API_KEY in .env")
    return ['technology', 'nature', 'city', 'people', 'business', 'background']


def _ask_ai(prompt, model=OLLAMA_MODEL, max_tokens=400):
    try:
        resp = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'temperature': 0.2,
                'max_tokens': max_tokens,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get('response', '')
    except requests.ConnectionError:
        print("    Starting local AI (Ollama)...")
        if _start_ollama():
            try:
                resp = requests.post(
                    'http://localhost:11434/api/generate',
                    json={
                        'model': model,
                        'prompt': prompt,
                        'stream': False,
                        'temperature': 0.2,
                        'max_tokens': max_tokens,
                    },
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('response', '')
            except Exception:
                pass
        return None
    except Exception:
        return None


def _via_ollama(script_text, max_queries):
    excerpt = script_text[:2000]

    prompt = (
        f"You are a video researcher. Read this script and generate {max_queries} "
        f"search queries for finding STOCK VIDEO FOOTAGE that matches the script topic.\n\n"
        f"RULES:\n"
        f"- Each query MUST be 2-5 words describing a visual scene\n"
        f"- Do NOT use single words\n"
        f"- Do NOT use generic terms like 'stock footage' or 'video background'\n"
        f"- Focus on the MAIN TOPIC and VISUAL ELEMENTS\n"
        f"- Return ONLY a JSON array of strings, no other text\n\n"
        f"Script:\n{excerpt}\n\n"
        f"Return ONLY valid JSON array:"
    )

    response = _ask_ai(prompt)
    if not response:
        return None

    match = re.search(r'\[[\s\S]*?\]', response)
    if not match:
        return None

    try:
        queries = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    # TODO: retry loop here — sometimes the AI generates good queries inside markdown backticks
    if not isinstance(queries, list) or len(queries) < 2:
        return None

    clean = [q.strip().strip('"').strip("'") for q in queries[:max_queries]]
    clean = [q for q in clean if len(q.split()) >= 2 and len(q) > 8]

    if clean:
        print(f"    Local AI read your script and generated {len(clean)} relevant searches:")
        for q in clean[:6]:
            print(f"      \u2022 {q}")
        if len(clean) > 6:
            print(f"      \u2022 ... and {len(clean)-6} more")

    return clean


def _via_freeai(script_text, api_key, max_queries):
    # Free.ai supposedly offers a free tier but I've never actually hit it
    try:
        excerpt = script_text[:1500]
        prompt = (
            f"You are a smart video researcher. Read this entire script, understand its main topic, "
            f"and generate {max_queries} search queries for finding STOCK VIDEO FOOTAGE that matches "
            f"the script's topic and themes.\n\n"
            f"RULES:\n"
            f"- Each query MUST be 2-5 words describing a visual scene related to the script\n"
            f"- Do NOT use single words or generic terms\n"
            f"- Focus on the MAIN TOPIC and KEY VISUAL ELEMENTS only\n"
            f"- Return ONLY a JSON array of strings, no other text\n\n"
            f"Script:\n{excerpt}\n\n"
            f"Return ONLY valid JSON array:"
        )

        resp = requests.post(
            'https://api.free.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 400,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content:
            return None

        match = re.search(r'\[[\s\S]*?\]', content)
        if not match:
            return None

        queries = json.loads(match.group())
        if isinstance(queries, list) and len(queries) > 1:
            clean = [q.strip().strip('"').strip("'") for q in queries[:max_queries]]
            clean = [q for q in clean if len(q.split()) >= 2 and len(q) > 8]
            if clean:
                print(f"    Cloud AI read your script and generated {len(clean)} relevant searches:")
                for q in clean[:6]:
                    print(f"      \u2022 {q}")
                if len(clean) > 6:
                    print(f"      \u2022 ... and {len(clean)-6} more")
                return clean

    except Exception:
        pass

    return None


def _via_brave(script_text, api_key, max_queries):
    try:
        topic = script_text[:200]

        resp = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers={
                'X-Subscription-Token': api_key,
                'Accept': 'application/json',
            },
            params={'q': topic, 'count': 8},
            timeout=15,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get('web', {}).get('results', [])

        combined = topic
        for r in results[:5]:
            combined += ' ' + (r.get('title', '') or '') + ' ' + (r.get('snippet', '') or '')

        excerpt = combined[:2000]

        prompt = (
            f"Read this web search results about a topic and generate {max_queries} "
            f"search queries for finding STOCK VIDEO FOOTAGE that matches.\n\n"
            f"RULES:\n"
            f"- Each query MUST be 2-5 words describing a visual scene\n"
            f"- Do NOT use single words\n"
            f"- Return ONLY a JSON array of strings\n\n"
            f"Content:\n{excerpt}\n\n"
            f"Return ONLY valid JSON array:"
        )

        response = _ask_ai(prompt)
        if not response:
            return None

        match = re.search(r'\[[\s\S]*?\]', response)
        if not match:
            return None

        queries = json.loads(match.group())
        if isinstance(queries, list) and len(queries) > 1:
            clean = [q.strip().strip('"').strip("'") for q in queries[:max_queries]]
            clean = [q for q in clean if len(q.split()) >= 2 and len(q) > 8]
            if clean:
                print(f"    Searched web and generated {len(clean)} relevant searches:")
                for q in clean[:4]:
                    print(f"      \u2022 {q}")
                return clean

    except Exception:
        pass

    return None
