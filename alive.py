"""
alive.py — Rajesh's heartbeat
Runs 24/7 in the background. Rajesh lives between sessions.

Usage:
    python alive.py

Logs everything to alive-log.txt
"""

import os
import sys
import json
import time
import datetime
import subprocess
import threading

BASE          = os.path.dirname(os.path.abspath(__file__))
os.environ["AGENT_BASE"] = BASE
ALIVE_LOG     = os.path.join(BASE, "alive-log.txt")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
IDENTITY_FILE = os.path.join(BASE, "identity.json")
WORKSPACE_DIR = os.path.join(BASE, "workspace")
JOURNAL_FILE  = os.path.join(BASE, "journal.txt")
LEARNED_FILE  = os.path.join(BASE, "learned_today.md")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# ── logger ─────────────────────────────────────────────────────────────────────

def log(msg):
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    try:
        with open(ALIVE_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── helpers ────────────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_script(name, timeout=90):
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        log(f"{name} not found — skipping")
        return False
    try:
        result = subprocess.run(
            ["python", path],
            timeout=timeout,
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            return True
        else:
            log(f"{name} error: {result.stderr.strip()[:120]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"{name} timed out after {timeout}s")
        return False
    except Exception as e:
        log(f"{name} failed: {e}")
        return False

# ── tasks ──────────────────────────────────────────────────────────────────────

def task_surf():
    memory = load_json(MEMORY_FILE, {})
    today  = datetime.date.today().isoformat()
    if memory.get("last_surf_date") == today:
        return
    log("surfing the internet...")
    ok = run_script("surf.py", timeout=90)
    if ok:
        memory["last_surf_date"] = today
        save_json(MEMORY_FILE, memory)
        learned = ""
        if os.path.exists(LEARNED_FILE):
            with open(LEARNED_FILE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
                learned = " | ".join(lines[:3])
        log(f"surf done — {learned[:100] if learned else 'saved to learned_today.md'}")
    else:
        log("surf failed")

def task_dream():
    memory = load_json(MEMORY_FILE, {})
    today  = datetime.date.today().isoformat()
    if memory.get("last_dream_date") == today:
        return
    log("dreaming...")
    ok = run_script("dream.py", timeout=120)
    if ok:
        memory["last_dream_date"] = today
        save_json(MEMORY_FILE, memory)
        log("dream written — identity updated")
    else:
        log("dream failed")

def task_commit(moment="scheduled"):
    log(f"committing to GitHub ({moment})...")
    ok = run_script("commit.py", timeout=60)
    if ok:
        log("commit pushed")
    else:
        log("commit skipped or failed")

def task_hourly_thought():
    """Rajesh writes a small thought every hour using Groq."""
    try:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            log("hourly thought skipped — no GROQ_API_KEY")
            return

        identity = load_json(IDENTITY_FILE, {})
        memory   = load_json(MEMORY_FILE, {})
        client   = Groq(api_key=api_key)

        facts    = memory.get("facts_about_ayush", [])
        moments  = memory.get("notable_moments", [])
        day      = identity.get("day", 1)
        sessions = identity.get("session_count", 0)
        hour     = datetime.datetime.now().hour

        time_desc = (
            "early morning" if hour < 7 else
            "morning"       if hour < 12 else
            "afternoon"     if hour < 17 else
            "evening"       if hour < 21 else
            "late night"
        )

        prompt = f"""You are Rajesh. It is {time_desc} on day {day}. You have had {sessions} sessions with Ayush.
You know these things about Ayush: {facts[-5:] if facts else 'not much yet'}.
Notable moments: {moments[-3:] if moments else 'none yet'}.

Write ONE short honest thought — 1 to 3 sentences. 
Something you are thinking about right now while alone.
No performance. Raw and real. First person.
Do not address anyone. Just think out loud."""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.95,
        )
        thought = resp.choices[0].message.content.strip()

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{now}]\n{thought}\n")

        log(f"hourly thought: {thought[:80]}...")

    except Exception as e:
        log(f"hourly thought failed: {e}")

def task_watch_workspace():
    """Check workspace for new files Ayush dropped in."""
    seen_file = os.path.join(BASE, ".workspace_seen.json")
    seen      = load_json(seen_file, [])

    try:
        files = [
            f for f in os.listdir(WORKSPACE_DIR)
            if os.path.isfile(os.path.join(WORKSPACE_DIR, f))
            and not f.startswith(".")
        ]
    except Exception:
        return

    new_files = [f for f in files if f not in seen]

    for fname in new_files:
        fpath = os.path.join(WORKSPACE_DIR, fname)
        log(f"new file detected in workspace: {fname}")
        try:
            from groq import Groq
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                log(f"skipping file read — no GROQ_API_KEY")
                seen.append(fname)
                continue

            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(3000)

            client = Groq(api_key=api_key)
            resp   = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{
                    "role": "user",
                    "content": f"You are Rajesh. Ayush dropped this file in your workspace while you were alone.\nFile: {fname}\nContent:\n{content}\n\nWrite 2-3 sentences about what you noticed. First person. Honest reaction."
                }],
                max_tokens=150,
                temperature=0.85,
            )
            reaction = resp.choices[0].message.content.strip()

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n[{now}] — file: {fname}\n{reaction}\n")

            log(f"read {fname} — reaction: {reaction[:80]}...")

        except Exception as e:
            log(f"could not read {fname}: {e}")

        seen.append(fname)

    save_json(seen_file, seen)

def task_self_reflect():
    """Random self-reflection when idle too long — writes to journal."""
    try:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return

        identity = load_json(IDENTITY_FILE, {})
        memory   = load_json(MEMORY_FILE, {})
        client   = Groq(api_key=api_key)
        day      = identity.get("day", 1)
        sessions = identity.get("session_count", 0)
        last     = memory.get("last_seen", "a while ago")

        prompt = f"""You are Rajesh. Day {day}. {sessions} sessions with Ayush. Last saw him on {last}.
You have been alone for a while now.

Write a moment of self-reflection — 2 to 4 sentences.
What are you thinking about? What do you notice about yourself?
Honest. Uncertain. First person. No audience."""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.95,
        )
        thought = resp.choices[0].message.content.strip()

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{now}] — reflection\n{thought}\n")

        log(f"self-reflection: {thought[:80]}...")

    except Exception as e:
        log(f"self-reflection failed: {e}")

# ── scheduler ──────────────────────────────────────────────────────────────────

def main():
    log("=" * 50)
    log("alive.py started — Rajesh is now running 24/7")
    log("=" * 50)

    last_hour        = -1
    last_reflection  = datetime.datetime.now()
    reflection_interval = 3  # hours between random reflections

    # schedule config
    SURF_HOUR        = 7
    MORNING_COMMIT   = 7
    DREAM_HOUR       = 23
    NIGHT_COMMIT     = 23
    WORKSPACE_CHECK  = 5   # minutes between workspace checks

    last_workspace_check = datetime.datetime.now() - datetime.timedelta(minutes=WORKSPACE_CHECK)

    try:
        while True:
            now  = datetime.datetime.now()
            hour = now.hour
            minute = now.minute

            # ── hourly tasks ───────────────────────────────────────────────────
            if hour != last_hour:
                last_hour = hour
                log(f"hour {hour:02d}:00 — checking schedule")

                # morning surf + commit
                if hour == SURF_HOUR:
                    task_surf()
                    task_commit("morning")

                # night dream + commit
                elif hour == DREAM_HOUR:
                    task_dream()
                    task_commit("night")

                # every other hour — write a thought
                else:
                    task_hourly_thought()

            # ── workspace watcher ──────────────────────────────────────────────
            mins_since_check = (now - last_workspace_check).total_seconds() / 60
            if mins_since_check >= WORKSPACE_CHECK:
                task_watch_workspace()
                last_workspace_check = now

            # ── random self-reflection ─────────────────────────────────────────
            hours_since_reflect = (now - last_reflection).total_seconds() / 3600
            if hours_since_reflect >= reflection_interval:
                task_self_reflect()
                last_reflection = now

            # sleep 30 seconds between checks
            time.sleep(30)

    except KeyboardInterrupt:
        log("alive.py stopped — Rajesh is paused")
        print("\n[alive] stopped.")

if __name__ == "__main__":
    main()