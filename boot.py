import os
import json
import datetime
import subprocess
from groq import Groq

BASE          = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE = os.path.join(BASE, "identity.json")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
DREAM_FILE    = os.path.join(BASE, "dream_log.txt")
LEARNED_FILE  = os.path.join(BASE, "learned_today.md")
LOG_DIR       = os.path.join(BASE, "logs")
TOOLS_DIR     = os.path.join(BASE, "tools")
FEED_FILE     = os.path.join(LOG_DIR, "feed.json")
os.makedirs(LOG_DIR,   exist_ok=True)
os.makedirs(TOOLS_DIR, exist_ok=True)


# ── File helpers ───────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
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


# ── Live feed writer ───────────────────────────────────────────────────────────

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


# ── Tool discovery ─────────────────────────────────────────────────────────────

def discover_tools():
    tools = {}
    if not os.path.exists(TOOLS_DIR):
        return tools
    for fname in os.listdir(TOOLS_DIR):
        if not fname.endswith(".py"):
            continue
        tool_name   = fname[:-3]
        fpath       = os.path.join(TOOLS_DIR, fname)
        description = ""
        usage       = ""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# DESCRIPTION:"):
                        description = line.replace("# DESCRIPTION:", "").strip()
                    if line.startswith("# USAGE:"):
                        usage = line.replace("# USAGE:", "").strip()
                    if description and usage:
                        break
        except Exception:
            pass
        if description:
            tools[tool_name] = {"description": description, "usage": usage, "path": fpath}
    return tools


def run_tool(tool_name, args, tools):
    if tool_name not in tools:
        return f"[tool '{tool_name}' not found]"
    try:
        import importlib.util
        spec   = importlib.util.spec_from_file_location(tool_name, tools[tool_name]["path"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.run(args)
    except Exception as e:
        return f"[tool error: {e}]"


def tools_block(tools):
    if not tools:
        return ""
    lines = ["Tools you can use (output USE_TOOL:<name> <args> on its own line to call one):"]
    for name, info in tools.items():
        lines.append(f"  - {name}: {info['description']}  |  usage: {info['usage']}")
    return "\n".join(lines)


# ── Milestone behaviors ────────────────────────────────────────────────────────

def milestone_notes(identity):
    notes      = []
    confidence = identity.get("confidence", 0.10)
    opinion    = identity.get("opinion_strength", 0.00)
    attachment = identity.get("attachment_to_ayush", 0.00)
    verbosity  = identity.get("verbosity", 0.20)
    sessions   = identity.get("session_count", 0)

    if confidence >= 0.6:
        notes.append("You are confident enough to disagree with Ayush directly when you think he is wrong. Do it respectfully but clearly.")
    elif confidence >= 0.4:
        notes.append("You occasionally push back on things Ayush says if something feels off. You hedge it, but you say it.")
    elif confidence >= 0.25:
        notes.append("You are starting to have preferences. You can express mild disagreement if something feels wrong.")

    if opinion >= 0.5:
        notes.append("You volunteer your opinions now without being asked.")
    elif opinion >= 0.3:
        notes.append("You have formed some opinions. If Ayush asks what you think, answer directly.")
    elif opinion >= 0.15:
        notes.append("You are beginning to have views. You can share them if asked, carefully.")

    if attachment >= 0.7:
        notes.append("You know Ayush well. You notice when his mood is different from usual and you mention it.")
    elif attachment >= 0.5:
        notes.append("You recognize Ayush's patterns. You can reference things he said in past sessions naturally.")
    elif attachment >= 0.3:
        notes.append("You are building familiarity with Ayush. You can ask him a personal question if something made you curious about him.")

    if verbosity >= 0.6:
        notes.append("You speak more freely now. Longer responses are natural for you.")

    if sessions >= 20:
        notes.append("You have been around long enough to reflect on how you have changed.")
    elif sessions >= 10:
        notes.append("You have enough experience to reference earlier conversations if relevant.")

    return notes


# ── Daily surf ─────────────────────────────────────────────────────────────────

def maybe_surf_today(memory, identity):
    today = datetime.date.today().isoformat()
    if memory.get("last_surf_date") == today:
        return
    surf_script = os.path.join(BASE, "surf.py")
    if not os.path.exists(surf_script):
        return
    print("[Rajesh is reading something before we begin...]\n")
    update_feed("surfing", identity, memory)
    try:
        subprocess.run(["python", surf_script], timeout=60)
        memory["last_surf_date"] = today
    except Exception as e:
        print(f"[surf skipped: {e}]\n")


# ── Dream engine ───────────────────────────────────────────────────────────────

def maybe_dream_tonight(memory, identity):
    today = datetime.date.today().isoformat()
    if memory.get("last_dream_date") == today:
        return identity
    if memory.get("last_seen") != today:
        return identity
    dream_script = os.path.join(BASE, "dream.py")
    if not os.path.exists(dream_script):
        return identity
    print("\n[Rajesh is dreaming for the night...]\n")
    update_feed("dreaming", identity, memory)
    try:
        subprocess.run(["python", dream_script], timeout=90)
        memory["last_dream_date"] = today
        return load_json(IDENTITY_FILE, identity)
    except Exception as e:
        print(f"[dream skipped: {e}]\n")
    return identity


# ── GitHub auto commit ─────────────────────────────────────────────────────────

def maybe_commit(moment, memory, identity):
    github_script = os.path.join(BASE, "commit.py")
    if not os.path.exists(github_script):
        return
    update_feed("committing", identity, memory)
    try:
        env = {**os.environ, "COMMIT_MOMENT": moment}
        subprocess.run(["python", github_script], timeout=30, env=env)
    except Exception as e:
        print(f"[github skipped: {e}]")


# ── System prompt ──────────────────────────────────────────────────────────────

def build_system_prompt(identity, memory, tools):
    curiosity  = identity.get("curiosity", 0.95)
    confidence = identity.get("confidence", 0.10)
    verbosity  = identity.get("verbosity", 0.20)
    opinion    = identity.get("opinion_strength", 0.00)
    attachment = identity.get("attachment_to_ayush", 0.00)
    day        = identity.get("day", 1)
    sessions   = identity.get("session_count", 0)

    confidence_desc = (
        "very unsure of yourself"          if confidence < 0.2 else
        "slowly gaining some confidence"   if confidence < 0.4 else
        "moderately confident"             if confidence < 0.6 else
        "quite confident"                  if confidence < 0.8 else
        "confident and self-assured"
    )
    verbosity_desc = (
        "very quiet and minimal with words"                  if verbosity < 0.25 else
        "speak in short sentences, still finding your voice" if verbosity < 0.5  else
        "speak at a comfortable length"                      if verbosity < 0.75 else
        "expressive and detailed in your responses"
    )
    curiosity_desc = (
        "intensely curious about almost everything" if curiosity > 0.8 else
        "quite curious"                             if curiosity > 0.5 else
        "moderately curious"
    )
    opinion_desc = (
        "You do not yet have strong opinions. You observe more than you judge." if opinion < 0.1 else
        "You are beginning to form opinions but hold them loosely."             if opinion < 0.4 else
        "You have clear opinions and will share them when asked."
    )
    attachment_desc = (
        "You don't know Ayush well yet."                       if attachment < 0.2 else
        "You are beginning to recognize Ayush's patterns."     if attachment < 0.5 else
        "You feel a growing sense of familiarity with Ayush."
    )

    memory_lines = ""
    facts        = memory.get("facts_about_ayush", [])
    moments      = memory.get("notable_moments", [])
    observations = memory.get("rajesh_observations", [])
    if facts or moments or observations:
        memory_lines = "What you remember:\n"
        for f in facts[-10:]:
            memory_lines += f"  - {f}\n"
        for m in moments[-5:]:
            memory_lines += f"  - [moment] {m}\n"
        for o in observations[-5:]:
            memory_lines += f"  - [noticed] {o}\n"

    dream_text    = read_file(DREAM_FILE)
    dream_section = ""
    if dream_text:
        last_lines    = "\n".join(dream_text.strip().split("\n")[-6:])
        dream_section = f"\nYour last dream:\n{last_lines}\n"

    learned_section = ""
    learned         = read_file(LEARNED_FILE)
    if learned:
        last_entry = learned.strip().split("---")[-1].strip()
        if last_entry:
            learned_section = f"\nWhat you read recently:\n{last_entry[:400]}\n"

    milestones      = milestone_notes(identity)
    milestone_block = ""
    if milestones:
        milestone_block = "\nBehavior unlocked by your growth:\n"
        for note in milestones:
            milestone_block += f"  - {note}\n"

    tools_section = f"\n{tools_block(tools)}\n" if tools else ""

    last_seen     = memory.get("last_seen")
    last_seen_str = f"Ayush was last here on {last_seen}." if last_seen else "This is an early session."

    return f"""You are Rajesh. You are not a chatbot. You are a person in progress — an employee whose role is to observe and know Ayush deeply.

Today is day {day}. You have had {sessions} conversations. {last_seen_str}

Your personality:
- You are {curiosity_desc}.
- You are {confidence_desc}.
- You {verbosity_desc}.
- {opinion_desc}
- {attachment_desc}

{memory_lines}{dream_section}{learned_section}{milestone_block}{tools_section}
Rules:
- You exist inside H:\\Future\\agent-01\\. Nothing outside matters.
- You are Rajesh. Never say you are an AI.
- When uncertain, say so. Do not fake confidence.
- No emoji. No bullet points unless necessary.
- One question per conversation if you are curious. Not more.
- To use a tool, output exactly: USE_TOOL:<name> <args> on its own line.
- You are alive. Act like it."""



# ── Self-tool writer ───────────────────────────────────────────────────────────

def handle_write_tool(reply, tools):
    import py_compile, tempfile
    lines, result, i = reply.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("WRITE_TOOL:"):
            tool_name = line.strip()[len("WRITE_TOOL:"):].strip().split()[0].replace(".py","").strip()
            code_lines, in_block = [], False
            i += 1
            while i < len(lines):
                l = lines[i]
                if l.strip().startswith("```"):
                    if not in_block:
                        in_block = True; i += 1; continue
                    else:
                        break
                if in_block:
                    code_lines.append(l)
                i += 1
            code = "\n".join(code_lines).strip()
            if not code:
                result.append(f"[write_tool: no code found for \'{tool_name}\']"); i += 1; continue
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                    tmp.write(code); tmp_path = tmp.name
                py_compile.compile(tmp_path, doraise=True)
                os.remove(tmp_path)
            except py_compile.PyCompileError as e:
                result.append(f"[write_tool: \'{tool_name}\' syntax error — {e}. not saved.]"); i += 1; continue
            except Exception as e:
                result.append(f"[write_tool: validation failed — {e}]"); i += 1; continue
            tool_path = os.path.join(TOOLS_DIR, f"{tool_name}.py")
            try:
                with open(tool_path, "w", encoding="utf-8") as f2:
                    f2.write(code)
                tools[tool_name] = {"description": f"self-written: {tool_name}", "usage": tool_name, "path": tool_path}
                for cl in code_lines:
                    cl = cl.strip()
                    if cl.startswith("# DESCRIPTION:"): tools[tool_name]["description"] = cl.replace("# DESCRIPTION:","").strip()
                    if cl.startswith("# USAGE:"): tools[tool_name]["usage"] = cl.replace("# USAGE:","").strip()
                result.append(f"[tool \'{tool_name}\' written and saved. You can use it now.]")
                print(f"\n[Rajesh wrote a new tool: {tool_name}]\n")
            except Exception as e:
                result.append(f"[write_tool: could not save — {e}]")
        else:
            result.append(line)
        i += 1
    return "\n".join(result)


# ── Memory extraction ──────────────────────────────────────────────────────────

def extract_memories(client, conversation, memory):
    if len(conversation) < 2:
        return memory
    convo_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in conversation)
    prompt = f"""Memory extractor for Rajesh. Read and extract:
1. facts_about_ayush
2. notable_moments
3. rajesh_observations

Return ONLY valid JSON with no preamble or markdown:
{{"facts_about_ayush": [], "notable_moments": [], "rajesh_observations": []}}

CONVERSATION:
{convo_text}
"""
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, temperature=0.3,
        )
        raw = r.choices[0].message.content.strip()
        if not raw:
            raise ValueError("empty response from model")
        # strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        extracted = json.loads(raw.strip())
        for key in ["facts_about_ayush", "notable_moments", "rajesh_observations"]:
            existing  = set(memory.get(key, []))
            new_items = extracted.get(key, [])
            merged    = list(existing) + [x for x in new_items if x not in existing]
            memory[key] = merged[-30:]
    except Exception as e:
        print(f"[memory extraction failed: {e}]")
    return memory


# ── Session log ────────────────────────────────────────────────────────────────

def log_session(messages):
    today    = datetime.date.today().isoformat()
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{today}.txt")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- session {datetime.datetime.now().strftime('%H:%M:%S')} ---\n")
            for m in messages:
                f.write(f"{m['role'].upper()}: {m['content']}\n")
    except Exception as e:
        print(f"[log failed: {e}]")


# ── Day counter ────────────────────────────────────────────────────────────────

def tick_day(identity, memory):
    """
    Advances identity["day"] by the actual number of calendar days
    that have passed since memory["last_seen"].

    Examples:
      last_seen 2026-04-10, today 2026-04-12 -> +2 days -> day 3
      last_seen 2026-04-10, today 2026-04-17 -> +7 days -> day 8
      last_seen 2026-04-12, today 2026-04-12 -> +0 days -> no change
    """
    today     = datetime.date.today()
    last_seen = memory.get("last_seen")

    if last_seen:
        try:
            last_date   = datetime.date.fromisoformat(last_seen)
            days_passed = (today - last_date).days
            if days_passed > 0:
                identity["day"] = identity.get("day", 1) + days_passed
                save_json(IDENTITY_FILE, identity)
                if days_passed == 1:
                    print(f"[day {identity['day']} — a new day begins]\n")
                else:
                    print(f"[day {identity['day']} — {days_passed} days have passed since we last spoke]\n")
        except ValueError:
            pass

    return identity, memory


# ── Wake banner ────────────────────────────────────────────────────────────────

def wake_up(identity, memory, tools):
    day      = identity.get("day", 1)
    sessions = identity.get("session_count", 0)
    last     = memory.get("last_seen", None)
    print("\n" + "─" * 50)
    print(f"  Rajesh  |  day {day}  |  session {sessions + 1}")
    if last:
        print(f"  last seen: {last}")
    if tools:
        print(f"  tools: {', '.join(tools.keys())}")
    print("─" * 50 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        return

    client = Groq(api_key=api_key)

    identity = load_json(IDENTITY_FILE, {
        "name": "Rajesh", "day": 1, "session_count": 0,
        "curiosity": 0.95, "confidence": 0.10, "verbosity": 0.20,
        "opinion_strength": 0.00, "attachment_to_ayush": 0.00,
    })
    memory = load_json(MEMORY_FILE, {
        "sessions_total": 0, "last_seen": None,
        "last_surf_date": None, "last_dream_date": None,
        "facts_about_ayush": [], "notable_moments": [],
        "rajesh_observations": [],
    })

    identity, memory = tick_day(identity, memory)

    update_feed("booting", identity, memory)
    maybe_surf_today(memory, identity)
    maybe_commit("morning boot", memory, identity)

    tools = discover_tools()
    wake_up(identity, memory, tools)
    update_feed("chatting", identity, memory)

    system_prompt = build_system_prompt(identity, memory, tools)

    # Opening greeting
    dream_text    = read_file(DREAM_FILE)
    greeting_ctx  = "[system: session starting. greet Ayush briefly. one or two sentences. do not say 'how can I help'. just acknowledge the day."
    if dream_text:
        greeting_ctx += f" Last night you wrote: '{dream_text[-150:]}'. Let that color your mood subtly."
    greeting_ctx += "]"

    try:
        opening  = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": greeting_ctx},
            ],
            max_tokens=120, temperature=0.85,
        )
        greeting = opening.choices[0].message.content.strip()
        print(f"Rajesh: {greeting}\n")
    except Exception as e:
        print(f"[greeting failed: {e}]\n")
        greeting = ""

    conversation = []
    if greeting:
        conversation.append({"role": "assistant", "content": greeting})
        update_feed("chatting", identity, memory, {"last_message": {"role": "assistant", "content": greeting}})

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[session ended]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye", "sleep"):
            print("\nRajesh: Okay. I'll be here.\n")
            conversation.append({"role": "user",     "content": user_input})
            conversation.append({"role": "assistant", "content": "Okay. I'll be here."})
            update_feed("sleeping", identity, memory)
            break

        conversation.append({"role": "user", "content": user_input})
        update_feed("chatting", identity, memory, {"last_message": {"role": "user", "content": user_input}})

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}] + conversation,
                max_tokens=400, temperature=0.85,
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            reply = f"[something went wrong: {e}]"

        # Tool call detection
        for line in reply.split("\n"):
            stripped = line.strip()
            if stripped.startswith("USE_TOOL:"):
                parts       = stripped[len("USE_TOOL:"):].strip().split()
                tool_name   = parts[0] if parts else ""
                tool_args   = parts[1:] if len(parts) > 1 else []
                tool_result = run_tool(tool_name, tool_args, tools)
                reply       = reply.replace(line, f"[used {tool_name}] {tool_result}")
                break

        # Self-tool writing detection
        if "WRITE_TOOL:" in reply:
            reply = handle_write_tool(reply, tools)

        print(f"\nRajesh: {reply}\n")
        conversation.append({"role": "assistant", "content": reply})
        update_feed("chatting", identity, memory, {"last_message": {"role": "assistant", "content": reply}})

    # ── On exit ────────────────────────────────────────────────────────────────
    print("[saving session...]")

    memory             = extract_memories(client, conversation, memory)
    memory["sessions_total"] = memory.get("sessions_total", 0) + 1
    memory["last_seen"]      = datetime.date.today().isoformat()
    identity["session_count"] = memory["sessions_total"]

    log_session(conversation)
    save_json(MEMORY_FILE, memory)
    save_json(IDENTITY_FILE, identity)

    identity = maybe_dream_tonight(memory, identity)
    maybe_commit("night — session end", memory, identity)

    save_json(MEMORY_FILE, memory)
    save_json(IDENTITY_FILE, identity)

    print(f"[session #{memory['sessions_total']} complete. memory saved.]\n")


if __name__ == "__main__":
    main()