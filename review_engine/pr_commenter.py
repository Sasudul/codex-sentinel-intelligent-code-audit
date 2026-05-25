"""
GitHub PR Commenting service.
Posts inline review comments and a summary comment back to the PR.
"""
import os
import requests
from django.conf import settings


def _get_headers():
    token = getattr(settings, 'GITHUB_API_TOKEN', os.getenv('GITHUB_API_TOKEN'))
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def post_pr_summary_comment(repo_full_name, pr_number, summary_text):
    """
    Posts a general (non-inline) comment on the PR issues thread.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    payload = {"body": summary_text}
    response = requests.post(url, json=payload, headers=_get_headers())
    return response.status_code in (200, 201)


def post_pr_review_with_comments(repo_full_name, pr_number, commit_sha, inline_comments, summary_body):
    """
    Posts a PR review with inline comments via the GitHub Reviews API.
    Falls back to issue comments if review API fails.

    inline_comments: list of dicts with keys: path, line, body
    """
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews"

    review_comments = []
    for c in inline_comments:
        if c.get('path') and c.get('line') and c.get('body'):
            review_comments.append({
                "path": c['path'],
                "line": int(c['line']),
                "side": "RIGHT",
                "body": c['body'],
            })

    payload = {
        "commit_id": commit_sha,
        "body": summary_body,
        "event": "COMMENT",  # APPROVE / REQUEST_CHANGES / COMMENT
        "comments": review_comments,
    }

    response = requests.post(url, json=payload, headers=_get_headers())

    if response.status_code in (200, 201):
        data = response.json()
        return True, data.get('id')

    # Fallback: post just the summary as an issue comment
    post_pr_summary_comment(repo_full_name, pr_number, summary_body)
    return False, None


def build_summary_markdown(code_review, comments):
    """
    Builds a nicely formatted Markdown summary for the PR comment.
    """
    score = code_review.overall_score or 0
    status_emoji = "✅" if score >= 80 else "⚠️" if score >= 50 else "❌"

    security = [c for c in comments if c.category == 'security']
    style = [c for c in comments if c.category in ('style', 'complexity')]
    ai_suggestions = [c for c in comments if c.category == 'ai_suggestion']

    lines = [
        f"## {status_emoji} Codex Sentinel Code Review",
        f"",
        f"**Overall Score:** `{score:.1f} / 100`",
        f"",
        f"| Category | Count |",
        f"|---|---|",
        f"| 🔐 Security Issues | {len(security)} |",
        f"| 🔍 Style / Complexity | {len(style)} |",
        f"| 🤖 AI Suggestions | {len(ai_suggestions)} |",
        f"",
    ]

    if security:
        lines.append("### 🔐 Security Issues")
        for c in security[:5]:
            lines.append(f"- **{c.file_path}:{c.line_number}** — {c.comment_text}")
        lines.append("")

    if ai_suggestions:
        lines.append("### 🤖 AI Suggestions")
        for c in ai_suggestions[:5]:
            lines.append(f"- **{c.file_path}:{c.line_number}** — {c.comment_text}")
        lines.append("")

    lines.append("---")
    lines.append("*Automated review by [Codex Sentinel](https://github.com)*")

    return "\n".join(lines)
