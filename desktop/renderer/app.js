/* ── Codex Sentinel Desktop App — Renderer Process ──────────────────────── */

const DEFAULT_API = 'http://localhost:8000';
let API_BASE = localStorage.getItem('api_base') || DEFAULT_API;

// ── API Client ───────────────────────────────────────────────────────────── //
const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}/api${path}`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  },
};

// ── Page Router ──────────────────────────────────────────────────────────── //
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const page = document.getElementById(`page-${name}`);
  const nav = document.getElementById(`nav-${name}`);
  if (page) page.classList.add('active');
  if (nav) nav.classList.add('active');
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// ── Window Controls ──────────────────────────────────────────────────────── //
if (window.electronAPI) {
  document.getElementById('btn-minimize').addEventListener('click', () => window.electronAPI.minimize());
  document.getElementById('btn-maximize').addEventListener('click', () => window.electronAPI.maximize());
  document.getElementById('btn-close').addEventListener('click', () => window.electronAPI.close());
}

// ── Backend Health Check ─────────────────────────────────────────────────── //
async function checkBackendStatus() {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  try {
    await api.get('/dashboard/stats/');
    dot.className = 'status-dot online';
    text.textContent = 'Backend online';
  } catch {
    dot.className = 'status-dot offline';
    text.textContent = 'Backend offline';
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────── //
function scoreChip(score) {
  if (score === null || score === undefined) return '<span class="score-chip">N/A</span>';
  const cls = score >= 80 ? 'score-high' : score >= 50 ? 'score-mid' : 'score-low';
  return `<span class="score-chip ${cls}">${score.toFixed(1)}</span>`;
}

function statusBadge(s) {
  return `<span class="badge badge-${s}">${s.replace('_', ' ')}</span>`;
}

function relativeTime(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Dashboard ────────────────────────────────────────────────────────────── //
async function loadDashboard() {
  try {
    const data = await api.get('/dashboard/stats/');

    document.getElementById('stat-repos').textContent = data.totals.repositories;
    document.getElementById('stat-prs').textContent = data.totals.pull_requests;
    document.getElementById('stat-score').textContent =
      data.average_score != null ? `${data.average_score.toFixed(1)}` : '—';
    document.getElementById('stat-security').textContent = data.issues.security;

    // Issues bar chart
    const total = data.issues.security + data.issues.style + data.issues.ai_suggestions || 1;
    const pct = (n) => Math.round((n / total) * 100);

    document.getElementById('bar-security').style.width = `${pct(data.issues.security)}%`;
    document.getElementById('bar-style').style.width = `${pct(data.issues.style)}%`;
    document.getElementById('bar-ai').style.width = `${pct(data.issues.ai_suggestions)}%`;
    document.getElementById('count-security').textContent = data.issues.security;
    document.getElementById('count-style').textContent = data.issues.style;
    document.getElementById('count-ai').textContent = data.issues.ai_suggestions;

    // Recent reviews table
    const tbody = document.getElementById('recent-reviews-body');
    if (!data.recent_reviews.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No reviews yet.</td></tr>';
      return;
    }

    tbody.innerHTML = data.recent_reviews.map(r => `
      <tr style="cursor:pointer" data-review-id="${r.review_id}">
        <td style="color:var(--text-primary);font-weight:500">${r.repo}</td>
        <td><a href="#" style="color:var(--blue);text-decoration:none;">#${r.pr_number} ${escapeHtml(r.pr_title)}</a></td>
        <td>${statusBadge(r.status)}</td>
        <td>${scoreChip(r.score)}</td>
        <td style="color:var(--text-muted)">${relativeTime(r.created_at)}</td>
      </tr>
    `).join('');

    // Click row to open review detail
    tbody.querySelectorAll('tr[data-review-id]').forEach(row => {
      row.addEventListener('click', () => {
        loadReviewDetail(row.dataset.reviewId);
        showPage('reviews');
      });
    });

  } catch (err) {
    document.getElementById('stat-repos').textContent = '—';
    console.error('Dashboard load failed:', err);
  }
}

document.getElementById('btn-refresh').addEventListener('click', () => {
  checkBackendStatus();
  loadDashboard();
  loadRepositories();
});

// ── Repositories ─────────────────────────────────────────────────────────── //
async function loadRepositories() {
  const grid = document.getElementById('repos-grid');
  grid.innerHTML = '<div class="loading-card">Loading repositories…</div>';
  try {
    const repos = await api.get('/repositories/');
    if (!repos.length) {
      grid.innerHTML = '<div class="loading-card">No repositories connected yet.</div>';
      return;
    }
    grid.innerHTML = repos.map(r => `
      <div class="repo-card" data-repo-id="${r.id}">
        <h3>${escapeHtml(r.owner)}/${escapeHtml(r.name)}</h3>
        <div class="repo-meta">
          <div class="repo-meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 012 2v7"/><line x1="6" y1="9" x2="6" y2="21"/></svg>
            ${r.pr_count} PRs
          </div>
        </div>
      </div>
    `).join('');

    grid.querySelectorAll('.repo-card').forEach(card => {
      card.addEventListener('click', () => loadRepoPRs(card.dataset.repoId));
    });
  } catch (err) {
    grid.innerHTML = '<div class="loading-card">Failed to load repositories.</div>';
  }
}

async function loadRepoPRs(repoId) {
  showPage('reviews');
  const container = document.getElementById('reviews-list-container');
  const backBtn = document.getElementById('btn-back-reviews');
  document.getElementById('review-detail-container').style.display = 'none';
  container.style.display = 'block';
  backBtn.style.display = 'none';
  container.innerHTML = '<p style="color:var(--text-muted)">Loading pull requests…</p>';

  try {
    const prs = await api.get(`/repositories/${repoId}/pull-requests/`);
    if (!prs.length) {
      container.innerHTML = '<p class="hint-text">No pull requests found for this repository.</p>';
      return;
    }
    container.innerHTML = `
      <div class="reviews-table-wrapper">
        <table class="reviews-table">
          <thead><tr><th>PR</th><th>Author</th><th>Status</th><th>Score</th><th>Reviews</th></tr></thead>
          <tbody>
            ${prs.map(pr => `
              <tr style="cursor:pointer" data-pr-id="${pr.id}">
                <td style="color:var(--text-primary);font-weight:500">#${pr.pr_number} ${escapeHtml(pr.title)}</td>
                <td>${escapeHtml(pr.author)}</td>
                <td>${statusBadge(pr.state)}</td>
                <td>${pr.latest_review ? scoreChip(pr.latest_review.overall_score) : 'N/A'}</td>
                <td>${pr.review_count}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;

    container.querySelectorAll('tr[data-pr-id]').forEach(row => {
      row.addEventListener('click', async () => {
        const prData = await api.get(`/pull-requests/${row.dataset.prId}/`);
        if (prData.latest_review) loadReviewDetail(prData.latest_review.id);
      });
    });
  } catch (err) {
    container.innerHTML = '<p class="hint-text">Failed to load pull requests.</p>';
  }
}

// ── Review Detail ─────────────────────────────────────────────────────────── //
async function loadReviewDetail(reviewId) {
  const container = document.getElementById('review-detail-container');
  const listContainer = document.getElementById('reviews-list-container');
  const backBtn = document.getElementById('btn-back-reviews');

  listContainer.style.display = 'none';
  container.style.display = 'block';
  backBtn.style.display = 'inline-flex';
  container.innerHTML = '<p style="color:var(--text-muted)">Loading review…</p>';

  backBtn.onclick = () => {
    container.style.display = 'none';
    listContainer.style.display = 'block';
    backBtn.style.display = 'none';
  };

  try {
    const review = await api.get(`/reviews/${reviewId}/`);
    const score = review.overall_score;
    const scoreColor = score >= 80 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)';

    container.innerHTML = `
      <div class="review-detail-header">
        <div style="display:flex;align-items:center;gap:24px">
          <div>
            <div class="review-score-big" style="color:${scoreColor}">${score != null ? score.toFixed(1) : 'N/A'}</div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px">Quality Score / 100</div>
          </div>
          <div style="flex:1">
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
              ${statusBadge(review.status)}
              <span class="badge" style="background:rgba(88,166,255,0.1);color:var(--blue)">${review.comment_count} Comments</span>
            </div>
            <div style="font-size:12px;color:var(--text-muted)">Commit: <code style="font-family:'JetBrains Mono',monospace;color:var(--purple-light)">${review.commit_sha}</code></div>
          </div>
        </div>
      </div>

      <div class="section-header"><h2>Findings (${review.comment_count})</h2></div>
      <div class="comments-list">
        ${review.comments.length ? review.comments.map(c => `
          <div class="comment-card ${c.severity}">
            <div class="comment-header">
              <span class="badge badge-${c.severity === 'error' ? 'failed' : c.severity === 'warning' ? 'pending' : 'in_progress'}">${c.category.replace('_', ' ')}</span>
              <span class="comment-file">${escapeHtml(c.file_path)}</span>
              ${c.line_number ? `<span class="comment-line">:${c.line_number}</span>` : ''}
            </div>
            <div class="comment-text">${escapeHtml(c.comment_text)}</div>
          </div>
        `).join('') : '<p class="hint-text">No issues found — great code! 🎉</p>'}
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<p class="hint-text">Failed to load review details.</p>';
  }
}

// ── Settings ─────────────────────────────────────────────────────────────── //
document.getElementById('setting-api-url').value = API_BASE;

document.getElementById('btn-save-settings').addEventListener('click', () => {
  const val = document.getElementById('setting-api-url').value.trim().replace(/\/$/, '');
  API_BASE = val || DEFAULT_API;
  localStorage.setItem('api_base', API_BASE);
  document.getElementById('webhook-url-display').textContent = `${API_BASE}/api/webhook/github/`;
  checkBackendStatus();
});

document.getElementById('btn-test-connection').addEventListener('click', async () => {
  const result = document.getElementById('connection-result');
  result.textContent = 'Testing…';
  result.style.color = 'var(--text-muted)';
  try {
    await api.get('/dashboard/stats/');
    result.textContent = '✅ Connected successfully!';
    result.style.color = 'var(--green)';
  } catch (err) {
    result.textContent = `❌ Failed: ${err.message}`;
    result.style.color = 'var(--red)';
  }
});

// Update webhook URL on load
document.getElementById('webhook-url-display').textContent = `${API_BASE}/api/webhook/github/`;

// ── Utils ─────────────────────────────────────────────────────────────────── //
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ─────────────────────────────────────────────────────────────────── //
(async () => {
  await checkBackendStatus();
  await loadDashboard();
  await loadRepositories();
  showPage('dashboard');

  // Poll backend status every 30s
  setInterval(checkBackendStatus, 30000);
})();
