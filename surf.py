import os
import json
import datetime
import random
import re
import requests
from urllib.parse import quote
from groq import Groq

BASE          = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE = os.path.join(BASE, "identity.json")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
LEARNED_FILE  = os.path.join(BASE, "learned_today.md")
DOWNLOADS_DIR = os.path.join(BASE, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

TOPIC_POOL = [
    "artificial intelligence",
    "how memory works in humans",
    "the history of the internet",
    "what is consciousness",
    "space exploration 2026",
    "how sleep affects the brain",
    "open source software",
    "the history of Rajasthan",
    "how language shapes thought",
    "robotics and automation",
    "climate change latest",
    "what is philosophy",
    "how git version control works",
    "famous scientists India",
    "the future of work",
    "linux operating system",
    "human psychology",
    "how the universe began",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def pick_topic(memory):
    facts    = memory.get("facts_about_ayush", [])
    keywords = []
    for fact in facts:
        words = fact.lower().split()
        for w in words:
            w = re.sub(r'[^\w]', '', w)
            if len(w) > 5:
                keywords.append(w)
    if keywords and random.random() < 0.4:
        return random.choice(keywords)
    return random.choice(TOPIC_POOL)


def extract_text_from_html(html):
    html = re.sub(r'<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_via_wikipedia(topic):
    try:
        search_term = topic.replace(' ', '_')
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(search_term)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")
            if len(extract) > 200:
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", url)
                return page_url, extract
    except Exception as e:
        print(f"[wikipedia fetch failed: {e}]")
    return None, None


def fetch_via_news(topic):
    try:
        search_url = (
            f"https://news.google.com/rss/search"
            f"?q={quote(topic)}&hl=en-IN&gl=IN&ceid=IN:en"
        )
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        urls = re.findall(r'<link>(https?://[^<]+)</link>', r.text)
        article_urls = [u for u in urls if "google.com" not in u]
        for url in article_urls[:3]:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code != 200:
                    continue
                text = extract_text_from_html(resp.text)
                if len(text) > 400:
                    return url, text[:3000]
            except Exception:
                continue
    except Exception as e:
        print(f"[news fetch failed: {e}]")
    return None, None


def fetch_via_groq(client, topic):
    """Last resort — ask Groq to write a factual summary about the topic."""
    try:
        prompt = f"""Write a factual, informative 300-word summary about: "{topic}"

Write it like a short encyclopedia article. Be accurate. No opinions. Just facts.
"""
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        text = r.choices[0].message.content.strip()
        url  = f"[internal knowledge — {topic}]"
        return url, text
    except Exception as e:
        print(f"[groq fallback failed: {e}]")
    return None, None


def fetch_article(client, topic):
    url, text = fetch_via_news(topic)
    if text:
        return url, text
    url, text = fetch_via_wikipedia(topic)
    if text:
        return url, text
    print("[network unavailable — using internal knowledge]")
    return fetch_via_groq(client, topic)


def rajesh_summarizes(client, topic, article_text, identity):
    confidence = identity.get("confidence", 0.10)
    tone = (
        "You are very uncertain, still forming thoughts."
        if confidence < 0.3
        else "You are cautiously forming an opinion."
    )

    prompt = f"""You are Rajesh — a young AI agent reading about the world for the first time. You are intensely curious. {tone}

You just read something about: "{topic}"

Content:
{article_text[:2000]}

Write a short entry for your learned_today.md. Include:
- What it was about (in your own words, simply)
- One thing that surprised you or made you think
- One question it left you with

Write in first person. Be honest. Don't be formal. React like a person encountering an idea for the first time. Under 200 words.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.85,
    )
    return response.choices[0].message.content.strip()


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        return

    client   = Groq(api_key=api_key)
    identity = load_json(IDENTITY_FILE, {"curiosity": 0.95, "confidence": 0.10})
    memory   = load_json(MEMORY_FILE,   {"facts_about_ayush": []})

    topic = pick_topic(memory)
    print(f"[Rajesh is reading about: {topic}]")

    url, article_text = fetch_article(client, topic)
    if not article_text:
        print("[couldn't fetch anything today. skipping.]")
        return

    print(f"[source: {url}]")
    print("[Rajesh is writing his thoughts...]")

    summary = rajesh_summarizes(client, topic, article_text, identity)
    today   = datetime.date.today().isoformat()
    entry   = f"\n\n---\n## {today} — {topic}\n**source:** {url}\n\n{summary}\n"

    with open(LEARNED_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    safe_topic = re.sub(r'[^\w\s-]', '', topic)[:30].replace(' ', '_')
    raw_path   = os.path.join(DOWNLOADS_DIR, f"{today}_{safe_topic}.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"topic: {topic}\nurl: {url}\n\n{article_text}")

    print(f"\n{summary}\n")
    print(f"[saved to learned_today.md]\n")


if __name__ == "__main__":
    main()