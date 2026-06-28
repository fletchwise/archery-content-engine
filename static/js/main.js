/* ══════════════════════════════════════════════
   Archery Content Engine — main.js
   ══════════════════════════════════════════════ */

// ─────────────────────────────────────────────
// Tab navigation
// ─────────────────────────────────────────────
function showTab(tab) {
  document.getElementById('tab-generate').classList.toggle('hidden', tab !== 'generate');
  document.getElementById('tab-history').classList.toggle('hidden', tab !== 'history');
  document.querySelectorAll('.nav-btn').forEach((btn, i) => {
    btn.classList.toggle('active',
      (i === 0 && tab === 'generate') || (i === 1 && tab === 'history')
    );
  });
  if (tab === 'history') loadHistory();
}

// ─────────────────────────────────────────────
// Form helpers
// ─────────────────────────────────────────────
function toggleComeback(checkbox) {
  document.getElementById('comeback_field').classList.toggle('hidden', !checkbox.checked);
}

function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

function getInt(id) {
  const v = parseInt(document.getElementById(id)?.value);
  return isNaN(v) ? null : v;
}

function getBool(id) {
  return document.getElementById(id)?.checked || false;
}

/** Build the JSON object that maps to the API schema */
function buildMatchJSON() {
  return {
    event: {
      name:       getVal('event_name'),
      location:   getVal('event_location'),
      date:       getVal('event_date'),
      round:      getVal('event_round'),
      discipline: getVal('event_discipline')
    },
    athletes: {
      home: {
        name:       getVal('home_name'),
        country:    getVal('home_country') || 'USA',
        world_rank: getInt('home_rank'),
        flag:       '🇺🇸'
      },
      opponent: {
        name:       getVal('opp_name'),
        country:    getVal('opp_country'),
        world_rank: getInt('opp_rank'),
        flag:       '🎯'
      }
    },
    match: {
      result:         getVal('match_result'),
      score_home:     getInt('score_home'),
      score_opponent: getInt('score_opp'),
      deciding_arrow: getBool('deciding_arrow'),
      perfect_ends:   getInt('perfect_ends') || 0,
      comeback:       getBool('comeback'),
      comeback_from:  getVal('comeback_from')
    },
    content: {
      platform:         document.querySelector('input[name="platform"]:checked')?.value || 'youtube',
      type:             getVal('content_type'),
      duration_minutes: getInt('duration'),
      extra_notes:      getVal('extra_notes')
    }
  };
}

// ─────────────────────────────────────────────
// Stage animation (simulated progress)
// ─────────────────────────────────────────────
let _stageTimers = [];

const STAGE_DELAYS = {
  A: 0,
  B: 7000,
  C: 15000,
  D: 22000
};

function startStageAnimation() {
  _stageTimers.forEach(clearTimeout);
  _stageTimers = [];
  resetAllStages();

  Object.entries(STAGE_DELAYS).forEach(([s, delay]) => {
    _stageTimers.push(setTimeout(() => activateStage(s), delay));
  });
}

function activateStage(s) {
  const el = document.getElementById(`stage-${s}`);
  if (!el) return;
  // Deactivate previous
  ['A', 'B', 'C', 'D'].forEach(prev => {
    if (prev !== s) {
      const p = document.getElementById(`stage-${prev}`);
      if (p && p.classList.contains('active')) {
        p.classList.remove('active');
        p.classList.add('pending');
      }
    }
  });
  el.classList.remove('pending');
  el.classList.add('active');
  el.querySelector('.stage-icon').textContent = '⟳';
}

function markAllStagesDone() {
  _stageTimers.forEach(clearTimeout);
  ['A', 'B', 'C', 'D'].forEach(s => {
    const el = document.getElementById(`stage-${s}`);
    if (!el) return;
    el.className = 'stage-item done';
    el.querySelector('.stage-icon').textContent = '✓';
  });
}

function resetAllStages() {
  ['A', 'B', 'C', 'D'].forEach((s, i) => {
    const el = document.getElementById(`stage-${s}`);
    if (!el) return;
    el.className = 'stage-item' + (i > 0 ? ' pending' : ' active');
    el.querySelector('.stage-icon').textContent = i === 0 ? '⟳' : '○';
  });
}

// ─────────────────────────────────────────────
// State management
// ─────────────────────────────────────────────
function showState(name) {
  const allStates = ['idle', 'loading', 'error', 'results'];
  allStates.forEach(s => {
    const el = document.getElementById(`state-${s}`);
    if (el) el.classList.add('hidden');
  });
  const target = document.getElementById(`state-${name}`);
  if (target) target.classList.remove('hidden');
}

function resetToIdle() {
  _stageTimers.forEach(clearTimeout);
  resetAllStages();
  showState('idle');
  const btn = document.getElementById('submitBtn');
  btn.disabled = false;
  btn.textContent = '⚡ Generate Content Package';
}

// ─────────────────────────────────────────────
// Form submission
// ─────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();

  const matchData = buildMatchJSON();

  // Switch UI to loading
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Generating...';
  showState('loading');
  startStageAnimation();

  try {
    const res  = await fetch('/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(matchData)
    });
    const data = await res.json();

    markAllStagesDone();
    // Brief pause so user sees all stages done
    await new Promise(r => setTimeout(r, 600));

    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Unknown error occurred.');
    }

    displayResults(data);

  } catch (err) {
    showState('error');
    document.getElementById('error-msg').textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Generate Content Package';
  }
}

// ─────────────────────────────────────────────
// Display results
// ─────────────────────────────────────────────
function displayResults(data) {
  const r = data.result || {};

  // Meta badges
  document.getElementById('meta-hook').textContent  = `Hook: ${data.hook_score || '—'}/100`;
  document.getElementById('meta-score').textContent = `Quality: ${data.content_score || '—'}/100`;
  document.getElementById('meta-time').textContent  = `${data.elapsed_sec || '—'}s`;

  // Title
  document.getElementById('result-title').textContent = r.title || '—';
  document.getElementById('winner-style').textContent  = (r._winning_style || '').toUpperCase();

  // Caption
  document.getElementById('result-caption').textContent = r.caption || '—';

  // Hashtags
  const hashWrap = document.getElementById('result-hashtags');
  hashWrap.innerHTML = '';
  (r.hashtags || []).forEach(tag => {
    const chip = document.createElement('span');
    chip.className = 'hashtag-chip';
    chip.textContent = tag;
    chip.onclick = () => { copyText(tag); showToast('Copied: ' + tag); };
    hashWrap.appendChild(chip);
  });

  // Post time
  const pt = r.optimal_post_time || {};
  document.getElementById('result-posttime').innerHTML = `
    <strong>${pt.day || '—'}</strong> at <strong>${pt.time_est || '—'}</strong>
    &nbsp;(${pt.time_gmt || '—'} GMT)
    <p class="post-reason">${pt.reason || ''}</p>
  `;

  // Thumbnail (YouTube only)
  const thumbBlock = document.getElementById('block-thumbnail');
  if (r.thumbnail_text && r.platform === 'youtube') {
    document.getElementById('result-thumbnail').textContent = r.thumbnail_text;
    thumbBlock.classList.remove('hidden');
  } else {
    thumbBlock.classList.add('hidden');
  }

  // All 5 scored titles
  const tbody = document.getElementById('titles-tbody');
  tbody.innerHTML = '';
  (data.all_titles || []).forEach(t => {
    const isWinner = t.title === r.title;
    const row = document.createElement('tr');
    row.className = isWinner ? 'winner-row' : '';
    row.innerHTML = `
      <td><span class="style-badge ${t.style || ''}">${t.style || '?'}</span></td>
      <td>${t.title || '—'} ${isWinner ? '🏆' : ''}</td>
      <td>${t.final_score != null ? t.final_score : '—'}</td>
    `;
    tbody.appendChild(row);
  });

  showState('results');
}

function toggleAllTitles() {
  const wrap = document.getElementById('all-titles-wrap');
  const icon = document.getElementById('titles-toggle-icon');
  const hidden = wrap.classList.toggle('hidden');
  icon.textContent = hidden ? '▼' : '▲';
}

// ─────────────────────────────────────────────
// Copy functions
// ─────────────────────────────────────────────
function copyField(elementId, btn) {
  const text = document.getElementById(elementId)?.textContent;
  if (!text) return;
  copyText(text);
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = '✓ Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 2000);
  }
}

function copyHashtags() {
  const chips = document.querySelectorAll('#result-hashtags .hashtag-chip');
  const text  = Array.from(chips).map(c => c.textContent).join(' ');
  if (!text) return;
  copyText(text);
  showToast('All 15 hashtags copied!');
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const el = document.createElement('textarea');
  el.value = text;
  el.style.position = 'fixed';
  el.style.opacity  = '0';
  document.body.appendChild(el);
  el.select();
  document.execCommand('copy');
  document.body.removeChild(el);
}

// ─────────────────────────────────────────────
// Toast notification
// ─────────────────────────────────────────────
let _toastTimer;
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg || 'Copied!';
  toast.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}

// ─────────────────────────────────────────────
// History
// ─────────────────────────────────────────────
async function loadHistory() {
  const list = document.getElementById('history-list');
  list.innerHTML = '<p class="muted-text">Loading...</p>';

  try {
    const res  = await fetch('/history?limit=30');
    const data = await res.json();

    if (!data.runs || data.runs.length === 0) {
      list.innerHTML = '<p class="muted-text">No generations yet. Generate your first content package!</p>';
      return;
    }

    list.innerHTML = `
      <table class="history-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Date</th>
            <th>Event</th>
            <th>Platform</th>
            <th>Winning Title</th>
            <th>Score</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${data.runs.map(r => `
            <tr class="history-row" onclick="window.open('/run/${r.id}','_blank')">
              <td>${r.id}</td>
              <td>${(r.created_at || '').slice(0, 16)}</td>
              <td>${r.event_name || '—'}</td>
              <td><span class="platform-tag ${r.platform || ''}">${r.platform || '—'}</span></td>
              <td class="title-cell">${r.final_title || '—'}</td>
              <td>${r.content_score || '—'}</td>
              <td><span class="status-tag ${r.status || 'running'}">${r.status || '?'}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    list.innerHTML = `<p class="muted-text" style="color:#DC2626">Failed to load history: ${err.message}</p>`;
  }
}
