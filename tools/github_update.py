# DESCRIPTION: Update a repo's description, topics, or README on Ayush's GitHub
# USAGE: github_update <repo_name> <description|topics|readme> <value>

import os
import json
import sys
import requests
import base64

def get_agent_base():
    this_file = os.path.abspath(__file__)
    tools_dir = os.path.dirname(this_file)
    return os.environ.get("AGENT_BASE", os.path.dirname(tools_dir))

def load_config():
    base        = get_agent_base()
    config_file = os.path.join(base, "github_config.json")
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

def update_description(owner, repo, description, token):
    r = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=get_headers(token),
        json={"description": description},
        timeout=15,
    )
    if r.status_code == 200:
        return f"description updated for {repo}"
    return f"failed: {r.status_code} {r.text[:200]}"

def update_topics(owner, repo, topics, token):
    headers = get_headers(token)
    headers["Accept"] = "application/vnd.github.mercy-preview+json"
    r = requests.put(
        f"https://api.github.com/repos/{owner}/{repo}/topics",
        headers=headers,
        json={"names": topics},
        timeout=15,
    )
    if r.status_code == 200:
        return f"topics updated for {repo}: {', '.join(topics)}"
    return f"failed: {r.status_code} {r.text[:200]}"

def update_readme(owner, repo, content, token, message=None):
    headers = get_headers(token)
    url     = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    r_get   = requests.get(url, headers=headers, timeout=15)
    sha     = r_get.json().get("sha") if r_get.status_code == 200 else None
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": message or f"docs: improve README for {repo}", "content": encoded}
    if sha:
        payload["sha"] = sha
    r_put = requests.put(url, headers=headers, json=payload, timeout=15)
    if r_put.status_code in (200, 201):
        return f"README {'updated' if sha else 'created'} for {repo}"
    return f"failed: {r_put.status_code} {r_put.text[:200]}"

def run(args):
    config   = load_config()
    token    = config.get("ayush_token", "")
    owner    = config.get("ayush_username", "Ayush442842q")

    if not token:
        return "[github_update] ayush_token not found in github_config.json"

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
