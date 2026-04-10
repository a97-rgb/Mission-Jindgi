"""
manager.py — Ayush's control panel.
Run from H:\Future\ to see all agents, stats, and issue commands.
"""
import os
import json
import datetime
import subprocess

FUTURE_BASE = os.path.dirname(os.path.abspath(__file__))
ROSTER_FILE = os.path.join(FUTURE_BASE, "roster.json")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def bar(value, width=20):
    filled = int(round(value * width))
    return "█" * filled + "░" * (width - filled)


# ── Load all agents from roster ────────────────────────────────────────────────

def load_agents():
    roster  = load_json(ROSTER_FILE, {"agents": []})
    agents  = []
    for entry in roster.get("agents", []):
        agent_dir = entry.get("path", "")
        if not os.path.isdir(agent_dir):
            continue
        identity = load_json(os.path.join(agent_dir, "identity.json"), {})
        memory   = load_json(os.path.join(agent_dir, "memory.json"),   {})
        feed_path= os.path.join(agent_dir, "logs", "feed.json")
        feed     = load_json(feed_path, {})
        agents.append({
            "path":     agent_dir,
            "identity": identity,
            "memory":   memory,
            "feed":     feed,
            "name":     identity.get("name", entry.get("name", "unknown")),
        })
    return agents


# ── Dashboard ──────────────────────────────────────────────────────────────────

def dashboard(agents):
    clear()
    print("═" * 60)
    print("  MISSION JINDGI — Manager Panel")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print("═" * 60)

    if not agents:
        print("\n  No agents found. Check roster.json.\n")
        return

    for i, agent in enumerate(agents):
        identity = agent["identity"]
        memory   = agent["memory"]
        feed     = agent["feed"]

        name      = agent["name"]
        day       = identity.get("day", 1)
        sessions  = identity.get("session_count", 0)
        last_seen = memory.get("last_seen", "never")
        status    = feed.get("status", "offline")

        print(f"\n  [{i+1}] {name.upper()}  —  day {day}  |  {sessions} sessions  |  last seen: {last_seen}")
        print(f"       status: {status}")

        # Personality bars
        stats = ["curiosity", "confidence", "verbosity", "opinion_strength", "attachment_to_ayush"]
        labels= ["curiosity  ", "confidence ", "verbosity  ", "opinion    ", "attachment "]
        for stat, label in zip(stats, labels):
            val = identity.get(stat, 0.0)
            print(f"       {label}  {bar(val, 16)}  {val:.2f}")

        facts_count = len(memory.get("facts_about_ayush", []))
        print(f"       facts on Ayush: {facts_count}")

        if feed.get("dream_snippet"):
            snip = feed["dream_snippet"][:60]
            print(f"       last dream: \"{snip}...\"")

        print()

    print("─" * 60)


# ── Commands ───────────────────────────────────────────────────────────────────

def send_message(agent):
    """Open a quick message session with an agent — runs boot.py."""
    print(f"\n[opening session with {agent['name']}...]\n")
    subprocess.run(["python", os.path.join(agent["path"], "boot.py")])


def trigger_dream(agent):
    """Force a dream cycle right now."""
    dream_script = os.path.join(agent["path"], "dream.py")
    if not os.path.exists(dream_script):
        print("[dream.py not found]")
        return
    print(f"\n[triggering dream for {agent['name']}...]\n")
    subprocess.run(["python", dream_script])


def trigger_surf(agent):
    """Force a surf cycle right now."""
    surf_script = os.path.join(agent["path"], "surf.py")
    if not os.path.exists(surf_script):
        print("[surf.py not found]")
        return
    print(f"\n[triggering surf for {agent['name']}...]\n")
    subprocess.run(["python", surf_script])


def trigger_commit(agent):
    """Force a GitHub commit right now."""
    github_script = os.path.join(agent["path"], "commit.py")
    if not os.path.exists(github_script):
        print("[commit.py not found]")
        return
    print(f"\n[triggering GitHub commit for {agent['name']}...]\n")
    subprocess.run(["python", github_script])


def view_memory(agent):
    """Print the agent's full memory.json."""
    memory = agent["memory"]
    print(f"\n── {agent['name']} memory ──────────────────────────────")
    print(f"sessions total : {memory.get('sessions_total', 0)}")
    print(f"last seen      : {memory.get('last_seen', 'never')}")
    print(f"\nfacts about Ayush:")
    for f in memory.get("facts_about_ayush", []):
        print(f"  - {f}")
    print(f"\nnotable moments:")
    for m in memory.get("notable_moments", []):
        print(f"  - {m}")
    print(f"\nrajesh observations:")
    for o in memory.get("rajesh_observations", []):
        print(f"  - {o}")
    print()


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    while True:
        agents = load_agents()
        dashboard(agents)

        if not agents:
            input("Press Enter to refresh...")
            continue

        print("  Commands:")
        print("  [1-N] select agent   [r] refresh   [q] quit")
        print()

        cmd = input("  > ").strip().lower()

        if cmd == "q":
            print("\n[manager closed]\n")
            break
        elif cmd == "r":
            continue
        elif cmd.isdigit():
            idx = int(cmd) - 1
            if 0 <= idx < len(agents):
                agent = agents[idx]
                clear()
                print(f"\n  Agent: {agent['name'].upper()}")
                print("  [1] talk to them")
                print("  [2] trigger dream")
                print("  [3] trigger surf")
                print("  [4] trigger GitHub commit")
                print("  [5] view memory")
                print("  [b] back")
                print()
                sub = input("  > ").strip().lower()
                if sub == "1":
                    send_message(agent)
                elif sub == "2":
                    trigger_dream(agent)
                    input("\nPress Enter to continue...")
                elif sub == "3":
                    trigger_surf(agent)
                    input("\nPress Enter to continue...")
                elif sub == "4":
                    trigger_commit(agent)
                    input("\nPress Enter to continue...")
                elif sub == "5":
                    view_memory(agent)
                    input("\nPress Enter to continue...")
            else:
                print("  [invalid selection]")
        else:
            print("  [unknown command]")


if __name__ == "__main__":
    main()
