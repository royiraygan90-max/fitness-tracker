import os
import re
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fitness-tracker-dev-secret')

@app.template_filter('format_date')
def format_date_filter(value):
    if not value:
        return value
    try:
        dt = datetime.strptime(str(value), '%Y-%m-%d')
        return dt.strftime('%d/%m/%y')
    except (ValueError, TypeError):
        return value

DATABASE_URL = os.environ.get('DATABASE_URL', '/app/data/fitness.db')

VALID_WORKOUT_TYPES = {'workout_a_gym', 'workout_a_home', 'workout_b_gym', 'workout_b_home', 'poci', 'flexibility'}

WORKOUT_A_GYM_EXERCISES = [
    'Squat', 'Bench Press', 'Pull-up', 'Lateral Raise', 'Cable Bicep Curl',
    'Back Extension', 'Overhead Tricep Extension (cable)',
    'Calf Raise (machine)', 'Core Finisher (your choice)'
]
WORKOUT_A_HOME_EXERCISES = [
    'Goblet Squat (dumbbell)', 'Parallette Dips', 'Chin-up', 'Lateral Raise (dumbbell)',
    'Dumbbell Bicep Curl', 'Lower Back (Superman)', 'Overhead Tricep Extension (dumbbell)',
    'Calf Raise (dumbbell)', 'Core Finisher (your choice)'
]
WORKOUT_B_GYM_EXERCISES = [
    'Romanian Deadlift', 'Upper Chest Fly (cable/pec deck)', 'Cable Row',
    'Bulgarian Split Squat', 'Tricep Pushdown (cable)', "Farmer's Carry",
    'EZ-Bar Curl', 'Calf Raise (machine)', 'Core Finisher (your choice)'
]
WORKOUT_B_HOME_EXERCISES = [
    'Romanian Deadlift (dumbbell)', 'Incline Dumbbell Press', 'Bent-over Dumbbell Row',
    'Bulgarian Split Squat (dumbbell)', 'Tricep Kickback (dumbbell)', 'Dumbbell Wrist Curl',
    'Dumbbell Hammer Curl', 'Calf Raise (dumbbell)', 'Core Finisher (your choice)'
]

# progression_kg is the suggested weight jump for the Coach's double-progression
# tips once every set hits the top of the rep range: 5kg for leg-dominant
# compounds, 2.5kg for everything else, None for time-held exercises (Plank)
# that aren't progressed by adding weight. See _suggested_increment_kg() for
# how this gets capped for lighter/bodyweight loads.
LIVE_WORKOUT_EXERCISES = {
    'workout_a_gym': [
        {'name': 'Squat', 'sets': 3, 'reps': '8–10', 'youtube': 'https://www.youtube.com/watch?v=8PMjqgR8Wa8',
         'tip': "Chest up, knees track over toes. Sit back like into a chair.", 'progression_kg': 5},
        {'name': 'Bench Press', 'sets': 3, 'reps': '8–10', 'youtube': 'https://www.youtube.com/watch?v=Pp8rHcFVIYg',
         'tip': "Keep shoulder blades pinned together, feet flat on the floor. Control the bar to mid-chest.", 'progression_kg': 2.5},
        {'name': 'Pull-up', 'sets': 3, 'reps': 'to failure / 8', 'youtube': 'https://www.youtube.com/watch?v=eGo4IYlbE5g',
         'tip': "Start from a dead hang. Pull shoulder blades down first before pulling up.", 'progression_kg': 2.5},
        {'name': 'Lateral Raise', 'sets': 3, 'reps': '12–15', 'youtube': 'https://www.youtube.com/watch?v=3VcKaXpzqRo',
         'tip': "Slight bend in elbow. Raise to shoulder height only — no higher.", 'progression_kg': 2.5},
        {'name': 'Cable Bicep Curl', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=5z4y7QRTx1w',
         'tip': "Keep elbows pinned to your sides. No swinging.", 'progression_kg': 2.5},
        {'name': 'Back Extension', 'sets': 2, 'reps': '12', 'youtube': 'https://www.youtube.com/watch?v=81riMKjNBuA',
         'tip': "Hips on the pad, rise until your body forms a straight line — don't hyperextend at the top.", 'progression_kg': 2.5},
        {'name': 'Overhead Tricep Extension (cable)', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=8WC7rIOkhi0',
         'tip': "Elbows pointing forward and still. Lower behind your head for a full stretch, then extend.", 'progression_kg': 2.5},
        {'name': 'Calf Raise (machine)', 'sets': 3, 'reps': '15–20', 'youtube': 'https://www.youtube.com/watch?v=97NbelB5yvQ',
         'tip': "Full stretch at the bottom, pause and squeeze hard at the top.", 'progression_kg': 2.5},
        {'name': 'Core Finisher (your choice)', 'sets': 2, 'reps': '15–20 or 30–60 sec', 'youtube': None,
         'tip': "Pick any ab exercise and vary it session to session — plank, crunches, leg raises, Russian twists.", 'progression_kg': None},
    ],
    'workout_a_home': [
        {'name': 'Goblet Squat (dumbbell)', 'sets': 3, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=gCESNsDsbqk',
         'tip': "Hold the dumbbell at chest height, sit back and down keeping your chest tall.", 'progression_kg': 5},
        {'name': 'Parallette Dips', 'sets': 3, 'reps': 'to failure / 10', 'youtube': 'https://www.youtube.com/watch?v=0EPpumD8eeI',
         'tip': "Lean slightly forward for chest emphasis. Control the descent, don't flare elbows too wide.", 'progression_kg': 2.5},
        {'name': 'Chin-up', 'sets': 3, 'reps': 'to failure / 8', 'youtube': 'https://www.youtube.com/watch?v=e1YSApl-QcM',
         'tip': "Underhand, shoulder-width grip. Pull your chest toward the bar, control the descent.", 'progression_kg': 2.5},
        {'name': 'Lateral Raise (dumbbell)', 'sets': 3, 'reps': '12–15', 'youtube': 'https://www.youtube.com/watch?v=3VcKaXpzqRo',
         'tip': "Slight bend in elbow. Raise to shoulder height only — no higher.", 'progression_kg': 2.5},
        {'name': 'Dumbbell Bicep Curl', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=XE_pHwbst04',
         'tip': "Keep elbows pinned to your sides. Control the negative.", 'progression_kg': 2.5},
        {'name': 'Lower Back (Superman)', 'sets': 2, 'reps': '12', 'youtube': 'https://www.youtube.com/watch?v=jTNpZIl1qU0',
         'tip': "Lift chest and legs together, squeeze glutes. Don't hyperextend the neck.", 'progression_kg': 2.5},
        {'name': 'Overhead Tricep Extension (dumbbell)', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=DZgpCf5alfI',
         'tip': "Hold one dumbbell with both hands, elbows in, lower behind your head under control.", 'progression_kg': 2.5},
        {'name': 'Calf Raise (dumbbell)', 'sets': 3, 'reps': '15–20', 'youtube': 'https://www.youtube.com/watch?v=HvvqTpTongY',
         'tip': "Balls of your feet on a step, full stretch at the bottom, squeeze at the top.", 'progression_kg': 2.5},
        {'name': 'Core Finisher (your choice)', 'sets': 2, 'reps': '15–20 or 30–60 sec', 'youtube': None,
         'tip': "Pick any ab exercise and vary it session to session — plank, crunches, leg raises, Russian twists.", 'progression_kg': None},
    ],
    'workout_b_gym': [
        {'name': 'Romanian Deadlift', 'sets': 3, 'reps': '8–10', 'youtube': 'https://www.youtube.com/watch?v=JCXUYuzwNrM',
         'tip': "Hinge at the hips, push hips back. Keep the bar close to your legs.", 'progression_kg': 5},
        {'name': 'Upper Chest Fly (cable/pec deck)', 'sets': 3, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=10hg4LAa7UQ',
         'tip': "Slight bend in elbows, squeeze at the top, control the negative.", 'progression_kg': 2.5},
        {'name': 'Cable Row', 'sets': 3, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=EU7bOadUsNI',
         'tip': "Pull elbows back, squeeze shoulder blades together, keep torso still.", 'progression_kg': 2.5},
        {'name': 'Bulgarian Split Squat', 'sets': 3, 'reps': '8 each leg', 'youtube': 'https://www.youtube.com/watch?v=2C-uNgKwPLE',
         'tip': "Front foot far enough forward. Torso upright, control the descent.", 'progression_kg': 5},
        {'name': 'Tricep Pushdown (cable)', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=odbyvJm7d8s',
         'tip': "Keep elbows pinned at your sides, full extension at the bottom.", 'progression_kg': 2.5},
        {'name': "Farmer's Carry", 'sets': 2, 'reps': '30–40 sec', 'youtube': 'https://www.youtube.com/watch?v=VBobkldqqvk',
         'tip': "Stand tall, shoulders back, brace your core. Walk with short, controlled steps.", 'progression_kg': None},
        {'name': 'EZ-Bar Curl', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=5NsFLGUf0Fo',
         'tip': "Elbows pinned to your sides, squeeze at the top, control the negative.", 'progression_kg': 2.5},
        {'name': 'Calf Raise (machine)', 'sets': 3, 'reps': '15–20', 'youtube': 'https://www.youtube.com/watch?v=97NbelB5yvQ',
         'tip': "Full stretch at the bottom, pause and squeeze hard at the top.", 'progression_kg': 2.5},
        {'name': 'Core Finisher (your choice)', 'sets': 2, 'reps': '15–20 or 30–60 sec', 'youtube': None,
         'tip': "Pick any ab exercise and vary it session to session — plank, crunches, leg raises, Russian twists.", 'progression_kg': None},
    ],
    'workout_b_home': [
        {'name': 'Romanian Deadlift (dumbbell)', 'sets': 3, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=aa57T45iFSE',
         'tip': "Hinge at the hips, push hips back. Keep the dumbbells close to your legs.", 'progression_kg': 5},
        {'name': 'Incline Dumbbell Press', 'sets': 3, 'reps': '8–10', 'youtube': 'https://www.youtube.com/watch?v=sK4Rvug6ufo',
         'tip': "Bench at ~30°. Press up and slightly inward, don't flare your elbows too wide.", 'progression_kg': 2.5},
        {'name': 'Bent-over Dumbbell Row', 'sets': 3, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=dfkco3keMns',
         'tip': "Flat back, pull elbow back and up, squeeze at the top.", 'progression_kg': 2.5},
        {'name': 'Bulgarian Split Squat (dumbbell)', 'sets': 3, 'reps': '8 each leg', 'youtube': 'https://www.youtube.com/watch?v=2C-uNgKwPLE',
         'tip': "Front foot far enough forward. Torso upright, control the descent.", 'progression_kg': 5},
        {'name': 'Tricep Kickback (dumbbell)', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=IqgklYrtcUo',
         'tip': "Keep your upper arm still, extend through the elbow only.", 'progression_kg': 2.5},
        {'name': 'Dumbbell Wrist Curl', 'sets': 2, 'reps': '12–15', 'youtube': 'https://www.youtube.com/watch?v=JtZ_iT8rn70',
         'tip': "Forearms on your thighs or a bench, palms up, curl through a full range.", 'progression_kg': 2.5},
        {'name': 'Dumbbell Hammer Curl', 'sets': 2, 'reps': '10–12', 'youtube': 'https://www.youtube.com/watch?v=FNvndC4Ov04',
         'tip': "Neutral grip (palms facing in) the whole way. No swinging.", 'progression_kg': 2.5},
        {'name': 'Calf Raise (dumbbell)', 'sets': 3, 'reps': '15–20', 'youtube': 'https://www.youtube.com/watch?v=HvvqTpTongY',
         'tip': "Balls of your feet on a step, full stretch at the bottom, squeeze at the top.", 'progression_kg': 2.5},
        {'name': 'Core Finisher (your choice)', 'sets': 2, 'reps': '15–20 or 30–60 sec', 'youtube': None,
         'tip': "Pick any ab exercise and vary it session to session — plank, crunches, leg raises, Russian twists.", 'progression_kg': None},
    ],
}

# ===== TRAINING APP (Home/Plan/History redesign) =====
# Functional strength (dumbbell) rotation + yoga, replacing the old
# Workout A/B + Poci + Flexibility split for new sessions going forward.
# Legacy routes/tables above are untouched and keep working for old data.

FUNCTIONAL_COLOR = '#2F82FF'
YOGA_COLOR = '#6FBFA0'
GOLD_COLOR = '#E8B84B'
POCI_COLOR = '#F97316'
FLEXIBILITY_COLOR = '#A855F7'
RUNNING_COLOR = '#EC4899'
# Gym variants are shades of blue, home variants are shades of green —
# matches the gym/home split introduced for Workout A/B (legacy 2-type
# workout_a/workout_b entries keep using FUNCTIONAL_COLOR, see legacy_meta).
WORKOUT_A_GYM_COLOR = '#3B82F6'
WORKOUT_B_GYM_COLOR = '#1D4ED8'
WORKOUT_A_HOME_COLOR = '#22C55E'
WORKOUT_B_HOME_COLOR = '#15803D'

WORKOUT_TYPE_LABELS = {
    'workout_a_gym': 'Workout A · Gym', 'workout_a_home': 'Workout A · Home',
    'workout_b_gym': 'Workout B · Gym', 'workout_b_home': 'Workout B · Home',
    'workout_a': 'Workout A (legacy)', 'workout_b': 'Workout B (legacy)',
}
REST_SECONDS_DEFAULT = 90

# A training block (mesocycle) this long before the Coach tab suggests
# rotating exercises / adjusting rep ranges / taking a deload week — within
# the commonly-cited 4-8 week range for hypertrophy-focused programs.
CYCLE_LENGTH_WEEKS = 6

# Workout types plannable on the Home calendar — same set offered by the
# Home screen's Gym/Home buttons and Yoga/Poci quick-start buttons.
PLAN_META = {
    'workout_a_gym': (WORKOUT_A_GYM_COLOR, WORKOUT_TYPE_LABELS['workout_a_gym'], 'functional'),
    'workout_a_home': (WORKOUT_A_HOME_COLOR, WORKOUT_TYPE_LABELS['workout_a_home'], 'functional'),
    'workout_b_gym': (WORKOUT_B_GYM_COLOR, WORKOUT_TYPE_LABELS['workout_b_gym'], 'functional'),
    'workout_b_home': (WORKOUT_B_HOME_COLOR, WORKOUT_TYPE_LABELS['workout_b_home'], 'functional'),
    'yoga': (YOGA_COLOR, 'Yoga', 'yoga'),
    'poci': (POCI_COLOR, 'Poci', 'poci'),
}

# The Home/Plan/History app's live-tracking content — derived from
# LIVE_WORKOUT_EXERCISES so there's a single source of truth for exercise
# names/sets/reps/cues, shared with the /workout/live/<type> legacy flow.
# No fixed weekly schedule: Workout A and B are always startable, and
# gym vs. home is chosen when the user starts a session, not baked into a day.
def _parse_rep_ceiling(reps_str):
    """Top of a prescribed rep range as an int (e.g. '8–10' -> 10, '8 each
    leg' -> 8), or None for time-held exercises ('30–45 sec') that aren't
    progressed by hitting a rep count."""
    if 'sec' in reps_str or 'min' in reps_str:
        return None
    nums = re.findall(r'\d+', reps_str)
    return int(nums[-1]) if nums else None


def _build_ab_workouts():
    out = {}
    for key, exercises in LIVE_WORKOUT_EXERCISES.items():
        out[key] = {
            'label': WORKOUT_TYPE_LABELS[key],
            'exercises': [
                {
                    'id': f'{key}_{i}',
                    'name': ex['name'],
                    'target_sets': ex['sets'],
                    'target_reps': ex['reps'],
                    'cue': ex['tip'],
                    'youtube': ex['youtube'],
                    'repCeiling': _parse_rep_ceiling(ex['reps']),
                    'progressionKg': ex.get('progression_kg'),
                }
                for i, ex in enumerate(exercises)
            ],
        }
    return out


AB_WORKOUTS = _build_ab_workouts()


def get_db():
    if not hasattr(g, '_db'):
        if DATABASE_URL == ':memory:':
            g._db = sqlite3.connect(':memory:')
            g._db.row_factory = sqlite3.Row
        else:
            db_path = DATABASE_URL
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
            g._db = sqlite3.connect(db_path)
            g._db.row_factory = sqlite3.Row
        g._db.execute('PRAGMA foreign_keys = ON')
        _create_tables(g._db)
        _migrate_db(g._db)
        if DATABASE_URL != ':memory:':
            _seed_sample_data(g._db)
            _purge_stale_mockup_sessions(g._db)
    return g._db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('_db', None)
    if db is not None:
        db.close()


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
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            session_type TEXT NOT NULL,
            workout_key TEXT,
            yoga_key TEXT,
            duration_sec INTEGER NOT NULL,
            pr_count INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS session_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            exercise_id TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            set_index INTEGER NOT NULL,
            weight REAL,
            reps INTEGER,
            is_pr BOOLEAN DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS exercise_notes (
            exercise_id TEXT PRIMARY KEY,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS planned_workouts (
            date TEXT PRIMARY KEY,
            workout_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS body_weight_logs (
            date TEXT PRIMARY KEY,
            weight_kg REAL NOT NULL,
            created_at TEXT NOT NULL
        );
    ''')
    conn.commit()


def _migrate_db(conn):
    cols = [row[1] for row in conn.execute('PRAGMA table_info(workout_exercises)').fetchall()]
    if 'weight_kg' not in cols:
        conn.execute('ALTER TABLE workout_exercises ADD COLUMN weight_kg TEXT')
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
    _purge_stale_mockup_sessions(conn)
    conn.close()


def _seed_sample_data(conn):
    """Demo data for a brand-new install only — gated on a one-time
    'seeded' flag rather than a live row count, so deleting the demo
    entries (or all history) later doesn't make them reappear on the next
    request."""
    if conn.execute("SELECT 1 FROM app_settings WHERE key='seeded'").fetchone():
        return
    conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('seeded', '1')")
    has_existing_data = (
        conn.execute('SELECT 1 FROM workouts LIMIT 1').fetchone()
        or conn.execute('SELECT 1 FROM sessions LIMIT 1').fetchone()
    )
    if has_existing_data:
        conn.commit()
        return
    today = date.today()
    samples = [
        (str(today - timedelta(days=5)), 'workout_a_gym', 'Felt strong today', [
            ('Squat', 3, '8,8,7'),
            ('Bench Press', 3, '10,10,9'),
            ('Pull-up', 3, '8,8,7'),
            ('Lower Back (Superman)', 2, '12,12'),
        ]),
        (str(today - timedelta(days=3)), 'poci', 'Great beach session, 2 hours', []),
        (str(today - timedelta(days=1)), 'workout_b_home', 'Heavy leg day', [
            ('Romanian Deadlift (dumbbell)', 3, '12,12,10'),
            ('Dumbbell Shoulder Press', 3, '10,10,9'),
            ('Bulgarian Split Squat (dumbbell)', 3, '10,10,9'),
            ('Plank', 2, '40s,40s'),
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


def _purge_stale_mockup_sessions(conn):
    """One-time cleanup: the first version of the redesigned app seeded
    sessions/session_sets with placeholder content from the Claude Design
    mockup (workout_key 'A'/'B'/'C', generic yoga templates). That content
    is being replaced with the user's real Workout A/B gym/home program, so
    wipe it once. Detected via the old single-letter workout_key values,
    which the current schema (workout_a_gym, etc.) never produces — once
    purged, this is permanently a no-op."""
    stale = conn.execute("SELECT 1 FROM sessions WHERE workout_key IN ('A','B','C') LIMIT 1").fetchone()
    if not stale:
        return
    conn.execute('DELETE FROM session_sets')
    conn.execute('DELETE FROM sessions')
    conn.execute('DELETE FROM exercise_notes')
    conn.commit()


def _weekday_sun0(d):
    """Weekday index with Sun=0..Sat=6."""
    return (d.weekday() + 1) % 7


def _fmt_num(v):
    if v is None:
        return '0'
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


def _fmt_rel_date(d, today):
    days_ago = (today - d).days
    if days_ago == 0:
        return 'Today'
    if days_ago == 1:
        return 'Yesterday'
    return d.strftime('%b') + ' ' + str(d.day)


def _day_has_any_session(db, d):
    ds = str(d)
    if db.execute("SELECT 1 FROM sessions WHERE date=? LIMIT 1", (ds,)).fetchone():
        return True
    return db.execute("SELECT 1 FROM workouts WHERE date=? LIMIT 1", (ds,)).fetchone() is not None


def _calc_day_streak(db, today):
    """Consecutive days (walking back from today) with at least one logged
    session of any kind — no fixed weekly schedule to match against anymore.
    Today doesn't break the streak if nothing's logged yet."""
    streak = 0
    d = today
    for _ in range(365):
        if _day_has_any_session(db, d):
            streak += 1
        elif d != today:
            break
        d -= timedelta(days=1)
    return streak


def _last_set_for_exercise(db, exercise_id):
    row = db.execute(
        '''SELECT ss.weight, ss.reps FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.exercise_id = ? ORDER BY s.date DESC, s.id DESC, ss.set_index ASC LIMIT 1''',
        (exercise_id,)
    ).fetchone()
    return {'weight': row['weight'], 'reps': row['reps']} if row else {'weight': 0, 'reps': 0}


def _best_weight_for_exercise(db, exercise_id):
    row = db.execute('SELECT MAX(weight) as m FROM session_sets WHERE exercise_id = ?', (exercise_id,)).fetchone()
    return row['m'] if row and row['m'] is not None else 0


def _last_pr(db):
    row = db.execute(
        '''SELECT ss.exercise_name, ss.weight, ss.reps FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.is_pr = 1 ORDER BY s.date DESC, s.id DESC LIMIT 1'''
    ).fetchone()
    if not row:
        return None
    return {'name': row['exercise_name'], 'value': _fmt_num(row['weight']) + 'kg × ' + str(row['reps'])}


def _get_setting(db, key, default=None):
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default


def _set_setting(db, key, value):
    db.execute(
        'INSERT INTO app_settings (key, value) VALUES (?,?) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        (key, value)
    )
    db.commit()


def _get_cycle_start(db, today):
    val = _get_setting(db, 'cycle_started_at')
    if val:
        return datetime.strptime(val, '%Y-%m-%d').date()
    # First time this is asked for: anchor to the earliest logged session so
    # an existing user doesn't get bumped back to "week 1" artificially; a
    # brand new user with no history yet just starts today.
    row = db.execute('SELECT MIN(date) as d FROM sessions').fetchone()
    start = datetime.strptime(row['d'], '%Y-%m-%d').date() if row and row['d'] else today
    _set_setting(db, 'cycle_started_at', str(start))
    return start


def _suggested_increment_kg(last_weight, base_increment):
    """The double-progression jump, capped so it's never more than ~10% of
    the current weight — the commonly-cited safe week-to-week load increase,
    to avoid the coach ever suggesting too big a jump on lighter weights."""
    if base_increment is None:
        return None
    if not last_weight or last_weight <= 0:
        return base_increment
    cap = last_weight * 0.10
    step = min(base_increment, cap)
    step = round(step * 2) / 2  # round to the nearest 0.5kg (typical plate/dumbbell jump)
    return max(step, 0.5)


def _progression_tip(db, exercise_id, rep_ceiling, base_increment_kg):
    """Double progression: once every set of the most recent session hit the
    top of the prescribed rep range, it's time to add weight next session."""
    if rep_ceiling is None or base_increment_kg is None:
        return None
    rows = db.execute(
        '''SELECT ss.session_id, ss.weight, ss.reps FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.exercise_id = ? ORDER BY s.date DESC, s.id DESC, ss.set_index ASC''',
        (exercise_id,)
    ).fetchall()
    if not rows:
        return None
    last_session_id = rows[0]['session_id']
    last_sets = [r for r in rows if r['session_id'] == last_session_id]
    last_weight = last_sets[0]['weight'] or 0
    hit_ceiling = all(r['reps'] is not None and r['reps'] >= rep_ceiling for r in last_sets)
    if hit_ceiling:
        step = _suggested_increment_kg(last_weight, base_increment_kg)
        return {
            'status': 'increase', 'repCeiling': rep_ceiling,
            'lastWeight': _fmt_num(last_weight), 'suggestedWeight': _fmt_num(round(last_weight + step, 1)),
        }
    return {'status': 'building', 'repCeiling': rep_ceiling, 'lastWeight': _fmt_num(last_weight)}


def _coach_tip_text(tip):
    if tip is None or tip['status'] != 'increase':
        return None
    return f"Coach: hit {tip['repCeiling']} reps on every set last time — try {tip['suggestedWeight']}kg today"


def _format_legacy_exercise_line(name, sets, reps, weight_kg):
    if weight_kg:
        reps_list = [r.strip() for r in reps.split(',')] if reps else []
        weight_list = [w.strip() for w in weight_kg.split(',')] if weight_kg else []
        pairs = []
        for i in range(max(len(reps_list), len(weight_list))):
            r = reps_list[i] if i < len(reps_list) else ''
            w = weight_list[i] if i < len(weight_list) else ''
            if w and r:
                pairs.append(w + 'kg×' + r)
            elif r:
                pairs.append(r)
        return ', '.join(pairs) if pairs else (reps or '—')
    if sets and reps:
        return str(sets) + ' sets · ' + reps
    return reps or ((str(sets) + ' sets') if sets else '—')


def _query_history(db, today, limit=None):
    items = []
    for r in db.execute(
        'SELECT id, date, session_type, workout_key, yoga_key, duration_sec, pr_count, notes '
        'FROM sessions ORDER BY date DESC, id DESC'
    ).fetchall():
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        if r['session_type'] == 'functional':
            w = AB_WORKOUTS.get(r['workout_key'])
            by_ex = {}
            for er in db.execute(
                'SELECT exercise_id, exercise_name, set_index, weight, reps FROM session_sets '
                'WHERE session_id=? ORDER BY exercise_id, set_index', (r['id'],)
            ).fetchall():
                by_ex.setdefault(er['exercise_id'], {'name': er['exercise_name'], 'sets': []})
                by_ex[er['exercise_id']]['sets'].append(_fmt_num(er['weight']) + '×' + str(er['reps']))
            items.append({
                'id': 's' + str(r['id']), 'category': 'functional', 'legacy': False, 'accent': FUNCTIONAL_COLOR,
                'title': w['label'] if w else (r['workout_key'] or 'Workout'),
                'date': str(d), 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': r['pr_count'] or 0,
                'exercises': [{'name': v['name'], 'sets': ', '.join(v['sets'])} for v in by_ex.values()],
                'notes': '', 'focusTags': [],
            })
        elif r['session_type'] == 'poci':
            items.append({
                'id': 's' + str(r['id']), 'category': 'poci', 'legacy': False, 'accent': POCI_COLOR,
                'title': 'Poci', 'date': str(d), 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': 0,
                'exercises': [], 'notes': r['notes'] or '', 'focusTags': [],
            })
        elif r['session_type'] == 'running':
            items.append({
                'id': 's' + str(r['id']), 'category': 'running', 'legacy': False, 'accent': RUNNING_COLOR,
                'title': r['notes'] or 'Run', 'date': str(d), 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': 0,
                'exercises': [], 'notes': '', 'focusTags': [],
            })
        else:
            items.append({
                'id': 's' + str(r['id']), 'category': 'yoga', 'legacy': False, 'accent': YOGA_COLOR,
                'title': r['notes'] if r['notes'] in {rt['title'] for rt in YOGA_ROUTINES} else 'Yoga Session',
                'date': str(d), 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': 0,
                'exercises': [], 'notes': r['notes'] or '', 'focusTags': [],
            })

    legacy_meta = {
        'workout_a': ('functional', FUNCTIONAL_COLOR, WORKOUT_TYPE_LABELS['workout_a']),
        'workout_b': ('functional', FUNCTIONAL_COLOR, WORKOUT_TYPE_LABELS['workout_b']),
        'workout_a_gym': ('functional', WORKOUT_A_GYM_COLOR, WORKOUT_TYPE_LABELS['workout_a_gym']),
        'workout_a_home': ('functional', WORKOUT_A_HOME_COLOR, WORKOUT_TYPE_LABELS['workout_a_home']),
        'workout_b_gym': ('functional', WORKOUT_B_GYM_COLOR, WORKOUT_TYPE_LABELS['workout_b_gym']),
        'workout_b_home': ('functional', WORKOUT_B_HOME_COLOR, WORKOUT_TYPE_LABELS['workout_b_home']),
        'poci': ('poci', POCI_COLOR, 'Poci'),
        'flexibility': ('flexibility', FLEXIBILITY_COLOR, 'Flexibility'),
    }
    for r in db.execute(
        '''SELECT w.id, w.date, w.type, w.notes,
                  GROUP_CONCAT(we.exercise_name || '|' || COALESCE(we.sets,'') || '|' || COALESCE(we.reps,'') || '|' || COALESCE(we.weight_kg,''), ';;') as ex_raw
           FROM workouts w LEFT JOIN workout_exercises we ON we.workout_id = w.id
           GROUP BY w.id ORDER BY w.date DESC'''
    ).fetchall():
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        category, accent, title = legacy_meta.get(r['type'], ('functional', FUNCTIONAL_COLOR, r['type']))
        exercises = []
        if r['ex_raw']:
            for chunk in r['ex_raw'].split(';;'):
                parts = chunk.split('|')
                if parts and parts[0]:
                    sets = parts[1] if len(parts) > 1 else ''
                    reps = parts[2] if len(parts) > 2 else ''
                    weight_kg = parts[3] if len(parts) > 3 else ''
                    exercises.append({'name': parts[0], 'sets': _format_legacy_exercise_line(parts[0], sets, reps, weight_kg)})
        items.append({
            'id': 'w' + str(r['id']), 'category': category, 'legacy': True, 'accent': accent,
            'title': title, 'date': str(d), 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
            'durationMin': None, 'prCount': 0, 'exercises': exercises, 'notes': r['notes'] or '', 'focusTags': [],
        })

    items.sort(key=lambda x: x['daysAgo'])
    return items[:limit] if limit else items


def _progress_chart_bars(db, today, exercise_id, metric):
    rows = list(reversed(db.execute(
        '''SELECT s.date, ss.weight, ss.reps FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.exercise_id = ? AND ss.set_index = 0 ORDER BY s.date DESC LIMIT 5''',
        (exercise_id,)
    ).fetchall()))
    vals = [(r['weight'] if metric == 'weight' else r['reps']) or 0 for r in rows]
    max_val = max(vals, default=1) or 1
    unit = 'kg' if metric == 'weight' else ''
    out = []
    for i, (r, v) in enumerate(zip(rows, vals)):
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        is_last = i == len(rows) - 1
        out.append({
            'value': _fmt_num(v) + unit,
            'heightPx': max(10, round(96 * (v / max_val))),
            'barColor': GOLD_COLOR if is_last else 'rgba(47,130,255,.55)',
            'valueColor': GOLD_COLOR if is_last else 'rgba(245,243,239,.55)',
            'label': _fmt_rel_date(d, today),
        })
    return out


def _is_time_based_exercise(exercise_id):
    workout_key, _, idx_str = exercise_id.rpartition('_')
    if not idx_str.isdigit() or workout_key not in LIVE_WORKOUT_EXERCISES:
        return False
    exercises = LIVE_WORKOUT_EXERCISES[workout_key]
    idx = int(idx_str)
    if idx >= len(exercises):
        return False
    reps_str = exercises[idx]['reps']
    return 'sec' in reps_str or 'min' in reps_str


def _all_progress_charts(db, today):
    """One chart per exercise logged at least twice: a weight chart if it's
    ever been logged with real weight, otherwise a reps chart for bodyweight
    exercises (Pull-up, Chin-up, Dips) where reps — not weight — is the real
    progression signal. Time-held exercises (Core Finisher, Farmer's Carry)
    are skipped entirely since neither metric is meaningful for those.
    Ordered by most recently logged."""
    rows = db.execute(
        '''SELECT ss.exercise_id, ss.exercise_name, COUNT(DISTINCT ss.session_id) as session_count,
                  MAX(s.date) as last_date, MAX(ss.weight) as max_weight
           FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.set_index = 0
           GROUP BY ss.exercise_id
           HAVING session_count >= 2
           ORDER BY last_date DESC'''
    ).fetchall()
    charts = []
    for r in rows:
        exercise_id = r['exercise_id']
        if r['max_weight']:
            metric = 'weight'
        elif not _is_time_based_exercise(exercise_id):
            metric = 'reps'
        else:
            continue
        charts.append({'exerciseId': exercise_id, 'label': r['exercise_name'], 'bars': _progress_chart_bars(db, today, exercise_id, metric)})
    return charts


def _body_weight_chart(db, today):
    rows = list(reversed(db.execute(
        'SELECT date, weight_kg FROM body_weight_logs ORDER BY date DESC LIMIT 8'
    ).fetchall()))
    max_kg = max((r['weight_kg'] for r in rows), default=1) or 1
    out = []
    for i, r in enumerate(rows):
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        is_last = i == len(rows) - 1
        out.append({
            'value': _fmt_num(r['weight_kg']) + 'kg',
            'heightPx': max(10, round(96 * (r['weight_kg'] / max_kg))),
            'barColor': GOLD_COLOR if is_last else 'rgba(47,130,255,.55)',
            'valueColor': GOLD_COLOR if is_last else 'rgba(245,243,239,.55)',
            'label': _fmt_rel_date(d, today),
        })
    return out


def _latest_body_weight(db):
    row = db.execute('SELECT date, weight_kg FROM body_weight_logs ORDER BY date DESC LIMIT 1').fetchone()
    if not row:
        return None
    return {'date': row['date'], 'weightKg': _fmt_num(row['weight_kg'])}


def _build_calendar_week(db, today, start):
    """7 days from `start` (a Sunday) — each day is either a completed
    session ('done'), a workout planned for a future/today date but not
    yet done ('planned'), or nothing ('empty')."""
    by_date = {}
    for h in _query_history(db, today):
        by_date.setdefault(h['date'], h)
    plan_rows = db.execute(
        'SELECT date, workout_key FROM planned_workouts WHERE date BETWEEN ? AND ?',
        (str(start), str(start + timedelta(days=6)))
    ).fetchall()
    plans = {r['date']: r['workout_key'] for r in plan_rows}

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        ds = str(d)
        entry = {
            'date': ds, 'dayLabel': d.strftime('%a').upper(), 'dayNum': d.day,
            'isToday': d == today, 'isFuture': d > today,
        }
        h = by_date.get(ds)
        plan_key = plans.get(ds)
        if h:
            entry.update(status='done', title=h['title'], accent=h['accent'], category=h['category'], prCount=h['prCount'])
        elif plan_key and plan_key in PLAN_META:
            accent, label, category = PLAN_META[plan_key]
            entry.update(status='planned', workoutKey=plan_key, title=label, accent=accent, category=category)
        else:
            entry.update(status='empty')
        days.append(entry)
    return days


def _build_coach_data(db, today):
    cycle_start = _get_cycle_start(db, today)
    days_in = (today - cycle_start).days
    cycle_week = min(CYCLE_LENGTH_WEEKS, days_in // 7 + 1)
    cycle_complete = days_in >= CYCLE_LENGTH_WEEKS * 7

    exercises = []
    seen_names = set()
    for key, exs in LIVE_WORKOUT_EXERCISES.items():
        for i, ex in enumerate(exs):
            if ex['name'] in seen_names:
                continue  # gym/home variants of the same move (e.g. Pull-up) share a name — show once
            ceiling = _parse_rep_ceiling(ex['reps'])
            tip = _progression_tip(db, f'{key}_{i}', ceiling, ex.get('progression_kg'))
            if tip is None:
                continue  # never logged, or not a weight-progressed (time-held) exercise
            seen_names.add(ex['name'])
            exercises.append(dict(tip, name=ex['name']))

    return {
        'cycleStartDate': str(cycle_start), 'cycleWeek': cycle_week,
        'cycleLengthWeeks': CYCLE_LENGTH_WEEKS, 'cycleComplete': cycle_complete,
        'exercises': exercises,
    }


def _build_initial_data(db):
    today = date.today()
    today_idx = _weekday_sun0(today)
    now = datetime.now()

    history = _query_history(db, today)
    ab_workouts_out = {}
    for key, w in AB_WORKOUTS.items():
        exs = []
        for ex in w['exercises']:
            last = _last_set_for_exercise(db, ex['id'])
            tip = _progression_tip(db, ex['id'], ex['repCeiling'], ex['progressionKg'])
            exs.append(dict(ex, lastWeight=last['weight'], lastReps=last['reps'], coachTip=_coach_tip_text(tip)))
        ab_workouts_out[key] = {'label': w['label'], 'exercises': exs}

    # Sessions logged from this Sun-Sat week through today — a simple
    # activity count, not tied to any required schedule.
    week_count = sum(1 for h in history if h['daysAgo'] <= today_idx)
    week_start = today - timedelta(days=today_idx)

    return {
        'today': str(today),
        'greeting': 'Good morning.' if now.hour < 12 else ('Good afternoon.' if now.hour < 18 else 'Good evening.'),
        'todayDateLabel': (today.strftime('%A, %b') + ' ' + str(today.day)).upper(),
        'streak': _calc_day_streak(db, today), 'showGamification': True,
        'restSeconds': REST_SECONDS_DEFAULT, 'autoRestTimer': True,
        'weekCount': week_count,
        'lastPR': _last_pr(db), 'lastSession': history[0] if history else None,
        'abWorkouts': ab_workouts_out,
        'exerciseNotes': {r['exercise_id']: r['note'] for r in db.execute('SELECT exercise_id, note FROM exercise_notes').fetchall()},
        'history': history,
        'progressCharts': _all_progress_charts(db, today),
        'calendarWeekStart': str(week_start), 'calendarWeek': _build_calendar_week(db, today, week_start),
        'coach': _build_coach_data(db, today),
        'bodyWeightChart': _body_weight_chart(db, today), 'bodyWeightLatest': _latest_body_weight(db),
        'yogaNextRoutine': _next_yoga_routine(db), 'yogaWristRoutine': YOGA_ROUTINES_BY_KEY['wrist'],
        'runningNextSession': _next_running_session(db),
    }


@app.route('/')
def dashboard():
    db = get_db()
    initial_data = _build_initial_data(db)
    return render_template('training_app.html', initial_data=initial_data)


@app.route('/api/calendar')
def get_calendar_week():
    try:
        start = datetime.strptime(request.args.get('start', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid start date'}), 400
    db = get_db()
    days = _build_calendar_week(db, date.today(), start)
    return jsonify({'start': str(start), 'days': days})


@app.route('/api/calendar/plan', methods=['POST'])
def set_planned_workout():
    data = request.get_json(silent=True) or {}
    try:
        d = datetime.strptime(data.get('date', ''), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date'}), 400
    if d < date.today():
        return jsonify({'error': 'Cannot plan a past date'}), 400

    workout_key = data.get('workoutKey')
    db = get_db()
    if workout_key is None:
        db.execute('DELETE FROM planned_workouts WHERE date=?', (str(d),))
    else:
        if workout_key not in PLAN_META:
            return jsonify({'error': 'Invalid workout key'}), 400
        db.execute(
            'INSERT INTO planned_workouts (date, workout_key, created_at) VALUES (?,?,?) '
            'ON CONFLICT(date) DO UPDATE SET workout_key=excluded.workout_key, created_at=excluded.created_at',
            (str(d), workout_key, datetime.now().isoformat())
        )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/coach/new-cycle', methods=['POST'])
def start_new_cycle():
    db = get_db()
    today = date.today()
    _set_setting(db, 'cycle_started_at', str(today))
    return jsonify({'success': True, 'cycleStartDate': str(today), 'cycleWeek': 1, 'cycleComplete': False})


@app.route('/api/bodyweight', methods=['POST'])
def log_body_weight():
    data = request.get_json(silent=True) or {}
    try:
        d = datetime.strptime(data.get('date', str(date.today())), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date'}), 400
    try:
        weight_kg = float(data.get('weightKg'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid weight'}), 400
    if weight_kg <= 0:
        return jsonify({'error': 'Invalid weight'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO body_weight_logs (date, weight_kg, created_at) VALUES (?,?,?) '
        'ON CONFLICT(date) DO UPDATE SET weight_kg=excluded.weight_kg, created_at=excluded.created_at',
        (str(d), weight_kg, datetime.now().isoformat())
    )
    db.commit()
    today = date.today()
    return jsonify({
        'success': True,
        'bodyWeightChart': _body_weight_chart(db, today),
        'bodyWeightLatest': _latest_body_weight(db),
    })


@app.route('/log', methods=['GET', 'POST'])
def log_workout():
    if request.method == 'POST':
        workout_type = request.form.get('workout_type')
        if not workout_type or workout_type not in VALID_WORKOUT_TYPES:
            flash('Invalid workout type.', 'error')
            return redirect(url_for('log_workout'))
        workout_date = request.form.get('date', str(date.today()))
        notes = request.form.get('notes', '')

        db = get_db()
        cur = db.execute(
            'INSERT INTO workouts (date, type, notes, created_at) VALUES (?,?,?,?)',
            (workout_date, workout_type, notes, datetime.now().isoformat())
        )
        workout_id = cur.lastrowid

        if workout_type in ('workout_a_gym', 'workout_a_home', 'workout_b_gym', 'workout_b_home'):
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
        flash('Workout logged successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('log_workout.html',
        workout_a_gym_exercises=WORKOUT_A_GYM_EXERCISES,
        workout_a_home_exercises=WORKOUT_A_HOME_EXERCISES,
        workout_b_gym_exercises=WORKOUT_B_GYM_EXERCISES,
        workout_b_home_exercises=WORKOUT_B_HOME_EXERCISES,
        today=str(date.today()))


@app.route('/history')
def history():
    filter_type = request.args.get('type', 'all')
    db = get_db()

    query = '''
        SELECT w.id, w.date, w.type, w.notes, w.created_at,
               GROUP_CONCAT(we.exercise_name || '|' || COALESCE(we.sets,'') || '|' || COALESCE(we.reps,'') || '|' || COALESCE(we.weight_kg,''), ';;') as exercises_raw
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
                if len(parts) >= 3:
                    exercises.append({
                        'name': parts[0],
                        'sets': parts[1],
                        'reps': parts[2],
                        'weight_kg': parts[3] if len(parts) > 3 else '',
                    })
        w['exercises'] = exercises
        workouts.append(w)

    return render_template('history.html', workouts=workouts, filter_type=filter_type)


@app.route('/api/delete/<int:workout_id>', methods=['POST'])
def delete_workout(workout_id):
    db = get_db()
    db.execute('DELETE FROM workout_exercises WHERE workout_id = ?', (workout_id,))
    db.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/history/delete/<item_id>', methods=['POST'])
def delete_history_item(item_id):
    """item_id matches the prefixed ids _query_history hands to the client:
    's<id>' for the new sessions table, 'w<id>' for legacy workouts rows."""
    db = get_db()
    if item_id.startswith('s') and item_id[1:].isdigit():
        db.execute('DELETE FROM sessions WHERE id = ?', (int(item_id[1:]),))
    elif item_id.startswith('w') and item_id[1:].isdigit():
        workout_id = int(item_id[1:])
        db.execute('DELETE FROM workout_exercises WHERE workout_id = ?', (workout_id,))
        db.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    else:
        return jsonify({'error': 'Invalid id'}), 400
    db.commit()
    return jsonify({'success': True})


@app.route('/api/workouts/previous/<workout_type>')
def previous_workout(workout_type):
    if workout_type not in LIVE_WORKOUT_EXERCISES:
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
        weights_list = [w.strip() for w in (ex['weight_kg'] or '').split(',')] if ex['weight_kg'] else []
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


@app.route('/workout/live/<workout_type>')
def live_workout(workout_type):
    if workout_type not in LIVE_WORKOUT_EXERCISES:
        return redirect(url_for('dashboard'))
    exercises = LIVE_WORKOUT_EXERCISES[workout_type]
    return render_template('live_workout.html',
        workout_type=workout_type,
        workout_label=WORKOUT_TYPE_LABELS.get(workout_type, workout_type),
        exercises=exercises,
        today=str(date.today()))


@app.route('/log/live', methods=['POST'])
def log_live():
    data = request.get_json(silent=True) or {}
    workout_type = data.get('workout_type')
    if not workout_type or workout_type not in VALID_WORKOUT_TYPES:
        return jsonify({'error': 'Invalid workout type'}), 400
    workout_date = data.get('date', str(date.today()))
    exercises = data.get('exercises', [])
    if not isinstance(exercises, list):
        return jsonify({'error': 'Invalid exercises'}), 400

    db = get_db()
    cur = db.execute(
        'INSERT INTO workouts (date, type, notes, created_at) VALUES (?,?,?,?)',
        (workout_date, workout_type, 'Live workout', datetime.now().isoformat())
    )
    workout_id = cur.lastrowid

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

    db.commit()
    flash('Workout logged successfully!', 'success')
    return jsonify({'success': True, 'redirect': url_for('dashboard')})


@app.route('/api/sessions/functional', methods=['POST'])
def save_functional_session():
    data = request.get_json(silent=True) or {}
    workout_key = data.get('workoutKey')
    if workout_key not in AB_WORKOUTS:
        return jsonify({'error': 'Invalid workout key'}), 400
    session_date = data.get('date', str(date.today()))
    try:
        duration_sec = max(1, int(data.get('durationSec') or 60))
    except (TypeError, ValueError):
        duration_sec = 60
    exercises = data.get('exercises', [])
    notes = data.get('notes') or {}
    if not isinstance(exercises, list) or not isinstance(notes, dict):
        return jsonify({'error': 'Invalid payload'}), 400

    db = get_db()
    cur = db.execute(
        'INSERT INTO sessions (date, session_type, workout_key, duration_sec, pr_count, created_at) VALUES (?,?,?,?,?,?)',
        (session_date, 'functional', workout_key, duration_sec, 0, datetime.now().isoformat())
    )
    session_id = cur.lastrowid
    pr_count = 0
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        exercise_id = str(ex.get('id', ''))[:50]
        exercise_name = str(ex.get('name', ''))[:200]
        sets = ex.get('sets', [])
        if not exercise_id or not isinstance(sets, list):
            continue
        best_before = _best_weight_for_exercise(db, exercise_id)
        for i, s in enumerate(sets):
            if not isinstance(s, dict):
                continue
            try:
                weight = float(s.get('weight'))
                reps = int(s.get('reps'))
            except (TypeError, ValueError):
                continue
            is_pr = best_before > 0 and weight > best_before
            if is_pr:
                pr_count += 1
                best_before = weight
            db.execute(
                'INSERT INTO session_sets (session_id, exercise_id, exercise_name, set_index, weight, reps, is_pr) '
                'VALUES (?,?,?,?,?,?,?)',
                (session_id, exercise_id, exercise_name, i, weight, reps, 1 if is_pr else 0)
            )
        note_text = notes.get(exercise_id)
        if note_text:
            db.execute(
                'INSERT INTO exercise_notes (exercise_id, note) VALUES (?, ?) '
                'ON CONFLICT(exercise_id) DO UPDATE SET note=excluded.note',
                (exercise_id, str(note_text)[:1000])
            )
    db.execute('UPDATE sessions SET pr_count=? WHERE id=?', (pr_count, session_id))
    db.execute('DELETE FROM planned_workouts WHERE date=?', (session_date,))
    db.commit()
    return jsonify({'success': True, 'prCount': pr_count})


GENERIC_SESSION_CATEGORIES = {'yoga', 'poci'}

# Real follow-along mobility videos, not a self-assembled pose list — a
# genuine instructor gives pacing/breathing/safety cues a static list can't.
# Rotates automatically each time one is logged; the wrist routine is also
# reachable on its own since carpal tunnel relief benefits from a much
# higher frequency (research suggests up to daily) than the others.
YOGA_ROUTINES = [
    {'key': 'legs', 'title': 'Leg & Squat Mobility', 'focus': 'Hip and ankle mobility for deeper, safer squats',
     'youtube': 'https://www.youtube.com/watch?v=tuTjC6u03Lg', 'duration_sec': 900},
    {'key': 'back_posture', 'title': 'Lower Back & Posture', 'focus': 'Spinal mobility and rounded-shoulder relief',
     'youtube': 'https://www.youtube.com/watch?v=6YgehNFlYH0', 'duration_sec': 900},
    {'key': 'wrist', 'title': 'Wrist & Carpal Tunnel Care', 'focus': 'Nerve glides and forearm stretches',
     'youtube': 'https://www.youtube.com/watch?v=TPXaQFC6xT4', 'duration_sec': 600},
]
YOGA_ROUTINES_BY_KEY = {r['key']: r for r in YOGA_ROUTINES}


def _walk(sec):
    return {'type': 'walk', 'duration_sec': sec}


def _run(sec):
    return {'type': 'run', 'duration_sec': sec}


def _run_walk(reps, run_sec, walk_sec, trailing_walk=True):
    """`reps` run/walk pairs back to back; drop the final walk when the
    interval right after this block is itself a run (e.g. week 5 day 1's
    5-3-5-3-5 pattern, which is 3 runs with only 2 walks between them)."""
    out = []
    for i in range(reps):
        out.append(_run(run_sec))
        if trailing_walk or i < reps - 1:
            out.append(_walk(walk_sec))
    return out


WARMUP_WALK = _walk(300)  # every session opens with the same 5-minute brisk walk


def _same_all_week(week_num, intervals):
    return [{'week': week_num, 'day': d, 'intervals': intervals} for d in (1, 2, 3)]


# The NHS Couch to 5K program — the most widely-used, validated beginner
# walk/run progression, 3 sessions/week over 9 weeks. Weeks 1, 2, 4, 7, 8, 9
# repeat the same session all 3 days; weeks 3, 5 and 6 vary session-to-session
# within the week as continuous running is introduced.
RUNNING_PROGRAM = (
    _same_all_week(1, [WARMUP_WALK] + _run_walk(8, 60, 90))
    + _same_all_week(2, [WARMUP_WALK] + _run_walk(6, 90, 120))
    + _same_all_week(3, [WARMUP_WALK] + (_run_walk(1, 90, 90) + _run_walk(1, 180, 180)) * 2)
    + _same_all_week(4, [WARMUP_WALK, _run(180), _walk(90), _run(300), _walk(150), _run(180), _walk(90), _run(300)])
    + [
        {'week': 5, 'day': 1, 'intervals': [WARMUP_WALK] + _run_walk(3, 300, 180, trailing_walk=False)},
        {'week': 5, 'day': 2, 'intervals': [WARMUP_WALK] + _run_walk(2, 480, 300, trailing_walk=False)},
        {'week': 5, 'day': 3, 'intervals': [WARMUP_WALK, _run(1200)]},
    ]
    + [
        {'week': 6, 'day': 1, 'intervals': [WARMUP_WALK, _run(300), _walk(180), _run(480), _walk(180), _run(300)]},
        {'week': 6, 'day': 2, 'intervals': [WARMUP_WALK] + _run_walk(2, 600, 180, trailing_walk=False)},
        {'week': 6, 'day': 3, 'intervals': [WARMUP_WALK, _run(1500)]},
    ]
    + _same_all_week(7, [WARMUP_WALK, _run(1500)])
    + _same_all_week(8, [WARMUP_WALK, _run(1680)])
    + _same_all_week(9, [WARMUP_WALK, _run(1800)])
)
RUNNING_PROGRAM_BY_WD = {(s['week'], s['day']): s for s in RUNNING_PROGRAM}
RUNNING_TOTAL_WEEKS = 9


def _running_progress(db):
    week = int(_get_setting(db, 'running_week', 1))
    day = int(_get_setting(db, 'running_day', 1))
    if (week, day) not in RUNNING_PROGRAM_BY_WD:
        week, day = 1, 1
    return week, day


def _next_running_session(db):
    week, day = _running_progress(db)
    session = RUNNING_PROGRAM_BY_WD[(week, day)]
    graduated = week == RUNNING_TOTAL_WEEKS and day == 3
    return {
        'week': week, 'day': day, 'totalWeeks': RUNNING_TOTAL_WEEKS,
        'intervals': session['intervals'],
        'totalDurationSec': sum(i['duration_sec'] for i in session['intervals']),
        'graduated': graduated,
    }


def _yoga_rotation_idx(db):
    val = _get_setting(db, 'yoga_rotation_idx')
    try:
        return int(val) % len(YOGA_ROUTINES)
    except (TypeError, ValueError):
        return 0


def _next_yoga_routine(db):
    return YOGA_ROUTINES[_yoga_rotation_idx(db)]


@app.route('/api/sessions/yoga', methods=['POST'])
def save_yoga_session():
    data = request.get_json(silent=True) or {}
    routine = YOGA_ROUTINES_BY_KEY.get(data.get('routineKey'))
    if not routine:
        return jsonify({'error': 'Invalid routine'}), 400
    session_date = data.get('date', str(date.today()))

    db = get_db()
    db.execute(
        'INSERT INTO sessions (date, session_type, duration_sec, notes, created_at) VALUES (?,?,?,?,?)',
        (session_date, 'yoga', routine['duration_sec'], routine['title'], datetime.now().isoformat())
    )
    db.execute('DELETE FROM planned_workouts WHERE date=?', (session_date,))
    idx = _yoga_rotation_idx(db)
    if YOGA_ROUTINES[idx]['key'] == routine['key']:
        _set_setting(db, 'yoga_rotation_idx', str((idx + 1) % len(YOGA_ROUTINES)))
    db.commit()
    return jsonify({'success': True, 'yogaNextRoutine': _next_yoga_routine(db)})


@app.route('/api/sessions/running', methods=['POST'])
def save_running_session():
    data = request.get_json(silent=True) or {}
    try:
        week, day = int(data.get('week')), int(data.get('day'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid week/day'}), 400
    session = RUNNING_PROGRAM_BY_WD.get((week, day))
    if not session:
        return jsonify({'error': 'Invalid week/day'}), 400
    session_date = data.get('date', str(date.today()))
    duration_sec = sum(i['duration_sec'] for i in session['intervals'])

    db = get_db()
    db.execute(
        'INSERT INTO sessions (date, session_type, duration_sec, notes, created_at) VALUES (?,?,?,?,?)',
        (session_date, 'running', duration_sec, f'Week {week} · Day {day}', datetime.now().isoformat())
    )
    db.execute('DELETE FROM planned_workouts WHERE date=?', (session_date,))
    cur_week, cur_day = _running_progress(db)
    is_graduation = week == RUNNING_TOTAL_WEEKS and day == 3
    if (cur_week, cur_day) == (week, day) and not is_graduation:
        next_day, next_week = (day + 1, week) if day < 3 else (1, week + 1)
        _set_setting(db, 'running_week', str(next_week))
        _set_setting(db, 'running_day', str(next_day))
    db.commit()
    return jsonify({'success': True, 'runningNextSession': _next_running_session(db)})


@app.route('/api/sessions/generic', methods=['POST'])
def save_generic_session():
    """Freeform timed session (yoga or poci) — just a duration and notes,
    no prescribed template. You can add your own real content later."""
    data = request.get_json(silent=True) or {}
    category = data.get('category')
    if category not in GENERIC_SESSION_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    session_date = data.get('date', str(date.today()))
    try:
        duration_sec = max(1, int(data.get('durationSec') or 60))
    except (TypeError, ValueError):
        duration_sec = 60
    notes = str(data.get('notes', ''))[:2000]

    db = get_db()
    db.execute(
        'INSERT INTO sessions (date, session_type, duration_sec, notes, created_at) VALUES (?,?,?,?,?)',
        (session_date, category, duration_sec, notes, datetime.now().isoformat())
    )
    db.execute('DELETE FROM planned_workouts WHERE date=?', (session_date,))
    db.commit()
    return jsonify({'success': True})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
