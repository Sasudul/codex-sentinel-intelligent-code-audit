from django.urls import path
from .views import (
    GitHubWebhookView,
    RepositoryListView,
    RepositoryDetailView,
    PullRequestListView,
    PullRequestDetailView,
    CodeReviewDetailView,
    DashboardStatsView,
)

urlpatterns = [
    # Webhook
    path('webhook/github/', GitHubWebhookView.as_view(), name='github_webhook'),

    # Dashboard API
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('repositories/', RepositoryListView.as_view(), name='repository_list'),
    path('repositories/<int:pk>/', RepositoryDetailView.as_view(), name='repository_detail'),
    path('repositories/<int:repo_id>/pull-requests/', PullRequestListView.as_view(), name='pr_list'),
    path('pull-requests/<int:pk>/', PullRequestDetailView.as_view(), name='pr_detail'),
    path('reviews/<int:pk>/', CodeReviewDetailView.as_view(), name='review_detail'),
]
