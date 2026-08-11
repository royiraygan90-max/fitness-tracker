import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
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

def test_log_workout_a_gym_post(client):
    r = client.post('/log', data={
        'workout_type': 'workout_a_gym',
        'date': '2026-06-06',
        'notes': '',
        'exercises': ['Squat', 'Pull-up'],
        'sets_Squat': '3',
        'reps_Squat': '8,8,7',
        'sets_Pull-up': '3',
        'reps_Pull-up': '8,8,6',
    }, follow_redirects=True)
    assert r.status_code == 200

def test_log_workout_a_home_post(client):
    r = client.post('/log', data={
        'workout_type': 'workout_a_home',
        'date': '2026-06-06',
        'notes': '',
        'exercises': ['Goblet Squat (dumbbell)', 'Parallette Dips'],
        'sets_Goblet Squat (dumbbell)': '3',
        'reps_Goblet Squat (dumbbell)': '10,10,9',
        'sets_Parallette Dips': '3',
        'reps_Parallette Dips': '10,10,8',
    }, follow_redirects=True)
    assert r.status_code == 200

def test_live_workout_page_loads(client):
    for workout_type in ('workout_a_gym', 'workout_a_home', 'workout_b_gym', 'workout_b_home'):
        r = client.get(f'/workout/live/{workout_type}')
        assert r.status_code == 200, workout_type

def test_live_workout_legacy_type_redirects(client):
    # workout_a/workout_b are retired for *new* live sessions — they only
    # still work as read-only history via legacy DB rows.
    r = client.get('/workout/live/workout_a')
    assert r.status_code == 302
    r = client.get('/workout/live/workout_b')
    assert r.status_code == 302

def test_live_workout_invalid_type_redirects(client):
    r = client.get('/workout/live/invalid')
    assert r.status_code == 302

def test_log_live_post(client):
    import json
    payload = {
        'workout_type': 'workout_a_gym',
        'date': '2026-06-07',
        'exercises': [
            {'name': 'Squat', 'sets': 3, 'reps': '8,8,7'},
            {'name': 'Pull-up', 'sets': 3, 'reps': '8,7,6'},
        ]
    }
    r = client.post('/log/live',
        data=json.dumps(payload),
        content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True

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

def test_previous_workout_none(client):
    import json
    r = client.get('/api/workouts/previous/workout_a_gym')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data == {'previous': None}

def test_previous_workout_invalid_type(client):
    r = client.get('/api/workouts/previous/poci')
    assert r.status_code == 400

def test_previous_workout_legacy_type_invalid(client):
    # workout_a/workout_b no longer have a live-tracking flow to resume into
    r = client.get('/api/workouts/previous/workout_a')
    assert r.status_code == 400

def test_previous_workout_returns_last(client):
    import json
    # Log an older workout_a_gym
    client.post('/log/live',
        data=json.dumps({
            'workout_type': 'workout_a_gym',
            'date': '2026-01-01',
            'exercises': [{'name': 'Pull-up', 'sets': 3, 'reps': '7,7,6', 'weights': '8,8,8'}]
        }),
        content_type='application/json')
    # Log a more recent workout_a_gym
    client.post('/log/live',
        data=json.dumps({
            'workout_type': 'workout_a_gym',
            'date': '2026-01-05',
            'exercises': [{'name': 'Pull-up', 'sets': 3, 'reps': '8,8,7', 'weights': '10,10,10'}]
        }),
        content_type='application/json')
    r = client.get('/api/workouts/previous/workout_a_gym')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['date'] == '2026-01-05'
    assert data['workout_type'] == 'workout_a_gym'
    assert len(data['exercises']) == 1
    ex = data['exercises'][0]
    assert ex['name'] == 'Pull-up'
    assert ex['reps'] == ['8', '8', '7']
    assert ex['weights'] == ['10', '10', '10']

def test_home_serves_training_app(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'window.__INITIAL__' in r.data
    assert b'training.js' in r.data


def test_save_functional_session(client):
    import json
    payload = {
        'workoutKey': 'workout_b_gym',
        'date': '2026-07-01',
        'durationSec': 1800,
        'exercises': [
            {'id': 'workout_b_gym_0', 'name': 'Smith Machine RDL', 'sets': [
                {'weight': 25, 'reps': 10}, {'weight': 25, 'reps': 10}, {'weight': 25, 'reps': 9},
            ]},
        ],
        'notes': {'workout_b_gym_0': 'Felt good today'},
    }
    r = client.post('/api/sessions/functional', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    # first-ever weight for this exercise in the empty test DB is a baseline, not a PR
    assert data['prCount'] == 0

    r2 = client.get('/')
    assert b'Smith Machine RDL' in r2.data


def test_save_functional_session_invalid_workout_key(client):
    import json
    r = client.post('/api/sessions/functional',
        data=json.dumps({'workoutKey': 'nope', 'exercises': []}),
        content_type='application/json')
    assert r.status_code == 400


def test_save_functional_session_detects_pr(client):
    import json
    base = {'workoutKey': 'workout_a_gym', 'exercises': [
        {'id': 'workout_a_gym_0', 'name': 'Squat', 'sets': [{'weight': 10, 'reps': 12}]},
    ]}
    client.post('/api/sessions/functional', data=json.dumps(base), content_type='application/json')
    heavier = {'workoutKey': 'workout_a_gym', 'exercises': [
        {'id': 'workout_a_gym_0', 'name': 'Squat', 'sets': [{'weight': 15, 'reps': 12}]},
    ]}
    r = client.post('/api/sessions/functional', data=json.dumps(heavier), content_type='application/json')
    data = json.loads(r.data)
    assert data['prCount'] == 1


def test_save_generic_session_yoga(client):
    import json
    payload = {'category': 'yoga', 'date': '2026-07-01', 'durationSec': 1500, 'notes': 'Good stretch'}
    r = client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

    r2 = client.get('/')
    assert b'Good stretch' in r2.data


def test_save_generic_session_poci(client):
    import json
    payload = {'category': 'poci', 'date': '2026-07-01', 'durationSec': 3600, 'notes': 'Beach session'}
    r = client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

    r2 = client.get('/')
    assert b'Beach session' in r2.data


def test_save_generic_session_invalid_category(client):
    import json
    r = client.post('/api/sessions/generic',
        data=json.dumps({'category': 'nope'}),
        content_type='application/json')
    assert r.status_code == 400


# ---------- clientToken dedup (retry-after-dropped-response protection) ----------

def test_functional_session_retry_with_same_token_not_duplicated(client):
    import json
    payload = {
        'workoutKey': 'workout_a_gym', 'clientToken': 'tok-func-1',
        'exercises': [{'id': 'workout_a_gym_0', 'name': 'Squat', 'sets': [{'weight': 20, 'reps': 10}]}],
    }
    r1 = client.post('/api/sessions/functional', data=json.dumps(payload), content_type='application/json')
    r2 = client.post('/api/sessions/functional', data=json.dumps(payload), content_type='application/json')
    assert r1.status_code == 200 and r2.status_code == 200
    assert json.loads(r1.data)['success'] is True
    assert json.loads(r2.data)['success'] is True

    db = flask_app.get_db()
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE client_token='tok-func-1'").fetchone()['c'] == 1
    assert db.execute("SELECT COUNT(*) c FROM session_sets").fetchone()['c'] == 1


def test_generic_session_retry_with_same_token_not_duplicated(client):
    import json
    payload = {'category': 'yoga', 'durationSec': 900, 'clientToken': 'tok-generic-1'}
    client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')
    client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')

    db = flask_app.get_db()
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE client_token='tok-generic-1'").fetchone()['c'] == 1


def test_running_session_retry_with_same_token_does_not_advance_progress_twice(client):
    import json
    payload = {'week': 1, 'day': 1, 'clientToken': 'tok-run-1'}
    r1 = client.post('/api/sessions/running', data=json.dumps(payload), content_type='application/json')
    r2 = client.post('/api/sessions/running', data=json.dumps(payload), content_type='application/json')
    data1 = json.loads(r1.data)['runningNextSession']
    data2 = json.loads(r2.data)['runningNextSession']
    # A single real completion should advance week/day exactly once, not twice.
    assert data1['week'] == 1 and data1['day'] == 2
    assert data2['week'] == 1 and data2['day'] == 2

    db = flask_app.get_db()
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE client_token='tok-run-1'").fetchone()['c'] == 1


def test_free_run_retry_with_same_token_not_duplicated(client):
    import json
    payload = {'distanceKm': 5.2, 'durationSec': 1800, 'clientToken': 'tok-freerun-1'}
    r1 = client.post('/api/sessions/running/free', data=json.dumps(payload), content_type='application/json')
    r2 = client.post('/api/sessions/running/free', data=json.dumps(payload), content_type='application/json')
    assert json.loads(r1.data)['runningStats']['totalDistanceKm'] == json.loads(r2.data)['runningStats']['totalDistanceKm']

    db = flask_app.get_db()
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE client_token='tok-freerun-1'").fetchone()['c'] == 1


def test_different_tokens_both_saved(client):
    import json
    payload1 = {'category': 'poci', 'durationSec': 600, 'clientToken': 'tok-a'}
    payload2 = {'category': 'poci', 'durationSec': 600, 'clientToken': 'tok-b'}
    client.post('/api/sessions/generic', data=json.dumps(payload1), content_type='application/json')
    client.post('/api/sessions/generic', data=json.dumps(payload2), content_type='application/json')

    db = flask_app.get_db()
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE session_type='poci'").fetchone()['c'] == 2


def test_missing_client_token_still_saves_normally(client):
    import json
    payload = {'category': 'poci', 'durationSec': 600}
    r1 = client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')
    r2 = client.post('/api/sessions/generic', data=json.dumps(payload), content_type='application/json')
    assert r1.status_code == 200 and r2.status_code == 200

    db = flask_app.get_db()
    # No token on either request means no dedup — both legitimately save,
    # same as two separate real Poci logs would.
    assert db.execute("SELECT COUNT(*) c FROM sessions WHERE session_type='poci'").fetchone()['c'] == 2


def test_log_live_with_weights(client):
    import json
    payload = {
        'workout_type': 'workout_a_gym',
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
    r2 = client.get('/api/workouts/previous/workout_a_gym')
    data2 = json.loads(r2.data)
    assert len(data2['exercises']) == 1
    ex2 = data2['exercises'][0]
    assert ex2['name'] == 'Pull-up'
    assert ex2['weights'] == ['10', '10', '10']


def test_legacy_workout_type_still_displays(client):
    # Simulate a workout logged before the gym/home split existed: a raw
    # 'workout_a' row inserted straight into the DB (the current /log and
    # /log/live endpoints no longer accept this type as input — only the
    # 4 new gym/home types and poci/flexibility are valid going forward).
    # Note: reuse the app context the `client` fixture already has pushed —
    # opening a *new* app_context() here would get its own separate
    # sqlite3.connect(':memory:') and never be seen by client.get/post.
    db = flask_app.get_db()
    db.execute(
        "INSERT INTO workouts (date, type, notes, created_at) VALUES (?,?,?,?)",
        ('2026-05-01', 'workout_a', 'legacy entry', '2026-05-01T00:00:00')
    )
    db.commit()

    r = client.get('/history')
    assert r.status_code == 200
    assert b'Workout A (legacy)' in r.data

    # It should also show up, unbroken, in the new unified History screen.
    r2 = client.get('/')
    assert r2.status_code == 200
    assert b'Workout A (legacy)' in r2.data


def test_valid_workout_types_are_the_four_gym_home_variants(client):
    assert flask_app.VALID_WORKOUT_TYPES == {
        'workout_a_gym', 'workout_a_home', 'workout_b_gym', 'workout_b_home',
        'poci', 'flexibility',
    }


def test_home_uses_real_ab_workouts_not_claude_design_mockup(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.data.decode()
    # the real gym/home program is what's served now...
    assert 'Squat' in body and 'Workout A \\u00b7 Gym' in body
    # ...and none of the placeholder mockup content from the Claude Design
    # handoff (Functional Strength A/B/C, prescribed yoga sessions) remains.
    for stale in ('Front Squat (Dumbbell)', 'Single-Leg RDL', 'Flow &amp; Breath', 'Coach Maya'):
        assert stale not in body


def test_purge_stale_mockup_sessions_wipes_old_seed_data(client):
    from datetime import datetime
    db = flask_app.get_db()
    db.execute(
        "INSERT INTO sessions (date, session_type, workout_key, duration_sec, pr_count, created_at) "
        "VALUES ('2026-07-17','functional','C',2200,1,?)",
        (datetime.now().isoformat(),)
    )
    db.execute(
        "INSERT INTO session_sets (session_id, exercise_id, exercise_name, set_index, weight, reps, is_pr) "
        "VALUES (1,'c1','Front Squat (Dumbbell)',0,22,9,1)"
    )
    db.execute("INSERT INTO exercise_notes (exercise_id, note) VALUES ('a2','Grip was the limiter.')")
    db.commit()
    assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1

    flask_app._purge_stale_mockup_sessions(db)

    assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM session_sets').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM exercise_notes').fetchone()[0] == 0


def test_purge_stale_mockup_sessions_leaves_real_data_alone(client):
    from datetime import datetime
    db = flask_app.get_db()
    db.execute(
        "INSERT INTO sessions (date, session_type, workout_key, duration_sec, pr_count, created_at) "
        "VALUES ('2026-07-17','functional','workout_a_gym',1800,0,?)",
        (datetime.now().isoformat(),)
    )
    db.commit()

    flask_app._purge_stale_mockup_sessions(db)

    assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
