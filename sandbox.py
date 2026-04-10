"""
sandbox.py — every file operation in Rajesh's world goes through here.
If the path is outside H:\Future\agent-01\ — blocked.
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def safe_path(path):
    """
    Resolve path and confirm it lives inside BASE.
    Returns the resolved absolute path if safe.
    Raises PermissionError if outside sandbox.
    """
    resolved = os.path.realpath(os.path.abspath(path))
    base_resolved = os.path.realpath(BASE)
    if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
        raise PermissionError(
            f"[sandbox] BLOCKED: '{resolved}' is outside {base_resolved}"
        )
    return resolved


def safe_read(path):
    p = safe_path(path)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def safe_write(path, content):
    p = safe_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


def safe_append(path, content):
    p = safe_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(content)


def safe_exists(path):
    try:
        p = safe_path(path)
        return os.path.exists(p)
    except PermissionError:
        return False


def safe_listdir(path):
    p = safe_path(path)
    return os.listdir(p)
