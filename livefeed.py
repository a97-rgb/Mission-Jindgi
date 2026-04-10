"""
livefeed.py — Ayush watches what Rajesh is doing in real time.
Run this in a second terminal while boot.py is running.
Watches the feed.json file that boot.py writes to continuously.
"""
import os
import json
import time
import datetime

BASE      = os.path.dirname(os.path.abspath(__file__))
FEED_FILE = os.path.join(BASE, "logs", "feed.json")
LOG_DIR   = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def load_feed():
    if os.path.exists(FEED_FILE):
        try:
            with open(FEED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def render(feed):
    clear()
    print("─" * 56)
    print("  LIVE FEED — Rajesh's Room")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print("─" * 56)

    status = feed.get("status", "unknown")
    status_icons = {
        "booting":    "◉  booting up",
        "surfing":    "◎  reading the internet",
        "chatting":   "●  talking to Ayush",
        "dreaming":   "◌  dreaming",
        "committing": "△  writing to GitHub",
        "idle":       "○  idle",
        "sleeping":   "—  session ended",
    }
    print(f"\n  status   {status_icons.get(status, '?  ' + status)}")

    if feed.get("topic"):
        print(f"  reading  {feed['topic']}")

    if feed.get("last_message"):
        msg = feed["last_message"]
        role = msg.get("role", "?").upper()
        content = msg.get("content", "")
        if len(content) > 60:
            content = content[:60] + "..."
        print(f"\n  last msg [{role}] {content}")

    identity = feed.get("identity", {})
    if identity:
        print(f"\n  personality")
        print(f"    curiosity       {identity.get('curiosity', 0):.2f}")
        print(f"    confidence      {identity.get('confidence', 0):.2f}")
        print(f"    verbosity       {identity.get('verbosity', 0):.2f}")
        print(f"    opinion         {identity.get('opinion_strength', 0):.2f}")
        print(f"    attachment      {identity.get('attachment_to_ayush', 0):.2f}")

    memory = feed.get("memory", {})
    if memory:
        print(f"\n  memory")
        print(f"    sessions        {memory.get('sessions_total', 0)}")
        print(f"    facts on Ayush  {len(memory.get('facts_about_ayush', []))}")
        print(f"    last seen       {memory.get('last_seen', 'never')}")

    if feed.get("dream_snippet"):
        snip = feed["dream_snippet"]
        if len(snip) > 80:
            snip = snip[:80] + "..."
        print(f"\n  last dream  \"{snip}\"")

    print("\n" + "─" * 56)
    print("  watching... (Ctrl+C to stop)")


def main():
    print("Live feed starting. Waiting for Rajesh to boot...")
    try:
        while True:
            feed = load_feed()
            if feed:
                render(feed)
            else:
                print("  [waiting for Rajesh to boot...]", end="\r")
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n\n[live feed stopped]")


if __name__ == "__main__":
    main()
