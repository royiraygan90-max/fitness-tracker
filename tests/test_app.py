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
