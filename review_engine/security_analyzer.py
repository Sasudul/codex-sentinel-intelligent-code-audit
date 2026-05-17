import re
from .models import Comment

# Common patterns for hardcoded secrets
SECRET_PATTERNS = [
    {
        'name': 'Generic API Key / Secret',
        'regex': re.compile(r'(?i)(api_key|apikey|secret|token|password|auth)[\s]*[=:]\s*[\'"][a-zA-Z0-9_\-]{16,}[\'"]'),
        'severity': 'error'
    },
    {
        'name': 'AWS Access Key ID',
        'regex': re.compile(r'AKIA[0-9A-Z]{16}'),
        'severity': 'error'
    },
    {
        'name': 'GitHub Personal Access Token',
        'regex': re.compile(r'(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}'),
        'severity': 'error'
    },
    {
        'name': 'JWT Token',
        'regex': re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'),
        'severity': 'error'
    }
]

def scan_for_secrets(file_content):
    """
    Scans the given file content for hardcoded secrets using regex patterns.
    Returns a list of dicts with issue details.
    """
    issues = []
    lines = file_content.splitlines()
    
    for i, line in enumerate(lines):
        line_num = i + 1
        # Skip very long lines to avoid regex performance issues (e.g. minified files)
        if len(line) > 1000:
            continue
            
        for pattern in SECRET_PATTERNS:
            if pattern['regex'].search(line):
                issues.append({
                    'line': line_num,
                    'message': f"Security Warning: Potential {pattern['name']} hardcoded in source.",
                    'severity': pattern['severity']
                })
                
    return issues

def run_security_analysis(code_review, changed_files, fetch_content_fn):
    """
    Runs security analysis on the modified files in the diff.
    Creates Comment objects for any findings on modified lines.
    """
    for file_path, modified_lines in changed_files.items():
        # Security scan applies to almost all file types, unlike flake8
        content = fetch_content_fn(file_path)
        if not content:
            continue
            
        issues = scan_for_secrets(content)
        
        for issue in issues:
            if issue['line'] in modified_lines:
                Comment.objects.create(
                    code_review=code_review,
                    file_path=file_path,
                    line_number=issue['line'],
                    comment_text=issue['message'],
                    severity=issue['severity'],
                    category='security'
                )
