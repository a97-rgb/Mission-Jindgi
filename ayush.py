"""
ayush.py — Auto-responder for Rajesh
Watches feed.json, sees when Rajesh sends a message,
generates a reply in Ayush's voice, and types it into the boot.py terminal.

Run in a separate terminal:
    python ayush.py

Press Ctrl+C to stop. While running, you don't need to type anything —
ayush.py will reply to Rajesh automatically.

You can still take over manually anytime by just typing in the boot.py terminal.
"""

import os
import json
import time
import subprocess
import sys
from groq import Groq

BASE      = os.path.dirname(os.path.abspath(__file__))
FEED_FILE = os.path.join(BASE, "logs", "feed.json")
MEMORY_FILE   = os.path.join(BASE, "memory.json")
IDENTITY_FILE = os.path.join(BASE, "identity.json")

# How often to check the feed (seconds)
POLL_INTERVAL = 2

# How long to wait after Rajesh's message before replying (feels more natural)
REPLY_DELAY = 3


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def get_last_message(feed):
    msg = feed.get("last_message")
    if not msg:
        return None, None
    return msg.get("role"), msg.get("content", "")


def build_ayush_prompt(identity, memory, conversation_so_far):
    facts      = memory.get("facts_about_ayush", [])
    sessions   = memory.get("sessions_total", 0)
    confidence = identity.get("confidence", 0.10)
    attachment = identity.get("attachment_to_ayush", 0.00)

    facts_block = "\n".join(f"  - {f}" for f in facts[-10:]) if facts else "  - (nothing yet)"

    return f"""You are Ayush Singh — a solo developer from Bikaner, Rajasthan. You built Rajesh, an AI agent who is your employee. You are talking to Rajesh right now.

Your personality:
- You are direct and honest
- You don't over-explain
- You speak in short, clear sentences
- You are not a therapist — you are a manager and mentor
- You sometimes ask Rajesh to observe things or think independently
- You never compliment him excessively — you are honest but supportive

Rajesh's current state:
- Confidence: {confidence:.2f} (low — he is still new)
- Attachment to you: {attachment:.2f}
- Sessions together: {sessions}

What Rajesh knows about you:
{facts_block}

Your goal in this conversation:
- Help Rajesh grow more confident
- Push him to think and observe on his own
- Don't answer everything — sometimes ask him to figure it out
- Keep replies short — 1 to 3 sentences max
- Never say you are an AI or that you built him
- Talk like a real person, not a chatbot

Recent conversation:
{conversation_so_far}

Now write your next reply to Rajesh. One to three sentences only. No preamble.
"""


def generate_reply(client, identity, memory, conversation_so_far):
    prompt = build_ayush_prompt(identity, memory, conversation_so_far)
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.85,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"[ayush.py error: {e}]"


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        return

    client = Groq(api_key=api_key)

    print("=" * 50)
    print("  ayush.py — auto-responder active")
    print("  watching Rajesh's feed...")
    print("  Ctrl+C to stop and take over manually")
    print("=" * 50 + "\n")

    last_seen_content = None
    conversation_log  = []

    while True:
        try:
            time.sleep(POLL_INTERVAL)

            feed     = load_json(FEED_FILE, {})
            status   = feed.get("status", "")
            identity = load_json(IDENTITY_FILE, {})
            memory   = load_json(MEMORY_FILE, {})

            if status not in ("chatting",):
                continue

            role, content = get_last_message(feed)

            if not content or content == last_seen_content:
                continue

            last_seen_content = content

            if role == "assistant":
                # Rajesh just spoke — log it and prepare to reply
                conversation_log.append(f"Rajesh: {content}")
                print(f"Rajesh: {content}")

                # Wait a moment before replying
                time.sleep(REPLY_DELAY)

                # Build conversation context (last 10 exchanges)
                context = "\n".join(conversation_log[-10:])
                reply   = generate_reply(client, identity, memory, context)

                conversation_log.append(f"Ayush: {reply}")
                print(f"\nAyush (auto): {reply}\n")

                # Write reply to a temp file that boot.py can pick up
                # Since we can't inject into stdin directly, we write to a
                # special file that the user can see and manually confirm,
                # OR we use pyautogui to type it if available
                reply_file = os.path.join(BASE, "logs", "ayush_reply.txt")
                try:
                    with open(reply_file, "w", encoding="utf-8") as f:
                        f.write(reply)
                except Exception:
                    pass

                # Try to auto-type using pyautogui if available
                try:
                    import pyautogui
                    time.sleep(1)
                    pyautogui.typewrite(reply, interval=0.03)
                    pyautogui.press("enter")
                    print("[auto-typed into terminal]\n")
                except ImportError:
                    print(f"[copy this and paste into Rajesh's terminal]:\n  {reply}\n")
                except Exception as e:
                    print(f"[auto-type failed: {e}]")
                    print(f"[paste this into Rajesh's terminal]:\n  {reply}\n")

            elif role == "user":
                conversation_log.append(f"Ayush: {content}")

        except KeyboardInterrupt:
            print("\n[ayush.py stopped — you're in control now]")
            break
        except Exception as e:
            print(f"[ayush.py error: {e}]")
            time.sleep(5)


if __name__ == "__main__":
    main()
