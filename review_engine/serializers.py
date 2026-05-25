from rest_framework import serializers
from .models import Repository, PullRequest, CodeReview, Comment


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            'id', 'file_path', 'line_number', 'comment_text',
            'severity', 'category', 'github_comment_id', 'created_at',
        ]


class CodeReviewSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = CodeReview
        fields = [
            'id', 'commit_sha', 'status', 'overall_score',
            'summary', 'created_at', 'completed_at',
            'comment_count', 'comments',
        ]

    def get_comment_count(self, obj):
        return obj.comments.count()


class PullRequestSerializer(serializers.ModelSerializer):
    latest_review = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = PullRequest
        fields = [
            'id', 'pr_number', 'title', 'state', 'author',
            'created_at', 'updated_at', 'review_count', 'latest_review',
        ]

    def get_latest_review(self, obj):
        review = obj.reviews.order_by('-created_at').first()
        if review:
            return CodeReviewSerializer(review, context=self.context).data
        return None

    def get_review_count(self, obj):
        return obj.reviews.count()


class RepositorySerializer(serializers.ModelSerializer):
    pr_count = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = ['id', 'github_id', 'owner', 'name', 'created_at', 'pr_count']

    def get_pr_count(self, obj):
        return obj.pull_requests.count()
