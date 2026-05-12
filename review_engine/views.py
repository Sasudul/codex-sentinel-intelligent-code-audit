import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Repository, PullRequest, CodeReview
from .github_service import verify_github_signature, fetch_pr_diff

class GitHubWebhookView(APIView):
    """
    Endpoint to receive GitHub webhook events.
    """
    
    def post(self, request, *args, **kwargs):
        # 1. Verify Signature
        signature_header = request.headers.get('X-Hub-Signature-256')
        secret_token = os.getenv('GITHUB_WEBHOOK_SECRET', '')
        
        if secret_token:
            is_valid = verify_github_signature(request.body, secret_token, signature_header)
            if not is_valid:
                return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)
        
        # 2. Parse Payload
        event_type = request.headers.get('X-GitHub-Event')
        
        if event_type == 'ping':
            return Response({'message': 'Pong! Webhook is working.'}, status=status.HTTP_200_OK)
            
        if event_type != 'pull_request':
            # We only care about PR events for now
            return Response({'message': 'Event ignored'}, status=status.HTTP_200_OK)
            
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON payload'}, status=status.HTTP_400_BAD_REQUEST)
            
        action = payload.get('action')
        if action not in ['opened', 'synchronize', 'reopened']:
            return Response({'message': f'Action {action} ignored'}, status=status.HTTP_200_OK)
            
        # 3. Extract PR Information
        repo_data = payload.get('repository', {})
        pr_data = payload.get('pull_request', {})
        
        repo_github_id = repo_data.get('id')
        repo_full_name = repo_data.get('full_name')  # e.g. "owner/name"
        repo_owner = repo_data.get('owner', {}).get('login')
        repo_name = repo_data.get('name')
        
        pr_number = pr_data.get('number')
        pr_title = pr_data.get('title')
        pr_author = pr_data.get('user', {}).get('login')
        commit_sha = pr_data.get('head', {}).get('sha')
        
        # 4. Save to Database
        # Ensure repository exists
        repository, _ = Repository.objects.get_or_create(
            github_id=repo_github_id,
            defaults={
                'owner': repo_owner,
                'name': repo_name,
            }
        )
        
        # Ensure PR exists
        pull_request, _ = PullRequest.objects.update_or_create(
            repository=repository,
            pr_number=pr_number,
            defaults={
                'title': pr_title,
                'state': 'open',
                'author': pr_author,
            }
        )
        
        # Create a new CodeReview entry
        code_review = CodeReview.objects.create(
            pull_request=pull_request,
            commit_sha=commit_sha,
            status='pending'
        )
        
        # In Step 4, we will trigger a Celery task here.
        # For now, we will just fetch the diff directly as a placeholder to prove it works.
        diff_text = fetch_pr_diff(repo_full_name, pr_number)
        if diff_text:
            code_review.summary = f"Fetched diff successfully. Lines: {len(diff_text.splitlines())}"
            code_review.status = 'completed'
        else:
            code_review.summary = "Failed to fetch diff. Check API token."
            code_review.status = 'failed'
            
        code_review.save()
        
        return Response({'message': 'Webhook processed successfully'}, status=status.HTTP_200_OK)
