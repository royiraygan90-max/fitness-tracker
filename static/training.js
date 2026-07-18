(() => {
  const D = window.__INITIAL__;
  const COLORS = { functional: '#2F82FF', yoga: '#6FBFA0', gold: '#E8B84B' };
  const RING_CIRC = 163.36;
  const SAVE_KEY = 'training_live_session';

  const state = {
    screen: 'home',
    activeTab: 'home',
    planSelectedDayIdx: D.todayIdx,
    activeWorkoutKey: null,
    activeYogaKey: null,
    exerciseIdx: 0,
    setLogs: {},
    exerciseNotesDraft: {},
    restActive: false,
    restSecLeft: 0,
    yogaRunning: false,
    yogaElapsed: 0,
    yogaNotes: '',
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

  // ---------- persistence ----------
  function saveSession() {
    if (state.screen !== 'live-functional' && state.screen !== 'live-yoga') return;
    localStorage.setItem(SAVE_KEY, JSON.stringify({
      screen: state.screen, activeWorkoutKey: state.activeWorkoutKey, activeYogaKey: state.activeYogaKey,
      exerciseIdx: state.exerciseIdx, setLogs: state.setLogs, exerciseNotesDraft: state.exerciseNotesDraft,
      restActive: state.restActive, restSecLeft: state.restSecLeft,
      yogaRunning: state.yogaRunning, yogaElapsed: state.yogaElapsed, yogaNotes: state.yogaNotes,
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
  function iconPlan(c) { return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="4" y="5" width="16" height="15" rx="2.5" stroke="${c}" stroke-width="1.8"/><path d="M4 10H20M8 3V6M16 3V6" stroke="${c}" stroke-width="1.8" stroke-linecap="round"/></svg>`; }
  function iconHistory(c) { return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8.5" stroke="${c}" stroke-width="1.8"/><path d="M12 7.5V12L15.5 14.5" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }
  function iconChevron(c) { return `<svg width="7" height="12" viewBox="0 0 7 12"><path d="M1 1L6 6L1 11" stroke="${c || 'rgba(245,243,239,.3)'}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }
  function iconClose() { return `<svg width="13" height="13" viewBox="0 0 14 14"><path d="M1 1L13 13M13 1L1 13" stroke="rgba(245,243,239,.8)" stroke-width="1.7" stroke-linecap="round"/></svg>`; }
  function iconPlaySmall(c) { return `<svg width="10" height="11" viewBox="0 0 10 11"><path d="M0 0L10 5.5L0 11V0Z" fill="${c}"/></svg>`; }
  function iconPlayBig() { return `<svg width="16" height="18" viewBox="0 0 16 18"><path d="M0 0L16 9L0 18V0Z" fill="#F5F3EF"/></svg>`; }
  function iconCheck() { return `<svg width="12" height="10" viewBox="0 0 14 11"><path d="M1 5.5L5 9.5L13 1.5" stroke="#0B0A0D" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`; }

  // ---------- tab bar ----------
  function renderTabBar() {
    const show = ['home', 'plan', 'history'].includes(state.screen);
    if (!show) { els.tabBar.innerHTML = ''; els.tabBar.style.display = 'none'; return; }
    els.tabBar.style.display = 'flex';
    const tabs = [['home', 'Home', iconHome], ['plan', 'Plan', iconPlan], ['history', 'History', iconHistory]];
    els.tabBar.innerHTML = tabs.map(([key, label, icon]) => {
      const active = state.activeTab === key;
      const color = active ? '#F5F3EF' : 'rgba(245,243,239,.35)';
      return `<button class="tr-tab" onclick="App.goTab('${key}')">${icon(color)}<span class="tr-tab-label" style="color:${color}">${label}</span></button>`;
    }).join('');
  }

  // ---------- shared: week strip ----------
  function weekStrip() {
    return `<div class="tr-week-strip">${D.weekDays.map(d => {
      const ring = d.isToday ? 'box-shadow:0 0 0 2px rgba(245,243,239,.55);' : '';
      const bg = d.done ? d.accent : 'transparent';
      const textColor = d.done ? '#0B0A0D' : (d.planType === 'rest' ? 'rgba(245,243,239,.4)' : '#F5F3EF');
      const selBg = d.idx === state.planSelectedDayIdx ? 'rgba(255,255,255,.06)' : 'transparent';
      return `<button class="tr-week-day" style="background:${selBg}" onclick="App.selectPlanDay(${d.idx})">
        <span class="tr-week-day-letter">${d.letter}</span>
        <div class="tr-week-day-circle" style="border-color:${d.accent};background:${bg};${ring}">
          <span class="tr-week-day-num" style="color:${textColor}">${d.dateNum}</span>
        </div>
      </button>`;
    }).join('')}</div>`;
  }

  function lastSessionMetaLine(s) {
    if (s.category === 'functional') {
      let line = s.exercises.length + ' exercises';
      if (s.prCount) line += ' · ' + s.prCount + ' PR' + (s.prCount > 1 ? 's' : '');
      return line;
    }
    return (s.durationMin ? s.durationMin + ' min · ' : '') + (s.focusTags || []).join(', ');
  }

  // ---------- Home ----------
  function renderHome() {
    const tp = D.todayPlan;
    const resume = loadSavedSession();
    const resumeBanner = resume ? `<div class="tr-resume-banner">
      <span class="tr-resume-text">Unfinished ${resume.screen === 'live-yoga' ? 'yoga session' : 'workout'} in progress</span>
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

      <div class="tr-card">
        <div class="tr-card-accent-bar" style="background:${tp.accent}"></div>
        <div class="tr-card-eyebrow" style="color:${tp.accent}">${esc(tp.eyebrow)}</div>
        <div class="tr-card-title">${esc(tp.title)}</div>
        <div class="tr-card-meta">${esc(tp.meta)}</div>
        ${tp.preview ? `<div class="tr-card-preview">${esc(tp.preview)}</div>` : ''}
        ${tp.showCta ? `<button class="tr-btn-cta" style="background:${tp.accent}" onclick="App.startToday()">${esc(tp.ctaLabel)}</button>` : ''}
      </div>

      ${weekStrip()}

      <div class="tr-stat-row">
        <div class="tr-stat-card"><div class="tr-stat-value">${esc(D.statWeek)}</div><div class="tr-stat-label">this week</div></div>
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

  // ---------- Plan ----------
  function renderPlan() {
    const detail = D.planByDay[state.planSelectedDayIdx];
    els.root.innerHTML = `<div class="tr-screen"><div class="tr-screen-pad">
      <div>
        <div class="tr-eyebrow-date">THIS WEEK</div>
        <div class="tr-greeting">${esc(D.weekRangeLabel)}</div>
      </div>
      ${weekStrip()}
      <div class="tr-card">
        <div class="tr-card-accent-bar" style="background:${detail.accent}"></div>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <div class="tr-card-eyebrow" style="color:${detail.accent}">${esc(detail.eyebrow)}</div>
          ${detail.hasStatus ? `<div class="tr-status-tag">${esc(detail.statusTag)}</div>` : ''}
        </div>
        <div class="tr-card-title">${esc(detail.title)}</div>
        <div class="tr-card-meta">${esc(detail.meta)}</div>
        ${detail.focusTags.length ? `<div class="tr-focus-tags">${detail.focusTags.map(t => `<span class="tr-focus-tag">${esc(t)}</span>`).join('')}</div>` : ''}
        ${detail.exercises.length ? `<div class="tr-plan-exercises">${detail.exercises.map(ex => `
          <div class="tr-plan-ex-row"><span class="tr-plan-ex-name">${esc(ex.name)}</span><span class="tr-plan-ex-target">${esc(ex.target)}</span></div>
        `).join('')}</div>` : ''}
        ${detail.showCta ? `<button class="tr-btn-cta" style="background:${detail.accent}" onclick="App.startToday()">${esc(detail.ctaLabel)}</button>` : ''}
      </div>
    </div></div>`;
  }

  // ---------- History ----------
  function renderHistory() {
    const filtered = D.history.filter(h => state.historyFilter === 'all' || h.category === state.historyFilter);
    els.root.innerHTML = `<div class="tr-screen"><div class="tr-screen-pad">
      <div class="tr-greeting" style="margin-top:0">History</div>
      ${D.squatChart.length ? `<div class="tr-chart-card">
        <div class="tr-chart-head"><div class="tr-chart-title">Squat (Dumbbell)</div><div class="tr-chart-sub">last ${D.squatChart.length} sessions</div></div>
        <div class="tr-chart-bars">${D.squatChart.map(b => `
          <div class="tr-chart-bar-col">
            <span class="tr-chart-bar-val" style="color:${b.valueColor}">${esc(b.value)}</span>
            <div class="tr-chart-bar" style="height:${b.heightPx}px;background:${b.barColor}"></div>
            <span class="tr-chart-bar-label">${esc(b.label)}</span>
          </div>`).join('')}</div>
      </div>` : ''}

      <div class="tr-filter-row">
        ${['all', 'functional', 'yoga'].map(key => {
          const active = state.historyFilter === key;
          const label = key === 'all' ? 'All' : (key === 'functional' ? 'Functional' : 'Yoga');
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
    } else if (h.category === 'yoga') {
      metaLine = (h.durationMin ? h.durationMin + ' min · ' : '') + (h.focusTags || []).join(', ');
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

  // ---------- Live functional ----------
  function renderLiveFunctional() {
    const workout = D.workouts[state.activeWorkoutKey];
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
            <div class="tr-live-title">${esc(workout.name)}</div>
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
          <button class="tr-demo-btn" style="border:1px solid rgba(47,130,255,.35);color:${COLORS.functional}" onclick="App.watchDemo()">${iconPlaySmall(COLORS.functional)} Watch demo</button>
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
          <div>${sets.map((s, i) => setRow(ex, s, i)).join('')}</div>
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

  function setRow(ex, s, i) {
    const done = s.done;
    const numBg = done ? COLORS.functional : '#1E1D24';
    const checkBorder = done ? (s.isPR ? COLORS.gold : COLORS.functional) : 'rgba(255,255,255,.2)';
    const checkBg = done ? (s.isPR ? COLORS.gold : COLORS.functional) : 'transparent';
    const checkIconColor = done ? '#0B0A0D' : 'rgba(255,255,255,.25)';
    return `<div class="tr-set-row" style="opacity:${done ? 0.5 : 1}">
      <div class="tr-set-num-circle" style="background:${numBg}">
        ${done ? iconCheck() : `<span class="tr-set-num-text">${i + 1}</span>`}
      </div>
      <div class="tr-set-inputs">
        <div class="tr-set-field">
          <input type="number" value="${esc(s.weight)}" ${done ? 'disabled' : ''} oninput="App.changeSetField('${ex.id}',${i},'weight',this.value)"/>
          <span class="tr-set-field-unit">KG</span>
        </div>
        <div class="tr-set-field">
          <input type="number" class="tr-reps-field" value="${esc(s.reps)}" ${done ? 'disabled' : ''} oninput="App.changeSetField('${ex.id}',${i},'reps',this.value)"/>
          <span class="tr-set-field-unit">REPS</span>
        </div>
      </div>
      <button class="tr-set-check" style="border-color:${checkBorder};background:${checkBg}" onclick="App.toggleSet('${ex.id}',${i})">
        <svg width="15" height="11" viewBox="0 0 16 12"><path d="M1 6L6 11L15 1" stroke="${checkIconColor}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>`;
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

  // ---------- Live yoga ----------
  function renderLiveYoga() {
    const y = D.yogaSessions[state.activeYogaKey];
    els.root.innerHTML = `<div class="tr-live-header tr-live-header-yoga">
        <button class="tr-icon-btn" onclick="App.closeLive()">${iconClose()}</button>
        <div class="tr-live-title-block">
          <div class="tr-live-title">${esc(y.title)}</div>
          <div class="tr-live-sub">${esc(y.coach)}</div>
        </div>
        <div style="width:34px"></div>
      </div>
      <div class="tr-live-body">
        <div class="tr-yoga-video">
          <div class="tr-yoga-video-frame">Video thumbnail</div>
          <div class="tr-yoga-play-overlay"><div class="tr-yoga-play-circle">${iconPlayBig()}</div></div>
        </div>
        <div class="tr-yoga-tags-row">
          <div class="tr-focus-tags">${y.focus.map(t => `<span class="tr-focus-tag">${esc(t)}</span>`).join('')}</div>
          <button class="tr-yt-btn" style="border:1px solid rgba(111,191,160,.35);color:${COLORS.yoga}" onclick="App.watchDemo()">Watch on YouTube</button>
        </div>
        <div class="tr-yoga-timer-card">
          <div class="tr-yoga-elapsed" id="yoga-elapsed">${fmtTime(state.yogaElapsed)}</div>
          <button class="tr-yoga-playpause" style="background:${COLORS.yoga}" onclick="App.toggleYogaTimer()">
            ${state.yogaRunning
              ? `<svg width="14" height="16" viewBox="0 0 14 16"><rect x="0" y="0" width="4" height="16" rx="1" fill="#0B0A0D"/><rect x="10" y="0" width="4" height="16" rx="1" fill="#0B0A0D"/></svg>`
              : iconPlayBig().replace('#F5F3EF', '#0B0A0D')}
          </button>
        </div>
        <div class="tr-yoga-notes-card">
          <div class="tr-yoga-notes-label">What did we work on today?</div>
          <textarea class="tr-yoga-notes-input" placeholder="Jot a quick note while it's fresh…" oninput="App.changeYogaNotes(this.value)">${esc(state.yogaNotes)}</textarea>
        </div>
      </div>
      <div class="tr-yoga-footer">
        <button class="tr-btn-finish" style="background:${COLORS.yoga}" ${state.saving ? 'disabled' : ''} onclick="App.finishYoga()">${state.saving ? 'Saving…' : 'Finish Session'}</button>
      </div>`;
  }

  // ---------- Complete ----------
  function renderComplete() {
    const c = state.completionStats;
    const accent = c.type === 'functional' ? COLORS.functional : COLORS.yoga;
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
        ` : `<div class="tr-complete-stat" style="flex:2;display:flex;align-items:center;justify-content:center;gap:6px;flex-wrap:wrap">${(c.focusTags || []).map(t => `<span class="tr-focus-tag">${esc(t)}</span>`).join('')}</div>`}
      </div>
      <button class="tr-btn-home" onclick="App.backHome()">Back to Home</button>
    </div>`;
  }

  // ---------- dispatch ----------
  function renderScreen() {
    if (state.screen === 'home') renderHome();
    else if (state.screen === 'plan') renderPlan();
    else if (state.screen === 'history') renderHistory();
    else if (state.screen === 'live-functional') renderLiveFunctional();
    else if (state.screen === 'live-yoga') renderLiveYoga();
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
    selectPlanDay(idx) { state.planSelectedDayIdx = idx; renderScreen(); },
    startToday() {
      const tp = state.screen === 'plan' ? D.planByDay[state.planSelectedDayIdx] : D.todayPlan;
      if (tp.type === 'functional') App.startFunctional(tp.workoutKey);
      else if (tp.type === 'yoga') App.startYoga(tp.yogaKey);
    },
    startFunctional(key) {
      const workout = D.workouts[key];
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
      state.screen = 'live-functional';
      state.activeTab = null;
      saveSession();
      render();
    },
    startYoga(key) {
      state.activeYogaKey = key;
      state.yogaRunning = true;
      state.yogaElapsed = 0;
      state.yogaNotes = '';
      state.sessionStartMs = Date.now();
      state.screen = 'live-yoga';
      state.activeTab = null;
      saveSession();
      render();
    },
    closeLive() {
      clearSavedSession();
      state.restActive = false;
      state.yogaRunning = false;
      state.screen = 'home';
      state.activeTab = 'home';
      render();
    },
    changeNote(exId, val) { state.exerciseNotesDraft[exId] = val; },
    changeSetField(exId, idx, field, val) {
      state.setLogs[exId][idx][field] = val === '' ? '' : Number(val);
      saveSession();
    },
    toggleSet(exId, idx) {
      const workout = D.workouts[state.activeWorkoutKey];
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
      const workout = D.workouts[state.activeWorkoutKey];
      state.exerciseIdx = Math.min(workout.exercises.length - 1, state.exerciseIdx + 1);
      state.restActive = false;
      saveSession();
      renderScreen();
    },
    nextExercise() {
      if (state.saving) return;
      const workout = D.workouts[state.activeWorkoutKey];
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
      const workout = D.workouts[state.activeWorkoutKey];
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
        state.completionStats = { type: 'functional', title: workout.name, durationSec, volume, prCount: (res && res.prCount) || state.sessionPRCount };
        state.screen = 'complete';
        clearSavedSession();
        render();
      }).catch(() => {
        state.saving = false;
        showToast('Could not save — check your connection and try again', 'neutral');
        renderScreen();
      });
    },
    watchDemo() { showToast('Demo video would open on YouTube', 'neutral'); },
    toggleYogaTimer() { state.yogaRunning = !state.yogaRunning; saveSession(); renderScreen(); },
    changeYogaNotes(val) { state.yogaNotes = val; saveSession(); },
    finishYoga() {
      if (state.saving) return;
      state.saving = true;
      renderScreen();
      const y = D.yogaSessions[state.activeYogaKey];
      const durationSec = state.yogaElapsed || Math.max(1, Math.round((Date.now() - state.sessionStartMs) / 1000));
      fetch('/api/sessions/yoga', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yogaKey: state.activeYogaKey, date: D.today, durationSec, notes: state.yogaNotes }),
      }).then(r => r.json()).then(() => {
        state.saving = false;
        state.completionStats = { type: 'yoga', title: y.title, durationSec, focusTags: y.focus };
        state.screen = 'complete';
        state.yogaRunning = false;
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
      // A session was just saved server-side — reload so Home/Plan/History
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

  // ---------- ticking (rest timer / yoga elapsed) ----------
  function startTicker() {
    tickTimer = setInterval(() => {
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
      if (state.screen === 'live-yoga' && state.yogaRunning) {
        state.yogaElapsed++;
        const el = document.getElementById('yoga-elapsed');
        if (el) el.textContent = fmtTime(state.yogaElapsed);
        saveSession();
      }
    }, 1000);
  }

  render();
  startTicker();
})();
