import os
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

VALID_WORKOUT_TYPES = {'workout_a', 'workout_b', 'poci', 'flexibility'}

WORKOUT_A_EXERCISES = [
    'Pull-up', 'Inverted Row', 'Wide Push-up',
    'Face Pull (band)', 'Plank', 'Hanging Knee Raise'
]

WORKOUT_B_EXERCISES = [
    'Squat (dumbbell)', 'Romanian Deadlift', 'Bulgarian Split Squat',
    'Standing Calf Raise', 'Single-Leg Calf Raise', 'Lateral Raise', 'Shrugs'
]

LIVE_WORKOUT_EXERCISES = {
    'workout_a': [
        {'name': 'Pull-up', 'sets': 3, 'reps': '5–10',
         'youtube': 'https://www.youtube.com/watch?v=eGo4IYlbE5g',
         'tip': "Start from dead hang. Pull shoulder blades DOWN first before pulling up. Drive elbows toward back pockets."},
        {'name': 'Inverted Row', 'sets': 3, 'reps': '10–12',
         'youtube': 'https://www.youtube.com/watch?v=LR0yiMqS5DI',
         'tip': "Keep body in a straight line from head to heels. Squeeze shoulder blades together at the top."},
        {'name': 'Wide Push-up', 'sets': 3, 'reps': '10–12',
         'youtube': 'https://www.youtube.com/watch?v=IODxDxX7oi4',
         'tip': "Keep core tight, don't let hips sag. Lower chest all the way to the floor."},
        {'name': 'Face Pull (band)', 'sets': 3, 'reps': '15',
         'youtube': 'https://www.youtube.com/watch?v=rep-qVOkqgk',
         'tip': "Pull to eye level, not chin. Keep elbows high throughout the movement."},
        {'name': 'Plank', 'sets': 3, 'reps': '40 sec',
         'youtube': 'https://www.youtube.com/watch?v=ASdvN_XEl_c',
         'tip': "Squeeze glutes and abs together. Don't hold your breath."},
        {'name': 'Hanging Knee Raise', 'sets': 3, 'reps': '12',
         'youtube': 'https://www.youtube.com/watch?v=Pr1ieGZ5atk',
         'tip': "No swinging. Control the lowering phase slowly."},
    ],
    'workout_b': [
        {'name': 'Squat (dumbbell)', 'sets': 3, 'reps': '10–12',
         'youtube': 'https://www.youtube.com/watch?v=ultWZbUMPL8',
         'tip': "Chest up, knees track over toes. Sit back like into a chair."},
        {'name': 'Romanian Deadlift', 'sets': 3, 'reps': '10–12',
         'youtube': 'https://www.youtube.com/watch?v=JCXUYuzwNrM',
         'tip': "Hinge at hips, push butt back. Keep dumbbells close to legs. Stop when you feel hamstring stretch."},
        {'name': 'Bulgarian Split Squat', 'sets': 3, 'reps': '8 each leg',
         'youtube': 'https://www.youtube.com/watch?v=2C-uNgKwPLE',
         'tip': "Front foot far enough forward. Keep torso upright, don't lean forward."},
        {'name': 'Standing Calf Raise', 'sets': 4, 'reps': '15–20',
         'youtube': 'https://www.youtube.com/watch?v=gwLzBJYoWlI',
         'tip': "Full range — all the way up AND all the way down. Pause 1 second at the top."},
        {'name': 'Single-Leg Calf Raise', 'sets': 3, 'reps': '12 each leg',
         'youtube': 'https://www.youtube.com/watch?v=SjPkUNVvmE0',
         'tip': "Hold something for balance only. Same full range as Standing Calf Raise."},
        {'name': 'Lateral Raise', 'sets': 3, 'reps': '12–15',
         'youtube': 'https://www.youtube.com/watch?v=3VcKaXpzqRo',
         'tip': "Slight bend in elbow. Raise to shoulder height only — no higher."},
        {'name': 'Shrugs', 'sets': 3, 'reps': '15',
         'youtube': 'https://www.youtube.com/watch?v=cJRVVxmytaM',
         'tip': "Straight up and down only. Never roll shoulders — it causes injury."},
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
REST_SECONDS_DEFAULT = 90
WEEKDAY_LETTERS_EN = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

FUNCTIONAL_WORKOUTS = {
    'A': {
        'name': 'Workout A', 'est_min': 35,
        'exercises': [
            {'id': 'a1', 'name': 'Goblet Squat (Dumbbell)', 'target_sets': 3, 'target_reps': '12–15',
             'cue': 'Elbows brush your knees at the bottom, drive up through mid-foot.'},
            {'id': 'a2', 'name': 'Dumbbell Deadlift', 'target_sets': 3, 'target_reps': '8–10',
             'cue': 'Flat back, hinge from the hips, keep the dumbbells close to your shins.'},
            {'id': 'a3', 'name': 'Step-Up (Dumbbell)', 'target_sets': 3, 'target_reps': '10/leg',
             'cue': 'Drive through the lead heel, control the descent.'},
            {'id': 'a4', 'name': 'Overhead Press (Dumbbell)', 'target_sets': 3, 'target_reps': '8–10',
             'cue': 'Ribs down, press straight up, brace your core.'},
            {'id': 'a5', 'name': 'Single-Arm Row (Dumbbell)', 'target_sets': 3, 'target_reps': '10/side',
             'cue': 'Flat back, pull your elbow past your hip, pause at the top.'},
            {'id': 'a6', 'name': 'Floor Press (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Elbows at 45°, pause briefly on the floor each rep.'},
            {'id': 'a7', 'name': 'Hammer Curl (Dumbbell)', 'target_sets': 3, 'target_reps': '12',
             'cue': 'Elbows pinned, no swinging — control the negative.'},
        ],
    },
    'B': {
        'name': 'Workout B', 'est_min': 40,
        'exercises': [
            {'id': 'b1', 'name': 'Squat (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Chest up, knees track over toes — sit back like into a chair.'},
            {'id': 'b2', 'name': 'Romanian Deadlift (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Soft knees, hinge at the hips, keep the dumbbells close to your shins.'},
            {'id': 'b3', 'name': 'Walking Lunge (Dumbbell)', 'target_sets': 3, 'target_reps': '12/leg',
             'cue': 'Long stride, drop the back knee straight down, drive through the front heel.'},
            {'id': 'b4', 'name': 'Push Press (Dumbbell)', 'target_sets': 3, 'target_reps': '8–10',
             'cue': 'Dip, drive, punch through — let your legs do the work.'},
            {'id': 'b5', 'name': 'Bent-Over Row (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Flat back, pull to the hip, squeeze at the top.'},
            {'id': 'b6', 'name': 'Floor Chest Press (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Elbows at 45°, press up and slightly in over the chest.'},
            {'id': 'b7', 'name': 'Renegade Row (Dumbbell)', 'target_sets': 3, 'target_reps': '8/side',
             'cue': 'Wide stance, minimize hip rotation, row without twisting.'},
        ],
    },
    'C': {
        'name': 'Workout C', 'est_min': 38,
        'exercises': [
            {'id': 'c1', 'name': 'Front Squat (Dumbbell)', 'target_sets': 3, 'target_reps': '8–10',
             'cue': 'Elbows high, core braced, sit straight down between your hips.'},
            {'id': 'c2', 'name': 'Single-Leg RDL (Dumbbell)', 'target_sets': 3, 'target_reps': '10/leg',
             'cue': 'Hips square, reach long, soft bend in the standing knee.'},
            {'id': 'c3', 'name': 'Reverse Lunge (Dumbbell)', 'target_sets': 3, 'target_reps': '10/leg',
             'cue': 'Step back light on the toe, drop straight down.'},
            {'id': 'c4', 'name': 'Arnold Press (Dumbbell)', 'target_sets': 3, 'target_reps': '8–10',
             'cue': 'Rotate through the bottom, press up and out.'},
            {'id': 'c5', 'name': 'Chest-Supported Row (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': 'Chest pinned to the bench, squeeze the shoulder blades.'},
            {'id': 'c6', 'name': 'Incline Press (Dumbbell)', 'target_sets': 3, 'target_reps': '10–12',
             'cue': '45° bench, press up and slightly back, control the descent.'},
            {'id': 'c7', 'name': 'Lateral Raise (Dumbbell)', 'target_sets': 3, 'target_reps': '12',
             'cue': 'Soft elbows, lead with the elbows, stop at shoulder height.'},
        ],
    },
}

YOGA_SESSIONS = {
    'yoga1': {'title': 'Flow & Breath', 'coach': 'Coach Maya · YouTube', 'est_min': 30, 'focus': ['Mobility', 'Breathwork']},
    'yoga2': {'title': 'Hips & Backbends', 'coach': 'Coach Maya · YouTube', 'est_min': 32, 'focus': ['Hips', 'Backbend']},
}

# Repeating weekly cycle, index 0=Sun .. 6=Sat
WEEKLY_PLAN = [
    {'type': 'rest'},
    {'type': 'functional', 'workout_key': 'A'},
    {'type': 'yoga', 'yoga_key': 'yoga1'},
    {'type': 'rest'},
    {'type': 'functional', 'workout_key': 'B'},
    {'type': 'yoga', 'yoga_key': 'yoga2'},
    {'type': 'functional', 'workout_key': 'C'},
]


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
            _seed_new_sessions(g._db)
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
    _seed_new_sessions(conn)
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


def _seed_new_sessions(conn):
    """Seed sample functional/yoga session history so the new Home/Plan/History
    screens aren't empty on a fresh install. No-ops once real sessions exist."""
    count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
    if count > 0:
        return
    today = date.today()

    def add_functional(days_ago, workout_key, duration_min, sets_by_exercise, pr_exercise_id=None):
        d = str(today - timedelta(days=days_ago))
        cur = conn.execute(
            'INSERT INTO sessions (date, session_type, workout_key, duration_sec, pr_count, created_at) VALUES (?,?,?,?,?,?)',
            (d, 'functional', workout_key, duration_min * 60, 1 if pr_exercise_id else 0, datetime.now().isoformat())
        )
        sid = cur.lastrowid
        names = {ex['id']: ex['name'] for ex in FUNCTIONAL_WORKOUTS[workout_key]['exercises']}
        for ex_id, sets in sets_by_exercise.items():
            for i, (weight, reps) in enumerate(sets):
                is_pr = 1 if (pr_exercise_id == ex_id and i == 0) else 0
                conn.execute(
                    'INSERT INTO session_sets (session_id, exercise_id, exercise_name, set_index, weight, reps, is_pr) '
                    'VALUES (?,?,?,?,?,?,?)',
                    (sid, ex_id, names[ex_id], i, weight, reps, is_pr)
                )

    def add_yoga(days_ago, yoga_key, duration_min, notes):
        d = str(today - timedelta(days=days_ago))
        conn.execute(
            'INSERT INTO sessions (date, session_type, yoga_key, duration_sec, notes, created_at) VALUES (?,?,?,?,?,?)',
            (d, 'yoga', yoga_key, duration_min * 60, notes, datetime.now().isoformat())
        )

    add_functional(1, 'C', 37, {
        'c1': [(22, 9), (22, 9), (22, 8)], 'c2': [(12, 10), (12, 10), (12, 9)],
        'c3': [(16, 10), (16, 10), (16, 10)], 'c4': [(12, 9), (12, 9), (12, 8)],
        'c5': [(18, 11), (18, 11), (18, 10)], 'c6': [(18, 10), (18, 10), (16, 12)],
        'c7': [(8, 12), (8, 12), (8, 12)],
    }, pr_exercise_id='c1')
    add_yoga(2, 'yoga2', 32, 'Deep pigeon variations today, still tight on the left hip. Backbends felt easier than last week.')
    add_functional(4, 'B', 41, {
        'b1': [(22, 12), (22, 12), (22, 11)], 'b2': [(20, 10), (20, 10), (20, 10)],
        'b3': [(14, 12), (14, 12), (12, 12)], 'b4': [(16, 9), (16, 8), (14, 10)],
        'b5': [(20, 11), (20, 11), (18, 12)], 'b6': [(20, 11), (18, 12), (18, 12)],
        'b7': [(12, 8), (12, 8), (10, 10)],
    }, pr_exercise_id='b1')
    add_yoga(6, 'yoga1', 29, 'Slower pace today, focused on breath timing through the sun salutations.')
    add_functional(8, 'A', 34, {
        'a1': [(18, 14), (18, 14), (18, 13)], 'a2': [(24, 9), (24, 9), (24, 8)],
        'a3': [(12, 10), (12, 10), (12, 10)], 'a4': [(14, 9), (14, 8), (12, 10)],
        'a5': [(20, 10), (20, 10), (20, 10)], 'a6': [(18, 11), (18, 11), (16, 12)],
        'a7': [(10, 12), (10, 12), (10, 12)],
    })
    add_functional(11, 'B', 39, {
        'b1': [(20, 12), (20, 12), (20, 10)], 'b2': [(18, 11), (18, 11), (18, 10)],
        'b3': [(12, 12), (12, 12), (12, 12)], 'b4': [(14, 10), (14, 9), (12, 10)],
        'b5': [(18, 12), (18, 11), (16, 12)], 'b6': [(18, 11), (16, 12), (16, 12)],
        'b7': [(10, 8), (10, 8), (10, 8)],
    })
    # Older Workout B sessions kept minimal — only here to give the squat
    # progress chart 5 data points of depth.
    add_functional(18, 'B', 40, {'b1': [(20, 11), (20, 11), (20, 10)]})
    add_functional(25, 'B', 40, {'b1': [(18, 12), (18, 11), (18, 10)]})
    add_functional(32, 'B', 40, {'b1': [(16, 12), (16, 12), (16, 11)]})

    conn.execute('INSERT INTO exercise_notes (exercise_id, note) VALUES (?,?)',
                 ('b1', 'Felt strong — ready to add weight next time.'))
    conn.execute('INSERT INTO exercise_notes (exercise_id, note) VALUES (?,?)',
                 ('a2', 'Grip was the limiter, not legs.'))
    conn.commit()


def _weekday_sun0(d):
    """Weekday index with Sun=0..Sat=6, matching WEEKLY_PLAN order."""
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


def _day_has_matching_session(db, d, plan_type):
    ds = str(d)
    if plan_type == 'functional':
        if db.execute("SELECT 1 FROM sessions WHERE date=? AND session_type='functional' LIMIT 1", (ds,)).fetchone():
            return True
        return db.execute(
            "SELECT 1 FROM workouts WHERE date=? AND type IN ('workout_a','workout_b') LIMIT 1", (ds,)
        ).fetchone() is not None
    if plan_type == 'yoga':
        if db.execute("SELECT 1 FROM sessions WHERE date=? AND session_type='yoga' LIMIT 1", (ds,)).fetchone():
            return True
        return db.execute(
            "SELECT 1 FROM workouts WHERE date=? AND type='flexibility' LIMIT 1", (ds,)
        ).fetchone() is not None
    return False


def _calc_day_streak(db, today):
    """Consecutive scheduled training days completed, walking back from today.
    Rest days don't count for or against it; today doesn't break it if unfinished."""
    streak = 0
    d = today
    for _ in range(365):
        plan_type = WEEKLY_PLAN[_weekday_sun0(d)]['type']
        if plan_type != 'rest':
            if _day_has_matching_session(db, d, plan_type):
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


def _plan_detail_for_day(db, d, plan, is_today, is_past):
    ptype = plan['type']
    if ptype == 'functional':
        w = FUNCTIONAL_WORKOUTS[plan['workout_key']]
        status = 'Completed' if (is_past and _day_has_matching_session(db, d, 'functional')) else \
            ('Missed' if is_past else ('Scheduled' if not is_today else ''))
        names = [ex['name'].replace(' (Dumbbell)', '') for ex in w['exercises']]
        preview = ' · '.join(names[:3]) + (' +' + str(len(names) - 3) + ' more' if len(names) > 3 else '')
        return {
            'type': 'functional', 'workoutKey': plan['workout_key'], 'accent': FUNCTIONAL_COLOR,
            'eyebrow': 'TODAY · FUNCTIONAL' if is_today else 'FUNCTIONAL STRENGTH',
            'title': w['name'], 'meta': str(len(w['exercises'])) + ' exercises · ~' + str(w['est_min']) + ' min',
            'exercises': [{'name': ex['name'], 'target': str(ex['target_sets']) + '×' + ex['target_reps']} for ex in w['exercises']],
            'focusTags': [], 'preview': preview, 'showCta': is_today, 'ctaLabel': 'Start Workout',
            'hasStatus': bool(status), 'statusTag': status,
        }
    if ptype == 'yoga':
        y = YOGA_SESSIONS[plan['yoga_key']]
        status = 'Completed' if (is_past and _day_has_matching_session(db, d, 'yoga')) else \
            ('Missed' if is_past else ('Scheduled' if not is_today else ''))
        return {
            'type': 'yoga', 'yogaKey': plan['yoga_key'], 'accent': YOGA_COLOR,
            'eyebrow': 'TODAY · YOGA' if is_today else 'YOGA',
            'title': y['title'], 'meta': y['coach'] + ' · ~' + str(y['est_min']) + ' min',
            'exercises': [], 'focusTags': y['focus'], 'preview': ' · '.join(y['focus']),
            'showCta': is_today, 'ctaLabel': 'Start Session',
            'hasStatus': bool(status), 'statusTag': status,
        }
    return {
        'type': 'rest', 'accent': 'rgba(245,243,239,.35)',
        'eyebrow': 'TODAY · REST' if is_today else 'REST DAY', 'title': 'Recovery day',
        'meta': 'Light movement, mobility, or full rest — your call.' if is_today else 'Light movement, mobility, or full rest.',
        'exercises': [], 'focusTags': [], 'preview': '', 'showCta': False, 'ctaLabel': '',
        'hasStatus': False, 'statusTag': '',
    }


def _query_history(db, today, limit=None):
    items = []
    for r in db.execute(
        'SELECT id, date, session_type, workout_key, yoga_key, duration_sec, pr_count, notes '
        'FROM sessions ORDER BY date DESC, id DESC'
    ).fetchall():
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        if r['session_type'] == 'functional':
            w = FUNCTIONAL_WORKOUTS.get(r['workout_key'])
            by_ex = {}
            for er in db.execute(
                'SELECT exercise_id, exercise_name, set_index, weight, reps FROM session_sets '
                'WHERE session_id=? ORDER BY exercise_id, set_index', (r['id'],)
            ).fetchall():
                by_ex.setdefault(er['exercise_id'], {'name': er['exercise_name'], 'sets': []})
                by_ex[er['exercise_id']]['sets'].append(_fmt_num(er['weight']) + '×' + str(er['reps']))
            items.append({
                'id': 's' + str(r['id']), 'category': 'functional', 'legacy': False, 'accent': FUNCTIONAL_COLOR,
                'title': w['name'] if w else (r['workout_key'] or 'Workout'),
                'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': r['pr_count'] or 0,
                'exercises': [{'name': v['name'], 'sets': ', '.join(v['sets'])} for v in by_ex.values()],
                'notes': '', 'focusTags': [],
            })
        else:
            y = YOGA_SESSIONS.get(r['yoga_key'])
            items.append({
                'id': 's' + str(r['id']), 'category': 'yoga', 'legacy': False, 'accent': YOGA_COLOR,
                'title': y['title'] if y else (r['yoga_key'] or 'Yoga'),
                'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
                'durationMin': max(1, round(r['duration_sec'] / 60)), 'prCount': 0,
                'exercises': [], 'notes': r['notes'] or '', 'focusTags': y['focus'] if y else [],
            })

    legacy_meta = {
        'workout_a': ('functional', FUNCTIONAL_COLOR, 'Workout A (legacy)'),
        'workout_b': ('functional', FUNCTIONAL_COLOR, 'Workout B (legacy)'),
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
            'title': title, 'dateLabel': _fmt_rel_date(d, today), 'daysAgo': (today - d).days,
            'durationMin': None, 'prCount': 0, 'exercises': exercises, 'notes': r['notes'] or '', 'focusTags': [],
        })

    items.sort(key=lambda x: x['daysAgo'])
    return items[:limit] if limit else items


def _squat_chart(db, today):
    rows = list(reversed(db.execute(
        '''SELECT s.date, ss.weight FROM session_sets ss JOIN sessions s ON s.id = ss.session_id
           WHERE ss.exercise_id = 'b1' AND ss.set_index = 0 ORDER BY s.date DESC LIMIT 5'''
    ).fetchall()))
    max_kg = max((r['weight'] for r in rows), default=1) or 1
    out = []
    for i, r in enumerate(rows):
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        is_last = i == len(rows) - 1
        out.append({
            'value': _fmt_num(r['weight']) + 'kg',
            'heightPx': max(10, round(96 * (r['weight'] / max_kg))),
            'barColor': GOLD_COLOR if is_last else 'rgba(47,130,255,.55)',
            'valueColor': GOLD_COLOR if is_last else 'rgba(245,243,239,.55)',
            'label': _fmt_rel_date(d, today),
        })
    return out


def _build_initial_data(db):
    today = date.today()
    today_idx = _weekday_sun0(today)
    sunday = today - timedelta(days=today_idx)
    now = datetime.now()

    week_days = []
    plan_by_day = []
    training_total, training_done = 0, 0
    for i in range(7):
        d = sunday + timedelta(days=i)
        plan = WEEKLY_PLAN[i]
        ptype = plan['type']
        is_today = i == today_idx
        done = ptype != 'rest' and _day_has_matching_session(db, d, ptype)
        if ptype != 'rest':
            training_total += 1
            if done:
                training_done += 1
        accent = FUNCTIONAL_COLOR if ptype == 'functional' else (YOGA_COLOR if ptype == 'yoga' else 'rgba(245,243,239,.16)')
        week_days.append({
            'idx': i, 'letter': WEEKDAY_LETTERS_EN[i], 'dateNum': d.day,
            'planType': ptype, 'accent': accent, 'done': done, 'isToday': is_today,
        })
        plan_by_day.append(_plan_detail_for_day(db, d, plan, is_today, i < today_idx))

    sat = sunday + timedelta(days=6)
    week_range_label = sunday.strftime('%b') + ' ' + str(sunday.day) + ' – ' + sat.strftime('%b') + ' ' + str(sat.day)

    history = _query_history(db, today)
    workouts_out = {}
    for key, w in FUNCTIONAL_WORKOUTS.items():
        exs = []
        for ex in w['exercises']:
            last = _last_set_for_exercise(db, ex['id'])
            exs.append(dict(ex, lastWeight=last['weight'], lastReps=last['reps']))
        workouts_out[key] = {'name': w['name'], 'estMin': w['est_min'], 'exercises': exs}

    return {
        'today': str(today), 'todayIdx': today_idx,
        'greeting': 'Good morning.' if now.hour < 12 else ('Good afternoon.' if now.hour < 18 else 'Good evening.'),
        'todayDateLabel': (today.strftime('%A, %b') + ' ' + str(today.day)).upper(),
        'streak': _calc_day_streak(db, today), 'showGamification': True,
        'restSeconds': REST_SECONDS_DEFAULT, 'autoRestTimer': True,
        'weekDays': week_days, 'weekRangeLabel': week_range_label,
        'todayPlan': plan_by_day[today_idx], 'planByDay': plan_by_day,
        'statWeek': str(training_done) + '/' + str(training_total),
        'lastPR': _last_pr(db), 'lastSession': history[0] if history else None,
        'workouts': workouts_out, 'yogaSessions': YOGA_SESSIONS,
        'exerciseNotes': {r['exercise_id']: r['note'] for r in db.execute('SELECT exercise_id, note FROM exercise_notes').fetchall()},
        'history': history, 'squatChart': _squat_chart(db, today),
    }


@app.route('/')
def dashboard():
    db = get_db()
    initial_data = _build_initial_data(db)
    return render_template('training_app.html', initial_data=initial_data)


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
    if workout_type not in ('workout_a', 'workout_b'):
        return redirect(url_for('dashboard'))
    exercises = LIVE_WORKOUT_EXERCISES[workout_type]
    return render_template('live_workout.html',
        workout_type=workout_type,
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
    if workout_key not in FUNCTIONAL_WORKOUTS:
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
    db.commit()
    return jsonify({'success': True, 'prCount': pr_count})


@app.route('/api/sessions/yoga', methods=['POST'])
def save_yoga_session():
    data = request.get_json(silent=True) or {}
    yoga_key = data.get('yogaKey')
    if yoga_key not in YOGA_SESSIONS:
        return jsonify({'error': 'Invalid yoga key'}), 400
    session_date = data.get('date', str(date.today()))
    try:
        duration_sec = max(1, int(data.get('durationSec') or 60))
    except (TypeError, ValueError):
        duration_sec = 60
    notes = str(data.get('notes', ''))[:2000]

    db = get_db()
    db.execute(
        'INSERT INTO sessions (date, session_type, yoga_key, duration_sec, notes, created_at) VALUES (?,?,?,?,?,?)',
        (session_date, 'yoga', yoga_key, duration_sec, notes, datetime.now().isoformat())
    )
    db.commit()
    return jsonify({'success': True})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
