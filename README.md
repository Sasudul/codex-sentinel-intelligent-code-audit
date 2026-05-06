# Codex Sentinel

An intelligent code review system built with Django that automatically analyzes GitHub pull requests and provides actionable feedback. It combines static code analysis, rule-based validation, and AI-powered insights to help developers improve code quality, security, and maintainability before merging.

## 🎯 Features

- **GitHub Integration**: Connect repositories via GitHub API & Webhooks.
- **AI-Powered Review**: Suggest code improvements, detect anti-patterns, and provide human-readable explanations using OpenAI.
- **Static Code Analysis**: Linting and complexity detection for multiple languages.
- **Security Analysis**: Detects hardcoded secrets and highlights unsafe coding practices.
- **Code Quality Scoring**: PR-level dashboard metrics for readability, complexity, and maintainability.
- **Inline PR Comments**: Automatically posts human-readable, line-by-line feedback directly on GitHub Pull Requests.

## 🏗️ Tech Stack

- **Backend**: Python / Django, Django REST Framework
- **Task Queue**: Celery & Redis
- **Database**: PostgreSQL
- **Integrations**: GitHub API, OpenAI API

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis server
- GitHub API Token
- OpenAI API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd codex-sentinel-intelligent-code-audit
   ```

2. **Set up the virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the project root with the following structure:
   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   DATABASE_URL=postgres://user:password@localhost:5432/dbname
   GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
   GITHUB_API_TOKEN=your_github_api_token
   OPENAI_API_KEY=your_openai_api_key
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the Development Server**
   ```bash
   python manage.py runserver
   ```

7. **Start the Celery Worker (In a separate terminal)**
   ```bash
   celery -A codex_sentinel worker -l info --pool=solo
   ```
