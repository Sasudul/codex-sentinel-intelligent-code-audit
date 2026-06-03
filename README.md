# Codex Sentinel

An intelligent, automated code review system that analyzes GitHub pull requests and posts actionable feedback — combining static analysis, security scanning, and AI-powered suggestions.

## 🎯 Features

- **GitHub Webhooks** — real-time trigger on PR create/update
- **Static Analysis** — Flake8 linting + McCabe complexity (Python)
- **Security Scanning** — regex detection for hardcoded secrets, API keys, JWT tokens
- **AI-Powered Review** — GPT-4o-mini sends structured JSON suggestions per file
- **Quality Scoring** — weighted 0–100 score from all findings
- **Inline PR Comments** — posts line-level comments + formatted summary card to GitHub
- **Desktop App** — Electron dashboard to visualise repos, PRs, scores, and findings

## 🏗️ Architecture

```
GitHub PR Event
      │
      ▼
Django Webhook (/api/webhook/github/)
      │   ← responds 200 immediately
      ▼
Celery Task (Redis queue)
      ├── fetch PR diff (GitHub API)
      ├── static_analyzer.py  (Flake8)
      ├── security_analyzer.py (regex patterns)
      ├── ai_reviewer.py      (OpenAI GPT-4o-mini)
      ├── scorer.py           (weighted quality score)
      └── pr_commenter.py     (post back to GitHub)

REST API (/api/*)  ◄──────  Electron Desktop App
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Django 5, Django REST Framework |
| Task Queue | Celery 5 + Redis |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI | OpenAI API (gpt-4o-mini) |
| GitHub | Webhooks + REST API v3 |
| Desktop | Electron 29 |

## 🚀 Quick Start

### 1. Clone & environment

```bash
git clone <repo-url>
cd codex-sentinel-intelligent-code-audit
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure `.env`

Copy the template and fill in your tokens:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/codex_sentinel   # optional, SQLite used if omitted
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
GITHUB_API_TOKEN=your_github_personal_access_token
OPENAI_API_KEY=your_openai_api_key
REDIS_URL=redis://localhost:6379/0
```

### 3. Migrate & run

```bash
python manage.py migrate
python manage.py runserver
```

In a **second terminal** (with venv active):

```bash
celery -A codex_sentinel worker -l info --pool=solo
```

### 4. GitHub Webhook setup

In your GitHub repository → **Settings → Webhooks → Add webhook**:
- **Payload URL**: `http://<your-server>/api/webhook/github/`
- **Content type**: `application/json`
- **Secret**: same as `GITHUB_WEBHOOK_SECRET`
- **Events**: ✅ Pull requests

> For local development use [ngrok](https://ngrok.com): `ngrok http 8000`

### 5. Desktop App

```bash
cd desktop
npm install
npm start
```

Configure the Backend URL in **Settings** (default: `http://localhost:8000`).

## 📡 API Endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/webhook/github/` | GitHub webhook receiver |
| `GET` | `/api/dashboard/stats/` | Aggregate metrics |
| `GET` | `/api/repositories/` | All connected repos |
| `GET` | `/api/repositories/<id>/pull-requests/` | PRs for a repo |
| `GET` | `/api/pull-requests/<id>/` | PR detail |
| `GET` | `/api/reviews/<id>/` | Review detail with comments |

## 📁 Project Structure

```
codex-sentinel-intelligent-code-audit/
├── codex_sentinel/          # Django project config
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── review_engine/           # Core Django app
│   ├── models.py            # Repository, PullRequest, CodeReview, Comment
│   ├── views.py             # Webhook + Dashboard REST API
│   ├── serializers.py       # DRF serializers
│   ├── tasks.py             # Celery pipeline orchestration
│   ├── github_service.py    # GitHub API helpers
│   ├── static_analyzer.py   # Flake8 + diff parsing
│   ├── security_analyzer.py # Secret detection
│   ├── ai_reviewer.py       # OpenAI review
│   ├── scorer.py            # Quality scoring
│   └── pr_commenter.py      # GitHub PR commenting
├── desktop/                 # Electron desktop app
│   ├── main.js
│   ├── preload.js
│   └── renderer/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── requirements.txt
├── .env                     # (gitignored)
└── README.md
```
