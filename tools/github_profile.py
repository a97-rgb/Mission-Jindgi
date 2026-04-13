# DESCRIPTION: Create or update your GitHub profile README (the one visitors see first)
# USAGE: github_profile

import os
import json
import sys
import requests
import base64
from groq import Groq

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, "github_config.json")
MEMORY_FILE = os.path.join(BASE, "memory.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def get_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def fetch_repos(owner, token):
    headers = get_headers(token)
    r = requests.get(
        f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated",
        headers=headers, timeout=15
    )
    if r.status_code == 200:
        return [repo for repo in r.json() if not repo.get("fork")]
    return []


def profile_repo_exists(owner, token):
    headers = get_headers(token)
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{owner}",
        headers=headers, timeout=15
    )
    return r.status_code == 200


def create_profile_repo(owner, token):
    headers = get_headers(token)
    r = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={
            "name": owner,
            "description": "My GitHub profile",
            "private": False,
            "auto_init": True,
        },
        timeout=15,
    )
    return r.status_code in (200, 201)


def update_file(owner, repo, path, content, message, token):
    headers = get_headers(token)
    url     = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r_get   = requests.get(url, headers=headers, timeout=15)
    sha     = r_get.json().get("sha") if r_get.status_code == 200 else None
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha
    r_put = requests.put(url, headers=headers, json=payload, timeout=15)
    return r_put.status_code in (200, 201)


def generate_profile_readme(client, owner, repos, memory):
    facts   = memory.get("facts_about_ayush", [])
    projects = [
        f"- **[{r['name']}](https://github.com/{owner}/{r['name']})** — {r.get('description') or 'Python project'}"
        for r in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    ]
    projects_str = "\n".join(projects)
    facts_str    = "\n".join(f"- {f}" for f in facts[:8]) if facts else "- Builder. Coder. Automator."

    prompt = f"""Write a professional GitHub profile README.md for a developer named Ayush Singh (username: {owner}).

What we know about Ayush:
{facts_str}

His top projects:
{projects_str}

Requirements:
- Start with a short punchy bio (2-3 sentences max)
- Show his top projects as a table or list with links
- Include a skills/tech section (Python, AI, Automation based on his projects)
- Add GitHub stats badge: ![GitHub stats](https://github-readme-stats.vercel.app/api?username={owner}&show_icons=true&theme=dark)
- Add a "currently building" section mentioning an AI agent project
- Keep it clean, modern, not over-decorated
- Pure markdown only — no HTML blocks
- Under 60 lines total
- Do not use placeholder text like [Your Name] — use real values only
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    return r.choices[0].message.content.strip()


def run(args):
    config  = load_config()
    token   = config.get("token", "")
    owner   = "Ayush442842q"
    api_key = os.environ.get("GROQ_API_KEY", "")

    if not token:
        return "[github_profile] no token in github_config.json"
    if not api_key:
        return "[github_profile] GROQ_API_KEY not set"

    client = Groq(api_key=api_key)
    memory = load_json(MEMORY_FILE, {})
    repos  = fetch_repos(owner, token)

    # create the special profile repo if it doesn't exist
    if not profile_repo_exists(owner, token):
        print(f"[github_profile] creating profile repo {owner}/{owner}...")
        created = create_profile_repo(owner, token)
        if not created:
            return f"[github_profile] could not create profile repo — create {owner}/{owner} manually on GitHub first"

    print("[github_profile] generating README with Groq...")
    readme = generate_profile_readme(client, owner, repos, memory)

    ok = update_file(
        owner, owner, "README.md", readme,
        "profile: Rajesh updated my GitHub profile README",
        token,
    )

    if ok:
        return f"profile README updated at github.com/{owner}\n\n--- preview ---\n{readme[:400]}..."
    return "[github_profile] failed to push README — check token permissions"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
