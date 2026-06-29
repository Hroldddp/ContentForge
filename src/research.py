import os
import requests


def research_topic(script_text):
    # Same fallback chain as topic.py, basically copy-pasted. Should've made it a shared module.
    research = _via_ollama(script_text)
    if research:
        return research

    freeai_key = os.getenv('FREEAI_API_KEY', '')
    if freeai_key:
        research = _via_freeai(script_text, freeai_key)
        if research:
            return research

    brave_key = os.getenv('BRAVE_API_KEY', '')
    if brave_key:
        research = _via_brave(script_text, brave_key)
        if research:
            return research

    print("  No API keys found for web research.")
    print("  For local AI research, ensure Ollama is running: sudo systemctl start ollama")
    print("  Continuing with your script as-is.")
    return script_text


def _via_ollama(script_text):
    try:
        topic = script_text[:200]

        prompt = (
            f"Research this topic and provide key facts, statistics, and context. "
            f"Keep it concise (max 200 words).\n\n"
            f"Topic: {topic}\n\n"
            f"Facts:"
        )

        resp = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3.2:3b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0.2,
                'max_tokens': 400,
            },
            timeout=120,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        research = data.get('response', '').strip()

        if research and len(research) > 20:
            enhanced = script_text + "\n\n[Research context from local AI]\n" + research
            print(f"  Local AI research added ({len(research)} chars)")
            return enhanced

    except requests.ConnectionError:
        print("    Starting local AI for research...")
        from .topic import _start_ollama
        if _start_ollama():
            try:
                resp2 = requests.post(
                    'http://localhost:11434/api/generate',
                    json={
                        'model': 'llama3.2:3b',
                        'prompt': prompt,
                        'stream': False,
                        'temperature': 0.2,
                        'max_tokens': 400,
                    },
                    timeout=120,
                )
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    research = data2.get('response', '').strip()
                    if research and len(research) > 20:
                        enhanced = script_text + "\n\n[Research context from local AI]\n" + research
                        print(f"  Local AI research added ({len(research)} chars)")
                        return enhanced
            except Exception:
                pass
    except Exception as e:
        print(f"  Local AI research failed: {e}")

    return None


def _via_freeai(script_text, api_key):
    try:
        topic = script_text[:200]

        resp = requests.post(
            'https://api.free.ai/v1/search/',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={'query': f"Research this topic and provide key facts: {topic}"},
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"  Free.ai API error ({resp.status_code}). Using original script.")
            return None

        data = resp.json()
        research = data.get('answer', data.get('content', ''))

        if research:
            enhanced = script_text + "\n\n[Research context from web]\n" + research
            print(f"  Web research added ({len(research)} chars from Free.ai)")
            return enhanced

    except Exception as e:
        print(f"  Free.ai research failed: {e}")

    return None


def _via_brave(script_text, api_key):
    try:
        topic = script_text[:100]

        resp = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers={
                'X-Subscription-Token': api_key,
                'Accept': 'application/json',
            },
            params={'q': topic, 'count': 5},
            timeout=15,
        )

        if resp.status_code != 200:
            print(f"  Brave Search API error ({resp.status_code}). Using original script.")
            return None

        data = resp.json()
        results = data.get('web', {}).get('results', [])

        if results:
            snippets = []
            for r in results[:3]:
                snippets.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")

            context = "\n".join(snippets)
            enhanced = script_text + "\n\n[Web research]\n" + context
            print(f"  Web research added ({len(context)} chars from Brave Search)")
            return enhanced

    except Exception as e:
        print(f"  Brave Search failed: {e}")

    return None
