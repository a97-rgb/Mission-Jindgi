# DESCRIPTION: Fetch all repos and their stats from Ayush's GitHub account
# USAGE: github_read

import os
import json
import sys
import requests

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

def fetch_repos(username, token):
    headers = get_headers(token)
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&sort=updated"
        r   = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"API error {r.status_code}: {r.text[:200]}"
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos, None

def run(args):
    config   = load_config()
    token    = config.get("ayush_token", "")
    username = config.get("ayush_username", "Ayush442842q")

    if not token:
        return "[github_read] ayush_token not found in github_config.json"

    repos, err = fetch_repos(username, token)
    if err:
        return f"[github_read] {err}"
    if not repos:
        return f"[github_read] no repos found for {username}"

    lines = [f"repos for {username} ({len(repos)} total)\n"]
    for repo in repos:
        name      = repo.get("name", "")
        desc      = repo.get("description") or "NO DESCRIPTION"
        stars     = repo.get("stargazers_count", 0)
        topics    = repo.get("topics", [])
        updated   = repo.get("updated_at", "")[:10]
        is_fork   = repo.get("fork", False)
        lang      = repo.get("language") or "unknown"
        topic_str = ", ".join(topics) if topics else "NO TOPICS"
        fork_str  = " [fork]" if is_fork else ""
        lines.append(
            f"  {name}{fork_str}\n"
            f"    stars   : {stars}\n"
            f"    lang    : {lang}\n"
            f"    desc    : {desc}\n"
            f"    topics  : {topic_str}\n"
            f"    updated : {updated}\n"
        )
    return "\n".join(lines)

if __name__ == "__main__":
    print(run(sys.argv[1:]))
