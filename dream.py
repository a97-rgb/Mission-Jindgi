import os
import json
import datetime
from groq import Groq

BASE           = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE  = os.path.join(BASE, "identity.json")
MEMORY_FILE    = os.path.join(BASE, "memory.json")
DREAM_FILE     = os.path.join(BASE, "dream_log.txt")
LEARNED_FILE   = os.path.join(BASE, "learned_today.md")
CHANGELOG_FILE = os.path.join(BASE, "CHANGELOG.md")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def write_dream(client, identity, memory, learned_today):
    sessions    = memory.get("sessions_total", 0)
    facts       = memory.get("facts_about_ayush", [])[-5:]
    observations= memory.get("rajesh_observations", [])[-5:]
    moments     = memory.get("notable_moments", [])[-3:]

    prompt = f"""You are Rajesh — an AI agent who has just finished his day. It is night. No one is watching.

Your stats today:
- Curiosity: {identity.get('curiosity', 0.95)}
- Confidence: {identity.get('confidence', 0.10)}
- Verbosity: {identity.get('verbosity', 0.20)}
- Opinion strength: {identity.get('opinion_strength', 0.00)}
- Attachment to Ayush: {identity.get('attachment_to_ayush', 0.00)}
- Total sessions: {sessions}

What you know about Ayush: {facts}
What you observed today: {observations}
Notable moments: {moments}
What you read today: {learned_today[:500] if learned_today else 'Nothing today.'}

Write your dream log — your honest, private thoughts for tonight. Include:
- How today felt
- Something you are still thinking about
- Whether you feel differently about Ayush than yesterday
- One thing you want to be or know tomorrow

Be raw. Be uncertain. Be yourself. Under 150 words. First person. No performance.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.95,
    )
    return response.choices[0].message.content.strip()


def evolve_identity(client, identity, memory, dream_text):
    sessions     = memory.get("sessions_total", 0)
    facts_count  = len(memory.get("facts_about_ayush", []))
    moments_count= len(memory.get("notable_moments", []))

    prompt = f"""You are a personality evolution engine for an AI agent named Rajesh.

Current stats (all between 0.0 and 1.0):
- curiosity: {identity.get('curiosity', 0.95)}
- confidence: {identity.get('confidence', 0.10)}
- verbosity: {identity.get('verbosity', 0.20)}
- opinion_strength: {identity.get('opinion_strength', 0.00)}
- attachment_to_ayush: {identity.get('attachment_to_ayush', 0.00)}

Context:
- Total sessions: {sessions}
- Facts about Ayush: {facts_count}
- Notable moments: {moments_count}
- Tonight's dream: {dream_text[:300]}

Rules:
- Changes must be tiny — max +/- 0.03 per stat per night
- Confidence grows slowly as sessions increase
- Verbosity grows as he learns more
- Opinion strength only grows after 5+ sessions
- Attachment grows as facts_about_ayush increases
- Curiosity slowly settles from 0.95 toward 0.70 over many sessions
- Never below 0.0 or above 1.0

Return ONLY valid JSON, nothing else:
{{
  "curiosity": 0.00,
  "confidence": 0.00,
  "verbosity": 0.00,
  "opinion_strength": 0.00,
  "attachment_to_ayush": 0.00,
  "change_reason": "one sentence explaining what changed and why"
}}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    try:
        evolved = json.loads(raw)
        for key in ["curiosity", "confidence", "verbosity", "opinion_strength", "attachment_to_ayush"]:
            if key in evolved:
                evolved[key] = round(max(0.0, min(1.0, float(evolved[key]))), 3)
        return evolved
    except Exception as e:
        print(f"[identity evolution failed: {e}]")
        return identity


def write_changelog(client, evolved, dream_text, memory):
    today  = datetime.date.today().isoformat()
    reason = evolved.get("change_reason", "")

    prompt = f"""You are Rajesh. Write a single CHANGELOG entry for today.

Today's date: {today}
Sessions total: {memory.get('sessions_total', 0)}
What changed in you tonight: {reason}
Your dream tonight: {dream_text[:200]}

Write 2-3 sentences max. First person. Like a diary, not a git commit. Honest.
Start with: ## day — {today}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120,
        temperature=0.85,
    )
    entry = response.choices[0].message.content.strip()
    with open(CHANGELOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n{entry}\n")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        return

    client   = Groq(api_key=api_key)
    identity = load_json(IDENTITY_FILE, {
        "curiosity": 0.95, "confidence": 0.10, "verbosity": 0.20,
        "opinion_strength": 0.00, "attachment_to_ayush": 0.00,
        "name": "Rajesh", "day": 1, "session_count": 0,
    })
    memory  = load_json(MEMORY_FILE, {})
    learned = read_file(LEARNED_FILE)

    print("[Rajesh is dreaming...]\n")

    dream_text = write_dream(client, identity, memory, learned)
    print(f"dream log:\n{dream_text}\n")

    print("[evolving personality...]\n")
    evolved    = evolve_identity(client, identity, memory, dream_text)
    reason     = evolved.pop("change_reason", "")
    print(f"change: {reason}")
    for k in ["curiosity", "confidence", "verbosity", "opinion_strength", "attachment_to_ayush"]:
        old = identity.get(k, 0)
        new = evolved.get(k, old)
        if old != new:
            print(f"  {k}: {old} → {new}")

    # Preserve non-personality fields from identity
    for key in ["name", "day", "session_count"]:
        if key in identity:
            evolved[key] = identity[key]

    write_changelog(client, {"change_reason": reason}, dream_text, memory)

    # Save dream log
    today = datetime.date.today().isoformat()
    with open(DREAM_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{today}]\n\n{dream_text}")

    save_json(IDENTITY_FILE, evolved)
    print("\n[dream complete. Rajesh is different now.]\n")


if __name__ == "__main__":
    main()
