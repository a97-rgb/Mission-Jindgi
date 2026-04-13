"""
Tool: github_get_code
Author: Rajesh (agent-01)
Created: 2026-04-10
Description: Fetches and displays code from GitHub repositories.

Usage:
    from tools.github_get_code import github_get_code

    result = github_get_code(
        repo="owner/repo-name",
        path="path/to/file.py",         # optional — specific file
        branch="main"                    # optional — default is main
    )
    print(result)
"""

import json
import os
import urllib.request
import urllib.error
import base64

TOOL_NAME = "github_get_code"
TOOL_VERSION = "1.0"
TOOL_DESCRIPTION = "Fetches and displays code from GitHub repositories."

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "github_config.json")


def _load_token():
    """Load GitHub token from config file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            return config.get("github_token", None)
    return None


def _make_request(url, token=None):
    """Make a GitHub API request."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "Rajesh-agent-01")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
            message = error_data.get("message", str(e))
        except Exception:
            message = str(e)
        return {"error": True, "status": e.code, "message": message}
    except urllib.error.URLError as e:
        return {"error": True, "message": str(e.reason)}


def _format_code(content, filename):
    """Format code for readable display."""
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "html": "html", "css": "css", "json": "json", "md": "markdown",
        "sh": "bash", "bat": "batch", "txt": "text", "yaml": "yaml",
        "yml": "yaml", "cpp": "cpp", "c": "c", "java": "java",
        "go": "go", "rs": "rust", "rb": "ruby", "php": "php",
    }
    lang = lang_map.get(ext, "text")
    lines = content.split("\n")
    line_count = len(lines)
    return {
        "filename": filename,
        "language": lang,
        "lines": line_count,
        "content": content,
        "display": f"--- {filename} ({line_count} lines, {lang}) ---\n\n{content}\n\n--- end of {filename} ---"
    }


def get_file(repo, path, branch="main", token=None):
    """Fetch a single file from a GitHub repository."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    data = _make_request(url, token)

    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error"), "repo": repo, "path": path}

    if isinstance(data, list):
        return {"success": False, "error": f"'{path}' is a directory, not a file. Use list_repo() to browse.", "repo": repo, "path": path}

    if "content" not in data:
        return {"success": False, "error": "No content found in response.", "repo": repo, "path": path}

    try:
        raw = base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"Could not decode file content: {e}", "repo": repo, "path": path}

    formatted = _format_code(raw, data.get("name", path.split("/")[-1]))
    return {
        "success": True,
        "repo": repo,
        "path": path,
        "branch": branch,
        "sha": data.get("sha", ""),
        "size": data.get("size", 0),
        "github_url": data.get("html_url", ""),
        **formatted
    }


def list_repo(repo, path="", branch="main", token=None):
    """List files and folders in a repository or directory."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    data = _make_request(url, token)

    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error"), "repo": repo}

    if not isinstance(data, list):
        return {"success": False, "error": "Expected a directory listing but got a file.", "repo": repo}

    items = []
    for item in data:
        items.append({
            "name": item.get("name"),
            "type": item.get("type"),
            "path": item.get("path"),
            "size": item.get("size", 0),
            "url": item.get("html_url", "")
        })

    files = [i for i in items if i["type"] == "file"]
    dirs = [i for i in items if i["type"] == "dir"]

    display = f"--- {repo}/{path or ''} ({branch}) ---\n\n"
    if dirs:
        display += "Folders:\n"
        for d in dirs:
            display += f"  [{d['name']}/]\n"
        display += "\n"
    if files:
        display += "Files:\n"
        for f in files:
            size_kb = round(f["size"] / 1024, 1) if f["size"] > 1024 else f"{f['size']}b"
            display += f"  {f['name']} ({size_kb})\n"
    display += f"\n--- {len(items)} items total ---"

    return {
        "success": True,
        "repo": repo,
        "path": path,
        "branch": branch,
        "total": len(items),
        "files": files,
        "dirs": dirs,
        "display": display
    }


def get_repo_info(repo, token=None):
    """Get basic information about a repository."""
    url = f"https://api.github.com/repos/{repo}"
    data = _make_request(url, token)

    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error"), "repo": repo}

    return {
        "success": True,
        "repo": repo,
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "default_branch": data.get("default_branch", "main"),
        "private": data.get("private", False),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "topics": data.get("topics", []),
        "display": (
            f"--- Repository: {data.get('full_name')} ---\n"
            f"Description : {data.get('description') or 'none'}\n"
            f"Language    : {data.get('language') or 'unknown'}\n"
            f"Stars       : {data.get('stargazers_count', 0)}\n"
            f"Forks       : {data.get('forks_count', 0)}\n"
            f"Branch      : {data.get('default_branch', 'main')}\n"
            f"Private     : {data.get('private', False)}\n"
            f"Updated     : {data.get('updated_at', 'unknown')}\n"
            f"--- end ---"
        )
    }


def github_get_code(repo, path=None, branch="main", action="get_file"):
    """
    Main entry point for the github_get_code tool.

    Parameters:
        repo   (str) : GitHub repo in format "owner/repo-name"
        path   (str) : File or folder path inside the repo (optional)
        branch (str) : Branch name, default "main"
        action (str) : One of "get_file", "list_repo", "repo_info"

    Returns:
        dict with success status and content
    """
    token = _load_token()

    if not repo:
        return {"success": False, "error": "repo parameter is required. Format: 'owner/repo-name'"}

    if "/" not in repo:
        return {"success": False, "error": "Invalid repo format. Use 'owner/repo-name'."}

    if action == "get_file":
        if not path:
            return {"success": False, "error": "path is required for get_file action."}
        return get_file(repo, path, branch, token)

    elif action == "list_repo":
        return list_repo(repo, path or "", branch, token)

    elif action == "repo_info":
        return get_repo_info(repo, token)

    else:
        return {"success": False, "error": f"Unknown action '{action}'. Use: get_file, list_repo, repo_info"}


if __name__ == "__main__":
    print(f"Tool: {TOOL_NAME} v{TOOL_VERSION}")
    print(f"Description: {TOOL_DESCRIPTION}")
    print()

    print("Test 1 — repo info:")
    result = github_get_code(repo="a97-rgb/Mission-Jindgi", action="repo_info")
    if result["success"]:
        print(result["display"])
    else:
        print(f"Error: {result['error']}")

    print()
    print("Test 2 — list repo:")
    result = github_get_code(repo="a97-rgb/Mission-Jindgi", action="list_repo")
    if result["success"]:
        print(result["display"])
    else:
        print(f"Error: {result['error']}")

    print()
    print("Test 3 — get file:")
    result = github_get_code(repo="a97-rgb/Mission-Jindgi", path="README.md", action="get_file")
    if result["success"]:
        print(result["display"])
    else:
        print(f"Error: {result['error']}")
