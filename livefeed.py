"""
livefeed.py — Ayush watches Rajesh in real time.
Run in a second terminal while boot.py is running.
"""
import os
import json
import time
import datetime

BASE         = os.path.dirname(os.path.abspath(__file__))
FEED_FILE    = os.path.join(BASE, "logs",          "feed.json")
AUDIT_FILE   = os.path.join(BASE, "logs",          "github_audit.json")
LEARNED_FILE = os.path.join(BASE,                  "learned_today.md")
LOG_DIR      = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

W = 62  # terminal width


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def read_learned_topics():
    """Parse learned_today.md and return list of topics read today."""
    if not os.path.exists(LEARNED_FILE):
        return []
    today = datetime.date.today().isoformat()
    topics = []
    try:
        with open(LEARNED_FILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"## {today}"):
                    topic = line.replace(f"## {today} —", "").strip()
                    if topic and topic not in topics:
                        topics.append(topic)
    except Exception:
        pass
    return topics


def bar(value, width=16):
    filled = int(round(value * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def trunc(text, n):
    return text[:n] + "..." if len(text) > n else text


def github_summary():
    """Read last audit and return total stars + worst repo."""
    data = load_json_list(AUDIT_FILE)
    if not data:
        return None, None, None
    total_stars = sum(r.get("stars", 0) for r in data)
    worst       = data[0] if data else None
    best        = max(data, key=lambda x: x.get("score", 0)) if data else None
    return total_stars, worst, best


def render(feed, thought_history):
    clear()
    now      = datetime.datetime.now()
    identity = feed.get("identity", {})
    memory   = feed.get("memory", {})
    status   = feed.get("status", "unknown")

    # ── header ─────────────────────────────────────────────────────────────────
    day      = identity.get("day", 1)
    sessions = identity.get("session_count", 0)
    print("═" * W)
    print(f"  RAJESH  ·  day {day}  ·  session {sessions}  ·  {now.strftime('%H:%M:%S')}")
    print("═" * W)

    # ── status ─────────────────────────────────────────────────────────────────
    status_icons = {
        "booting":    "◉  booting up",
        "surfing":    "◎  reading the internet",
        "chatting":   "●  talking to Ayush",
        "dreaming":   "◌  dreaming",
        "committing": "△  writing to GitHub",
        "thinking":   "◈  thinking",
        "idle":       "○  idle",
        "sleeping":   "—  session ended",
    }
    print(f"\n  status     {status_icons.get(status, '?  ' + status)}")

    # ── current tool ───────────────────────────────────────────────────────────
    current_tool = feed.get("current_tool")
    if current_tool:
        print(f"  tool       {current_tool}  running...")

    # ── current topic ──────────────────────────────────────────────────────────
    if feed.get("topic"):
        print(f"  reading    {trunc(feed['topic'], 48)}")

    # ── last 3 thoughts ────────────────────────────────────────────────────────
    print(f"\n  {'─' * (W-4)}")
    print(f"  recent thoughts")
    if thought_history:
        for i, t in enumerate(thought_history[-3:]):
            role    = t.get("role", "?").upper()
            content = trunc(t.get("content", ""), 52)
            prefix  = "  >" if role == "ASSISTANT" else "  you"
            print(f"  {prefix:<6} {content}")
    else:
        print("  —  nothing yet")

    # ── personality ────────────────────────────────────────────────────────────
    print(f"\n  {'─' * (W-4)}")
    print(f"  personality")
    stats = [
        ("curiosity",   identity.get("curiosity", 0)),
        ("confidence",  identity.get("confidence", 0)),
        ("verbosity",   identity.get("verbosity", 0)),
        ("opinion",     identity.get("opinion_strength", 0)),
        ("attachment",  identity.get("attachment_to_ayush", 0)),
    ]
    for name, val in stats:
        print(f"  {name:<12} {bar(val)}  {val:.2f}")

    # ── memory ─────────────────────────────────────────────────────────────────
    print(f"\n  {'─' * (W-4)}")
    print(f"  memory")
    print(f"  sessions       {memory.get('sessions_total', 0)}")
    print(f"  facts on Ayush {len(memory.get('facts_about_ayush', []))}")
    last_seen = memory.get('last_seen', 'never')
    print(f"  last seen      {last_seen}")

    # ── learned today ──────────────────────────────────────────────────────────
    topics = read_learned_topics()
    print(f"\n  {'─' * (W-4)}")
    print(f"  learned today  ({len(topics)} topics)")
    if topics:
        for t in topics[:5]:
            print(f"  ·  {trunc(t, 54)}")
    else:
        print("  —  nothing yet today")

    # ── github stats ───────────────────────────────────────────────────────────
    total_stars, worst, best = github_summary()
    print(f"\n  {'─' * (W-4)}")
    print(f"  github  (Ayush442842q)")
    if total_stars is not None:
        print(f"  total stars    ★ {total_stars}")
        if best:
            print(f"  best repo      {best['name']}  ({best['score']}/100)")
        if worst:
            print(f"  needs work     {worst['name']}  ({worst['score']}/100)")
        last_commit = feed.get("last_commit")
        if last_commit:
            print(f"  last commit    {last_commit}")
    else:
        print("  —  run github_audit to see stats")

    # ── dream ──────────────────────────────────────────────────────────────────
    if feed.get("dream_snippet"):
        snip = trunc(feed["dream_snippet"], W - 18)
        print(f"\n  {'─' * (W-4)}")
        print(f"  last dream")
        print(f"  \"{snip}\"")

    # ── next surf countdown ────────────────────────────────────────────────────
    next_surf = feed.get("next_surf_in")
    if next_surf is not None:
        mins = int(next_surf // 60)
        secs = int(next_surf % 60)
        print(f"\n  next surf in   {mins}m {secs}s")

    # ── footer ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print(f"  watching... Ctrl+C to stop")


def main():
    print("Live feed starting. Waiting for Rajesh to boot...")
    thought_history = []

    try:
        while True:
            feed = load_json(FEED_FILE)
            if feed:
                # maintain rolling thought history (last 3 messages)
                msg = feed.get("last_message")
                if msg and msg.get("content"):
                    if not thought_history or thought_history[-1].get("content") != msg.get("content"):
                        thought_history.append(msg)
                        if len(thought_history) > 3:
                            thought_history.pop(0)

                render(feed, thought_history)
            else:
                print("  [waiting for Rajesh to boot...]", end="\r")
            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\n\n[live feed stopped]")


if __name__ == "__main__":
    main()