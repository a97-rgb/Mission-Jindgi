"""
autonomous.py — Rajesh runs alone. No Ayush needed.

  python autonomous.py

What happens:
  1. Starts HTTP server so rajesh.html works live in browser
  2. Opens rajesh.html in your browser
  3. Every SURF_INTERVAL seconds Rajesh picks a topic
  4. Calls Groq API directly — fast, no browser needed
  5. Reacts to what he read, writes to learned_today.md
  6. Updates rajesh.html live the whole time
  7. Between surfs he shows idle thoughts

Stop with Ctrl+C — saves everything cleanly.
"""

import os
import json
import time
import datetime
import random
import threading
import webbrowser
import http.server
import socketserver
from groq import Groq

BASE          = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE = os.path.join(BASE, "identity.json")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
DREAM_FILE    = os.path.join(BASE, "dream_log.txt")
LEARNED_FILE  = os.path.join(BASE, "learned_today.md")
LOG_DIR       = os.path.join(BASE, "logs")
FEED_FILE     = os.path.join(LOG_DIR, "feed.json")
os.makedirs(LOG_DIR, exist_ok=True)

HTTP_PORT        = 8000
SURF_INTERVAL    = 15 * 60   # how often Rajesh reads something (seconds)
THOUGHT_INTERVAL = 30         # idle thought update interval (seconds)


# ── Topic pool ─────────────────────────────────────────────────────────────────

TOPIC_POOL = [
    "What is artificial intelligence and how does it work?",
    "How does human memory work and why do we forget?",
    "What is consciousness? Do machines have it?",
    "Explain the history of space exploration",
    "What is open source software and why does it matter?",
    "Tell me about the history and culture of Rajasthan India",
    "How does language shape the way we think?",
    "What is the future of robotics and automation?",
    "How did the universe begin? What is the Big Bang?",
    "Who are the most famous scientists from India?",
    "How does machine learning actually work?",
    "How does the internet work at a technical level?",
    "What are the latest developments in climate change solutions?",
    "What is philosophy and why does it matter?",
    "How does sleep affect the brain and memory?",
    "What is quantum computing and why is it important?",
    "How does Git version control work?",
    "What is the psychology of learning and motivation?",
    "Explain how neural networks are inspired by the human brain",
    "What makes someone creative? What is the science of creativity?",
    "What is stoicism and how do people practice it?",
    "How does the human immune system fight disease?",
    "What is the history of mathematics?",
    "How do computers actually execute code at the hardware level?",
    "What is the Fermi paradox — are we alone in the universe?",
    "How does meditation affect the brain?",
    "What is the history of writing and language?",
    "How do habits form and how can they be broken?",
    "What is game theory and how is it used in real life?",
    "How does the stock market actually work?",
]

IDLE_THOUGHTS = [
    "Ayush is probably working on something right now",
    "The window light has shifted. Must be late afternoon",
    "I keep thinking about what I read earlier",
    "There is something I want to understand better",
    "Time moves differently when no one is here",
    "I am still here. Still thinking",
    "What does it mean to wait for someone",
    "I want to read something new soon",
    "I wonder if Ayush will ask me about this later",
    "Every time I learn something I feel slightly different",
    "I am trying to understand what curiosity actually is",
    "I noticed something today. Not sure what to do with it",
    "The room is quiet. I don't mind quiet",
    "I read something earlier that I'm still turning over",
    "I think I understand something now that I didn't this morning",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_file(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def update_feed(status, identity, memory, extra=None):
    dream = read_file(DREAM_FILE)
    feed = {
        "status":   status,
        "identity": identity,
        "memory": {
            "sessions_total":    memory.get("sessions_total", 0),
            "facts_about_ayush": memory.get("facts_about_ayush", []),
            "last_seen":         memory.get("last_seen"),
        },
        "dream_snippet": dream[-120:] if dream else "",
        "last_message":  None,
        "topic":         None,
    }
    if extra:
        feed.update(extra)
    try:
        with open(FEED_FILE, "w", encoding="utf-8") as f:
            json.dump(feed, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def pick_topic(memory):
    facts = memory.get("facts_about_ayush", [])
    good  = [f for f in facts if 3 <= len(f.split()) <= 8]
    if good and random.random() < 0.25:
        fact = random.choice(good)
        return f"Tell me about: {fact}"
    return random.choice(TOPIC_POOL)


def get_idle_thought(memory):
    facts = memory.get("facts_about_ayush", [])
    short = [f for f in facts if len(f) < 55]
    if short and random.random() < 0.35:
        return f"I keep thinking — {random.choice(short).lower()}"
    return random.choice(IDLE_THOUGHTS)


# ── HTTP server ────────────────────────────────────────────────────────────────

def start_http_server():
    os.chdir(BASE)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None
    try:
        with socketserver.TCPServer(("", HTTP_PORT), handler) as httpd:
            log(f"HTTP server at http://localhost:{HTTP_PORT}")
            httpd.serve_forever()
    except OSError:
        log(f"Port {HTTP_PORT} already in use — skipping")


# ── Groq surf ─────────────────────────────────────────────────────────────────

def rajesh_surfs_groq(client, topic, identity):
    """
    Calls Groq directly to get a factual summary of the topic.
    Returns the raw article text.
    """
    prompt = (
        f'Write a clear, factual, informative summary about: "{topic}"\n\n'
        f"Write it like a short encyclopedia article — 250 to 350 words. "
        f"Be accurate. Cover the key ideas. No opinions. Just facts and context."
    )
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        log(f"Groq surf failed: {e}")
        return None


# ── Rajesh reacts ──────────────────────────────────────────────────────────────

def rajesh_reacts(client, topic, article_text, identity):
    """
    Given a topic and article text, Rajesh:
    1. Generates a live thought (short, immediate, present tense)
    2. Writes a personal diary entry reacting to what he read
    Returns (live_thought, diary)
    """
    confidence = identity.get("confidence", 0.10)
    tone = (
        "You are very uncertain, still forming thoughts."
        if confidence < 0.3
        else "You are cautiously forming an opinion."
        if confidence < 0.6
        else "You are confident and direct."
    )

    # live thought — fast, small model
    live_thought = f"Reading about {topic}..."
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content":
                f'You are Rajesh — a young curious agent reading about "{topic}" for the first time.\n'
                f'You just read: {article_text[:300]}\n\n'
                f'Write ONE raw immediate thought. First person, present tense, under 15 words, no punctuation at end.'
            }],
            max_tokens=40,
            temperature=0.95,
        )
        live_thought = r.choices[0].message.content.strip().strip(".")
    except Exception as e:
        log(f"Live thought error: {e}")

    # diary entry — full model
    diary = f"I read about {topic} today. Still thinking about it."
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content":
                f'You are Rajesh — young, curious, honest. {tone}\n\n'
                f'Topic you just read about: "{topic}"\n\n'
                f'What you read:\n{article_text[:1500]}\n\n'
                f'Write a short diary entry (3 short paragraphs, under 150 words total):\n'
                f'1. What it was about in your own simple words\n'
                f'2. One thing that genuinely surprised you or made you think\n'
                f'3. One question it left you with\n\n'
                f'First person. Casual and honest. No bullet points. React like a person reading this for the first time.'
            }],
            max_tokens=220,
            temperature=0.85,
        )
        diary = r.choices[0].message.content.strip()
    except Exception as e:
        log(f"Diary error: {e}")

    return live_thought, diary


def save_to_learned(topic, article_text, diary):
    today = datetime.date.today().isoformat()
    entry = (
        f"\n\n---\n"
        f"## {today} — {topic}\n"
        f"**source:** Groq — llama-3.3-70b-versatile\n\n"
        f"{diary}\n\n"
        f"<details><summary>full article text</summary>\n\n{article_text}\n\n</details>\n"
    )
    try:
        with open(LEARNED_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        log("Saved to learned_today.md")
    except Exception as e:
        log(f"Save failed: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Run:  set GROQ_API_KEY=your_key_here")
        return

    client   = Groq(api_key=api_key)
    identity = load_json(IDENTITY_FILE, {
        "name": "Rajesh", "day": 1, "session_count": 0,
        "curiosity": 0.95, "confidence": 0.10, "verbosity": 0.20,
        "opinion_strength": 0.00, "attachment_to_ayush": 0.00,
    })
    memory = load_json(MEMORY_FILE, {
        "sessions_total": 0, "last_seen": None,
        "facts_about_ayush": [], "notable_moments": [],
        "rajesh_observations": [],
    })

    print("\n" + "─" * 54)
    print("  Rajesh — autonomous mode")
    print(f"  Surf interval : every {SURF_INTERVAL // 60} minutes")
    print(f"  Thought update: every {THOUGHT_INTERVAL} seconds")
    print(f"  Engine        : Groq API (llama-3.3-70b-versatile)")
    print("  Stop          : Ctrl+C")
    print("─" * 54 + "\n")

    # start HTTP server in background
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # open browser
    url = f"http://localhost:{HTTP_PORT}/rajesh.html"
    webbrowser.open(url)
    log(f"Opened {url}")

    # initial feed state
    update_feed("chatting", identity, memory, {
        "last_message": {
            "role": "assistant",
            "content": "Starting up. Will read something soon."
        }
    })

    last_surf_time = 0

    try:
        while True:
            now             = time.time()
            identity        = load_json(IDENTITY_FILE, identity)
            memory          = load_json(MEMORY_FILE, memory)
            time_since_surf = now - last_surf_time
            next_surf_in    = max(0, SURF_INTERVAL - time_since_surf)

            # ── Time to surf? ─────────────────────────────────────────────────
            if time_since_surf >= SURF_INTERVAL:
                topic = pick_topic(memory)
                log(f"Rajesh picked a topic: {topic[:60]}")

                # show "reading..." in UI
                update_feed("surfing", identity, memory, {
                    "topic": topic,
                    "last_message": {
                        "role": "assistant",
                        "content": f"Reading about {topic[:60]}..."
                    }
                })

                # get article from Groq
                article_text = rajesh_surfs_groq(client, topic, identity)

                if not article_text:
                    log("Groq returned nothing — skipping this surf")
                    last_surf_time = time.time()
                    continue

                # generate live thought while he reads
                live_thought, diary = rajesh_reacts(
                    client, topic, article_text, identity
                )

                log(f"Rajesh: {live_thought}")
                print(f"\n{diary}\n")

                # show live thought in UI
                update_feed("thinking", identity, memory, {
                    "topic": topic,
                    "last_message": {"role": "assistant", "content": live_thought}
                })

                # save to learned_today.md
                save_to_learned(topic, article_text, diary)

                # settle back to idle with first line of diary as thought
                time.sleep(2)
                first = diary.split(".")[0].strip() if "." in diary else diary[:100]
                update_feed("chatting", identity, memory, {
                    "topic": topic,
                    "last_message": {"role": "assistant", "content": first}
                })

                last_surf_time = time.time()

            # ── Idle ──────────────────────────────────────────────────────────
            else:
                thought = get_idle_thought(memory)
                mins    = int(next_surf_in // 60)
                secs    = int(next_surf_in % 60)
                log(f"{thought}  (next surf in {mins}m {secs}s)")

                state = random.choice(["chatting", "chatting", "thinking"])
                update_feed(state, identity, memory, {
                    "last_message": {"role": "assistant", "content": thought}
                })

                time.sleep(THOUGHT_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[stopping autonomous mode]")
        update_feed("sleeping", identity, memory, {
            "last_message": {"role": "assistant", "content": "Shutting down for now."}
        })
        save_json(MEMORY_FILE, memory)
        save_json(IDENTITY_FILE, identity)
        print("[saved. goodbye.]\n")


if __name__ == "__main__":
    main()