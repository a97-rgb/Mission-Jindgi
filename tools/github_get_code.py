"""
Tool: github_get_code
Description: Fetches and displays code from GitHub repositories.
"""

import json
import os
import urllib.request
import urllib.error
import base64

TOOL_NAME = "github_get_code"
TOOL_DESC = "Fetch code or list files from any GitHub repo"
TOOL_VERSION = "1.0"


def _get_agent_base():
    this_file = os.path.abspath(__file__)
    tools_dir = os.path.dirname(this_file)
    return os.environ.get("AGENT_BASE", os.path.dirname(tools_dir))

def _load_config():
    config_path = os.path.join(_get_agent_base(), "github_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def _load_token():
    cfg = _load_config()
    return cfg.get("ayush_token") or cfg.get("token", None)

def _default_owner():
    cfg = _load_config()
    return cfg.get("ayush_username", "Ayush442842q")

def _resolve_repo(repo):
    """Auto-prepend owner if repo has no slash."""
    if not repo:
        return None
    if "/" not in repo:
        return f"{_default_owner()}/{repo}"
    return repo

def _make_request(url, token=None):
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
            message = json.loads(error_body).get("message", str(e))
        except Exception:
            message = str(e)
        return {"error": True, "status": e.code, "message": message}
    except urllib.error.URLError as e:
        return {"error": True, "message": str(e.reason)}

def _format_code(content, filename):
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"
    lang_map = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "html": "html", "css": "css", "json": "json", "md": "markdown",
        "sh": "bash", "bat": "batch", "txt": "text", "yaml": "yaml",
        "yml": "yaml", "cpp": "cpp", "c": "c", "java": "java",
        "go": "go", "rs": "rust", "rb": "ruby", "php": "php",
    }
    lang  = lang_map.get(ext, "text")
    lines = content.split("\n")
    return {
        "filename": filename,
        "language": lang,
        "lines": len(lines),
        "content": content,
        "display": f"--- {filename} ({len(lines)} lines, {lang}) ---\n\n{content}\n\n--- end of {filename} ---"
    }

def get_file(repo, path, branch="main", token=None):
    url  = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    data = _make_request(url, token)
    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error")}
    if isinstance(data, list):
        return {"success": False, "error": f"'{path}' is a directory — use action=list_repo to browse."}
    if "content" not in data:
        return {"success": False, "error": "No content in response."}
    try:
        raw = base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"Could not decode: {e}"}
    formatted = _format_code(raw, data.get("name", path.split("/")[-1]))
    return {"success": True, "repo": repo, "path": path, "branch": branch,
            "sha": data.get("sha",""), "github_url": data.get("html_url",""), **formatted}

def list_repo(repo, path="", branch="main", token=None):
    url  = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    data = _make_request(url, token)
    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error")}
    if not isinstance(data, list):
        return {"success": False, "error": "Expected a directory listing."}
    items = [{"name": i.get("name"), "type": i.get("type"),
              "path": i.get("path"), "size": i.get("size",0)} for i in data]
    files = [i for i in items if i["type"] == "file"]
    dirs  = [i for i in items if i["type"] == "dir"]
    display = f"--- {repo}/{path or ''} ({branch}) ---\n\n"
    if dirs:
        display += "Folders:\n" + "".join(f"  [{d['name']}/]\n" for d in dirs) + "\n"
    if files:
        display += "Files:\n"
        for f in files:
            size = f"{round(f['size']/1024,1)}kb" if f["size"] > 1024 else f"{f['size']}b"
            display += f"  {f['name']} ({size})\n"
    display += f"\n--- {len(items)} items total ---"
    return {"success": True, "repo": repo, "path": path, "branch": branch,
            "total": len(items), "files": files, "dirs": dirs, "display": display}

def get_repo_info(repo, token=None):
    url  = f"https://api.github.com/repos/{repo}"
    data = _make_request(url, token)
    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data.get("message", "Unknown error")}
    return {
        "success": True, "repo": repo,
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "default_branch": data.get("default_branch", "main"),
        "private": data.get("private", False),
        "topics": data.get("topics", []),
        "updated_at": data.get("updated_at"),
        "display": (
            f"--- Repository: {data.get('full_name')} ---\n"
            f"Description : {data.get('description') or 'none'}\n"
            f"Language    : {data.get('language') or 'unknown'}\n"
            f"Stars       : {data.get('stargazers_count', 0)}\n"
            f"Forks       : {data.get('forks_count', 0)}\n"
            f"Branch      : {data.get('default_branch', 'main')}\n"
            f"Updated     : {data.get('updated_at', 'unknown')}\n"
            f"--- end ---"
        )
    }

def github_get_code(repo, path=None, branch="main", action=None):
    token = _load_token()
    repo  = _resolve_repo(repo)
    if not repo:
        return {"success": False, "error": "repo is required."}
    if action is None:
        action = "list_repo" if not path else "get_file"
    if action == "get_file":
        if not path:
            return {"success": False, "error": "path is required for get_file."}
        return get_file(repo, path, branch, token)
    elif action == "list_repo":
        return list_repo(repo, path or "", branch, token)
    elif action == "repo_info":
        return get_repo_info(repo, token)
    else:
        return {"success": False, "error": f"Unknown action '{action}'. Use: get_file, list_repo, repo_info"}

def run(args=None):
    """Boot.py tool runner entry point."""
    if args is None:
        args = {}
    if isinstance(args, list):
        d = {}
        if len(args) > 0: d["repo"]   = args[0]
        if len(args) > 1: d["path"]   = args[1]
        if len(args) > 2: d["branch"] = args[2]
        if len(args) > 3: d["action"] = args[3]
        args = d
    result = github_get_code(
        repo   = args.get("repo", ""),
        path   = args.get("path", None),
        branch = args.get("branch", "main"),
        action = args.get("action", None),
    )
    if result.get("success"):
        return result.get("display", str(result))
    return f"[github_get_code] {result.get('error', 'unknown error')}"

if __name__ == "__main__":
    print(run({"repo": "Handwritten-Digit-Recognition", "action": "list_repo"}))