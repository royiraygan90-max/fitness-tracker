# Pre-Workout Warmup Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 7-item warmup routine screen that appears before every Live Workout session, showing one item at a time with an auto-countdown for timed items and a Next button for rep-based items, then transitions automatically into the regular workout flow.

**Architecture:** Pure frontend change — `live_workout.html` gains a `#warmup-section` (shown first) and the existing workout UI is wrapped in `#workout-section` (hidden initially). A `renderWarmup()` function drives the warmup state; calling `startWorkout()` swaps visibility and calls the existing `renderExercise()`. No backend changes.

**Tech Stack:** Vanilla JS, Jinja2 templates, CSS custom properties (already defined in `static/style.css`).

---

## Files

- Modify: `static/style.css` — add `.lw-warmup-card`, `.lw-warmup-display`, `.lw-warmup-count`, `.lw-warmup-count-reps`, `.lw-warmup-reps-label`, `.lw-warmup-complete`, `.lw-warmup-skip`
- Modify: `templates/live_workout.html` — add `#warmup-section` HTML, wrap workout HTML in `#workout-section`, add `WARMUP_ITEMS` const + warmup JS functions, update fetch callback (remove `renderExercise()` call), replace bottom `renderExercise()` with `renderWarmup()`

---

### Task 1: Add warmup CSS to style.css

**Files:**
- Modify: `static/style.css` (append after `.lw-nav button:disabled` rule, before the `/* ===== MOBILE =====*/` block — currently around line 415)

- [ ] **Step 1: Open style.css and locate the insertion point**

  The block to insert after is (currently ends around line 415):
  ```css
  .lw-nav button:disabled { opacity: 0.35; cursor: not-allowed; transform: none !important; pointer-events: none; }
  ```
  Insert the new block immediately after it, before `/* ===== MOBILE ===== */`.

- [ ] **Step 2: Insert the warmup CSS block**

  Add exactly this block:
  ```css
  /* ===== WARMUP SCREEN ===== */
  .lw-warmup-card { text-align: center; padding: 2rem 1.25rem; }
  .lw-warmup-display { margin-top: 1.25rem; }
  .lw-warmup-count {
    display: block; font-size: 4.5rem; font-weight: 700;
    color: var(--accent); line-height: 1; font-variant-numeric: tabular-nums;
  }
  .lw-warmup-count-reps { color: #22c55e; }
  .lw-warmup-reps-label { display: block; font-size: 1.1rem; color: var(--text-muted); margin-top: 0.4rem; }
  .lw-warmup-complete { color: #22c55e !important; }
  .lw-warmup-skip { font-size: 0.82rem; padding: 0.5rem 0.875rem; opacity: 0.7; }
  .lw-warmup-skip:hover { opacity: 1; }
  ```

- [ ] **Step 3: Verify the file is syntactically correct**

  Run: `grep -n 'lw-warmup' /Users/royiraygan/Documents/Projects/fitness-tracker/static/style.css`

  Expected: 8 lines of output, each containing a `.lw-warmup-*` selector or property.

- [ ] **Step 4: Commit**

  ```bash
  git add static/style.css
  git commit -m "style: add warmup screen CSS classes"
  ```

---

### Task 2: Rewrite live_workout.html with warmup section

**Files:**
- Modify: `templates/live_workout.html` (full rewrite — changes span almost every part of the file)

The rewrite makes three structural changes:
1. Adds `<div id="warmup-section">` before the workout HTML
2. Wraps existing workout HTML in `<div id="workout-section" style="display:none">`
3. Adds warmup JS (WARMUP_ITEMS, state, functions) and updates existing JS (fetch callback, bottom call)

- [ ] **Step 1: Replace the entire file with the new content**

  Write `templates/live_workout.html` with this exact content:

  ```html
  {% extends "base.html" %}
  {% block title %}{{ "Workout A" if workout_type == "workout_a" else "Workout B" }} — Live{% endblock %}
  {% block content %}

  <div id="warmup-section">
    <div class="glass-card lw-header">
      <h1 class="lw-title">Warmup</h1>
      <div class="lw-progress-text" id="warmup-progress">1 / 7</div>
      <div class="lw-progress-bar">
        <div class="lw-progress-fill" id="warmup-progress-fill" style="width:0%"></div>
      </div>
    </div>
    <div class="glass-card lw-warmup-card">
      <h2 class="lw-ex-name" id="warmup-name"></h2>
      <div class="lw-ex-target" id="warmup-desc"></div>
      <div class="lw-warmup-display" id="warmup-timer-display" style="display:none">
        <span class="lw-warmup-count" id="warmup-timer-text">0:30</span>
      </div>
      <div class="lw-warmup-display" id="warmup-reps-display" style="display:none">
        <span class="lw-warmup-count lw-warmup-count-reps" id="warmup-reps-text">10</span>
        <span class="lw-warmup-reps-label">reps</span>
      </div>
    </div>
    <div class="lw-nav">
      <button class="btn-secondary lw-warmup-skip" id="warmup-skip">Skip Warmup</button>
      <button class="btn-primary" id="warmup-next" style="display:none">Next →</button>
    </div>
  </div>

  <div id="workout-section" style="display:none">
    <div class="glass-card lw-header">
      <h1 class="lw-title">{{ "Workout A 💪" if workout_type == "workout_a" else "Workout B 💪" }}</h1>
      <div class="lw-progress-text">Exercise <span id="ex-num">1</span> of <span id="ex-total">{{ exercises | length }}</span></div>
      <div class="lw-progress-bar">
        <div class="lw-progress-fill" id="progress-fill" style="width:0%"></div>
      </div>
      <div class="lw-sets-remaining" id="sets-remaining"></div>
    </div>

    <div class="glass-card lw-exercise-card">
      <h2 class="lw-ex-name" id="ex-name"></h2>
      <div class="lw-ex-target" id="ex-target"></div>
      <div class="lw-tip-box" id="ex-tip"></div>
      <a class="lw-yt-btn" id="ex-youtube" href="#" target="_blank" rel="noopener noreferrer">🎥 Watch on YouTube</a>
    </div>

    <div class="glass-card lw-sets-card">
      <div class="card-title">Sets</div>
      <div class="lw-last-summary" id="ex-last" style="display:none"></div>
      <div id="sets-container"></div>
      <div class="lw-timer" id="rest-timer" title="Tap to dismiss">
        <span id="timer-text">Rest: 1:00</span>
        <span class="lw-timer-dismiss">tap to dismiss</span>
      </div>
    </div>

    <div class="lw-nav">
      <button class="btn-secondary" id="btn-prev" disabled>← Previous</button>
      <button class="btn-primary" id="btn-next" disabled>Next Exercise →</button>
    </div>
  </div>

  <script>
  const WORKOUT_TYPE = {{ workout_type | tojson }};
  const TODAY = {{ today | tojson }};
  const EXERCISES = {{ exercises | tojson }};
  const WARMUP_ITEMS = [
    { name: 'Arm Circles', desc: 'Forward + backward', type: 'timed', duration: 30 },
    { name: 'Shoulder Rotations', desc: 'Scapular prep', type: 'timed', duration: 30 },
    { name: 'Hip Circles', desc: 'Full hip mobility', type: 'timed', duration: 30 },
    { name: 'Leg Swings', desc: 'Forward / back, both legs', type: 'timed', duration: 30 },
    { name: 'Bodyweight Squat', desc: 'Slow and controlled', type: 'reps', reps: 10 },
    { name: 'Dead Hang / Scapular Shrug', desc: 'Shoulder joint prep', type: 'timed', duration: 20 },
    { name: 'Inchworm', desc: 'Hamstrings → plank → push-up → stand', type: 'reps', reps: 4 },
  ];

  // ===== WARMUP STATE =====
  let warmupIdx = 0;
  let warmupTimerInterval = null;

  // ===== WORKOUT STATE =====
  let currentIdx = 0;
  const state = EXERCISES.map(function(ex) {
    return {sets: Array.from({length: ex.sets}, function() { return {checked: false, reps: '', weight: ''}; })};
  });
  let timerInterval = null;
  let timerSeconds = 0;
  let previousData = {};

  fetch('/api/workouts/previous/' + WORKOUT_TYPE)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data && data.exercises) {
        data.exercises.forEach(function(ex) { previousData[ex.name] = ex; });
      }
    })
    .catch(function() {});

  // ===== WARMUP FUNCTIONS =====

  function stopWarmupTimer() {
    if (warmupTimerInterval) { clearInterval(warmupTimerInterval); warmupTimerInterval = null; }
  }

  function renderWarmup() {
    const item = WARMUP_ITEMS[warmupIdx];
    document.getElementById('warmup-progress').textContent = (warmupIdx + 1) + ' / ' + WARMUP_ITEMS.length;
    document.getElementById('warmup-progress-fill').style.width = ((warmupIdx / WARMUP_ITEMS.length) * 100) + '%';
    document.getElementById('warmup-name').textContent = item.name;
    document.getElementById('warmup-name').className = 'lw-ex-name';
    document.getElementById('warmup-desc').textContent = item.desc;

    const timerDisplay = document.getElementById('warmup-timer-display');
    const repsDisplay = document.getElementById('warmup-reps-display');
    const nextBtn = document.getElementById('warmup-next');

    stopWarmupTimer();

    if (item.type === 'timed') {
      timerDisplay.style.display = 'block';
      repsDisplay.style.display = 'none';
      nextBtn.style.display = 'none';
      let secs = item.duration;
      document.getElementById('warmup-timer-text').textContent = formatTime(secs);
      warmupTimerInterval = setInterval(function() {
        secs--;
        document.getElementById('warmup-timer-text').textContent = formatTime(secs);
        if (secs <= 0) {
          stopWarmupTimer();
          advanceWarmup();
        }
      }, 1000);
    } else {
      timerDisplay.style.display = 'none';
      repsDisplay.style.display = 'block';
      document.getElementById('warmup-reps-text').textContent = item.reps;
      nextBtn.style.display = 'flex';
      nextBtn.textContent = warmupIdx === WARMUP_ITEMS.length - 1 ? 'Done ✓' : 'Next →';
    }
  }

  function advanceWarmup() {
    stopWarmupTimer();
    if (warmupIdx < WARMUP_ITEMS.length - 1) {
      warmupIdx++;
      renderWarmup();
    } else {
      showWarmupComplete();
    }
  }

  function showWarmupComplete() {
    document.getElementById('warmup-name').textContent = 'Warmup Complete ✓';
    document.getElementById('warmup-name').className = 'lw-ex-name lw-warmup-complete';
    document.getElementById('warmup-desc').textContent = '';
    document.getElementById('warmup-timer-display').style.display = 'none';
    document.getElementById('warmup-reps-display').style.display = 'none';
    document.getElementById('warmup-next').style.display = 'none';
    document.getElementById('warmup-skip').style.display = 'none';
    document.getElementById('warmup-progress-fill').style.width = '100%';
    document.getElementById('warmup-progress').textContent = WARMUP_ITEMS.length + ' / ' + WARMUP_ITEMS.length;
    setTimeout(startWorkout, 1500);
  }

  function startWorkout() {
    stopWarmupTimer();
    document.getElementById('warmup-section').style.display = 'none';
    document.getElementById('workout-section').style.display = 'block';
    renderExercise();
  }

  document.getElementById('warmup-next').addEventListener('click', advanceWarmup);
  document.getElementById('warmup-skip').addEventListener('click', startWorkout);

  // ===== WORKOUT FUNCTIONS =====

  function getTotalSetsRemaining() {
    let total = 0;
    state.forEach(function(ex) { ex.sets.forEach(function(s) { if (!s.checked) total++; }); });
    return total;
  }

  function formatTime(s) {
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  }

  function stopRestTimer() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    const el = document.getElementById('rest-timer');
    el.style.display = 'none';
    el.classList.remove('ready');
  }

  function startRestTimer() {
    stopRestTimer();
    timerSeconds = 60;
    const timerEl = document.getElementById('rest-timer');
    const timerText = document.getElementById('timer-text');
    timerEl.style.display = 'flex';
    timerText.textContent = 'Rest: ' + formatTime(timerSeconds);
    timerInterval = setInterval(function() {
      timerSeconds--;
      if (timerSeconds <= 0) {
        clearInterval(timerInterval);
        timerInterval = null;
        timerEl.classList.add('ready');
        timerText.textContent = 'Ready! ✓';
      } else {
        timerText.textContent = 'Rest: ' + formatTime(timerSeconds);
      }
    }, 1000);
  }

  function updateNav() {
    const nextBtn = document.getElementById('btn-next');
    const isLast = currentIdx === EXERCISES.length - 1;
    const hasChecked = state[currentIdx].sets.some(function(s) { return s.checked; });
    document.getElementById('btn-prev').disabled = currentIdx === 0;
    nextBtn.disabled = !hasChecked;
    nextBtn.textContent = isLast ? '✓ Finish Workout' : 'Next Exercise →';
  }

  function renderExercise() {
    const ex = EXERCISES[currentIdx];
    const exState = state[currentIdx];

    document.getElementById('ex-num').textContent = currentIdx + 1;
    document.getElementById('progress-fill').style.width = ((currentIdx / EXERCISES.length) * 100) + '%';
    document.getElementById('sets-remaining').textContent = getTotalSetsRemaining() + ' sets remaining';
    document.getElementById('ex-name').textContent = ex.name;
    document.getElementById('ex-target').textContent = ex.sets + ' sets × ' + ex.reps + ' reps';
    document.getElementById('ex-tip').textContent = ex.tip;
    document.getElementById('ex-youtube').href = ex.youtube;

    const lastEl = document.getElementById('ex-last');
    const prev = previousData[ex.name];
    if (prev && prev.reps && prev.reps.length > 0) {
      let lastText = 'LAST: ' + prev.sets + ' × ' + prev.reps[0];
      if (prev.weights && prev.weights.length > 0 && prev.weights[0]) {
        lastText += ' @ ' + prev.weights[0] + ' kg';
      }
      lastEl.textContent = lastText;
      lastEl.style.display = 'block';
    } else {
      lastEl.style.display = 'none';
    }

    const container = document.getElementById('sets-container');
    container.innerHTML = '';
    exState.sets.forEach(function(setData, setIdx) {
      const row = document.createElement('div');
      row.className = 'lw-set-row' + (setData.checked ? ' done' : '');

      const label = document.createElement('label');
      label.className = 'lw-set-label';

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = setData.checked;

      const mark = document.createElement('span');
      mark.className = 'lw-set-checkmark';

      const numSpan = document.createElement('span');
      numSpan.className = 'lw-set-num';
      numSpan.textContent = 'Set ' + (setIdx + 1);

      label.appendChild(cb);
      label.appendChild(mark);
      label.appendChild(numSpan);

      const repsInput = document.createElement('input');
      repsInput.type = 'number';
      repsInput.className = 'lw-reps-input';
      repsInput.placeholder = ex.reps;
      repsInput.value = setData.reps;
      repsInput.min = '0';
      repsInput.setAttribute('aria-label', 'Reps for set ' + (setIdx + 1));

      const weightInput = document.createElement('input');
      weightInput.type = 'number';
      weightInput.className = 'lw-weight-input';
      weightInput.placeholder = 'ק"ג';
      weightInput.value = setData.weight;
      weightInput.min = '0';
      weightInput.step = '0.5';
      weightInput.setAttribute('aria-label', 'Weight for set ' + (setIdx + 1));

      const weightUnit = document.createElement('span');
      weightUnit.className = 'lw-weight-unit';
      weightUnit.textContent = 'ק"ג';

      cb.addEventListener('change', function() {
        setData.checked = cb.checked;
        setData.reps = repsInput.value;
        setData.weight = weightInput.value;
        row.classList.toggle('done', cb.checked);
        if (cb.checked) startRestTimer();
        updateNav();
        document.getElementById('sets-remaining').textContent = getTotalSetsRemaining() + ' sets remaining';
      });

      repsInput.addEventListener('input', function() { setData.reps = repsInput.value; });
      weightInput.addEventListener('input', function() { setData.weight = weightInput.value; });

      row.appendChild(label);
      row.appendChild(repsInput);
      row.appendChild(weightInput);
      row.appendChild(weightUnit);
      container.appendChild(row);
    });

    stopRestTimer();
    updateNav();
  }

  document.getElementById('btn-prev').addEventListener('click', function() {
    if (currentIdx > 0) { currentIdx--; renderExercise(); }
  });

  document.getElementById('btn-next').addEventListener('click', function() {
    if (currentIdx < EXERCISES.length - 1) {
      currentIdx++;
      renderExercise();
    } else {
      finishWorkout();
    }
  });

  document.getElementById('rest-timer').addEventListener('click', stopRestTimer);

  function finishWorkout() {
    const exercises = [];
    EXERCISES.forEach(function(ex, i) {
      const checked = state[i].sets.filter(function(s) { return s.checked; });
      if (checked.length === 0) return;
      exercises.push({
        name: ex.name,
        sets: checked.length,
        reps: checked.map(function(s) { return s.reps || ex.reps; }).join(','),
        weights: checked.map(function(s) { return s.weight || ''; }).join(',')
      });
    });

    const nextBtn = document.getElementById('btn-next');
    nextBtn.disabled = true;
    nextBtn.textContent = 'Saving…';

    fetch('/log/live', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({workout_type: WORKOUT_TYPE, date: TODAY, exercises: exercises})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.success) {
        window.location.href = data.redirect;
      } else {
        alert('Failed to save workout. Please try again.');
        nextBtn.disabled = false;
        nextBtn.textContent = '✓ Finish Workout';
      }
    })
    .catch(function() {
      alert('Network error. Please try again.');
      nextBtn.disabled = false;
      nextBtn.textContent = '✓ Finish Workout';
    });
  }

  renderWarmup();
  </script>
  {% endblock %}
  ```

- [ ] **Step 2: Verify the file was written correctly**

  Run: `grep -c 'warmup' /Users/royiraygan/Documents/Projects/fitness-tracker/templates/live_workout.html`

  Expected: a number ≥ 20 (many references to warmup elements and functions).

- [ ] **Step 3: Verify `renderExercise()` is NOT called at the bottom (only `renderWarmup()` should be)**

  Run: `tail -5 /Users/royiraygan/Documents/Projects/fitness-tracker/templates/live_workout.html`

  Expected: last JS line before `</script>` is `renderWarmup();`

- [ ] **Step 4: Run existing tests to confirm all 13 pass**

  Run: `cd /Users/royiraygan/Documents/Projects/fitness-tracker && python -m pytest tests/test_app.py -v`

  Expected: `13 passed` — the live workout page load test (`test_live_workout_page_loads`) confirms the template still renders without errors.

- [ ] **Step 5: Commit**

  ```bash
  git add templates/live_workout.html
  git commit -m "feat: add pre-workout warmup screen with countdown timer and rep counter"
  ```

---

### Task 3: Final verification

**Files:** None — read-only verification pass.

- [ ] **Step 1: Run full test suite**

  Run: `cd /Users/royiraygan/Documents/Projects/fitness-tracker && python -m pytest tests/test_app.py -v`

  Expected output:
  ```
  test_dashboard_loads PASSED
  test_log_page_loads PASSED
  test_history_page_loads PASSED
  test_log_workout_post PASSED
  test_log_workout_a_post PASSED
  test_live_workout_page_loads PASSED
  test_live_workout_invalid_type_redirects PASSED
  test_log_live_post PASSED
  test_delete_workout PASSED
  test_previous_workout_none PASSED
  test_previous_workout_invalid_type PASSED
  test_previous_workout_returns_last PASSED
  test_log_live_with_weights PASSED
  13 passed
  ```

  If any test fails, do not proceed — fix the failure first.

- [ ] **Step 2: Confirm warmup CSS classes are present in style.css**

  Run: `grep -c 'lw-warmup' /Users/royiraygan/Documents/Projects/fitness-tracker/static/style.css`

  Expected: ≥ 8

- [ ] **Step 3: Confirm workout-section and warmup-section exist in live_workout.html**

  Run: `grep -E 'id="(warmup|workout)-section"' /Users/royiraygan/Documents/Projects/fitness-tracker/templates/live_workout.html`

  Expected:
  ```
  <div id="warmup-section">
  <div id="workout-section" style="display:none">
  ```

- [ ] **Step 4: Commit all remaining changes (if any unstaged)**

  ```bash
  git status
  ```

  All changes should already be committed from Tasks 1 and 2. If `git status` shows clean working tree, done. If not, add and commit the remaining files.
