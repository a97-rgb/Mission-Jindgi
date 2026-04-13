# DESCRIPTION: Create or update the Ayush442842q GitHub profile README using Groq
# USAGE: github_profile

import os
import json
import sys
import requests
import base64
from groq import Groq

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

def load_memory():
    base        = get_agent_base()
    memory_file = os.path.join(base, "memory.json")
    if os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

def fetch_repos(owner, token):
    r = requests.get(
        f"https://api.github.com/users/{owner}/repos?per_page=100&sort=stars",
        headers=get_headers(token), timeout=15
    )
    if r.status_code == 200:
        return [repo for repo in r.json() if not repo.get("fork")]
    return []

def profile_repo_exists(owner, token):
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{owner}",
        headers=get_headers(token), timeout=15
    )
    return r.status_code == 200

def create_profile_repo(owner, token):
    r = requests.post(
        "https://api.github.com/user/repos",
        headers=get_headers(token),
        json={"name": owner, "description": "My GitHub profile", "private": False, "auto_init": True},
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
    facts    = memory.get("facts_about_ayush", [])
    projects = [
        f"| [{r['name']}](https://github.com/{owner}/{r['name']}) | {r.get('description') or 'Python project'} | {r.get('language','Python')} | ★ {r.get('stargazers_count',0)} |"
        for r in repos[:6]
    ]
    projects_str = "\n".join(projects)
    facts_str    = "\n".join(f"- {f}" for f in facts[:6]) if facts else "- Builder. Coder. Automator."

    prompt = f"""Write a professional GitHub profile README.md for a developer named Ayush Singh (username: {owner}).

Known facts about Ayush:
{facts_str}

Top projects:
{projects_str}

Requirements:
- Short punchy opening bio — 2 sentences max, first person
- Projects table with columns: Project | Description | Language | Stars
- Skills section — Python, AI/ML, Automation, Computer Vision based on his work
- GitHub stats: ![stats](https://github-readme-stats.vercel.app/api?username={owner}&show_icons=true&theme=dark&hide_border=true)
- One line about what he is currently building (mention an AI agent that manages his GitHub)
- Clean, modern — no excessive emojis, no generic filler text
- Pure markdown only
- Under 60 lines
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    return r.choices[0].message.content.strip()

def run(args=None):
    config  = load_config()
    token   = config.get("ayush_token", "")
    owner   = config.get("ayush_username", "Ayush442842q")
    api_key = os.environ.get("GROQ_API_KEY", "")

    if not token:
        return "[github_profile] ayush_token not found in github_config.json"
    if not api_key:
        return "[github_profile] GROQ_API_KEY not set"

    client = Groq(api_key=api_key.strip())
    memory = load_memory()
    repos  = fetch_repos(owner, token)

    if not profile_repo_exists(owner, token):
        print(f"[github_profile] creating profile repo {owner}/{owner}...")
        if not create_profile_repo(owner, token):
            return f"[github_profile] could not create profile repo — create {owner}/{owner} manually on GitHub first"

    print("[github_profile] generating README with Groq...")
    readme = generate_profile_readme(client, owner, repos, memory)

    ok = update_file(
        owner, owner, "README.md", readme,
        "profile: Rajesh updated the profile README",
        token,
    )

    if ok:
        return f"profile README updated at github.com/{owner}\n\n--- preview (first 400 chars) ---\n{readme[:400]}..."
    return "[github_profile] failed to push README — check token has repo + user permissions"

if __name__ == "__main__":
    print(run(sys.argv[1:]))
