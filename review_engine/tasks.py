"""
Celery tasks for Codex Sentinel.
process_pull_request_review orchestrates the full review pipeline:
  1. Fetch GitHub diff
  2. Static analysis (Flake8 + complexity)
  3. Security scan (regex secret detection)
  4. AI-powered review (OpenAI)
  5. Score computation
  6. Post comments back to GitHub PR
"""
from celery import shared_task
from django.utils import timezone

from .models import CodeReview
from .github_service import fetch_pr_diff
from .static_analyzer import run_static_analysis, parse_diff, fetch_file_content
from .security_analyzer import run_security_analysis
from .ai_reviewer import run_ai_review
from .scorer import compute_score
from .pr_commenter import post_pr_review_with_comments, build_summary_markdown


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_pull_request_review(self, code_review_id, repo_full_name, pr_number):
    """
    Full review pipeline for a single PR commit.
    """
    try:
        code_review = CodeReview.objects.get(id=code_review_id)
    except CodeReview.DoesNotExist:
        print(f"[Codex Sentinel] CodeReview {code_review_id} not found. Aborting.")
        return

    try:
        code_review.status = 'in_progress'
        code_review.save(update_fields=['status'])

        commit_sha = code_review.commit_sha

        # ── Step 1: Fetch Diff ────────────────────────────────────────────────
        diff_text = fetch_pr_diff(repo_full_name, pr_number)
        if not diff_text:
            code_review.summary = "Failed to fetch PR diff. Verify GITHUB_API_TOKEN and repo access."
            code_review.status = 'failed'
            code_review.save(update_fields=['summary', 'status'])
            return

        changed_files = parse_diff(diff_text)

        def fetch_content_fn(file_path):
            return fetch_file_content(repo_full_name, commit_sha, file_path)

        # ── Step 2: Static Analysis ───────────────────────────────────────────
        run_static_analysis(code_review, repo_full_name, commit_sha, diff_text)

        # ── Step 3: Security Scan ─────────────────────────────────────────────
        run_security_analysis(code_review, changed_files, fetch_content_fn)

        # ── Step 4: AI Review ─────────────────────────────────────────────────
        run_ai_review(code_review, diff_text, changed_files)

        # ── Step 5: Score ─────────────────────────────────────────────────────
        all_comments = list(code_review.comments.all())
        score = compute_score(code_review, all_comments)

        # ── Step 6: Build summary & post to GitHub ────────────────────────────
        summary_md = build_summary_markdown(code_review, all_comments)

        inline_comments = [
            {
                'path': c.file_path,
                'line': c.line_number,
                'body': c.comment_text,
            }
            for c in all_comments
            if c.line_number is not None and c.file_path != 'N/A'
        ]

        posted, review_id = post_pr_review_with_comments(
            repo_full_name,
            pr_number,
            commit_sha,
            inline_comments,
            summary_md,
        )

        # ── Finalise ──────────────────────────────────────────────────────────
        code_review.summary = summary_md
        code_review.status = 'completed'
        code_review.completed_at = timezone.now()
        code_review.save(update_fields=['summary', 'status', 'completed_at'])

        print(
            f"[Codex Sentinel] Review complete for PR#{pr_number} in {repo_full_name}. "
            f"Score={score}. Comments={len(all_comments)}. GitHub post={'OK' if posted else 'FAILED'}."
        )

    except Exception as exc:
        print(f"[Codex Sentinel] Pipeline error for CodeReview {code_review_id}: {exc}")
        try:
            code_review.summary = f"Review pipeline error: {str(exc)}"
            code_review.status = 'failed'
            code_review.save(update_fields=['summary', 'status'])
        except Exception:
            pass
        # Retry with exponential backoff
        raise self.retry(exc=exc)
