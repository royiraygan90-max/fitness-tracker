import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fitness-tracker-dev-secret')

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
        if DATABASE_URL != ':memory:':
            _seed_sample_data(g._db)
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

    return render_template('history.html', workouts=workouts, filter_type=filter_type)


@app.route('/api/delete/<int:workout_id>', methods=['POST'])
def delete_workout(workout_id):
    db = get_db()
    db.execute('DELETE FROM workout_exercises WHERE workout_id = ?', (workout_id,))
    db.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    db.commit()
    return jsonify({'success': True})


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
        db.execute(
            'INSERT INTO workout_exercises (workout_id, exercise_name, sets, reps, completed) VALUES (?,?,?,?,1)',
            (workout_id, name, sets_int, reps_val)
        )

    db.commit()
    flash('Workout logged successfully!', 'success')
    return jsonify({'success': True, 'redirect': url_for('dashboard')})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
