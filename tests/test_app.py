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

def test_live_workout_page_loads(client):
    r = client.get('/workout/live/workout_a')
    assert r.status_code == 200
    r = client.get('/workout/live/workout_b')
    assert r.status_code == 200

def test_live_workout_invalid_type_redirects(client):
    r = client.get('/workout/live/invalid')
    assert r.status_code == 302

def test_log_live_post(client):
    import json
    payload = {
        'workout_type': 'workout_a',
        'date': '2026-06-07',
        'exercises': [
            {'name': 'Pull-up', 'sets': 3, 'reps': '8,8,7'},
            {'name': 'Plank', 'sets': 3, 'reps': '40 sec,40 sec,40 sec'},
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
    assert data['workout_type'] == 'workout_a'
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
        'workoutKey': 'B',
        'date': '2026-07-01',
        'durationSec': 1800,
        'exercises': [
            {'id': 'b1', 'name': 'Squat (Dumbbell)', 'sets': [
                {'weight': 25, 'reps': 10}, {'weight': 25, 'reps': 10}, {'weight': 25, 'reps': 9},
            ]},
        ],
        'notes': {'b1': 'Felt good today'},
    }
    r = client.post('/api/sessions/functional', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    # first-ever weight for b1 in this empty test DB is a baseline, not a PR
    assert data['prCount'] == 0

    r2 = client.get('/')
    assert b'Squat (Dumbbell)' in r2.data


def test_save_functional_session_invalid_workout_key(client):
    import json
    r = client.post('/api/sessions/functional',
        data=json.dumps({'workoutKey': 'Z', 'exercises': []}),
        content_type='application/json')
    assert r.status_code == 400


def test_save_functional_session_detects_pr(client):
    import json
    base = {'workoutKey': 'A', 'exercises': [
        {'id': 'a1', 'name': 'Goblet Squat (Dumbbell)', 'sets': [{'weight': 10, 'reps': 12}]},
    ]}
    client.post('/api/sessions/functional', data=json.dumps(base), content_type='application/json')
    heavier = {'workoutKey': 'A', 'exercises': [
        {'id': 'a1', 'name': 'Goblet Squat (Dumbbell)', 'sets': [{'weight': 15, 'reps': 12}]},
    ]}
    r = client.post('/api/sessions/functional', data=json.dumps(heavier), content_type='application/json')
    data = json.loads(r.data)
    assert data['prCount'] == 1


def test_save_yoga_session(client):
    import json
    payload = {'yogaKey': 'yoga1', 'date': '2026-07-01', 'durationSec': 1500, 'notes': 'Good stretch'}
    r = client.post('/api/sessions/yoga', data=json.dumps(payload), content_type='application/json')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

    r2 = client.get('/')
    assert b'Good stretch' in r2.data


def test_save_yoga_session_invalid_key(client):
    import json
    r = client.post('/api/sessions/yoga',
        data=json.dumps({'yogaKey': 'nope'}),
        content_type='application/json')
    assert r.status_code == 400


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
    assert len(data2['exercises']) == 1
    ex2 = data2['exercises'][0]
    assert ex2['name'] == 'Pull-up'
    assert ex2['weights'] == ['10', '10', '10']
