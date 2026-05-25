"""
AI-Powered Code Review using OpenAI.
Sends a condensed diff snippet to GPT and parses structured JSON feedback.
"""
import os
import json
from openai import OpenAI
from .models import Comment

# Maximum characters to send to the AI per file to stay within token limits
MAX_DIFF_CHARS = 6000

SYSTEM_PROMPT = """You are an expert senior software engineer performing a code review.
You will receive a code diff (unified diff format) for a pull request.
Your job is to identify:
1. Bugs and potential runtime errors
2. Anti-patterns and bad practices
3. Performance issues
4. Security vulnerabilities
5. Readability and maintainability improvements

Respond ONLY with a valid JSON array. Each element must have:
- "file": the file path (string, use the path from the diff)
- "line": the approximate line number in the new file (integer, use 1 if unknown)
- "severity": one of "info", "warning", "error"
- "message": a clear, actionable explanation of the issue (string)

If there are no issues, return an empty array: []
Do not include any text outside the JSON array."""


def get_openai_client():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def run_ai_review(code_review, diff_text, changed_files):
    """
    Sends PR diff to OpenAI and saves AI-generated comments to the DB.
    Skips gracefully if OPENAI_API_KEY is not configured.
    """
    client = get_openai_client()
    if not client:
        Comment.objects.create(
            code_review=code_review,
            file_path='N/A',
            line_number=None,
            comment_text='AI review skipped: OPENAI_API_KEY is not configured.',
            severity='info',
            category='ai_suggestion'
        )
        return

    # Truncate diff to avoid exceeding context window
    diff_snippet = diff_text[:MAX_DIFF_CHARS]
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_snippet += "\n... (diff truncated for brevity)"

    user_prompt = f"""Please review the following pull request diff:\n\n```diff\n{diff_snippet}\n```"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        # The response_format forces JSON object output; we wrap it if needed
        parsed = json.loads(raw_content)

        # The AI might return {"issues": [...]} or just an array; normalise
        if isinstance(parsed, list):
            issues = parsed
        elif isinstance(parsed, dict):
            # Try common wrapper keys
            issues = parsed.get('issues') or parsed.get('comments') or parsed.get('results') or []
        else:
            issues = []

        valid_files = set(changed_files.keys())

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            file_path = issue.get('file', 'N/A')
            line_num = issue.get('line')
            severity = issue.get('severity', 'info')
            message = issue.get('message', '')

            if not message:
                continue

            # Validate severity
            if severity not in ('info', 'warning', 'error'):
                severity = 'info'

            # Only accept comments on files actually changed in the PR
            if file_path not in valid_files and file_path != 'N/A':
                # Try stripping leading slashes
                stripped = file_path.lstrip('/')
                if stripped in valid_files:
                    file_path = stripped
                else:
                    file_path = list(valid_files)[0] if valid_files else 'N/A'

            Comment.objects.create(
                code_review=code_review,
                file_path=file_path,
                line_number=line_num,
                comment_text=f"🤖 AI Review: {message}",
                severity=severity,
                category='ai_suggestion'
            )

    except json.JSONDecodeError as e:
        Comment.objects.create(
            code_review=code_review,
            file_path='N/A',
            line_number=None,
            comment_text=f'AI review error: Failed to parse response — {str(e)}',
            severity='info',
            category='ai_suggestion'
        )
    except Exception as e:
        Comment.objects.create(
            code_review=code_review,
            file_path='N/A',
            line_number=None,
            comment_text=f'AI review error: {str(e)}',
            severity='info',
            category='ai_suggestion'
        )
