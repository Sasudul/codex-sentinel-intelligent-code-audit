from django.contrib import admin
from .models import Repository, PullRequest, CodeReview, Comment, AnalysisRule

@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'github_id', 'created_at')
    search_fields = ('owner', 'name', 'github_id')

@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ('repository', 'pr_number', 'title', 'state', 'author', 'created_at')
    list_filter = ('state', 'repository')
    search_fields = ('title', 'author', 'pr_number')

@admin.register(CodeReview)
class CodeReviewAdmin(admin.ModelAdmin):
    list_display = ('pull_request', 'status', 'overall_score', 'created_at')
    list_filter = ('status',)
    search_fields = ('pull_request__pr_number', 'commit_sha')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('code_review', 'file_path', 'line_number', 'severity', 'category')
    list_filter = ('severity', 'category')
    search_fields = ('file_path', 'comment_text')

@admin.register(AnalysisRule)
class AnalysisRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_type', 'is_active')
    list_filter = ('rule_type', 'is_active')
    search_fields = ('name', 'description')
