(() => {
  const D = window.__INITIAL__;
  const COLORS = { functional: '#2F82FF', yoga: '#6FBFA0', poci: '#F97316', gold: '#E8B84B' };
  const RING_CIRC = 163.36;
  const SAVE_KEY = 'training_live_session';
  const WARMUP_ITEMS = [
    { name: 'Arm Circles', desc: 'Forward + backward', type: 'timed', duration: 30 },
    { name: 'Shoulder Rotations', desc: 'Scapular prep', type: 'timed', duration: 30 },
    { name: 'Hip Circles', desc: 'Full hip mobility', type: 'timed', duration: 30 },
    { name: 'Leg Swings', desc: 'Forward / back, both legs', type: 'timed', duration: 30 },
    { name: 'Bodyweight Squat', desc: 'Slow and controlled', type: 'reps', reps: 10 },
    { name: 'Dead Hang / Scapular Shrug', desc: 'Shoulder joint prep', type: 'timed', duration: 20 },
    { name: 'Inchworm', desc: 'Hamstrings → plank → push-up → stand', type: 'reps', reps: 4 },
  ];

  const state = {
    screen: 'home',
    activeTab: 'home',
    activeWorkoutKey: null,
    activeGenericCategory: null,
    warmupIdx: 0,
    warmupSecLeft: 0,
    exerciseIdx: 0,
    setLogs: {},
    exerciseNotesDraft: {},
    restActive: false,
    restSecLeft: 0,
    genericRunning: false,
    genericElapsed: 0,
    genericNotes: '',
    toast: null,
    historyFilter: 'all',
    expandedHistoryId: null,
    sessionStartMs: null,
    sessionPRCount: 0,
    completionStats: null,
    saving: false,
  };

  const els = {
    root: document.getElementById('screen-root'),
    tabBar: document.getElementById('tab-bar'),
    toastRoot: document.getElementById('toast-root'),
  };

  let toastTimer = null;
  let tickTimer = null;

  // ---------- helpers ----------
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function fmtNum(v) { return String(Number(v)); }
  function fmtTime(sec) {
    sec = Math.max(0, Math.round(sec));
    const m = Math.floor(sec / 60), r = sec % 60;
    return m + ':' + String(r).padStart(2, '0');
  }
  function restRingOffset() {
    return (RING_CIRC * (1 - state.restSecLeft / D.restSeconds)).toFixed(2);
  }
  function genericLabel(category) { return category === 'poci' ? 'Poci Session' : 'Yoga Session'; }
  function genericColor(category) { return category === 'poci' ? COLORS.poci : COLORS.yoga; }

  // ---------- persistence ----------
  function saveSession() {
    if (!['warmup', 'live-functional', 'live-generic'].includes(state.screen)) return;
    localStorage.setItem(SAVE_KEY, JSON.stringify({
      screen: state.screen, activeWorkoutKey: state.activeWorkoutKey, activeGenericCategory: state.activeGenericCategory,
      warmupIdx: state.warmupIdx, warmupSecLeft: state.warmupSecLeft,
      exerciseIdx: state.exerciseIdx, setLogs: state.setLogs, exerciseNotesDraft: state.exerciseNotesDraft,
      restActive: state.restActive, restSecLeft: state.restSecLeft,
      genericRunning: state.genericRunning, genericElapsed: state.genericElapsed, genericNotes: state.genericNotes,
      sessionStartMs: state.sessionStartMs, sessionPRCount: state.sessionPRCount,
      savedAt: Date.now(),
    }));
  }
  function clearSavedSession() { localStorage.removeItem(SAVE_KEY); }
  function loadSavedSession() {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) return null;
    try {
      const s = JSON.parse(raw);
      if (Date.now() - s.savedAt > 12 * 60 * 60 * 1000) { clearSavedSession(); return null; }
      return s;
    } catch (e) { return null; }
  }

  // ---------- toast ----------
  function showToast(msg, tone) {
    state.toast = { msg, tone };
    renderToast();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { state.toast = null; renderToast(); }, 2600);
  }
  function renderToast() {
    if (!state.toast) { els.toastRoot.innerHTML = ''; return; }
    const dot = state.toast.tone === 'gold' ? COLORS.gold : 'rgba(255,255,255,.6)';
    els.toastRoot.innerHTML = `<div class="tr-toast"><div class="tr-dot" style="background:${dot}"></div><span class="tr-toast-text">${esc(state.toast.msg)}</span></div>`;
  }

  // ---------- icons ----------
  function iconHome(c) { return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 11L12 4L20 11V20H14V14H10V20H4V11Z" stroke="${c}" stroke-width="1.8" stroke-linejoin="round"/></svg>`; }
  function iconHistory(c) { return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8.5" stroke="${c}" stroke-width="1.8"/><path d="M12 7.5V12L15.5 14.5" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }
  function iconChevron(c) { return `<svg width="7" height="12" viewBox="0 0 7 12"><path d="M1 1L6 6L1 11" stroke="${c || 'rgba(245,243,239,.3)'}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }
  function iconClose() { return `<svg width="13" height="13" viewBox="0 0 14 14"><path d="M1 1L13 13M13 1L1 13" stroke="rgba(245,243,239,.8)" stroke-width="1.7" stroke-linecap="round"/></svg>`; }
  function iconPlayBig(fill) { return `<svg width="16" height="18" viewBox="0 0 16 18"><path d="M0 0L16 9L0 18V0Z" fill="${fill || '#0B0A0D'}"/></svg>`; }
  function iconCheck() { return `<svg width="12" height="10" viewBox="0 0 14 11"><path d="M1 5.5L5 9.5L13 1.5" stroke="#0B0A0D" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }

  // ---------- tab bar ----------
  function renderTabBar() {
    const show = ['home', 'history'].includes(state.screen);
    if (!show) { els.tabBar.innerHTML = ''; els.tabBar.style.display = 'none'; return; }
    els.tabBar.style.display = 'flex';
    const tabs = [['home', 'Home', iconHome], ['history', 'History', iconHistory]];
    els.tabBar.innerHTML = tabs.map(([key, label, icon]) => {
      const active = state.activeTab === key;
      const color = active ? '#F5F3EF' : 'rgba(245,243,239,.35)';
      return `<button class="tr-tab" onclick="App.goTab('${key}')">${icon(color)}<span class="tr-tab-label" style="color:${color}">${label}</span></button>`;
    }).join('');
  }

  function lastSessionMetaLine(s) {
    if (s.category === 'functional') {
      let line = s.exercises.length + ' exercises';
      if (s.prCount) line += ' · ' + s.prCount + ' PR' + (s.prCount > 1 ? 's' : '');
      return line;
    }
    if (s.category === 'yoga' || s.category === 'poci') {
      const parts = [];
      if (s.durationMin) parts.push(s.durationMin + ' min');
      if (s.notes) parts.push(s.notes.slice(0, 40));
      return parts.join(' · ') || 'Logged';
    }
    return s.notes ? s.notes.slice(0, 60) : 'Logged';
  }

  // ---------- Home ----------
  function abCard(labelLetter, gymKey, homeKey) {
    return `<div class="tr-card tr-ab-card">
      <div class="tr-card-title" style="margin-top:0">Workout ${labelLetter}</div>
      <div class="tr-ab-buttons">
        <button class="tr-ab-btn" style="border-color:${COLORS.functional}" onclick="App.startFunctional('${gymKey}')">Gym</button>
        <button class="tr-ab-btn" style="border-color:${COLORS.functional}" onclick="App.startFunctional('${homeKey}')">Home</button>
      </div>
    </div>`;
  }

  function renderHome() {
    const resume = loadSavedSession();
    const resumeBanner = resume ? `<div class="tr-resume-banner">
      <span class="tr-resume-text">Unfinished ${resume.screen === 'live-generic' ? 'session' : 'workout'} in progress</span>
      <button class="tr-resume-btn" onclick="App.resumeSaved()">Continue</button>
    </div>` : '';
    els.root.innerHTML = `<div class="tr-screen"><div class="tr-screen-pad">
      ${resumeBanner}
      <div style="display:flex;align-items:flex-start;justify-content:space-between;">
        <div>
          <div class="tr-eyebrow-date">${esc(D.todayDateLabel)}</div>
          <div class="tr-greeting">${esc(D.greeting)}</div>
        </div>
        ${D.showGamification ? `<div class="tr-streak"><div class="tr-streak-num">${D.streak}</div><div class="tr-streak-label">day streak</div></div>` : ''}
      </div>

      <div class="tr-ab-row">
        ${abCard('A', 'workout_a_gym', 'workout_a_home')}
        ${abCard('B', 'workout_b_gym', 'workout_b_home')}
      </div>

      <div class="tr-quick-row">
        <button class="tr-quick-btn" style="border-color:${COLORS.yoga};color:${COLORS.yoga}" onclick="App.startGeneric('yoga')">Start Yoga</button>
        <button class="tr-quick-btn" style="border-color:${COLORS.poci};color:${COLORS.poci}" onclick="App.startGeneric('poci')">Start Poci</button>
      </div>

      <div class="tr-stat-row">
        <div class="tr-stat-card"><div class="tr-stat-value">${D.weekCount}</div><div class="tr-stat-label">sessions this week</div></div>
        ${D.showGamification && D.lastPR ? `<div class="tr-stat-card tr-clickable" style="flex:1.4" onclick="App.goTab('history')">
          <div class="tr-stat-value tr-gold">${esc(D.lastPR.value)}</div>
          <div class="tr-stat-label">PR · ${esc(D.lastPR.name.replace(' (Dumbbell)', ''))}</div>
        </div>` : ''}
      </div>

      ${D.lastSession ? `<div class="tr-last-session" onclick="App.goTab('history')">
        <div class="tr-dot" style="background:${D.lastSession.accent}"></div>
        <div style="flex:1">
          <div class="tr-last-session-label">Last Session · ${esc(D.lastSession.dateLabel)}</div>
          <div class="tr-last-session-title">${esc(D.lastSession.title)}</div>
          <div class="tr-last-session-meta">${esc(lastSessionMetaLine(D.lastSession))}</div>
        </div>
        <div class="tr-chevron">${iconChevron()}</div>
      </div>` : ''}
    </div></div>`;
  }

  // ---------- History ----------
  function renderHistory() {
    const filtered = D.history.filter(h => state.historyFilter === 'all' || h.category === state.historyFilter);
    els.root.innerHTML = `<div class="tr-screen"><div class="tr-screen-pad">
      <div class="tr-greeting" style="margin-top:0">History</div>
      ${D.progressChart.length ? `<div class="tr-chart-card">
        <div class="tr-chart-head"><div class="tr-chart-title">${esc(D.progressChartLabel)}</div><div class="tr-chart-sub">last ${D.progressChart.length} sessions</div></div>
        <div class="tr-chart-bars">${D.progressChart.map(b => `
          <div class="tr-chart-bar-col">
            <span class="tr-chart-bar-val" style="color:${b.valueColor}">${esc(b.value)}</span>
            <div class="tr-chart-bar" style="height:${b.heightPx}px;background:${b.barColor}"></div>
            <span class="tr-chart-bar-label">${esc(b.label)}</span>
          </div>`).join('')}</div>
      </div>` : ''}

      <div class="tr-filter-row">
        ${['all', 'functional', 'yoga', 'poci'].map(key => {
          const active = state.historyFilter === key;
          const label = key === 'all' ? 'All' : (key === 'functional' ? 'Workout' : (key === 'yoga' ? 'Yoga' : 'Poci'));
          return `<button class="tr-filter-btn" style="border:1px solid ${active ? 'rgba(255,255,255,.2)' : 'rgba(255,255,255,.08)'};background:${active ? 'rgba(255,255,255,.1)' : 'transparent'};color:${active ? '#F5F3EF' : 'rgba(245,243,239,.45)'}" onclick="App.setHistoryFilter('${key}')">${label}</button>`;
        }).join('')}
      </div>

      <div class="tr-history-list">
        ${filtered.length ? filtered.map(h => historyItem(h)).join('') : '<div class="tr-empty">No sessions yet.</div>'}
      </div>
    </div></div>`;
  }

  function historyItem(h) {
    const expanded = state.expandedHistoryId === h.id;
    let metaLine;
    if (h.category === 'functional') {
      metaLine = h.exercises.length + ' exercises' + (h.prCount ? ' · ' + h.prCount + ' PR' + (h.prCount > 1 ? 's' : '') : '') + (h.durationMin ? ' · ' + h.durationMin + ' min' : '');
    } else if (h.category === 'yoga' || h.category === 'poci') {
      metaLine = h.durationMin ? h.durationMin + ' min' : (h.notes ? h.notes.slice(0, 60) : 'Logged');
    } else {
      metaLine = h.durationMin ? h.durationMin + ' min' : (h.notes ? h.notes.slice(0, 60) : 'Logged manually');
    }
    let body = '';
    if (expanded) {
      if (h.exercises.length) {
        body += h.exercises.map(e => `<div class="tr-history-ex-row"><span class="tr-history-ex-name">${esc(e.name)}</span><span class="tr-history-ex-sets">${esc(e.sets)}</span></div>`).join('');
      }
      if (h.focusTags && h.focusTags.length) {
        body += `<div class="tr-focus-tags" style="padding-top:10px">${h.focusTags.map(t => `<span class="tr-focus-tag">${esc(t)}</span>`).join('')}</div>`;
      }
      if (h.notes) body += `<div class="tr-history-notes">${esc(h.notes)}</div>`;
      if (!body) body = '<div class="tr-empty" style="padding:10px 0">No details recorded.</div>';
      body = `<div class="tr-history-body">${body}</div>`;
    }
    return `<div class="tr-history-item">
      <button class="tr-history-head" onclick="App.toggleHistoryExpand('${h.id}')">
        <div class="tr-dot" style="background:${h.accent}"></div>
        <div style="flex:1">
          <div class="tr-history-title-row"><span class="tr-history-title">${esc(h.title)}</span><span class="tr-history-date">${esc(h.dateLabel)}</span></div>
          <div class="tr-history-meta">${esc(metaLine)}</div>
        </div>
        <svg width="10" height="10" viewBox="0 0 10 10" style="transform:rotate(${expanded ? 180 : 0}deg);flex-shrink:0"><path d="M1 3L5 7L9 3" stroke="rgba(245,243,239,.4)" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      ${body}
    </div>`;
  }

  // ---------- Warmup ----------
  function renderWarmup() {
    const item = WARMUP_ITEMS[state.warmupIdx];
    const isLast = state.warmupIdx === WARMUP_ITEMS.length - 1;
    const progressPct = Math.round((state.warmupIdx / WARMUP_ITEMS.length) * 100);
    els.root.innerHTML = `<div class="tr-live-header">
        <div class="tr-live-topbar">
          <button class="tr-icon-btn" onclick="App.closeLive()">${iconClose()}</button>
          <div class="tr-live-title-block">
            <div class="tr-live-title">Warmup</div>
            <div class="tr-live-sub">${state.warmupIdx + 1} of ${WARMUP_ITEMS.length}</div>
          </div>
          <div style="width:34px"></div>
        </div>
        <div class="tr-progress-bar"><div class="tr-progress-fill" style="width:${progressPct}%;background:${COLORS.functional}"></div></div>
      </div>
      <div class="tr-live-body">
        <div class="tr-card tr-warmup-card">
          <div class="tr-ex-name">${esc(item.name)}</div>
          <div class="tr-ex-target">${esc(item.desc)}</div>
          ${item.type === 'timed'
            ? `<div class="tr-warmup-count" id="warmup-count">${fmtTime(state.warmupSecLeft)}</div>`
            : `<div class="tr-warmup-count">${item.reps}<span class="tr-warmup-reps-label">reps</span></div>`}
        </div>
      </div>
      <div class="tr-live-footer">
        <button class="tr-btn-nav tr-btn-prev" onclick="App.skipWarmup()">Skip Warmup</button>
        ${item.type === 'reps'
          ? `<button class="tr-btn-nav tr-btn-next" style="background:${COLORS.functional}" onclick="App.warmupNext()">${isLast ? 'Start Workout' : 'Next Exercise'}</button>`
          : ''}
      </div>`;
  }

  // ---------- Live functional (Workout A/B, gym/home) ----------
  function renderLiveFunctional() {
    const workout = D.abWorkouts[state.activeWorkoutKey];
    const idx = state.exerciseIdx;
    const ex = workout.exercises[idx];
    const sets = state.setLogs[ex.id];
    const isLast = idx === workout.exercises.length - 1;
    const nextEx = workout.exercises[idx + 1] || null;
    const progressPct = Math.round((idx / workout.exercises.length) * 100);

    els.root.innerHTML = `<div class="tr-live-header">
        <div class="tr-live-topbar">
          <button class="tr-icon-btn" onclick="App.closeLive()">${iconClose()}</button>
          <div class="tr-live-title-block">
            <div class="tr-live-title">${esc(workout.label)}</div>
            <div class="tr-live-sub">Exercise ${idx + 1} of ${workout.exercises.length}</div>
          </div>
          <div style="width:34px"></div>
        </div>
        <div class="tr-progress-bar"><div class="tr-progress-fill" style="width:${progressPct}%;background:${COLORS.functional}"></div></div>
      </div>
      <div class="tr-live-body">
        <div class="tr-card">
          <div class="tr-ex-name">${esc(ex.name)}</div>
          <div class="tr-ex-target">${ex.target_sets} sets × ${esc(ex.target_reps)} reps</div>
          <div class="tr-cue-box">
            <div class="tr-cue-label" style="color:${COLORS.functional}">Coach Cue</div>
            <div class="tr-cue-text">${esc(ex.cue)}</div>
          </div>
          ${ex.youtube ? `<a class="tr-yt-link" href="${esc(ex.youtube)}" target="_blank" rel="noopener noreferrer">Watch tutorial ↗</a>` : ''}
        </div>

        <div class="tr-card">
          <div class="tr-sets-head">
            <div class="tr-sets-label">Sets</div>
            <div class="tr-sets-last">${ex.lastWeight ? 'Last: ' + fmtNum(ex.lastWeight) + 'kg × ' + ex.lastReps : ''}</div>
          </div>
          <div class="tr-note-row">
            <span class="tr-note-label">Note</span>
            <input type="text" class="tr-note-input" value="${esc(state.exerciseNotesDraft[ex.id] || '')}" placeholder="e.g. felt easy — add weight next time" oninput="App.changeNote('${ex.id}', this.value)"/>
          </div>
          <div>${sets.map((s, i) => setRow(ex, s, i, sets.length)).join('')}</div>
          ${state.restActive ? restCard(nextEx) : ''}
        </div>

        ${nextEx ? `<div class="tr-upnext-card" onclick="App.jumpNext()">
          <div style="flex:1">
            <div class="tr-upnext-label">Up Next</div>
            <div class="tr-upnext-title">${esc(nextEx.name)}</div>
            <div class="tr-upnext-target">${nextEx.target_sets} sets × ${esc(nextEx.target_reps)}</div>
          </div>
          ${iconChevron()}
        </div>` : ''}
      </div>
      <div class="tr-live-footer">
        <button class="tr-btn-nav tr-btn-prev" style="color:${idx === 0 ? 'rgba(245,243,239,.25)' : 'rgba(245,243,239,.85)'}" ${idx === 0 ? 'disabled' : ''} onclick="App.prevExercise()">Previous</button>
        <button class="tr-btn-nav tr-btn-next" style="background:${COLORS.functional}" ${state.saving ? 'disabled' : ''} onclick="App.nextExercise()">${state.saving ? 'Saving…' : (isLast ? 'Finish Workout' : 'Next Exercise')}</button>
      </div>`;
  }

  function setRow(ex, s, i, totalSets) {
    const done = s.done;
    const numBg = done ? COLORS.functional : '#1E1D24';
    const checkBorder = done ? (s.isPR ? COLORS.gold : COLORS.functional) : 'rgba(255,255,255,.2)';
    const checkBg = done ? (s.isPR ? COLORS.gold : COLORS.functional) : 'transparent';
    const checkIconColor = done ? '#0B0A0D' : 'rgba(255,255,255,.25)';
    const copyLink = (i === 0 && totalSets > 1 && !done)
      ? `<button class="tr-copy-link" onclick="App.copyFirstSetToAll('${ex.id}')">Copy to all sets ↓</button>`
      : '';
    return `<div class="tr-set-row" style="opacity:${done ? 0.5 : 1}">
      <div class="tr-set-num-circle" style="background:${numBg}">
        ${done ? iconCheck() : `<span class="tr-set-num-text">${i + 1}</span>`}
      </div>
      <div class="tr-set-inputs">
        <div class="tr-set-field">
          <input type="number" inputmode="decimal" value="${esc(s.weight)}" ${done ? 'disabled' : ''} oninput="App.changeSetField('${ex.id}',${i},'weight',this.value)"/>
          <span class="tr-set-field-unit">KG</span>
        </div>
        <div class="tr-set-field">
          <input type="number" inputmode="numeric" class="tr-reps-field" value="${esc(s.reps)}" ${done ? 'disabled' : ''} oninput="App.changeSetField('${ex.id}',${i},'reps',this.value)"/>
          <span class="tr-set-field-unit">REPS</span>
        </div>
      </div>
      <button class="tr-set-check" style="border-color:${checkBorder};background:${checkBg}" onclick="App.toggleSet('${ex.id}',${i})">
        <svg width="15" height="11" viewBox="0 0 16 12"><path d="M1 6L6 11L15 1" stroke="${checkIconColor}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
    ${copyLink}`;
  }

  function restCard(nextEx) {
    return `<div class="tr-rest-card">
      <div class="tr-rest-ring-wrap">
        <svg width="48" height="48" viewBox="0 0 60 60" style="transform:rotate(-90deg)">
          <circle cx="30" cy="30" r="26" fill="none" stroke="rgba(255,255,255,.1)" stroke-width="5"/>
          <circle id="rest-ring-fg" cx="30" cy="30" r="26" fill="none" stroke="${COLORS.functional}" stroke-width="5" stroke-linecap="round" stroke-dasharray="163.36" stroke-dashoffset="${restRingOffset()}"/>
        </svg>
        <div class="tr-rest-ring-label" id="rest-ring-label">${fmtTime(state.restSecLeft)}</div>
      </div>
      <div class="tr-rest-info">
        <div class="tr-rest-label" style="color:${COLORS.functional}">Resting</div>
        <div class="tr-rest-next">Next: ${esc(nextEx ? nextEx.name : 'finish workout')}</div>
      </div>
      <button class="tr-skip-btn" onclick="App.skipRest()">Skip</button>
    </div>`;
  }

  // ---------- Live generic (Yoga / Poci) ----------
  function renderLiveGeneric() {
    const category = state.activeGenericCategory;
    const color = genericColor(category);
    els.root.innerHTML = `<div class="tr-live-header tr-live-header-yoga">
        <button class="tr-icon-btn" onclick="App.closeLive()">${iconClose()}</button>
        <div class="tr-live-title-block">
          <div class="tr-live-title">${esc(genericLabel(category))}</div>
        </div>
        <div style="width:34px"></div>
      </div>
      <div class="tr-live-body">
        <div class="tr-yoga-timer-card">
          <div class="tr-yoga-elapsed" id="generic-elapsed">${fmtTime(state.genericElapsed)}</div>
          <button class="tr-yoga-playpause" style="background:${color}" onclick="App.toggleGenericTimer()">
            ${state.genericRunning
              ? `<svg width="14" height="16" viewBox="0 0 14 16"><rect x="0" y="0" width="4" height="16" rx="1" fill="#0B0A0D"/><rect x="10" y="0" width="4" height="16" rx="1" fill="#0B0A0D"/></svg>`
              : iconPlayBig('#0B0A0D')}
          </button>
        </div>
        <div class="tr-yoga-notes-card">
          <div class="tr-yoga-notes-label">Notes</div>
          <textarea class="tr-yoga-notes-input" placeholder="Jot a quick note while it's fresh…" oninput="App.changeGenericNotes(this.value)">${esc(state.genericNotes)}</textarea>
        </div>
      </div>
      <div class="tr-yoga-footer">
        <button class="tr-btn-finish" style="background:${color}" ${state.saving ? 'disabled' : ''} onclick="App.finishGeneric()">${state.saving ? 'Saving…' : 'Finish Session'}</button>
      </div>`;
  }

  // ---------- Complete ----------
  function renderComplete() {
    const c = state.completionStats;
    const accent = c.type === 'functional' ? COLORS.functional : genericColor(c.category);
    els.root.innerHTML = `<div class="tr-complete-screen">
      <div class="tr-complete-icon" style="background:${accent}">
        <svg width="30" height="23" viewBox="0 0 30 23"><path d="M2 12L11 21L28 2" stroke="#0B0A0D" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div>
        <div class="tr-complete-heading">${c.type === 'functional' ? 'Workout Complete' : 'Session Complete'}</div>
        <div class="tr-complete-title">${esc(c.title)}</div>
      </div>
      <div class="tr-complete-stats">
        <div class="tr-complete-stat"><div class="tr-complete-stat-value">${fmtTime(c.durationSec)}</div><div class="tr-complete-stat-label">duration</div></div>
        ${c.type === 'functional' ? `
          <div class="tr-complete-stat"><div class="tr-complete-stat-value">${Math.round(c.volume || 0).toLocaleString()}</div><div class="tr-complete-stat-label">volume (kg)</div></div>
          <div class="tr-complete-stat" style="background:rgba(232,184,75,.1);border-color:rgba(232,184,75,.25)"><div class="tr-complete-stat-value" style="color:${COLORS.gold}">${c.prCount || 0}</div><div class="tr-complete-stat-label" style="color:${COLORS.gold}">new PRs</div></div>
        ` : ''}
      </div>
      <button class="tr-btn-home" onclick="App.backHome()">Back to Home</button>
    </div>`;
  }

  // ---------- dispatch ----------
  function renderScreen() {
    if (state.screen === 'home') renderHome();
    else if (state.screen === 'history') renderHistory();
    else if (state.screen === 'warmup') renderWarmup();
    else if (state.screen === 'live-functional') renderLiveFunctional();
    else if (state.screen === 'live-generic') renderLiveGeneric();
    else if (state.screen === 'complete') renderComplete();
  }
  function render() {
    renderScreen();
    renderTabBar();
    renderToast();
  }

  // ---------- actions ----------
  const App = {
    goTab(tab) {
      state.activeTab = tab;
      state.screen = tab;
      render();
    },
    startFunctional(key) {
      const workout = D.abWorkouts[key];
      state.activeWorkoutKey = key;
      state.exerciseIdx = 0;
      state.setLogs = {};
      state.exerciseNotesDraft = {};
      workout.exercises.forEach(ex => {
        state.setLogs[ex.id] = Array.from({ length: ex.target_sets }, () => ({ weight: ex.lastWeight || 0, reps: ex.lastReps || 0, done: false }));
        state.exerciseNotesDraft[ex.id] = D.exerciseNotes[ex.id] || '';
      });
      state.restActive = false;
      state.sessionStartMs = Date.now();
      state.sessionPRCount = 0;
      state.warmupIdx = 0;
      state.warmupSecLeft = WARMUP_ITEMS[0].duration || 0;
      state.screen = 'warmup';
      state.activeTab = null;
      saveSession();
      render();
    },
    startGeneric(category) {
      state.activeGenericCategory = category;
      state.genericRunning = true;
      state.genericElapsed = 0;
      state.genericNotes = '';
      state.sessionStartMs = Date.now();
      state.screen = 'live-generic';
      state.activeTab = null;
      saveSession();
      render();
    },
    closeLive() {
      clearSavedSession();
      state.restActive = false;
      state.genericRunning = false;
      state.screen = 'home';
      state.activeTab = 'home';
      render();
    },
    warmupNext() {
      if (state.warmupIdx < WARMUP_ITEMS.length - 1) {
        state.warmupIdx++;
        state.warmupSecLeft = WARMUP_ITEMS[state.warmupIdx].duration || 0;
        saveSession();
        renderScreen();
      } else {
        App.beginWorkoutAfterWarmup();
      }
    },
    skipWarmup() { App.beginWorkoutAfterWarmup(); },
    beginWorkoutAfterWarmup() {
      state.screen = 'live-functional';
      saveSession();
      renderScreen();
    },
    changeNote(exId, val) { state.exerciseNotesDraft[exId] = val; },
    changeSetField(exId, idx, field, val) {
      state.setLogs[exId][idx][field] = val === '' ? '' : Number(val);
      saveSession();
    },
    copyFirstSetToAll(exId) {
      const sets = state.setLogs[exId];
      const first = sets[0];
      sets.forEach((s, i) => {
        if (i > 0 && !s.done) {
          s.weight = first.weight;
          s.reps = first.reps;
        }
      });
      saveSession();
      renderScreen();
    },
    toggleSet(exId, idx) {
      const workout = D.abWorkouts[state.activeWorkoutKey];
      const ex = workout.exercises.find(e => e.id === exId);
      const set = state.setLogs[exId][idx];
      const willComplete = !set.done;
      set.done = willComplete;
      if (willComplete) {
        const w = Number(set.weight);
        if (D.showGamification && ex.lastWeight && w > ex.lastWeight) {
          set.isPR = true;
          state.sessionPRCount++;
          showToast('New PR — ' + fmtNum(w) + 'kg × ' + set.reps + ' on ' + ex.name.replace(' (Dumbbell)', ''), 'gold');
        }
        const allDone = state.setLogs[exId].every(s => s.done);
        const isLastExercise = state.exerciseIdx === workout.exercises.length - 1;
        if (D.autoRestTimer && !(allDone && isLastExercise)) {
          state.restActive = true;
          state.restSecLeft = D.restSeconds;
        }
      }
      saveSession();
      renderScreen();
    },
    skipRest() { state.restActive = false; renderScreen(); },
    prevExercise() {
      state.exerciseIdx = Math.max(0, state.exerciseIdx - 1);
      state.restActive = false;
      saveSession();
      renderScreen();
    },
    jumpNext() {
      const workout = D.abWorkouts[state.activeWorkoutKey];
      state.exerciseIdx = Math.min(workout.exercises.length - 1, state.exerciseIdx + 1);
      state.restActive = false;
      saveSession();
      renderScreen();
    },
    nextExercise() {
      if (state.saving) return;
      const workout = D.abWorkouts[state.activeWorkoutKey];
      if (state.exerciseIdx < workout.exercises.length - 1) {
        state.exerciseIdx++;
        state.restActive = false;
        saveSession();
        renderScreen();
      } else {
        App.finishWorkout();
      }
    },
    finishWorkout() {
      if (state.saving) return;
      state.saving = true;
      renderScreen();
      const workout = D.abWorkouts[state.activeWorkoutKey];
      const durationSec = Math.max(1, Math.round((Date.now() - state.sessionStartMs) / 1000));
      let volume = 0;
      const exercisesPayload = [];
      workout.exercises.forEach(ex => {
        const doneSets = state.setLogs[ex.id].filter(s => s.done);
        doneSets.forEach(s => { volume += (Number(s.weight) || 0) * (Number(s.reps) || 0); });
        if (doneSets.length) {
          exercisesPayload.push({ id: ex.id, name: ex.name, sets: doneSets.map(s => ({ weight: Number(s.weight), reps: Number(s.reps) })) });
        }
      });
      const notesPayload = {};
      Object.keys(state.exerciseNotesDraft).forEach(k => { if (state.exerciseNotesDraft[k]) notesPayload[k] = state.exerciseNotesDraft[k]; });

      fetch('/api/sessions/functional', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workoutKey: state.activeWorkoutKey, date: D.today, durationSec, exercises: exercisesPayload, notes: notesPayload }),
      }).then(r => r.json()).then(res => {
        state.saving = false;
        state.completionStats = { type: 'functional', title: workout.label, durationSec, volume, prCount: (res && res.prCount) || state.sessionPRCount };
        state.screen = 'complete';
        clearSavedSession();
        render();
      }).catch(() => {
        state.saving = false;
        showToast('Could not save — check your connection and try again', 'neutral');
        renderScreen();
      });
    },
    toggleGenericTimer() { state.genericRunning = !state.genericRunning; saveSession(); renderScreen(); },
    changeGenericNotes(val) { state.genericNotes = val; saveSession(); },
    finishGeneric() {
      if (state.saving) return;
      state.saving = true;
      renderScreen();
      const category = state.activeGenericCategory;
      const durationSec = state.genericElapsed || Math.max(1, Math.round((Date.now() - state.sessionStartMs) / 1000));
      fetch('/api/sessions/generic', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, date: D.today, durationSec, notes: state.genericNotes }),
      }).then(r => r.json()).then(() => {
        state.saving = false;
        state.completionStats = { type: 'generic', category, title: genericLabel(category), durationSec };
        state.screen = 'complete';
        state.genericRunning = false;
        clearSavedSession();
        render();
      }).catch(() => {
        state.saving = false;
        showToast('Could not save — check your connection and try again', 'neutral');
        renderScreen();
      });
    },
    toggleHistoryExpand(id) { state.expandedHistoryId = state.expandedHistoryId === id ? null : id; renderScreen(); },
    setHistoryFilter(f) { state.historyFilter = f; renderScreen(); },
    backHome() {
      // A session was just saved server-side — reload so Home/History
      // pick up the fresh streak, PR, history and chart data.
      window.location.href = '/';
    },
    resumeSaved() {
      const s = loadSavedSession();
      if (!s) { renderScreen(); return; }
      Object.assign(state, s);
      render();
    },
  };
  window.App = App;

  // ---------- ticking (rest timer / generic elapsed) ----------
  function startTicker() {
    tickTimer = setInterval(() => {
      if (state.screen === 'warmup' && WARMUP_ITEMS[state.warmupIdx].type === 'timed') {
        state.warmupSecLeft--;
        if (state.warmupSecLeft <= 0) {
          App.warmupNext();
        } else {
          const el = document.getElementById('warmup-count');
          if (el) el.textContent = fmtTime(state.warmupSecLeft);
          saveSession();
        }
      }
      if (state.screen === 'live-functional' && state.restActive) {
        state.restSecLeft--;
        if (state.restSecLeft <= 0) {
          state.restActive = false;
          state.restSecLeft = 0;
          renderScreen();
        } else {
          const ring = document.getElementById('rest-ring-fg');
          const label = document.getElementById('rest-ring-label');
          if (ring) ring.setAttribute('stroke-dashoffset', restRingOffset());
          if (label) label.textContent = fmtTime(state.restSecLeft);
        }
        saveSession();
      }
      if (state.screen === 'live-generic' && state.genericRunning) {
        state.genericElapsed++;
        const el = document.getElementById('generic-elapsed');
        if (el) el.textContent = fmtTime(state.genericElapsed);
        saveSession();
      }
    }, 1000);
  }

  render();
  startTicker();
})();
