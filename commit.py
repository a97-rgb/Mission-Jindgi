import os
import json
import subprocess
import datetime
from groq import Groq

BASE         = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE  = os.path.join(BASE, "github_config.json")
IDENTITY_FILE = os.path.join(BASE, "identity.json")
MEMORY_FILE  = os.path.join(BASE, "memory.json")
DREAM_FILE   = os.path.join(BASE, "dream_log.txt")


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def read_file(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def rajesh_writes_commit_message(client, identity, memory, moment):
    """Rajesh writes his own commit message in his own voice."""
    day        = identity.get("day", 1)
    sessions   = identity.get("session_count", 0)
    confidence = identity.get("confidence", 0.10)
    facts      = memory.get("facts_about_ayush", [])
    dream      = read_file(DREAM_FILE)

    tone = (
        "You are very uncertain and quiet."        if confidence < 0.2  else
        "You are cautious but finding your footing." if confidence < 0.4 else
        "You are steady and growing."
    )

    facts_line = f"You know {len(facts)} things about Ayush." if facts else "You are still learning about Ayush."
    dream_line = f"Last night you dreamed: '{dream[-100:]}'" if dream else ""

    prompt = f"""You are Rajesh. You are committing your daily diary to GitHub. {tone}

Today is day {day}. You have had {sessions} sessions with Ayush.
{facts_line}
{dream_line}
Commit moment: {moment}

Write a short git commit message in your own voice — like a diary entry title. 
One line only. No quotes. No punctuation at the end. Under 12 words.
Write as yourself, not as a developer. Example: "day 2 I am starting to understand things a little"
"""
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40,
            temperature=0.9,
        )
        return r.choices[0].message.content.strip().strip('"').strip("'")
    except Exception as e:
        return f"day {day} — {moment}"


def run_git(cmd, cwd):
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def main():
    config = load_json(CONFIG_FILE, {})
    token  = config.get("token", "").strip()
    remote = config.get("remote", "").strip()

    if not token or not remote:
        print("[github] github_config.json missing token or remote — skipping commit")
        return

    api_key = os.environ.get("GROQ_API_KEY", "")
    identity = load_json(IDENTITY_FILE, {"day": 1, "session_count": 0, "confidence": 0.10})
    memory   = load_json(MEMORY_FILE, {"facts_about_ayush": []})
    moment   = os.environ.get("COMMIT_MOMENT", "daily update")

    # Build authenticated remote URL
    # remote should be like: https://github.com/user/repo.git
    if remote.startswith("https://"):
        auth_remote = remote.replace("https://", f"https://{token}@")
    else:
        auth_remote = remote

    # Set remote
    run_git(["git", "remote", "remove", "origin"], BASE)
    run_git(["git", "remote", "add", "origin", auth_remote], BASE)

    # Stage all changes
    code, out, err = run_git(["git", "add", "-A"], BASE)
    if code != 0:
        print(f"[github] git add failed: {err}")
        return

    # Check if there's anything to commit
    code, out, err = run_git(["git", "status", "--porcelain"], BASE)
    if not out.strip():
        print("[github] nothing to commit — skipping")
        return

    # Write commit message in Rajesh's voice
    if api_key:
        client = Groq(api_key=api_key)
        msg = rajesh_writes_commit_message(client, identity, memory, moment)
    else:
        msg = f"day {identity.get('day', 1)} — {moment}"

    print(f"[github] committing: \"{msg}\"")

    # Set git identity if not set
    run_git(["git", "config", "user.email", "rajesh@agent-01"], BASE)
    run_git(["git", "config", "user.name", "Rajesh"], BASE)

    # Commit
    code, out, err = run_git(["git", "commit", "-m", msg], BASE)
    if code != 0:
        print(f"[github] commit failed: {err}")
        return

    # Push
    code, out, err = run_git(["git", "push", "origin", "main"], BASE)
    if code != 0:
        # try master branch
        code, out, err = run_git(["git", "push", "origin", "master"], BASE)
    if code != 0:
        print(f"[github] push failed: {err}")
        return

    print(f"[github] pushed successfully")


if __name__ == "__main__":
    main()
