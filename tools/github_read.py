# DESCRIPTION: Fetch all repos and their stats from GitHub API
# USAGE: github_read [username]

import os
import json
import sys
import requests

BASE          = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(BASE, "github_config.json")


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


def fetch_repos(username, token):
    headers = get_headers(token)
    repos   = []
    page    = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&sort=updated"
        r   = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"[github_read] API error {r.status_code}: {r.text[:200]}")
            break
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def fetch_readme(owner, repo_name, token):
    headers = get_headers(token)
    url     = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
    r       = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        import base64
        content = r.json().get("content", "")
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return ""


def run(args):
    config   = load_config()
    token    = config.get("token", "")
    username = args[0] if args else config.get("username", "Ayush442842q")

    if not token:
        return "[github_read] no token found in github_config.json"

    repos = fetch_repos(username, token)
    if not repos:
        return f"[github_read] no repos found for {username}"

    lines = [f"repos for {username} ({len(repos)} total)\n"]
    for repo in repos:
        name        = repo.get("name", "")
        desc        = repo.get("description") or "NO DESCRIPTION"
        stars       = repo.get("stargazers_count", 0)
        topics      = repo.get("topics", [])
        updated     = repo.get("updated_at", "")[:10]
        is_fork     = repo.get("fork", False)
        lang        = repo.get("language") or "unknown"

        topic_str   = ", ".join(topics) if topics else "NO TOPICS"
        fork_str    = " [fork]" if is_fork else ""

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
