import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['INGEST_API_KEY'] = 'test-key'
os.environ['ML_AUTO_TRAIN_ENABLED'] = 'false'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base, get_session
from app.main import app


@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_session] = session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


payload = dict(device_id='esp32-01', temperature_c=25.0, air_humidity_pct=65,
               soil_raw=2100, measured_at='2026-11-09T12:00:00Z')
headers = {'X-API-Key': 'test-key'}


def test_store_and_filter(client):
    result = client.post('/api/v1/measurements', json=payload, headers=headers)
    assert result.status_code == 201
    assert result.json()['soil_raw'] == 2100
    assert result.json()['received_at']
    rows = client.get('/api/v1/measurements?device_id=esp32-01', headers=headers)
    assert len(rows.json()) == 1
    assert client.get('/api/v1/measurements?device_id=other', headers=headers).json() == []
    assert client.get('/api/v1/measurements?since=2026-11-10T00:00:00Z', headers=headers).json() == []


@pytest.mark.parametrize('changes', [dict(air_humidity_pct=101), dict(soil_raw=-1),
    dict(measured_at='2026-11-09T12:00:00'), dict(soil_raw=1.2), dict(unknown=1)])
def test_invalid_samples(client, changes):
    assert client.post('/api/v1/measurements', json=payload | changes, headers=headers).status_code == 422


def test_authorization_and_query_limits(client):
    assert client.post('/api/v1/measurements', json=payload).status_code == 401
    assert client.get('/api/v1/measurements').status_code == 401
    assert client.get('/api/v1/measurements?limit=1001', headers=headers).status_code == 422
    assert client.get('/api/v1/measurements?since=2026-11-09T00:00:00', headers=headers).status_code == 422
    assert client.get('/health').json() == {'status': 'ok'}


def test_prediction_requires_auth_and_real_model(client):
    assert client.get('/api/v1/predictions?device_id=esp32-01').status_code == 401
    result = client.get('/api/v1/predictions?device_id=esp32-01', headers=headers)
    assert result.status_code == 200
    assert result.json()['status'] == 'unavailable'
    assert 'predicted_soil_raw' not in result.json()


def test_history_range_for_dashboard(client):
    client.post('/api/v1/measurements', json=payload, headers=headers)
    assert client.get('/api/v1/measurements?until=2026-11-09T11:00:00Z', headers=headers).json() == []
    assert len(client.get('/api/v1/measurements?until=2026-11-09T13:00:00Z', headers=headers).json()) == 1
    assert client.get('/api/v1/measurements?until=2026-11-09T11:00:00', headers=headers).status_code == 422
    assert client.get('/api/v1/measurements?since=2026-11-10T00:00:00Z&until=2026-11-09T00:00:00Z', headers=headers).status_code == 422


def test_api_root_supports_optional_react_build(client):
    result = client.get('/')
    assert result.status_code == 200
    assert 'Ambiente' in result.text


def test_cors_allows_only_configured_frontend(client):
    allowed = client.options('/api/v1/measurements', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'X-API-Key'})
    assert allowed.status_code == 200
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    denied = client.options('/api/v1/measurements', headers={
        'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'GET'})
    assert 'access-control-allow-origin' not in denied.headers
