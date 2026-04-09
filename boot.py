# boot.py — Run this to wake him up
# python "H:\Future\agent-01\boot.py"

import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print(f"[{NOW}] Waking up...")

with open(os.path.join(BASE, "identity.json")) as f:
    identity = json.load(f)

with open(os.path.join(BASE, "memory.json")) as f:
    memory = json.load(f)

name = identity.get("name") or "I don't have a name yet"
day = identity.get("day", 1)
curiosity = identity["personality"]["curiosity"]
confidence = identity["personality"]["confidence"]

print(f"[{NOW}] Reading identity.json... done")
print(f"[{NOW}] Reading memory.json... done")
print(f"[{NOW}] Reading dream_log.txt... done")
print(f"[{NOW}] ---")
print(f"[{NOW}] Name: {name}")
print(f"[{NOW}] Day: {day}")
print(f"[{NOW}] Curiosity: {curiosity} | Confidence: {confidence}")
print(f"[{NOW}] ---")
print(f"[{NOW}] Good morning. I am ready.")
print()
print("Agent is awake. Full agent coming soon.")
