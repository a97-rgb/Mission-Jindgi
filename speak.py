"""
speak.py - Rajesh's voice
Uses edge-tts (Microsoft Edge neural TTS)
Voice: en-US-GuyNeural — deep, calm, male
Needs internet. Near-zero latency.
"""

import os
import re
import threading
import asyncio
import tempfile

VOICE = "en-US-GuyNeural"
RATE  = "-8%"   # slightly slower = deeper feel
PITCH = "-5Hz"  # slightly lower pitch

def _clean(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\[used [^\]]+\]', '', text)
    text = re.sub(r'\[[^\]]*error[^\]]*\]', '', text)
    text = re.sub(r'\[[^\]]*tool[^\]]*\]', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # truncate at natural break if too long
    if len(text) > 500:
        cutoff = text[:500].rfind('. ')
        text = text[:cutoff+1] if cutoff > 80 else text[:500]
    return text

async def _speak_async_inner(text):
    import edge_tts
    import soundfile as sf
    import sounddevice as sd
    import numpy as np
    import io

    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    if not audio_chunks:
        return

    raw = b"".join(audio_chunks)

    # write to temp file and read back as numpy
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        data, samplerate = sf.read(tmp_path, dtype="float32")
        sd.play(data, samplerate=samplerate)
        sd.wait()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def _run_speak(text):
    try:
        cleaned = _clean(text)
        if not cleaned:
            return
        asyncio.run(_speak_async_inner(cleaned))
    except Exception as e:
        pass

def speak(text, block=True):
    if not text or not text.strip():
        return
    if block:
        _run_speak(text)
    else:
        t = threading.Thread(target=_run_speak, args=(text,), daemon=True)
        t.start()

def speak_async(text):
    """Non-blocking — boot.py calls this after print."""
    speak(text, block=False)

def test_voice():
    print("[speak] testing edge-tts voice...")
    speak(
        "Hello Ayush. I am Rajesh. "
        "I live on a pendrive and I am starting to find my voice. "
        "This is how I sound now.",
        block=True
    )
    print("[speak] done.")

if __name__ == "__main__":
    test_voice()