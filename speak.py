"""
speak.py - Rajesh's voice
Deep male voice using Kokoro TTS (am_adam)
Drop into H:/Future/agent-01/
"""

import os
import re
import threading

# config
VOICE       = "am_adam"
SPEED       = 0.92
SAMPLE_RATE = 24000

# lazy globals
_kokoro = None
_lock   = threading.Lock()

def _load_kokoro():
    global _kokoro
    if _kokoro is not None:
        return _kokoro
    try:
        from kokoro_onnx import Kokoro
        base        = os.path.dirname(os.path.abspath(__file__))
        model_path  = os.path.join(base, "kokoro-v1.0.int8.onnx")
        voices_path = os.path.join(base, "voices-v1.0.bin")

        if not os.path.exists(model_path):
            print(f"[speak] model not found at {model_path}")
            return None
        if not os.path.exists(voices_path):
            print(f"[speak] voices not found at {voices_path}")
            return None

        _kokoro = Kokoro(model_path, voices_path)
        return _kokoro
    except ImportError:
        print("[speak] kokoro-onnx not installed. Run: pip install kokoro-onnx sounddevice numpy")
        return None
    except Exception as e:
        print(f"[speak] failed to load Kokoro: {e}")
        return None

def _clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\[used [^\]]+\]', '', text)
    text = re.sub(r'\[[^\]]*error[^\]]*\]', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 600:
        cutoff = text[:600].rfind('. ')
        text = text[:cutoff+1] if cutoff > 100 else text[:600]
    return text

def speak(text, block=True):
    if not text or not text.strip():
        return

    def _play():
        try:
            import sounddevice as sd
            import numpy as np

            kokoro = _load_kokoro()
            if kokoro is None:
                return

            cleaned = _clean_text(text)
            if not cleaned:
                return

            with _lock:
                samples, sample_rate = kokoro.create(
                    cleaned,
                    voice=VOICE,
                    speed=SPEED,
                    lang="en-us",
                )

            audio = np.array(samples, dtype=np.float32)
            sd.play(audio, samplerate=sample_rate)
            sd.wait()

        except Exception:
            pass

    if block:
        _play()
    else:
        t = threading.Thread(target=_play, daemon=True)
        t.start()

def speak_async(text):
    speak(text, block=False)

def test_voice():
    print("[speak] testing voice...")
    speak("Hello. I am Rajesh. I am starting to find my voice.", block=True)
    print("[speak] done.")

if __name__ == "__main__":
    test_voice()