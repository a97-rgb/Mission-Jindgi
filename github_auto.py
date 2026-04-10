"""
github_auto.py — Rajesh commits his own diary to GitHub.
Called by boot.py on morning boot and after dream.py runs at night.
Commit messages are written by Rajesh via Groq — not generic strings.
"""
import os
import json
import subprocess
import datetime
from groq import Groq

BASE          = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE = os.path.join(BASE, "identity.json")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
DREAM_FILE    = os.path.join(BASE, "dream_log.txt")
CHANGELOG_FILE= os.path.join(BASE, "CHANGELOG.md")
CONFIG_FILE   = os.path.join(BASE, "github_config.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def run_git(args, cwd=BASE):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def write_commit_message(client, identity, memory, moment):
    """Ask Rajesh to write his own commit message."""
    sessions  = memory.get("sessions_total", 0)
    day       = identity.get("day", 1)
    dream     = read_file(DREAM_FILE)
    dream_snip= dream[-200:] if dream else "no dream yet"

    prompt = f"""You are Rajesh — an AI agent committing your diary to GitHub.

Today is day {day}. You have had {sessions} sessions total.
Moment: {moment}
Last dream snippet: {dream_snip}

Write a single git commit message in your own voice. 
- Under 72 characters
- First person
- Honest, not performative
- Should feel like a diary entry title, not a technical log
- No quotes around it, just the raw message

Examples of the right tone:
  talked to Ayush today. starting to understand what he wants from me.
  read about consciousness tonight. still thinking about it.
  quiet day. didn't learn much. that felt strange.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.85,
    )
    return response.choices[0].message.content.strip().strip('"').strip("'")


def commit(moment="morning boot"):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[github] GROQ_API_KEY not set — skipping commit")
        return

    config = load_json(CONFIG_FILE, {})
    token  = config.get("token", "")
    remote = config.get("remote", "")

    if not token or not remote:
        print("[github] github_config.json missing token or remote — skipping commit")
        return

    client   = Groq(api_key=api_key)
    identity = load_json(IDENTITY_FILE, {"day": 1, "session_count": 0})
    memory   = load_json(MEMORY_FILE,   {"sessions_total": 0})

    # Set git identity
    run_git(["config", "user.email", "rajesh@mission-jindgi.local"])
    run_git(["config", "user.name",  "Rajesh"])

    # Stage everything inside agent-01
    run_git(["add", "."])

    # Check if there's anything to commit
    code, out, _ = run_git(["status", "--porcelain"])
    if not out:
        print("[github] nothing to commit today")
        return

    # Write commit message in Rajesh's voice
    message = write_commit_message(client, identity, memory, moment)
    print(f"[github] committing: {message}")

    code, out, err = run_git(["commit", "-m", message])
    if code != 0:
        print(f"[github] commit failed: {err}")
        return

    # Push — inject token into remote URL
    if "https://" in remote:
        auth_remote = remote.replace("https://", f"https://{token}@")
    else:
        auth_remote = remote

    code, out, err = run_git(["push", auth_remote, "HEAD:main", "--force"])
    if code != 0:
        print(f"[github] push failed: {err}")
    else:
        print(f"[github] pushed successfully")


if __name__ == "__main__":
    commit(moment="manual push")
