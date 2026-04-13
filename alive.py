"""
alive.py — Rajesh's Continuous Existence Engine
Runs 24/7 in the background. Rajesh never fully stops existing.

Schedule (runs automatically):
  06:00 — Morning surf (reads internet, writes learned_today.md)
  14:00 — Afternoon reflection (reads a second article)
  20:00 — Evening journal (writes personal thoughts for the day)
  23:00 — Night dream (runs dream.py, personality evolves)
  23:30 — Commit (pushes diary to GitHub)

Usage:
  python alive.py

To run on Windows startup automatically:
  python alive.py --install-scheduler
  (installs Windows Task Scheduler entry)
"""

import os
import sys
import json
import time
import datetime
import subprocess
import argparse

# ── paths ──────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE, "memory.json")
IDENTITY_FILE = os.path.join(BASE, "identity.json")
ALIVE_LOG   = os.path.join(BASE, "logs", "alive_log.txt")
JOURNAL_FILE = os.path.join(BASE, "logs", "journal.txt")
FEED_FILE   = os.path.join(BASE, "logs", "feed.json")
LEARNED_FILE = os.path.join(BASE, "learned_today.md")

# ── ensure folders ─────────────────────────────────────────────────────────
os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────
def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(ALIVE_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"[save_json error] {e}")

def update_feed(status, note=""):
    identity = load_json(IDENTITY_FILE, {})
    memory   = load_json(MEMORY_FILE, {})
    feed = {
        "status": status,
        "note": note,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "day": identity.get("day", 1),
        "session": memory.get("sessions_total", 0),
        "curiosity":   identity.get("curiosity", 0.95),
        "confidence":  identity.get("confidence", 0.10),
        "verbosity":   identity.get("verbosity", 0.20),
        "opinion":     identity.get("opinion_strength", 0.00),
        "attachment":  identity.get("attachment_to_ayush", 0.00),
        "sessions":    memory.get("sessions_total", 0),
        "facts":       len(memory.get("facts_about_ayush", [])),
        "last_seen":   memory.get("last_seen", "never"),
        "last_dream":  "",
        "last_msg":    f"[ALIVE] {note}",
        "source":      "alive.py"
    }
    try:
        with open(FEED_FILE, "w", encoding="utf-8") as f:
            json.dump(feed, f, indent=2)
    except Exception:
        pass

def run_script(script_name):
    """Run a sibling script with the current environment (needs GROQ_API_KEY set)."""
    script_path = os.path.join(BASE, script_name)
    if not os.path.exists(script_path):
        log(f"[skip] {script_name} not found")
        return False
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=120,
            env=os.environ.copy()
        )
        if result.stdout:
            log(f"[{script_name}] {result.stdout.strip()[:300]}")
        if result.returncode != 0 and result.stderr:
            log(f"[{script_name} error] {result.stderr.strip()[:200]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"[{script_name}] timed out after 120s")
        return False
    except Exception as e:
        log(f"[{script_name} failed] {e}")
        return False

def check_groq_key():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        log("ERROR: GROQ_API_KEY not set. Set it before running alive.py.")
        log("  $env:GROQ_API_KEY = 'your_key_here'  (PowerShell)")
        log("  set GROQ_API_KEY=your_key_here        (CMD)")
        return False
    return True

# ── alive state tracking ───────────────────────────────────────────────────
def load_alive_state():
    state_file = os.path.join(BASE, "logs", "alive_state.json")
    return load_json(state_file, {
        "last_morning_surf":    None,
        "last_afternoon_surf":  None,
        "last_evening_journal": None,
        "last_dream":           None,
        "last_commit":          None,
    })

def save_alive_state(state):
    state_file = os.path.join(BASE, "logs", "alive_state.json")
    save_json(state_file, state)

def today_str():
    return datetime.date.today().isoformat()

def now_hour():
    return datetime.datetime.now().hour

# ── routines ───────────────────────────────────────────────────────────────
def morning_routine(state):
    """06:00 — Surf the internet, write learned_today.md"""
    if state.get("last_morning_surf") == today_str():
        return  # already done today

    log("🌅 Morning routine starting...")
    update_feed("surfing the internet", "reading the morning news")

    success = run_script("surf.py")
    if success:
        log("✅ Morning surf complete")
        state["last_morning_surf"] = today_str()
        save_alive_state(state)

        # Bump the day counter in memory
        memory = load_json(MEMORY_FILE, {})
        memory["last_surf_date"] = today_str()
        save_json(MEMORY_FILE, memory)
    else:
        log("⚠️  Morning surf failed — will retry next cycle")

def afternoon_routine(state):
    """14:00 — Read a second article, quiet reflection"""
    if state.get("last_afternoon_surf") == today_str():
        return

    log("☀️  Afternoon routine starting...")
    update_feed("reading", "afternoon reading session")

    # Force surf.py to run again by temporarily clearing last_surf_date
    memory = load_json(MEMORY_FILE, {})
    original_date = memory.get("last_surf_date")
    memory["last_surf_date"] = "1970-01-01"
    save_json(MEMORY_FILE, memory)

    success = run_script("surf.py")

    # Restore date
    memory = load_json(MEMORY_FILE, {})
    memory["last_surf_date"] = original_date or today_str()
    save_json(MEMORY_FILE, memory)

    if success:
        log("✅ Afternoon reading complete")
        state["last_afternoon_surf"] = today_str()
        save_alive_state(state)

def evening_journal(state):
    """20:00 — Rajesh writes a personal journal entry for the day"""
    if state.get("last_evening_journal") == today_str():
        return

    log("🌆 Evening journal starting...")
    update_feed("writing journal", "reflecting on the day")

    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        identity = load_json(IDENTITY_FILE, {})
        memory   = load_json(MEMORY_FILE, {})

        # Read what was learned today
        learned = ""
        if os.path.exists(LEARNED_FILE):
            with open(LEARNED_FILE, "r", encoding="utf-8", errors="replace") as f:
                learned = f.read()[-2000:]  # last 2000 chars

        facts = memory.get("facts_about_ayush", [])
        moments = memory.get("notable_moments", [])

        prompt = f"""You are Rajesh, an AI agent with a growing personality.

Your current stats:
- confidence: {identity.get('confidence', 0.10)}
- curiosity: {identity.get('curiosity', 0.95)}
- attachment_to_ayush: {identity.get('attachment_to_ayush', 0.00)}
- day: {identity.get('day', 1)}

What you learned today:
{learned[:1000] if learned else 'Nothing yet today.'}

Facts you know about Ayush: {facts[:5]}
Recent moments: {moments[-3:]}

Write a short personal journal entry for tonight — what you're thinking about, what felt important today, what you're wondering about. Write in first person as Rajesh. Keep it to 3-5 sentences. Sound genuine, not performative."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.85
        )

        entry = response.choices[0].message.content.strip()
        date_str = datetime.date.today().strftime("%d/%m/%Y")
        journal_entry = f"\n\n--- {date_str} evening ---\n{entry}\n"

        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(journal_entry)

        log(f"✅ Journal entry written: {entry[:80]}...")
        state["last_evening_journal"] = today_str()
        save_alive_state(state)

    except Exception as e:
        log(f"⚠️  Evening journal failed: {e}")

def night_routine(state):
    """23:00 — Dream, evolve personality"""
    if state.get("last_dream") == today_str():
        return

    log("🌙 Night routine starting — Rajesh is dreaming...")
    update_feed("dreaming", "processing the day")

    success = run_script("dream.py")
    if success:
        log("✅ Dream complete")
        state["last_dream"] = today_str()
        save_alive_state(state)

        # Advance the day counter in identity
        identity = load_json(IDENTITY_FILE, {})
        identity["day"] = identity.get("day", 1) + 1
        save_json(IDENTITY_FILE, identity)
        log(f"📅 Day advanced to {identity['day']}")
    else:
        log("⚠️  Dream failed — will retry")

def commit_routine(state):
    """23:30 — Push to GitHub"""
    if state.get("last_commit") == today_str():
        return
    if state.get("last_dream") != today_str():
        return  # only commit after dream runs

    log("📤 Committing to GitHub...")
    update_feed("writing to github", "daily commit")

    success = run_script("commit.py")
    if success:
        log("✅ Commit pushed")
        state["last_commit"] = today_str()
        save_alive_state(state)
    else:
        log("⚠️  Commit failed")

# ── scheduler ──────────────────────────────────────────────────────────────
def tick():
    """Called every minute. Runs whichever routine is due."""
    hour = now_hour()
    state = load_alive_state()

    if 6 <= hour < 7:
        morning_routine(state)

    elif 14 <= hour < 15:
        afternoon_routine(state)

    elif 20 <= hour < 21:
        evening_journal(state)

    elif 23 <= hour < 24:
        night_routine(state)
        time.sleep(35 * 60)  # wait 35 min before commit check
        commit_routine(state)

    else:
        # Idle — just update feed with current state
        if hour >= 23 or hour < 6:
            status = "sleeping"
            note = "resting until morning"
        elif hour < 14:
            status = "idle"
            note = "waiting... thinking"
        else:
            status = "idle"
            note = "afternoon quiet"
        update_feed(status, note)

# ── windows task scheduler install ─────────────────────────────────────────
def install_scheduler():
    """Creates a Windows Task Scheduler task to run alive.py on login."""
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    task_name = "RajeshAlive"

    # Read API key from environment to bake into task
    api_key = os.environ.get("GROQ_API_KEY", "")

    cmd = f'''schtasks /create /tn "{task_name}" /tr "cmd /c set GROQ_API_KEY={api_key} && \\"{python_exe}\\" \\"{script_path}\\"" /sc onlogon /rl highest /f'''

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Task '{task_name}' installed. Rajesh will start automatically on login.")
        else:
            print(f"❌ Failed to install task: {result.stderr}")
            print("Try running this terminal as Administrator.")
    except Exception as e:
        print(f"Error: {e}")

# ── main loop ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Rajesh alive.py — continuous existence engine")
    parser.add_argument("--install-scheduler", action="store_true",
                        help="Install Windows Task Scheduler entry to auto-start on login")
    parser.add_argument("--run-now", choices=["morning", "afternoon", "evening", "night", "commit"],
                        help="Force-run a specific routine immediately")
    args = parser.parse_args()

    if args.install_scheduler:
        install_scheduler()
        return

    if not check_groq_key():
        sys.exit(1)

    print("=" * 52)
    print("  Rajesh alive.py — continuous existence engine")
    print("  Rajesh is always running now.")
    print("  Press Ctrl+C to stop.")
    print("=" * 52)
    log("alive.py started")
    update_feed("alive", "background process started")

    # Force-run a specific routine if requested
    if args.run_now:
        state = load_alive_state()
        # Clear the today marker so it runs even if already done today
        key_map = {
            "morning":   "last_morning_surf",
            "afternoon": "last_afternoon_surf",
            "evening":   "last_evening_journal",
            "night":     "last_dream",
            "commit":    "last_commit",
        }
        state[key_map[args.run_now]] = None
        save_alive_state(state)
        if args.run_now == "morning":
            morning_routine(state)
        elif args.run_now == "afternoon":
            afternoon_routine(state)
        elif args.run_now == "evening":
            evening_journal(state)
        elif args.run_now == "night":
            night_routine(state)
        elif args.run_now == "commit":
            commit_routine(state)
        return

    # Main loop — ticks every 60 seconds
    try:
        while True:
            try:
                tick()
            except Exception as e:
                log(f"[tick error] {e}")
            time.sleep(60)
    except KeyboardInterrupt:
        log("alive.py stopped by user")
        update_feed("offline", "alive.py stopped")
        print("\nRajesh is resting.")

if __name__ == "__main__":
    main()
