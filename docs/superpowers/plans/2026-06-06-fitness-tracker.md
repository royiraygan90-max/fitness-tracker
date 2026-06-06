# Fitness Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack Flask/Python fitness tracking web app with SQLite persistence, deployable on Railway with a dark glassmorphism UI.

**Architecture:** Single Flask app (`app.py`) serving server-rendered Jinja2 templates with vanilla JS for interactivity. SQLite at `/app/data/fitness.db` (env-configurable). All routes are standard GET/POST with JSON API endpoints for delete. Static files served by Flask.

**Tech Stack:** Python 3, Flask, SQLite3, Gunicorn, Jinja2, Vanilla JS/CSS, Railway

---

## File Map

| File | Responsibility |
|------|---------------|
| `app.py` | Flask app, DB init, all routes (`/`, `/log`, `/history`, `/api/delete/<id>`) |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway web process |
| `templates/base.html` | Shared layout: `<head>`, nav, toast container |
| `templates/index.html` | Dashboard: calendar, streak, heatmap, recent workouts |
| `templates/log_workout.html` | Multi-step workout logging form |
| `templates/history.html` | Paginated history with filter + delete |
| `static/style.css` | Dark glassmorphism theme, mobile-first |
| `static/app.js` | Log form wizard, delete confirm, toast, heatmap render |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `Procfile`
- Create: `static/.gitkeep`
- Create: `templates/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
flask==3.0.3
gunicorn==22.0.0
```

- [ ] **Step 2: Create Procfile**

```
web: gunicorn app:app
```

- [ ] **Step 3: Create directories**

```bash
mkdir -p static templates
touch static/.gitkeep templates/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt Procfile
git commit -m "chore: project scaffold"
```

---

## Task 2: Flask App — Database + Routes

**Files:**
- Create: `app.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_app.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import tempfile, pytest
os.environ['DATABASE_URL'] = ':memory:'

import app as flask_app

@pytest.fixture
def client():
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['DATABASE_URL'] = ':memory:'
    with flask_app.app.test_client() as client:
        with flask_app.app.app_context():
            flask_app.init_db()
        yield client

def test_dashboard_loads(client):
    r = client.get('/')
    assert r.status_code == 200

def test_log_page_loads(client):
    r = client.get('/log')
    assert r.status_code == 200

def test_history_page_loads(client):
    r = client.get('/history')
    assert r.status_code == 200

def test_log_workout_post(client):
    r = client.post('/log', data={
        'workout_type': 'poci',
        'date': '2026-06-06',
        'notes': 'Great session'
    }, follow_redirects=True)
    assert r.status_code == 200

def test_log_workout_a_post(client):
    r = client.post('/log', data={
        'workout_type': 'workout_a',
        'date': '2026-06-06',
        'notes': '',
        'exercises': ['Pull-up', 'Plank'],
        'sets_Pull-up': '3',
        'reps_Pull-up': '8,8,7',
        'sets_Plank': '3',
        'reps_Plank': '60s',
    }, follow_redirects=True)
    assert r.status_code == 200

def test_delete_workout(client):
    # Create a workout first
    client.post('/log', data={
        'workout_type': 'flexibility',
        'date': '2026-06-05',
        'notes': 'stretching'
    })
    # Get its id from history
    r = client.get('/history')
    assert r.status_code == 200
    # Delete workout id=1
    r = client.post('/api/delete/1')
    assert r.status_code == 200
    import json
    data = json.loads(r.data)
    assert data['success'] is True
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/royiraygan/Documents/Projects/fitness-tracker
pip install flask gunicorn pytest
pytest tests/test_app.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` or similar — `app.py` doesn't exist yet.

- [ ] **Step 3: Write app.py**

```python
import os
import sqlite3
import json
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fitness-tracker-dev-secret')

DATABASE_URL = os.environ.get('DATABASE_URL', '/app/data/fitness.db')

WORKOUT_A_EXERCISES = [
    'Pull-up', 'Inverted Row', 'Wide Push-up',
    'Face Pull (band)', 'Plank', 'Hanging Knee Raise'
]

WORKOUT_B_EXERCISES = [
    'Squat (dumbbell)', 'Romanian Deadlift', 'Bulgarian Split Squat',
    'Standing Calf Raise', 'Single-Leg Calf Raise', 'Lateral Raise', 'Shrugs'
]


def get_db():
    if DATABASE_URL == ':memory:':
        if not hasattr(g, '_db'):
            g._db = sqlite3.connect(':memory:')
            g._db.row_factory = sqlite3.Row
            _create_tables(g._db)
        return g._db
    db_path = DATABASE_URL
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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
            completed BOOLEAN DEFAULT 1
        );
    ''')
    conn.commit()


def init_db():
    if DATABASE_URL == ':memory:':
        return  # handled in get_db() for in-memory
    db_path = DATABASE_URL
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    _seed_sample_data(conn)
    conn.close()


def _seed_sample_data(conn):
    count = conn.execute('SELECT COUNT(*) FROM workouts').fetchone()[0]
    if count > 0:
        return
    today = date.today()
    samples = [
        (str(today - timedelta(days=5)), 'workout_a', 'Felt strong today', [
            ('Pull-up', 3, '8,8,7'),
            ('Inverted Row', 3, '10,10,9'),
            ('Wide Push-up', 3, '15,12,12'),
            ('Plank', 3, '60s'),
        ]),
        (str(today - timedelta(days=3)), 'poci', 'Great beach session, 2 hours', []),
        (str(today - timedelta(days=1)), 'workout_b', 'Heavy leg day', [
            ('Squat (dumbbell)', 4, '12,12,10,10'),
            ('Romanian Deadlift', 3, '12,12,11'),
            ('Bulgarian Split Squat', 3, '10,10,9'),
            ('Lateral Raise', 3, '15,15,12'),
        ]),
    ]
    for s_date, s_type, s_notes, exercises in samples:
        cur = conn.execute(
            'INSERT INTO workouts (date, type, notes, created_at) VALUES (?,?,?,?)',
            (s_date, s_type, s_notes, datetime.now().isoformat())
        )
        wid = cur.lastrowid
        for name, sets, reps in exercises:
            conn.execute(
                'INSERT INTO workout_exercises (workout_id, exercise_name, sets, reps, completed) VALUES (?,?,?,?,1)',
                (wid, name, sets, reps)
            )
    conn.commit()


@app.route('/')
def dashboard():
    db = get_db()
    # Last 5 workouts
    recent = db.execute(
        'SELECT w.*, COUNT(we.id) as exercise_count FROM workouts w '
        'LEFT JOIN workout_exercises we ON we.workout_id = w.id '
        'GROUP BY w.id ORDER BY w.date DESC, w.created_at DESC LIMIT 5'
    ).fetchall()

    # This week (Sun-Sat)
    today = date.today()
    weekday = today.weekday()  # Mon=0
    # Adjust to Sunday start
    days_since_sunday = (weekday + 1) % 7
    week_start = today - timedelta(days=days_since_sunday)
    week_end = week_start + timedelta(days=6)

    week_workouts = db.execute(
        'SELECT date, type FROM workouts WHERE date >= ? AND date <= ? ORDER BY date',
        (str(week_start), str(week_end))
    ).fetchall()

    # Build week calendar: list of 7 dicts
    week_days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_workouts = [w for w in week_workouts if w['date'] == str(d)]
        week_days.append({
            'date': d,
            'label': d.strftime('%a'),
            'day_num': d.day,
            'is_today': d == today,
            'workouts': [dict(w) for w in day_workouts]
        })

    # Weekly summary
    week_all = db.execute(
        'SELECT type FROM workouts WHERE date >= ? AND date <= ?',
        (str(week_start), str(week_end))
    ).fetchall()
    week_summary = {
        'workouts': sum(1 for w in week_all if w['type'] in ('workout_a', 'workout_b')),
        'poci': sum(1 for w in week_all if w['type'] == 'poci'),
        'flexibility': sum(1 for w in week_all if w['type'] == 'flexibility'),
    }

    # Streak: consecutive weeks with at least one workout
    streak = _calc_streak(db, today)

    # Heatmap: last 12 weeks
    heatmap = _build_heatmap(db, today)

    if DATABASE_URL != ':memory:':
        db.close()
    return render_template('index.html',
        recent=recent, week_days=week_days, week_summary=week_summary,
        streak=streak, heatmap=heatmap, today=today)


def _calc_streak(db, today):
    """Count consecutive weeks (ending today's week) that had at least one workout."""
    streak = 0
    weekday = today.weekday()
    days_since_sunday = (weekday + 1) % 7
    for w in range(52):
        week_end = today - timedelta(days=days_since_sunday) + timedelta(days=6) - timedelta(weeks=w)
        week_start = week_end - timedelta(days=6)
        count = db.execute(
            'SELECT COUNT(*) FROM workouts WHERE date >= ? AND date <= ?',
            (str(week_start), str(week_end))
        ).fetchone()[0]
        if count > 0:
            streak += 1
        else:
            break
    return streak


def _build_heatmap(db, today):
    """Build 12-week heatmap data. Returns list of week lists (Sun-Sat), each day has date+count+type."""
    weekday = today.weekday()
    days_since_sunday = (weekday + 1) % 7
    end_of_week = today - timedelta(days=days_since_sunday) + timedelta(days=6)
    start = end_of_week - timedelta(weeks=12) + timedelta(days=1)

    rows = db.execute(
        'SELECT date, type, COUNT(*) as cnt FROM workouts WHERE date >= ? AND date <= ? GROUP BY date, type',
        (str(start), str(end_of_week))
    ).fetchall()

    by_date = {}
    for r in rows:
        if r['date'] not in by_date:
            by_date[r['date']] = {'count': 0, 'types': []}
        by_date[r['date']]['count'] += r['cnt']
        by_date[r['date']]['types'].append(r['type'])

    weeks = []
    current = start
    week = []
    while current <= end_of_week:
        ds = str(current)
        info = by_date.get(ds, {'count': 0, 'types': []})
        primary_type = info['types'][0] if info['types'] else None
        week.append({
            'date': ds,
            'count': info['count'],
            'type': primary_type,
            'is_future': current > today,
        })
        if len(week) == 7:
            weeks.append(week)
            week = []
        current += timedelta(days=1)
    if week:
        weeks.append(week)
    return weeks


@app.route('/log', methods=['GET', 'POST'])
def log_workout():
    if request.method == 'POST':
        workout_type = request.form.get('workout_type')
        workout_date = request.form.get('date', str(date.today()))
        notes = request.form.get('notes', '')

        db = get_db()
        cur = db.execute(
            'INSERT INTO workouts (date, type, notes, created_at) VALUES (?,?,?,?)',
            (workout_date, workout_type, notes, datetime.now().isoformat())
        )
        workout_id = cur.lastrowid

        if workout_type in ('workout_a', 'workout_b'):
            checked = request.form.getlist('exercises')
            for ex in checked:
                sets_val = request.form.get(f'sets_{ex}', '0')
                reps_val = request.form.get(f'reps_{ex}', '')
                try:
                    sets_int = int(sets_val)
                except ValueError:
                    sets_int = 0
                db.execute(
                    'INSERT INTO workout_exercises (workout_id, exercise_name, sets, reps, completed) VALUES (?,?,?,?,1)',
                    (workout_id, ex, sets_int, reps_val)
                )

        db.commit()
        if DATABASE_URL != ':memory:':
            db.close()
        flash('Workout logged successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('log_workout.html',
        workout_a_exercises=WORKOUT_A_EXERCISES,
        workout_b_exercises=WORKOUT_B_EXERCISES,
        today=str(date.today()))


@app.route('/history')
def history():
    filter_type = request.args.get('type', 'all')
    db = get_db()

    query = '''
        SELECT w.id, w.date, w.type, w.notes, w.created_at,
               GROUP_CONCAT(we.exercise_name || '|' || COALESCE(we.sets,'') || '|' || COALESCE(we.reps,''), ';;') as exercises_raw
        FROM workouts w
        LEFT JOIN workout_exercises we ON we.workout_id = w.id
    '''
    params = []
    if filter_type != 'all':
        query += ' WHERE w.type = ?'
        params.append(filter_type)
    query += ' GROUP BY w.id ORDER BY w.date DESC, w.created_at DESC'

    rows = db.execute(query, params).fetchall()
    workouts = []
    for row in rows:
        w = dict(row)
        exercises = []
        if w['exercises_raw']:
            for ex_str in w['exercises_raw'].split(';;'):
                parts = ex_str.split('|')
                if len(parts) == 3:
                    exercises.append({'name': parts[0], 'sets': parts[1], 'reps': parts[2]})
        w['exercises'] = exercises
        workouts.append(w)

    if DATABASE_URL != ':memory:':
        db.close()
    return render_template('history.html', workouts=workouts, filter_type=filter_type)


@app.route('/api/delete/<int:workout_id>', methods=['POST'])
def delete_workout(workout_id):
    db = get_db()
    db.execute('DELETE FROM workout_exercises WHERE workout_id = ?', (workout_id,))
    db.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    db.commit()
    if DATABASE_URL != ':memory:':
        db.close()
    return jsonify({'success': True})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/royiraygan/Documents/Projects/fitness-tracker
pytest tests/test_app.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: flask app with db schema, routes, and seed data"
```

---

## Task 3: Base HTML Template

**Files:**
- Create: `templates/base.html`

- [ ] **Step 1: Create base.html**

```html
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Fitness Tracker{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <nav class="navbar">
    <div class="nav-brand">💪 Fitness Tracker</div>
    <div class="nav-links">
      <a href="{{ url_for('dashboard') }}" class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}">Dashboard</a>
      <a href="{{ url_for('log_workout') }}" class="nav-link btn-primary-small {% if request.endpoint == 'log_workout' %}active{% endif %}">+ Log</a>
      <a href="{{ url_for('history') }}" class="nav-link {% if request.endpoint == 'history' %}active{% endif %}">History</a>
    </div>
  </nav>

  <main class="main-content">
    {% block content %}{% endblock %}
  </main>

  <!-- Toast container -->
  <div id="toast-container"></div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <script>
        window.__flashMessages = {{ messages | tojson }};
      </script>
    {% endif %}
  {% endwith %}

  <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: base HTML template with nav"
```

---

## Task 4: Dashboard Template

**Files:**
- Create: `templates/index.html`

- [ ] **Step 1: Create index.html**

```html
{% extends "base.html" %}
{% block title %}Dashboard — Fitness Tracker{% endblock %}
{% block content %}

<div class="page-header">
  <h1 class="page-title">Dashboard</h1>
  <a href="{{ url_for('log_workout') }}" class="btn-primary">+ Log Workout</a>
</div>

<!-- Stats row -->
<div class="stats-row">
  <div class="stat-card">
    <div class="stat-value">{{ streak }}</div>
    <div class="stat-label">Week Streak 🔥</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ week_summary.workouts }}</div>
    <div class="stat-label">Workouts This Week</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ week_summary.poci }}</div>
    <div class="stat-label">🏐 Poci Sessions</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ week_summary.flexibility }}</div>
    <div class="stat-label">🧘 Flexibility</div>
  </div>
</div>

<!-- Weekly Calendar -->
<div class="glass-card">
  <h2 class="card-title">This Week</h2>
  <div class="week-calendar">
    {% for day in week_days %}
    <div class="week-day {% if day.is_today %}today{% endif %} {% if day.workouts %}has-workout{% endif %}">
      <div class="day-label">{{ day.label }}</div>
      <div class="day-num">{{ day.day_num }}</div>
      <div class="day-icons">
        {% for w in day.workouts %}
          <span class="type-dot type-{{ w.type }}" title="{{ w.type }}"></span>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- Activity Heatmap -->
<div class="glass-card">
  <h2 class="card-title">Activity (Last 12 Weeks)</h2>
  <div class="heatmap-wrapper">
    <div class="heatmap" id="heatmap">
      {% for week in heatmap %}
        <div class="heatmap-col">
          {% for day in week %}
            <div class="heatmap-cell {% if day.count > 0 and not day.is_future %}active type-{{ day.type }}{% elif day.is_future %}future{% endif %}"
                 title="{{ day.date }}{% if day.count %} — {{ day.count }} workout(s){% endif %}">
            </div>
          {% endfor %}
        </div>
      {% endfor %}
    </div>
    <div class="heatmap-legend">
      <span class="legend-item"><span class="legend-dot type-workout_a"></span> Workout A</span>
      <span class="legend-item"><span class="legend-dot type-workout_b"></span> Workout B</span>
      <span class="legend-item"><span class="legend-dot type-poci"></span> Poci</span>
      <span class="legend-item"><span class="legend-dot type-flexibility"></span> Flexibility</span>
    </div>
  </div>
</div>

<!-- Recent Workouts -->
<div class="glass-card">
  <h2 class="card-title">Recent Workouts</h2>
  {% if recent %}
    <div class="workout-list">
      {% for w in recent %}
        <div class="workout-item">
          <div class="workout-meta">
            <span class="type-badge type-{{ w.type }}">
              {% if w.type == 'workout_a' %}💪 Workout A
              {% elif w.type == 'workout_b' %}💪 Workout B
              {% elif w.type == 'poci' %}🏐 Poci
              {% else %}🧘 Flexibility{% endif %}
            </span>
            <span class="workout-date">{{ w.date }}</span>
          </div>
          {% if w.exercise_count > 0 %}
            <div class="workout-detail">{{ w.exercise_count }} exercises</div>
          {% elif w.notes %}
            <div class="workout-detail">{{ w.notes[:60] }}{% if w.notes|length > 60 %}…{% endif %}</div>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  {% else %}
    <p class="empty-state">No workouts yet. <a href="{{ url_for('log_workout') }}">Log your first one!</a></p>
  {% endif %}
</div>

{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/index.html
git commit -m "feat: dashboard template with calendar, heatmap, stats"
```

---

## Task 5: Log Workout Template

**Files:**
- Create: `templates/log_workout.html`

- [ ] **Step 1: Create log_workout.html**

```html
{% extends "base.html" %}
{% block title %}Log Workout — Fitness Tracker{% endblock %}
{% block content %}

<div class="page-header">
  <h1 class="page-title">Log Workout</h1>
</div>

<form method="POST" action="{{ url_for('log_workout') }}" id="log-form">
  <!-- Step 1: Type Selection -->
  <div class="glass-card" id="step-type">
    <h2 class="card-title">Step 1 — Select Workout Type</h2>
    <div class="type-grid">
      <label class="type-card type-workout_a">
        <input type="radio" name="workout_type" value="workout_a" required>
        <span class="type-icon">💪</span>
        <span class="type-name">Workout A</span>
        <span class="type-sub">Upper Body Push/Pull</span>
      </label>
      <label class="type-card type-workout_b">
        <input type="radio" name="workout_type" value="workout_b" required>
        <span class="type-icon">💪</span>
        <span class="type-name">Workout B</span>
        <span class="type-sub">Lower Body + Shoulders</span>
      </label>
      <label class="type-card type-poci">
        <input type="radio" name="workout_type" value="poci" required>
        <span class="type-icon">🏐</span>
        <span class="type-name">Poci</span>
        <span class="type-sub">Beach Volleyball</span>
      </label>
      <label class="type-card type-flexibility">
        <input type="radio" name="workout_type" value="flexibility" required>
        <span class="type-icon">🧘</span>
        <span class="type-name">Flexibility</span>
        <span class="type-sub">Stretch & Mobility</span>
      </label>
    </div>
  </div>

  <!-- Step 2: Date -->
  <div class="glass-card">
    <h2 class="card-title">Step 2 — Date</h2>
    <input type="date" name="date" value="{{ today }}" class="date-input" required>
  </div>

  <!-- Step 3: Exercises (Workout A/B only) -->
  <div class="glass-card" id="exercise-section" style="display:none">
    <h2 class="card-title">Step 3 — Exercises</h2>

    <div id="exercises-workout_a" class="exercise-list" style="display:none">
      {% for ex in workout_a_exercises %}
        <div class="exercise-row">
          <label class="exercise-check">
            <input type="checkbox" name="exercises" value="{{ ex }}" class="ex-checkbox">
            <span class="checkmark"></span>
            <span class="ex-name">{{ ex }}</span>
          </label>
          <div class="exercise-inputs" style="display:none">
            <div class="input-group">
              <label>Sets</label>
              <input type="number" name="sets_{{ ex }}" min="1" max="10" value="3" class="small-input">
            </div>
            <div class="input-group">
              <label>Reps</label>
              <input type="text" name="reps_{{ ex }}" placeholder="e.g. 8,8,7" class="small-input">
            </div>
          </div>
        </div>
      {% endfor %}
    </div>

    <div id="exercises-workout_b" class="exercise-list" style="display:none">
      {% for ex in workout_b_exercises %}
        <div class="exercise-row">
          <label class="exercise-check">
            <input type="checkbox" name="exercises" value="{{ ex }}" class="ex-checkbox">
            <span class="checkmark"></span>
            <span class="ex-name">{{ ex }}</span>
          </label>
          <div class="exercise-inputs" style="display:none">
            <div class="input-group">
              <label>Sets</label>
              <input type="number" name="sets_{{ ex }}" min="1" max="10" value="3" class="small-input">
            </div>
            <div class="input-group">
              <label>Reps</label>
              <input type="text" name="reps_{{ ex }}" placeholder="e.g. 12,12,10" class="small-input">
            </div>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>

  <!-- Step 4: Notes -->
  <div class="glass-card">
    <h2 class="card-title" id="notes-label">Step 3 — Notes</h2>
    <textarea name="notes" class="notes-textarea" placeholder="How did it go? Any observations..."></textarea>
  </div>

  <div class="form-footer">
    <a href="{{ url_for('dashboard') }}" class="btn-secondary">Cancel</a>
    <button type="submit" class="btn-primary">Save Workout ✓</button>
  </div>
</form>

{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/log_workout.html
git commit -m "feat: log workout template with multi-step form"
```

---

## Task 6: History Template

**Files:**
- Create: `templates/history.html`

- [ ] **Step 1: Create history.html**

```html
{% extends "base.html" %}
{% block title %}History — Fitness Tracker{% endblock %}
{% block content %}

<div class="page-header">
  <h1 class="page-title">History</h1>
</div>

<!-- Filter tabs -->
<div class="filter-tabs">
  <a href="{{ url_for('history') }}" class="filter-tab {% if filter_type == 'all' %}active{% endif %}">All</a>
  <a href="{{ url_for('history', type='workout_a') }}" class="filter-tab type-workout_a {% if filter_type == 'workout_a' %}active{% endif %}">💪 Workout A</a>
  <a href="{{ url_for('history', type='workout_b') }}" class="filter-tab type-workout_b {% if filter_type == 'workout_b' %}active{% endif %}">💪 Workout B</a>
  <a href="{{ url_for('history', type='poci') }}" class="filter-tab type-poci {% if filter_type == 'poci' %}active{% endif %}">🏐 Poci</a>
  <a href="{{ url_for('history', type='flexibility') }}" class="filter-tab type-flexibility {% if filter_type == 'flexibility' %}active{% endif %}">🧘 Flexibility</a>
</div>

{% if workouts %}
  <div class="history-list">
    {% for w in workouts %}
      <div class="glass-card history-card" id="workout-{{ w.id }}">
        <div class="history-header">
          <div class="history-meta">
            <span class="type-badge type-{{ w.type }}">
              {% if w.type == 'workout_a' %}💪 Workout A
              {% elif w.type == 'workout_b' %}💪 Workout B
              {% elif w.type == 'poci' %}🏐 Poci
              {% else %}🧘 Flexibility{% endif %}
            </span>
            <span class="history-date">{{ w.date }}</span>
          </div>
          <button class="btn-delete" onclick="confirmDelete({{ w.id }})" aria-label="Delete workout">🗑</button>
        </div>

        {% if w.exercises %}
          <div class="exercise-detail-list">
            {% for ex in w.exercises %}
              <div class="exercise-detail-row">
                <span class="ex-detail-name">{{ ex.name }}</span>
                {% if ex.sets %}<span class="ex-detail-sets">{{ ex.sets }} sets</span>{% endif %}
                {% if ex.reps %}<span class="ex-detail-reps">{{ ex.reps }}</span>{% endif %}
              </div>
            {% endfor %}
          </div>
        {% endif %}

        {% if w.notes %}
          <p class="history-notes">{{ w.notes }}</p>
        {% endif %}
      </div>
    {% endfor %}
  </div>
{% else %}
  <div class="glass-card">
    <p class="empty-state">No workouts found. <a href="{{ url_for('log_workout') }}">Log your first one!</a></p>
  </div>
{% endif %}

{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/history.html
git commit -m "feat: history template with filter tabs and delete"
```

---

## Task 7: CSS — Dark Glassmorphism Theme

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: Create style.css**

```css
/* ===== RESET & BASE ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0f1117;
  --bg-2: #1a1f2e;
  --card: rgba(30, 36, 51, 0.85);
  --card-border: rgba(255,255,255,0.08);
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --accent: #3b82f6;
  --accent-hover: #2563eb;

  --workout-a: #3b82f6;
  --workout-b: #22c55e;
  --poci: #f97316;
  --flexibility: #a855f7;

  --radius: 12px;
  --radius-sm: 8px;
  --shadow: 0 8px 32px rgba(0,0,0,0.4);
  --transition: 0.2s ease;
}

html { font-family: 'Inter', system-ui, sans-serif; }

body {
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse at 20% 0%, rgba(59,130,246,0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(168,85,247,0.08) 0%, transparent 50%);
}

a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); }

/* ===== NAVBAR ===== */
.navbar {
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.875rem 1.5rem;
  background: rgba(15,17,23,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--card-border);
}
.nav-brand { font-size: 1.1rem; font-weight: 700; color: var(--text); }
.nav-links { display: flex; gap: 0.5rem; align-items: center; }
.nav-link {
  padding: 0.4rem 0.875rem; border-radius: var(--radius-sm);
  color: var(--text-muted); font-size: 0.9rem; font-weight: 500;
  transition: var(--transition);
}
.nav-link:hover, .nav-link.active { color: var(--text); background: rgba(255,255,255,0.06); }
.btn-primary-small {
  background: var(--accent); color: #fff !important;
  padding: 0.4rem 0.875rem; border-radius: var(--radius-sm);
}
.btn-primary-small:hover { background: var(--accent-hover); }

/* ===== LAYOUT ===== */
.main-content { max-width: 800px; margin: 0 auto; padding: 1.5rem 1rem 4rem; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.5rem;
}
.page-title { font-size: 1.6rem; font-weight: 700; }

/* ===== GLASS CARD ===== */
.glass-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1.25rem;
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow);
}
.card-title { font-size: 1rem; font-weight: 600; color: var(--text-muted); margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em; }

/* ===== BUTTONS ===== */
.btn-primary {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: var(--accent); color: #fff;
  border: none; border-radius: var(--radius-sm);
  padding: 0.6rem 1.25rem; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; transition: var(--transition); text-decoration: none;
}
.btn-primary:hover { background: var(--accent-hover); color: #fff; transform: translateY(-1px); }

.btn-secondary {
  display: inline-flex; align-items: center;
  background: rgba(255,255,255,0.07); color: var(--text-muted);
  border: 1px solid var(--card-border); border-radius: var(--radius-sm);
  padding: 0.6rem 1.25rem; font-size: 0.95rem; font-weight: 500;
  cursor: pointer; transition: var(--transition); text-decoration: none;
}
.btn-secondary:hover { background: rgba(255,255,255,0.12); color: var(--text); }

.btn-delete {
  background: transparent; border: 1px solid rgba(239,68,68,0.3);
  color: #ef4444; border-radius: var(--radius-sm);
  padding: 0.35rem 0.6rem; cursor: pointer; font-size: 1rem;
  transition: var(--transition);
}
.btn-delete:hover { background: rgba(239,68,68,0.15); border-color: #ef4444; }

/* ===== STATS ROW ===== */
.stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.875rem; margin-bottom: 1.25rem;
}
.stat-card {
  background: var(--card); border: 1px solid var(--card-border);
  border-radius: var(--radius); padding: 1rem; text-align: center;
  backdrop-filter: blur(8px);
}
.stat-value { font-size: 2rem; font-weight: 700; color: var(--accent); line-height: 1; }
.stat-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem; }

/* ===== WEEK CALENDAR ===== */
.week-calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.5rem; }
.week-day {
  text-align: center; padding: 0.6rem 0.25rem;
  border-radius: var(--radius-sm); background: rgba(255,255,255,0.03);
  border: 1px solid transparent; transition: var(--transition);
}
.week-day.today { border-color: var(--accent); background: rgba(59,130,246,0.1); }
.week-day.has-workout { background: rgba(255,255,255,0.06); }
.day-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.25rem; }
.day-num { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; }
.day-icons { display: flex; justify-content: center; gap: 3px; min-height: 8px; }
.type-dot {
  width: 8px; height: 8px; border-radius: 50%; display: inline-block;
}

/* ===== TYPE COLORS ===== */
.type-workout_a, .type-dot.type-workout_a, .legend-dot.type-workout_a,
.heatmap-cell.type-workout_a { background-color: var(--workout-a); }
.type-workout_b, .type-dot.type-workout_b, .legend-dot.type-workout_b,
.heatmap-cell.type-workout_b { background-color: var(--workout-b); }
.type-poci, .type-dot.type-poci, .legend-dot.type-poci,
.heatmap-cell.type-poci { background-color: var(--poci); }
.type-flexibility, .type-dot.type-flexibility, .legend-dot.type-flexibility,
.heatmap-cell.type-flexibility { background-color: var(--flexibility); }

/* Type badges */
.type-badge {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.2rem 0.6rem; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; color: #fff;
}
.type-badge.type-workout_a { background: rgba(59,130,246,0.25); color: #93c5fd; border: 1px solid rgba(59,130,246,0.4); }
.type-badge.type-workout_b { background: rgba(34,197,94,0.2); color: #86efac; border: 1px solid rgba(34,197,94,0.4); }
.type-badge.type-poci { background: rgba(249,115,22,0.2); color: #fdba74; border: 1px solid rgba(249,115,22,0.4); }
.type-badge.type-flexibility { background: rgba(168,85,247,0.2); color: #d8b4fe; border: 1px solid rgba(168,85,247,0.4); }

/* ===== HEATMAP ===== */
.heatmap-wrapper { overflow-x: auto; }
.heatmap { display: flex; gap: 3px; padding-bottom: 0.5rem; }
.heatmap-col { display: flex; flex-direction: column; gap: 3px; }
.heatmap-cell {
  width: 14px; height: 14px; border-radius: 3px;
  background: rgba(255,255,255,0.06); transition: transform 0.1s;
}
.heatmap-cell.future { background: rgba(255,255,255,0.02); }
.heatmap-cell:hover { transform: scale(1.3); cursor: pointer; }
.heatmap-legend { display: flex; gap: 1rem; margin-top: 0.75rem; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 0.35rem; font-size: 0.75rem; color: var(--text-muted); }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

/* ===== RECENT WORKOUTS ===== */
.workout-list { display: flex; flex-direction: column; gap: 0.75rem; }
.workout-item {
  display: flex; align-items: center; gap: 1rem;
  padding: 0.75rem; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); border: 1px solid var(--card-border);
}
.workout-meta { display: flex; align-items: center; gap: 0.75rem; flex: 1; }
.workout-date { font-size: 0.85rem; color: var(--text-muted); }
.workout-detail { font-size: 0.85rem; color: var(--text-muted); margin-right: auto; }

/* ===== LOG FORM ===== */
.type-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.875rem;
}
.type-card {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.4rem; padding: 1.25rem 1rem;
  border: 2px solid var(--card-border); border-radius: var(--radius);
  cursor: pointer; transition: var(--transition);
  background: rgba(255,255,255,0.03);
}
.type-card input[type="radio"] { display: none; }
.type-card:hover { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.06); }
.type-card.selected,
.type-card:has(input:checked) { border-color: var(--accent); background: rgba(59,130,246,0.1); }
.type-card.type-workout_b:has(input:checked) { border-color: var(--workout-b); background: rgba(34,197,94,0.08); }
.type-card.type-poci:has(input:checked) { border-color: var(--poci); background: rgba(249,115,22,0.08); }
.type-card.type-flexibility:has(input:checked) { border-color: var(--flexibility); background: rgba(168,85,247,0.08); }
.type-icon { font-size: 2rem; }
.type-name { font-size: 1rem; font-weight: 600; }
.type-sub { font-size: 0.75rem; color: var(--text-muted); text-align: center; }

.date-input {
  width: 100%; padding: 0.65rem 0.875rem;
  background: rgba(255,255,255,0.05); border: 1px solid var(--card-border);
  border-radius: var(--radius-sm); color: var(--text); font-size: 1rem;
}
.date-input:focus { outline: none; border-color: var(--accent); }

.exercise-list { display: flex; flex-direction: column; gap: 0.75rem; }
.exercise-row {
  padding: 0.75rem; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); border: 1px solid var(--card-border);
  transition: var(--transition);
}
.exercise-row.checked { border-color: rgba(59,130,246,0.4); background: rgba(59,130,246,0.06); }
.exercise-check {
  display: flex; align-items: center; gap: 0.75rem; cursor: pointer;
  font-size: 0.95rem; user-select: none;
}
.exercise-check input[type="checkbox"] { display: none; }
.checkmark {
  width: 20px; height: 20px; border-radius: 4px;
  border: 2px solid rgba(255,255,255,0.2); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: var(--transition);
}
.exercise-check input:checked ~ .checkmark {
  background: var(--accent); border-color: var(--accent);
}
.exercise-check input:checked ~ .checkmark::after { content: '✓'; color: #fff; font-size: 0.75rem; font-weight: 700; }
.ex-name { font-weight: 500; }
.exercise-inputs {
  display: flex; gap: 1rem; margin-top: 0.6rem; padding-top: 0.6rem;
  border-top: 1px solid var(--card-border);
}
.input-group { display: flex; flex-direction: column; gap: 0.25rem; }
.input-group label { font-size: 0.75rem; color: var(--text-muted); }
.small-input {
  padding: 0.4rem 0.6rem; width: 90px;
  background: rgba(255,255,255,0.06); border: 1px solid var(--card-border);
  border-radius: var(--radius-sm); color: var(--text); font-size: 0.9rem;
}
.small-input:focus { outline: none; border-color: var(--accent); }

.notes-textarea {
  width: 100%; min-height: 100px; padding: 0.75rem;
  background: rgba(255,255,255,0.05); border: 1px solid var(--card-border);
  border-radius: var(--radius-sm); color: var(--text);
  font-size: 0.95rem; font-family: inherit; resize: vertical;
}
.notes-textarea:focus { outline: none; border-color: var(--accent); }
.notes-textarea::placeholder { color: var(--text-muted); }

.form-footer { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }

/* ===== HISTORY ===== */
.filter-tabs { display: flex; gap: 0.5rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.filter-tab {
  padding: 0.4rem 0.875rem; border-radius: 999px;
  background: rgba(255,255,255,0.05); border: 1px solid var(--card-border);
  color: var(--text-muted); font-size: 0.85rem; font-weight: 500;
  transition: var(--transition);
}
.filter-tab:hover { color: var(--text); background: rgba(255,255,255,0.09); }
.filter-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }

.history-card { margin-bottom: 1rem; }
.history-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.history-meta { display: flex; align-items: center; gap: 0.75rem; }
.history-date { font-size: 0.85rem; color: var(--text-muted); }
.history-notes { font-size: 0.875rem; color: var(--text-muted); margin-top: 0.5rem; font-style: italic; }

.exercise-detail-list { display: flex; flex-direction: column; gap: 0.4rem; }
.exercise-detail-row {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.4rem 0.6rem; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); font-size: 0.875rem;
}
.ex-detail-name { flex: 1; font-weight: 500; }
.ex-detail-sets { color: var(--text-muted); font-size: 0.8rem; }
.ex-detail-reps { color: var(--accent); font-size: 0.8rem; font-weight: 600; font-family: monospace; }

/* ===== TOAST ===== */
#toast-container { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 0.5rem; align-items: center; }
.toast {
  padding: 0.75rem 1.25rem; border-radius: var(--radius-sm);
  font-size: 0.9rem; font-weight: 500; color: #fff;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  animation: toast-in 0.3s ease, toast-out 0.3s ease 2.7s forwards;
  white-space: nowrap;
}
.toast.success { background: rgba(34,197,94,0.9); }
.toast.error { background: rgba(239,68,68,0.9); }
@keyframes toast-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes toast-out { from { opacity: 1; } to { opacity: 0; transform: translateY(10px); } }

/* ===== EMPTY STATE ===== */
.empty-state { color: var(--text-muted); text-align: center; padding: 2rem; font-size: 0.95rem; }

/* ===== MOBILE ===== */
@media (max-width: 600px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .type-grid { grid-template-columns: repeat(2, 1fr); }
  .nav-brand { font-size: 0.95rem; }
  .page-title { font-size: 1.3rem; }
  .week-calendar { gap: 0.25rem; }
  .day-num { font-size: 0.9rem; }
  .heatmap-cell { width: 11px; height: 11px; }
  .exercise-inputs { flex-wrap: wrap; }
  .filter-tabs { gap: 0.375rem; }
  .filter-tab { font-size: 0.8rem; padding: 0.35rem 0.65rem; }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: dark glassmorphism CSS theme"
```

---

## Task 8: JavaScript — Interactions

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Create app.js**

```javascript
/* ===== TOAST ===== */
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3100);
}

// Show flash messages from server
if (window.__flashMessages) {
  window.__flashMessages.forEach(([cat, msg]) => showToast(msg, cat));
}

/* ===== LOG FORM WIZARD ===== */
const typeRadios = document.querySelectorAll('input[name="workout_type"]');
const exerciseSection = document.getElementById('exercise-section');
const notesLabel = document.getElementById('notes-label');

function updateFormForType(type) {
  const isWorkout = type === 'workout_a' || type === 'workout_b';
  if (exerciseSection) {
    exerciseSection.style.display = isWorkout ? 'block' : 'none';
  }
  if (notesLabel) {
    notesLabel.textContent = isWorkout ? 'Step 4 — Notes' : 'Step 3 — Notes';
  }

  // Show/hide correct exercise list
  ['workout_a', 'workout_b'].forEach(t => {
    const el = document.getElementById(`exercises-${t}`);
    if (el) el.style.display = (type === t) ? 'block' : 'none';
  });
}

typeRadios.forEach(radio => {
  radio.addEventListener('change', () => updateFormForType(radio.value));
});

/* ===== EXERCISE CHECKBOXES ===== */
document.querySelectorAll('.ex-checkbox').forEach(checkbox => {
  checkbox.addEventListener('change', function () {
    const row = this.closest('.exercise-row');
    const inputs = row.querySelector('.exercise-inputs');
    if (inputs) inputs.style.display = this.checked ? 'flex' : 'none';
    row.classList.toggle('checked', this.checked);
  });
});

/* ===== DELETE CONFIRMATION ===== */
function confirmDelete(workoutId) {
  if (!confirm('Delete this workout? This cannot be undone.')) return;
  fetch(`/api/delete/${workoutId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const el = document.getElementById(`workout-${workoutId}`);
        if (el) {
          el.style.transition = 'opacity 0.3s, transform 0.3s';
          el.style.opacity = '0';
          el.style.transform = 'translateX(20px)';
          setTimeout(() => el.remove(), 320);
        }
        showToast('Workout deleted');
      }
    })
    .catch(() => showToast('Failed to delete', 'error'));
}
```

- [ ] **Step 2: Commit**

```bash
git add static/app.js
git commit -m "feat: JavaScript interactions — form wizard, toast, delete"
```

---

## Task 9: Wire Everything Together + Run App

**Files:**
- Modify: `app.py` (verify DATABASE_URL env handling for Railway)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/royiraygan/Documents/Projects/fitness-tracker
pytest tests/test_app.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 2: Run the app locally**

```bash
cd /Users/royiraygan/Documents/Projects/fitness-tracker
DATABASE_URL=./fitness_dev.db python app.py
```

Expected: App starts on http://127.0.0.1:5000 with no errors. Confirm in browser:
- Dashboard shows 3 sample workouts, heatmap with dots, streak > 0
- "Log Workout" button works, form type-switching works
- History shows 3 entries with filter tabs
- Delete removes an entry with animation

- [ ] **Step 3: Remove dev db artifact**

```bash
rm -f fitness_dev.db
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify full app runs end-to-end"
```

---

## Task 10: Railway Deployment Config

**Files:**
- Verify: `Procfile` (already created in Task 1)
- Create: `.gitignore`
- Create: `railway.toml` (optional but helpful)

- [ ] **Step 1: Create .gitignore**

```
__pycache__/
*.pyc
*.db
.env
.venv/
venv/
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 2: Verify Procfile content**

```bash
cat Procfile
```

Expected output:
```
web: gunicorn app:app
```

- [ ] **Step 3: Create railway.toml**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:app"
restartPolicyType = "on-failure"
restartPolicyMaxRetries = 3
```

- [ ] **Step 4: Verify requirements.txt**

```bash
cat requirements.txt
```

Expected:
```
flask==3.0.3
gunicorn==22.0.0
```

- [ ] **Step 5: Final commit**

```bash
git add .gitignore railway.toml
git commit -m "chore: Railway deployment config and gitignore"
```

---

## Self-Review Against Spec

### Spec Coverage Check

| Requirement | Task |
|-------------|------|
| SQLite at /app/data/fitness.db, env-configurable | Task 2 (DATABASE_URL env var) |
| workouts table schema | Task 2 (`_create_tables`) |
| workout_exercises table schema | Task 2 (`_create_tables`) |
| Dashboard: weekly calendar Sun-Sat | Task 4 (index.html + Task 2 route) |
| Dashboard: streak counter | Task 2 (`_calc_streak`) + Task 4 |
| Dashboard: weekly summary | Task 2 (route) + Task 4 |
| Dashboard: activity heatmap 12 weeks | Task 2 (`_build_heatmap`) + Task 4 |
| Dashboard: "Log Workout" button | Task 4 |
| Dashboard: last 5 workouts | Task 2 (route) + Task 4 |
| Log: workout type selection (4 types) | Task 5 |
| Log: date picker defaults to today | Task 5 |
| Log: Workout A exercise checklist | Task 5 |
| Log: Workout B exercise checklist | Task 5 |
| Log: sets + reps per exercise | Task 5 |
| Log: notes textarea for poci/flex | Task 5 |
| Log: redirect to dashboard with toast | Task 2 (flash) + Task 8 (toast) |
| History: newest first | Task 2 (ORDER BY) |
| History: type icon per entry | Task 6 |
| History: exercises with sets/reps | Task 6 |
| History: filter by type | Task 2 (route) + Task 6 |
| History: delete with confirmation | Task 6 + Task 8 |
| Dark theme #0f1117, cards #1e2433, accent #3b82f6 | Task 7 |
| Glassmorphism cards | Task 7 |
| Mobile-friendly | Task 7 (media queries) |
| Colored type badges | Task 7 |
| Sample data on first run | Task 2 (`_seed_sample_data`) |
| Procfile for Railway | Task 1 + Task 10 |
| python app.py runs | Task 2 (`if __name__ == '__main__'`) |

All requirements covered. No gaps found.

### Placeholder Scan

No TBD, TODO, or incomplete code blocks found.

### Type Consistency

- `workout_type` values: `workout_a`, `workout_b`, `poci`, `flexibility` — consistent across app.py routes, templates, and CSS classes.
- `exercises` form field name + `sets_{ex}` / `reps_{ex}` pattern — consistent between log_workout.html and app.py POST handler.
- `DATABASE_URL` env var — used in `get_db()`, `init_db()`, all route handlers. Consistent.
