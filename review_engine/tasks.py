from celery import shared_task
from .models import CodeReview
from .github_service import fetch_pr_diff
from .static_analyzer import run_static_analysis, parse_diff, fetch_file_content
from .security_analyzer import run_security_analysis

@shared_task
def process_pull_request_review(code_review_id, repo_full_name, pr_number):
    try:
        code_review = CodeReview.objects.get(id=code_review_id)
        code_review.status = 'in_progress'
        code_review.save()

        # Step 1: Fetch Diff
        diff_text = fetch_pr_diff(repo_full_name, pr_number)
        if not diff_text:
            code_review.summary = "Failed to fetch diff. Check API token or repository access."
            code_review.status = 'failed'
            code_review.save()
            return
            
        # Step 5: Static Analysis
        commit_sha = code_review.commit_sha
        run_static_analysis(code_review, repo_full_name, commit_sha, diff_text)
        
        # Step 6: Security Analysis
        changed_files = parse_diff(diff_text)
        
        def fetch_content_fn(file_path):
            return fetch_file_content(repo_full_name, commit_sha, file_path)
            
        run_security_analysis(code_review, changed_files, fetch_content_fn)
        
        # Placeholders for future steps (AI)
        # We will integrate these in Step 7
        
        code_review.summary = f"Diff fetched successfully. {len(diff_text.splitlines())} lines found."
        code_review.status = 'completed'
        code_review.overall_score = 100.0  # Placeholder score
        code_review.save()
        
    except CodeReview.DoesNotExist:
        print(f"CodeReview with id {code_review_id} not found.")
    except Exception as e:
        print(f"Error processing PR review: {str(e)}")
        # If we have the object, mark it failed
        try:
            code_review.summary = f"Error processing review: {str(e)}"
            code_review.status = 'failed'
            code_review.save()
        except:
            pass
