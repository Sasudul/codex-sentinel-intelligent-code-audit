"""
Code quality scoring engine.
Computes a weighted score from static, security, and AI findings.
"""
from django.utils import timezone


WEIGHT_SECURITY = 0.40   # Security issues are most critical
WEIGHT_COMPLEXITY = 0.25  # Complexity / maintainability
WEIGHT_STYLE = 0.20       # Style / linting
WEIGHT_AI = 0.15          # AI-identified issues

PENALTY_ERROR = 10
PENALTY_WARNING = 3
PENALTY_INFO = 1


def _penalty(comments, category_filter):
    total = 0
    for c in comments:
        if c.category in category_filter:
            if c.severity == 'error':
                total += PENALTY_ERROR
            elif c.severity == 'warning':
                total += PENALTY_WARNING
            else:
                total += PENALTY_INFO
    return total


def compute_score(code_review, comments):
    """
    Computes an overall quality score (0–100) and saves it to code_review.
    Higher is better. Each penalty point reduces the score in proportion to its weight.
    """
    security_penalty = _penalty(comments, ['security'])
    complexity_penalty = _penalty(comments, ['complexity'])
    style_penalty = _penalty(comments, ['style'])
    ai_penalty = _penalty(comments, ['ai_suggestion'])

    # Convert penalties to 0-100 sub-scores (cap penalty effect at 100)
    def sub_score(penalty):
        return max(0.0, 100.0 - penalty)

    weighted = (
        WEIGHT_SECURITY * sub_score(security_penalty) +
        WEIGHT_COMPLEXITY * sub_score(complexity_penalty) +
        WEIGHT_STYLE * sub_score(style_penalty) +
        WEIGHT_AI * sub_score(ai_penalty)
    )

    final_score = round(weighted, 1)

    code_review.overall_score = final_score
    code_review.completed_at = timezone.now()
    code_review.save(update_fields=['overall_score', 'completed_at'])

    return final_score
