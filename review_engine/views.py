"""
API views for the Codex Sentinel dashboard and GitHub webhook.
"""
import os
import json
from django.db.models import Avg, Count
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status

from .models import Repository, PullRequest, CodeReview, Comment
from .serializers import RepositorySerializer, PullRequestSerializer, CodeReviewSerializer
from .github_service import verify_github_signature
from .tasks import process_pull_request_review


# ── Webhook ────────────────────────────────────────────────────────────────────

class GitHubWebhookView(APIView):
    """
    POST /api/webhook/github/
    Receives GitHub webhook events, persists the PR, and dispatches Celery task.
    """

    def post(self, request, *args, **kwargs):
        # 1. Verify Signature
        signature_header = request.headers.get('X-Hub-Signature-256')
        secret_token = os.getenv('GITHUB_WEBHOOK_SECRET', '')

        if secret_token:
            if not verify_github_signature(request.body, secret_token, signature_header):
                return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        # 2. Handle event type
        event_type = request.headers.get('X-GitHub-Event', '')

        if event_type == 'ping':
            return Response({'message': 'Pong! Codex Sentinel webhook is active.'}, status=status.HTTP_200_OK)

        if event_type != 'pull_request':
            return Response({'message': f'Event "{event_type}" ignored'}, status=status.HTTP_200_OK)

        # 3. Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        action = payload.get('action')
        if action not in ('opened', 'synchronize', 'reopened'):
            return Response({'message': f'Action "{action}" ignored'}, status=status.HTTP_200_OK)

        # 4. Extract data
        repo_data = payload.get('repository', {})
        pr_data = payload.get('pull_request', {})

        repo_github_id = repo_data.get('id')
        repo_full_name = repo_data.get('full_name')
        repo_owner = repo_data.get('owner', {}).get('login')
        repo_name = repo_data.get('name')

        pr_number = pr_data.get('number')
        pr_title = pr_data.get('title', '')
        pr_author = pr_data.get('user', {}).get('login', '')
        commit_sha = pr_data.get('head', {}).get('sha', '')

        # 5. Persist
        repository, _ = Repository.objects.get_or_create(
            github_id=repo_github_id,
            defaults={'owner': repo_owner, 'name': repo_name},
        )

        pull_request, _ = PullRequest.objects.update_or_create(
            repository=repository,
            pr_number=pr_number,
            defaults={'title': pr_title, 'state': 'open', 'author': pr_author},
        )

        code_review = CodeReview.objects.create(
            pull_request=pull_request,
            commit_sha=commit_sha,
            status='pending',
        )

        # 6. Dispatch async task — respond immediately
        process_pull_request_review.delay(
            code_review_id=code_review.id,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
        )

        return Response(
            {'message': 'Webhook received. Review queued.', 'review_id': code_review.id},
            status=status.HTTP_200_OK,
        )


# ── Dashboard API ──────────────────────────────────────────────────────────────

class RepositoryListView(ListAPIView):
    """GET /api/repositories/"""
    queryset = Repository.objects.annotate(pr_count=Count('pull_requests')).order_by('-created_at')
    serializer_class = RepositorySerializer


class RepositoryDetailView(RetrieveAPIView):
    """GET /api/repositories/<pk>/"""
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer


class PullRequestListView(ListAPIView):
    """GET /api/repositories/<repo_id>/pull-requests/"""
    serializer_class = PullRequestSerializer

    def get_queryset(self):
        repo_id = self.kwargs['repo_id']
        return PullRequest.objects.filter(repository_id=repo_id).order_by('-created_at')


class PullRequestDetailView(RetrieveAPIView):
    """GET /api/pull-requests/<pk>/"""
    queryset = PullRequest.objects.all()
    serializer_class = PullRequestSerializer


class CodeReviewDetailView(RetrieveAPIView):
    """GET /api/reviews/<pk>/"""
    queryset = CodeReview.objects.all()
    serializer_class = CodeReviewSerializer


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/
    Returns aggregate metrics for the desktop app dashboard.
    """

    def get(self, request, *args, **kwargs):
        total_repos = Repository.objects.count()
        total_prs = PullRequest.objects.count()
        total_reviews = CodeReview.objects.count()
        completed_reviews = CodeReview.objects.filter(status='completed')

        avg_score = completed_reviews.aggregate(avg=Avg('overall_score'))['avg'] or 0.0

        security_issues = Comment.objects.filter(category='security').count()
        style_issues = Comment.objects.filter(category__in=['style', 'complexity']).count()
        ai_suggestions = Comment.objects.filter(category='ai_suggestion').count()

        recent_reviews = CodeReview.objects.select_related(
            'pull_request__repository'
        ).order_by('-created_at')[:10]

        recent_data = []
        for r in recent_reviews:
            pr = r.pull_request
            repo = pr.repository
            recent_data.append({
                'review_id': r.id,
                'repo': f"{repo.owner}/{repo.name}",
                'pr_number': pr.pr_number,
                'pr_title': pr.title,
                'status': r.status,
                'score': r.overall_score,
                'created_at': r.created_at.isoformat(),
            })

        return Response({
            'totals': {
                'repositories': total_repos,
                'pull_requests': total_prs,
                'reviews': total_reviews,
            },
            'average_score': round(avg_score, 1),
            'issues': {
                'security': security_issues,
                'style': style_issues,
                'ai_suggestions': ai_suggestions,
            },
            'recent_reviews': recent_data,
        })
