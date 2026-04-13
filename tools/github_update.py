# DESCRIPTION: Update a repo's description, topics, or README via GitHub API
# USAGE: github_update <repo_name> <what> <value>

import os
import json
import sys
import requests
import base64

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, "github_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def update_description(owner, repo, description, token):
    url  = f"https://api.github.com/repos/{owner}/{repo}"
    r    = requests.patch(
        url,
        headers=get_headers(token),
        json={"description": description},
        timeout=15,
    )
    if r.status_code == 200:
        return f"description updated for {repo}"
    return f"failed to update description: {r.status_code} {r.text[:200]}"


def update_topics(owner, repo, topics, token):
    """topics should be a list of strings"""
    url  = f"https://api.github.com/repos/{owner}/{repo}/topics"
    headers = get_headers(token)
    headers["Accept"] = "application/vnd.github.mercy-preview+json"
    r    = requests.put(
        url,
        headers=headers,
        json={"names": topics},
        timeout=15,
    )
    if r.status_code == 200:
        return f"topics updated for {repo}: {', '.join(topics)}"
    return f"failed to update topics: {r.status_code} {r.text[:200]}"


def update_readme(owner, repo, content, token, message=None):
    """
    Creates or updates README.md in the repo.
    content = full markdown string
    """
    headers  = get_headers(token)
    url      = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"

    # check if README exists to get its sha
    r_get    = requests.get(url, headers=headers, timeout=15)
    sha      = None
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")

    encoded  = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload  = {
        "message": message or f"docs: improve README for {repo}",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    r_put = requests.put(url, headers=headers, json=payload, timeout=15)
    if r_put.status_code in (200, 201):
        action = "updated" if sha else "created"
        return f"README {action} for {repo}"
    return f"failed to update README: {r_put.status_code} {r_put.text[:200]}"


def run(args):
    """
    Usage from Rajesh:
      github_update <repo> description <text>
      github_update <repo> topics <tag1,tag2,tag3>
      github_update <repo> readme <markdown_text>
    """
    config   = load_config()
    token    = config.get("token", "")
    owner    = "Ayush442842q"

    if not token:
        return "[github_update] no token in github_config.json"

    if len(args) < 3:
        return "[github_update] usage: github_update <repo> <description|topics|readme> <value>"

    repo  = args[0]
    what  = args[1].lower()
    value = " ".join(args[2:])

    if what == "description":
        return update_description(owner, repo, value, token)

    elif what == "topics":
        topics = [t.strip().lower() for t in value.split(",") if t.strip()]
        return update_topics(owner, repo, topics, token)

    elif what == "readme":
        return update_readme(owner, repo, value, token)

    else:
        return f"[github_update] unknown action '{what}' — use description, topics, or readme"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
