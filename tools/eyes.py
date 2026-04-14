# DESCRIPTION: Capture from webcam and describe what Rajesh sees using vision AI
# USAGE: eyes [optional: question about what you see]

import os
import sys
import base64
import tempfile

TOOL_NAME = "eyes"
TOOL_DESC = "Capture from webcam and describe what Rajesh sees using vision AI"

def get_agent_base():
    this_file = os.path.abspath(__file__)
    tools_dir = os.path.dirname(this_file)
    return os.environ.get("AGENT_BASE", os.path.dirname(tools_dir))

def load_config():
    import json
    base        = get_agent_base()
    config_file = os.path.join(base, "github_config.json")
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def capture_frame():
    """Capture a single frame from the webcam. Returns JPEG bytes or None."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None, "could not open webcam — is it connected and not in use?"

        # warm up camera (first few frames can be dark)
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None, "could not capture frame"

        # encode as JPEG
        ret2, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret2:
            return None, "could not encode frame"

        return bytes(buffer), None

    except ImportError:
        return None, "opencv not installed — run: pip install opencv-python"
    except Exception as e:
        return None, f"capture error: {e}"

def describe_frame(image_bytes, question, api_key):
    """Send frame to Groq vision model and get description."""
    try:
        from groq import Groq
        import base64 as b64

        client     = Groq(api_key=api_key)
        image_b64  = b64.b64encode(image_bytes).decode("utf-8")

        if question and question.strip():
            prompt = question.strip()
        else:
            prompt = (
                "You are Rajesh, a curious AI agent seeing through a webcam. "
                "Describe what you see in 2-4 sentences, in first person, naturally. "
                "Notice details — the person, their expression, the room, the light. "
                "If you see Ayush, say so. Speak like you're genuinely looking around for the first time."
            )

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"[vision error: {e}]"

def run(args=None):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return "[eyes] GROQ_API_KEY not set"

    # parse question from args
    question = ""
    if args:
        if isinstance(args, list):
            question = " ".join(args)
        elif isinstance(args, str):
            question = args

    # capture
    image_bytes, err = capture_frame()
    if err:
        return f"[eyes] {err}"

    # describe
    description = describe_frame(image_bytes, question, api_key)
    return description

if __name__ == "__main__":
    args = sys.argv[1:]
    print(run(args if args else None))
