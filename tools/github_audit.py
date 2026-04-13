# DESCRIPTION: Audit all repos and score them — flags what needs fixing
# USAGE: github_audit

import os
import json
import sys
import requests
import base64

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, "github_config.json")
LOG_DIR     = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


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
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&sort=updated"
        r   = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
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
        try:
            content = r.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return ""


def score_repo(repo, readme):
    """
    Score a repo out of 100.
    Returns (score, list of issues found)
    """
    score  = 0
    issues = []

    # description (20 pts)
    desc = repo.get("description") or ""
    if desc and len(desc) > 20:
        score += 20
    elif desc:
        score += 10
        issues.append("description is too short — expand it")
    else:
        issues.append("no description — add one immediately")

    # topics (20 pts)
    topics = repo.get("topics", [])
    if len(topics) >= 5:
        score += 20
    elif len(topics) >= 2:
        score += 10
        issues.append(f"only {len(topics)} topics — add more (aim for 5-8)")
    else:
        issues.append("no topics — GitHub search cannot find this repo")

    # README (30 pts)
    if len(readme) > 2000:
        score += 30
    elif len(readme) > 500:
        score += 20
        issues.append("README exists but is thin — expand it")
    elif len(readme) > 0:
        score += 10
        issues.append("README is very short — needs proper content")
    else:
        issues.append("no README — this repo looks abandoned")

    # recent activity (15 pts)
    updated = repo.get("updated_at", "")[:10]
    if updated:
        import datetime
        try:
            last   = datetime.date.fromisoformat(updated)
            today  = datetime.date.today()
            days   = (today - last).days
            if days <= 30:
                score += 15
            elif days <= 90:
                score += 8
                issues.append(f"last updated {days} days ago — add activity")
            else:
                issues.append(f"last updated {days} days ago — looks dead to visitors")
        except Exception:
            pass

    # stars (15 pts — informational only)
    stars = repo.get("stargazers_count", 0)
    if stars >= 10:
        score += 15
    elif stars >= 3:
        score += 8
    elif stars >= 1:
        score += 3

    return score, issues


def run(args):
    config   = load_config()
    token    = config.get("token", "")
    username = args[0] if args else "Ayush442842q"

    if not token:
        return "[github_audit] no token in github_config.json"

    repos = fetch_repos(username, token)
    if not repos:
        return f"[github_audit] no repos found for {username}"

    results = []
    for repo in repos:
        if repo.get("fork"):
            continue
        name   = repo.get("name", "")
        readme = fetch_readme(username, name, token)
        score, issues = score_repo(repo, readme)
        results.append({
            "name":   name,
            "stars":  repo.get("stargazers_count", 0),
            "score":  score,
            "issues": issues,
            "desc":   repo.get("description") or "",
            "topics": repo.get("topics", []),
            "lang":   repo.get("language") or "unknown",
        })

    # sort by score ascending — worst first
    results.sort(key=lambda x: x["score"])

    # save full audit to logs
    audit_path = os.path.join(LOG_DIR, "github_audit.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # build readable report
    lines = [f"GitHub audit — {username} — {len(results)} repos\n"]
    lines.append("─" * 50)

    for r in results:
        bar   = "█" * (r["score"] // 10) + "░" * (10 - r["score"] // 10)
        lines.append(f"\n  {r['name']}")
        lines.append(f"  score  : {r['score']}/100  [{bar}]  ★ {r['stars']}")
        lines.append(f"  lang   : {r['lang']}")
        if r["desc"]:
            lines.append(f"  desc   : {r['desc'][:80]}")
        if r["topics"]:
            lines.append(f"  topics : {', '.join(r['topics'])}")
        if r["issues"]:
            for issue in r["issues"]:
                lines.append(f"  ⚠  {issue}")

    lines.append(f"\n─" * 50)
    lines.append(f"\nfull audit saved to logs/github_audit.json")

    return "\n".join(lines)


if __name__ == "__main__":
    print(run(sys.argv[1:]))
