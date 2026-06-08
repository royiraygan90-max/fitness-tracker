# Live Workout Weight Input & Previous Workout Display — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-set weight tracking to Live Workout Mode and display a compact "LAST: 3 × 8 @ 10 kg" summary per exercise drawn from the previous workout of the same type.

**Architecture:** Add a nullable `weight_kg TEXT` column to `workout_exercises` (comma-separated per-set values, same format as `reps`); add a startup migration helper; extend the `/log/live` POST, add a new `GET /api/workouts/previous/<workout_type>` endpoint, update history display, and update the live workout template to fetch previous data and render weight inputs.

**Tech Stack:** Python/Flask, SQLite (via `sqlite3`), Jinja2 templates, vanilla JS, CSS custom properties.

**Spec:** `docs/superpowers/specs/2026-06-08-live-workout-weight-and-history-design.md`

---

## File Map

| File | Change |
|------|--------|
| `app.py` | `_create_tables` (add column), new `_migrate_db`, `get_db` (call migration), new `/api/workouts/previous/<workout_type>`, update `/log/live`, update `/history` GROUP_CONCAT + parse loop |
| `templates/history.html` | Show `first_reps × first_weight kg` when weight present |
| `templates/live_workout.html` | Add `#ex-last` div; overhaul script: `previousData`, fetch, per-set weight input, LAST summary, updated `finishWorkout` |
| `static/style.css` | Add `.lw-last-summary`, `.lw-weight-input`, `.lw-weight-unit` |
| `tests/test_app.py` | Add 4 new tests |

---

## Task 1: Write the four new failing tests

**Files:**
- Modify: `tests/test_app.py`

- [ ] **Step 1: Add the four new tests to the end of `tests/test_app.py`**

```python
def test_previous_workout_none(client):
    import json
    r = client.get('/api/workouts/previous/workout_a')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data == {'previous': None}

def test_previous_workout_invalid_type(client):
    r = client.get('/api/workouts/previous/poci')
    assert r.status_code == 400

def test_previous_workout_returns_last(client):
    import json
    # Log an older workout_a
    client.post('/log/live',
        data=json.dumps({
            'workout_type': 'workout_a',
            'date': '2026-01-01',
            'exercises': [{'name': 'Pull-up', 'sets': 3, 'reps': '7,7,6', 'weights': '8,8,8'}]
        }),
        content_type='application/json')
    # Log a more recent workout_a
    client.post('/log/live',
        data=json.dumps({
            'workout_type': 'workout_a',
            'date': '2026-01-05',
            'exercises': [{'name': 'Pull-up', 'sets': 3, 'reps': '8,8,7', 'weights': '10,10,10'}]
        }),
        content_type='application/json')
    r = client.get('/api/workouts/previous/workout_a')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['date'] == '2026-01-05'
    assert len(data['exercises']) == 1
    ex = data['exercises'][0]
    assert ex['name'] == 'Pull-up'
    assert ex['reps'] == ['8', '8', '7']
    assert ex['weights'] == ['10', '10', '10']

def test_log_live_with_weights(client):
    import json
    payload = {
        'workout_type': 'workout_a',
        'date': '2026-06-08',
        'exercises': [
            {'name': 'Pull-up', 'sets': 3, 'reps': '8,8,7', 'weights': '10,10,10'}
        ]
    }
    r = client.post('/log/live',
        data=json.dumps(payload),
        content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    # Verify weights were stored via the previous-workout endpoint
    r2 = client.get('/api/workouts/previous/workout_a')
    data2 = json.loads(r2.data)
    assert data2['exercises'][0]['weights'] == ['10', '10', '10']
```

- [ ] **Step 2: Run the new tests to confirm they all fail (endpoints missing)**

```bash
cd /Users/royiraygan/Documents/Projects/fitness-tracker
pytest tests/test_app.py::test_previous_workout_none tests/test_app.py::test_previous_workout_invalid_type tests/test_app.py::test_previous_workout_returns_last tests/test_app.py::test_log_live_with_weights -v
```

Expected: all 4 FAIL (404 for missing endpoint, or column errors).

---

## Task 2: Schema — add `weight_kg` column + migration helper

**Files:**
- Modify: `app.py` — `_create_tables`, new `_migrate_db`, `get_db`

- [ ] **Step 1: Update `_create_tables` to include `weight_kg TEXT` in the `workout_exercises` table**

Replace the existing `_create_tables` body in `app.py` (the `executescript` string):

```python
def _create_tables(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL,
            sets INTEGER,
            reps TEXT,
            weight_kg TEXT,
            completed BOOLEAN DEFAULT 1
        );
    ''')
    conn.commit()
```

- [ ] **Step 2: Add `_migrate_db` function directly after `_create_tables`**

```python
def _migrate_db(conn):
    cols = [row[1] for row in conn.execute('PRAGMA table_info(workout_exercises)').fetchall()]
    if 'weight_kg' not in cols:
        conn.execute('ALTER TABLE workout_exercises ADD COLUMN weight_kg TEXT')
        conn.commit()
```

- [ ] **Step 3: Call `_migrate_db` in `get_db()`, immediately after `_create_tables`**

Find this line in `get_db()`:
```python
        _create_tables(g._db)
```
Replace it with:
```python
        _create_tables(g._db)
        _migrate_db(g._db)
```

- [ ] **Step 4: Run the full test suite to confirm existing tests still pass**

```bash
pytest tests/test_app.py -v
```

Expected: all original tests PASS; the 4 new tests still FAIL (endpoint missing).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add weight_kg column to workout_exercises with startup migration"
```

---

## Task 3: Add `GET /api/workouts/previous/<workout_type>` endpoint

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add the new route to `app.py`, after the `delete_workout` route (~line 359)**

```python
@app.route('/api/workouts/previous/<workout_type>')
def previous_workout(workout_type):
    if workout_type not in ('workout_a', 'workout_b'):
        return jsonify({'error': 'Invalid workout type'}), 400
    db = get_db()
    row = db.execute(
        'SELECT id, date FROM workouts WHERE type = ? ORDER BY date DESC, created_at DESC LIMIT 1',
        (workout_type,)
    ).fetchone()
    if not row:
        return jsonify({'previous': None})
    exercise_rows = db.execute(
        'SELECT exercise_name, sets, reps, weight_kg FROM workout_exercises WHERE workout_id = ?',
        (row['id'],)
    ).fetchall()
    exercises = []
    for ex in exercise_rows:
        reps_list = [r.strip() for r in ex['reps'].split(',')] if ex['reps'] else []
        weights_list = [w.strip() for w in ex['weight_kg'].split(',')] if ex['weight_kg'] else []
        exercises.append({
            'name': ex['exercise_name'],
            'sets': ex['sets'],
            'reps': reps_list,
            'weights': weights_list,
        })
    return jsonify({
        'workout_type': workout_type,
        'date': row['date'],
        'exercises': exercises,
    })
```

- [ ] **Step 2: Run the two tests that this endpoint satisfies**

```bash
pytest tests/test_app.py::test_previous_workout_none tests/test_app.py::test_previous_workout_invalid_type -v
```

Expected: both PASS. (`test_previous_workout_returns_last` and `test_log_live_with_weights` still FAIL because weights aren't stored yet.)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add GET /api/workouts/previous/<workout_type> endpoint"
```

---

## Task 4: Update `POST /log/live` to store weights

**Files:**
- Modify: `app.py` — the `log_live` route

- [ ] **Step 1: Update the exercise INSERT inside `log_live` to accept and store `weights`**

Find the exercise processing loop in `log_live` (currently around line 391–406). Replace the loop body with:

```python
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        name = str(ex.get('name', ''))[:200]
        if not name:
            continue
        try:
            sets_int = int(ex.get('sets', 0))
        except (TypeError, ValueError):
            sets_int = 0
        reps_val = str(ex.get('reps', ''))[:200]
        weights_val = str(ex.get('weights', '')).strip()[:200] or None
        db.execute(
            'INSERT INTO workout_exercises (workout_id, exercise_name, sets, reps, weight_kg, completed) VALUES (?,?,?,?,?,1)',
            (workout_id, name, sets_int, reps_val, weights_val)
        )
```

- [ ] **Step 2: Run all 4 new tests**

```bash
pytest tests/test_app.py::test_previous_workout_none tests/test_app.py::test_previous_workout_invalid_type tests/test_app.py::test_previous_workout_returns_last tests/test_app.py::test_log_live_with_weights -v
```

Expected: all 4 PASS.

- [ ] **Step 3: Run full suite to confirm nothing is broken**

```bash
pytest tests/test_app.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: store weight_kg per set in /log/live endpoint"
```

---

## Task 5: Update `/history` route and template to display weights

**Files:**
- Modify: `app.py` — `history` route (query + parse loop)
- Modify: `templates/history.html` — exercise detail rendering

- [ ] **Step 1: Update the `GROUP_CONCAT` query in the `history` route**

Find this line in `app.py` in the `history` function:
```python
               GROUP_CONCAT(we.exercise_name || '|' || COALESCE(we.sets,'') || '|' || COALESCE(we.reps,''), ';;') as exercises_raw
```
Replace it with:
```python
               GROUP_CONCAT(we.exercise_name || '|' || COALESCE(we.sets,'') || '|' || COALESCE(we.reps,'') || '|' || COALESCE(we.weight_kg,''), ';;') as exercises_raw
```

- [ ] **Step 2: Update the parse loop in the `history` route to extract the fourth segment**

Find this block:
```python
        if w['exercises_raw']:
            for ex_str in w['exercises_raw'].split(';;'):
                parts = ex_str.split('|')
                if len(parts) == 3:
                    exercises.append({'name': parts[0], 'sets': parts[1], 'reps': parts[2]})
```
Replace it with:
```python
        if w['exercises_raw']:
            for ex_str in w['exercises_raw'].split(';;'):
                parts = ex_str.split('|')
                if len(parts) >= 3:
                    exercises.append({
                        'name': parts[0],
                        'sets': parts[1],
                        'reps': parts[2],
                        'weight_kg': parts[3] if len(parts) > 3 else '',
                    })
```

- [ ] **Step 3: Update `templates/history.html` to display weight when present**

Find this line in `history.html`:
```html
                {% if ex.reps %}<span class="ex-detail-reps">{{ ex.reps }}</span>{% endif %}
```
Replace it with:
```html
                {% if ex.reps %}<span class="ex-detail-reps">{% if ex.weight_kg %}{{ ex.reps.split(',')[0] }} reps × {{ ex.weight_kg.split(',')[0] }} kg{% else %}{{ ex.reps }}{% endif %}</span>{% endif %}
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/test_app.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py templates/history.html
git commit -m "feat: show weight alongside reps in workout history"
```

---

## Task 6: Add CSS styles for weight input and LAST summary

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Add new CSS rules after `.lw-reps-input::placeholder` (around line 382)**

After the block ending with `.lw-reps-input::placeholder { ... }`, insert:

```css
.lw-weight-input {
  width: 70px; padding: 0.4rem 0.5rem; text-align: center;
  background: rgba(255,255,255,0.06); border: 1px solid var(--card-border);
  border-radius: var(--radius-sm); color: var(--text); font-size: 0.9rem;
}
.lw-weight-input:focus { outline: none; border-color: var(--accent); }
.lw-weight-input::placeholder { color: var(--text-muted); font-size: 0.78rem; }

.lw-weight-unit {
  font-size: 0.82rem; color: var(--text-muted); flex-shrink: 0;
}

.lw-last-summary {
  font-size: 0.8rem; color: var(--text-muted);
  margin-bottom: 0.75rem; letter-spacing: 0.03em;
}
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "style: add weight input and LAST summary CSS for live workout"
```

---

## Task 7: Update live workout template — weight inputs + LAST summary

**Files:**
- Modify: `templates/live_workout.html`

- [ ] **Step 1: Add `#ex-last` div to the HTML portion of `live_workout.html`**

Find this block in the template HTML:
```html
<div class="glass-card lw-sets-card">
  <div class="card-title">Sets</div>
  <div id="sets-container"></div>
```
Replace it with:
```html
<div class="glass-card lw-sets-card">
  <div class="card-title">Sets</div>
  <div class="lw-last-summary" id="ex-last" style="display:none"></div>
  <div id="sets-container"></div>
```

- [ ] **Step 2: Replace the entire `<script>` block in `live_workout.html` with the updated version**

Replace everything from `<script>` to `</script>` with:

```html
<script>
const WORKOUT_TYPE = {{ workout_type | tojson }};
const TODAY = {{ today | tojson }};
const EXERCISES = {{ exercises | tojson }};

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
    renderExercise();
  })
  .catch(function() {});

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

renderExercise();
</script>
```

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/test_app.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/live_workout.html
git commit -m "feat: add weight input per set and LAST summary to live workout mode"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run the complete test suite one final time**

```bash
pytest tests/test_app.py -v
```

Expected output (all passing):
```
tests/test_app.py::test_dashboard_loads PASSED
tests/test_app.py::test_log_page_loads PASSED
tests/test_app.py::test_history_page_loads PASSED
tests/test_app.py::test_log_workout_post PASSED
tests/test_app.py::test_log_workout_a_post PASSED
tests/test_app.py::test_live_workout_page_loads PASSED
tests/test_app.py::test_live_workout_invalid_type_redirects PASSED
tests/test_app.py::test_log_live_post PASSED
tests/test_app.py::test_delete_workout PASSED
tests/test_app.py::test_previous_workout_none PASSED
tests/test_app.py::test_previous_workout_invalid_type PASSED
tests/test_app.py::test_previous_workout_returns_last PASSED
tests/test_app.py::test_log_live_with_weights PASSED
```
