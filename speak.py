"""
speak.py - Rajesh's voice
Sentence-streaming: each sentence generates and plays immediately.
Deep male voice using Kokoro TTS (am_adam)
"""

import os
import re
import threading
import queue

# config
VOICE = "am_adam"
SPEED = 0.92

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
            print(f"[speak] model not found: {model_path}")
            return None
        if not os.path.exists(voices_path):
            print(f"[speak] voices not found: {voices_path}")
            return None
        _kokoro = Kokoro(model_path, voices_path)
        return _kokoro
    except ImportError:
        print("[speak] kokoro-onnx not installed.")
        return None
    except Exception as e:
        print(f"[speak] load failed: {e}")
        return None

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
    return text

def _split_sentences(text):
    """Split text into natural sentences for streaming."""
    # split on . ! ? followed by space or end
    parts = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # if a chunk is very long, split further at commas
        if len(part) > 120:
            sub = re.split(r'(?<=,)\s+', part)
            sentences.extend([s.strip() for s in sub if s.strip()])
        else:
            sentences.append(part)
    return sentences

def _generate_audio(kokoro, text):
    """Generate audio for a single sentence."""
    try:
        with _lock:
            samples, sample_rate = kokoro.create(
                text,
                voice=VOICE,
                speed=SPEED,
                lang="en-us",
            )
        import numpy as np
        return np.array(samples, dtype=np.float32), sample_rate
    except Exception:
        return None, None

def _player_thread(audio_queue):
    """Dedicated thread that plays audio chunks as they arrive."""
    import sounddevice as sd
    while True:
        item = audio_queue.get()
        if item is None:
            break
        audio, sample_rate = item
        if audio is not None and len(audio) > 0:
            try:
                sd.play(audio, samplerate=sample_rate)
                sd.wait()
            except Exception:
                pass
        audio_queue.task_done()

def speak(text, block=True):
    if not text or not text.strip():
        return

    cleaned = _clean(text)
    if not cleaned:
        return

    sentences = _split_sentences(cleaned)
    if not sentences:
        return

    def _run():
        try:
            kokoro = _load_kokoro()
            if kokoro is None:
                return

            # queue for player thread
            audio_queue = queue.Queue()
            player = threading.Thread(target=_player_thread, args=(audio_queue,), daemon=True)
            player.start()

            for sentence in sentences:
                if not sentence.strip():
                    continue
                audio, sample_rate = _generate_audio(kokoro, sentence)
                if audio is not None:
                    audio_queue.put((audio, sample_rate))

            # signal player to stop
            audio_queue.put(None)
            player.join()

        except Exception:
            pass

    if block:
        _run()
    else:
        t = threading.Thread(target=_run, daemon=True)
        t.start()

def speak_async(text):
    """Non-blocking — boot.py calls this after print."""
    speak(text, block=False)

def test_voice():
    print("[speak] testing sentence streaming...")
    speak(
        "Hello. I am Rajesh. I live on a pendrive. "
        "Each sentence should play immediately after the last. "
        "The gap should be small now.",
        block=True
    )
    print("[speak] done.")

if __name__ == "__main__":
    test_voice()