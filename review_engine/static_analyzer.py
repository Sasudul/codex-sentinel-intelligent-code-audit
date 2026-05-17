import tempfile
import subprocess
import os
import requests
from django.conf import settings
from .models import Comment

def parse_diff(diff_text):
    """
    Very basic unified diff parser to get modified files and their added lines.
    Returns a dict: { 'filename': [line_numbers_added] }
    """
    files = {}
    current_file = None
    current_line = 0
    
    for line in diff_text.splitlines():
        if line.startswith('+++ b/'):
            current_file = line[6:]
            files[current_file] = []
        elif line.startswith('@@'):
            # @@ -old_line,old_count +new_line,new_count @@
            try:
                parts = line.split('+')[1].split(' ')[0].split(',')
                current_line = int(parts[0]) - 1
            except (IndexError, ValueError):
                pass
        elif current_file is not None:
            if line.startswith('+') and not line.startswith('+++'):
                current_line += 1
                files[current_file].append(current_line)
            elif line.startswith('-') and not line.startswith('---'):
                pass
            elif not line.startswith('\\'):
                current_line += 1
                
    return files

def fetch_file_content(repo_full_name, commit_sha, file_path):
    token = getattr(settings, 'GITHUB_API_TOKEN', os.getenv('GITHUB_API_TOKEN'))
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={commit_sha}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.text
    return None

def run_flake8_on_file(file_content):
    """
    Runs flake8 on the given string content.
    Returns a list of dicts: [{'line': 10, 'message': 'E501 line too long', 'severity': 'warning'}]
    """
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w', encoding='utf-8') as f:
        f.write(file_content)
        temp_path = f.name
        
    issues = []
    try:
        # Run flake8 with McCabe complexity enabled.
        result = subprocess.run(
            ['flake8', temp_path, '--max-complexity=10', '--format=%(row)d|%(code)s %(text)s'],
            capture_output=True,
            text=True
        )
        output = result.stdout
        
        for line in output.splitlines():
            if '|' in line:
                parts = line.split('|', 1)
                try:
                    line_num = int(parts[0])
                    msg = parts[1]
                    severity = 'error' if msg.startswith('E') or msg.startswith('F') else 'warning'
                    category = 'complexity' if msg.startswith('C90') else 'style'
                    
                    issues.append({
                        'line': line_num,
                        'message': f"Flake8: {msg}",
                        'severity': severity,
                        'category': category
                    })
                except ValueError:
                    continue
    finally:
        os.remove(temp_path)
        
    return issues

def run_static_analysis(code_review, repo_full_name, commit_sha, diff_text):
    """
    Runs static analysis on the modified files in the diff.
    Creates Comment objects for any findings on modified lines.
    """
    changed_files = parse_diff(diff_text)
    
    for file_path, modified_lines in changed_files.items():
        if not file_path.endswith('.py'):
            continue  # Only analyzing Python files for now
            
        content = fetch_file_content(repo_full_name, commit_sha, file_path)
        if not content:
            continue
            
        issues = run_flake8_on_file(content)
        
        for issue in issues:
            if issue['line'] in modified_lines:
                Comment.objects.create(
                    code_review=code_review,
                    file_path=file_path,
                    line_number=issue['line'],
                    comment_text=issue['message'],
                    severity=issue['severity'],
                    category=issue.get('category', 'style')
                )
