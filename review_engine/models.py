from django.db import models

class Repository(models.Model):
    github_id = models.BigIntegerField(unique=True, help_text="GitHub's internal ID for the repository")
    owner = models.CharField(max_length=255, help_text="Owner of the repository (user or organization)")
    name = models.CharField(max_length=255, help_text="Name of the repository")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Repositories"
        unique_together = ('owner', 'name')

    def __str__(self):
        return f"{self.owner}/{self.name}"

class PullRequest(models.Model):
    STATE_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('merged', 'Merged'),
    ]

    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='pull_requests')
    pr_number = models.IntegerField(help_text="The PR number on GitHub")
    title = models.CharField(max_length=512)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='open')
    author = models.CharField(max_length=255, help_text="GitHub username of the PR author")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('repository', 'pr_number')

    def __str__(self):
        return f"PR #{self.pr_number} - {self.title}"

class CodeReview(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE, related_name='reviews')
    commit_sha = models.CharField(max_length=40, help_text="The commit SHA that was reviewed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    overall_score = models.FloatField(null=True, blank=True, help_text="Score out of 100 based on review findings")
    summary = models.TextField(null=True, blank=True, help_text="General summary of the review")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Review for PR #{self.pull_request.pr_number} at {self.commit_sha[:7]}"

class Comment(models.Model):
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    CATEGORY_CHOICES = [
        ('security', 'Security'),
        ('style', 'Style/Linting'),
        ('complexity', 'Complexity'),
        ('bug', 'Potential Bug'),
        ('ai_suggestion', 'AI Suggestion'),
    ]

    code_review = models.ForeignKey(CodeReview, on_delete=models.CASCADE, related_name='comments')
    file_path = models.CharField(max_length=1024, help_text="Path of the file being commented on")
    line_number = models.IntegerField(null=True, blank=True, help_text="Line number in the file (if applicable)")
    comment_text = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='ai_suggestion')
    github_comment_id = models.BigIntegerField(null=True, blank=True, help_text="ID of the comment on GitHub if posted")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.severity.upper()}: {self.file_path} (Line {self.line_number})"

class AnalysisRule(models.Model):
    RULE_TYPE_CHOICES = [
        ('regex', 'Regular Expression (Secrets/Patterns)'),
        ('ai_prompt', 'AI System Prompt Instruction'),
        ('complexity', 'Complexity Threshold'),
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    configuration = models.JSONField(help_text="JSON containing rule specifics (e.g., regex pattern, threshold limit)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"
