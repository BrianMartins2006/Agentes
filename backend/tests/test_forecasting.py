from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import math

import pytest
from app.forecasting import (aggregate, chronological_split, fit_model, forecast,
                             InsufficientData, make_examples)


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def samples(count=400):
    # Synthetic fixture only; never inserted into the application database.
    return [SimpleNamespace(device_id="test-device", measured_at=START + timedelta(minutes=i),
                soil_raw=3300 + i + 20 * math.sin(i / 30),
                temperature_c=24 + math.sin(i / 60), air_humidity_pct=60 + math.cos(i / 60))
            for i in range(count)]


def test_target_horizon_and_no_temporal_overlap():
    buckets = aggregate(samples(), START + timedelta(minutes=400))
    examples = make_examples(buckets)
    train, test = chronological_split(examples)
    assert all(e[1] - e[0] == timedelta(minutes=30) for e in examples)
    assert train[-1][1] < test[0][0] - timedelta(minutes=5)


def test_gaps_and_unfinished_minute_are_excluded():
    rows = samples(60)
    rows.pop(30)
    buckets = aggregate(rows, START + timedelta(minutes=59, seconds=30))
    assert START + timedelta(minutes=60) not in buckets
    assert not make_examples(buckets)  # Neither continuous segment is long enough.


def test_fit_roundtrip_and_stale_inference():
    rows = samples()
    now = START + timedelta(minutes=400)
    artifact = fit_model(rows, now)
    result = forecast(artifact, rows, now)
    assert math.isfinite(result["predicted_soil_raw"])
    assert result["target_at"] == (now + timedelta(minutes=30)).isoformat()
    assert artifact["metrics"]["baseline_mae"] > 0
    assert len(artifact["dataset_sha256"]) == 64
    assert artifact["train_samples"] >= 60
    with pytest.raises(InsufficientData, match="atrasadas"):
        forecast(artifact, rows, now + timedelta(minutes=6))


def test_short_and_constant_history_rejected():
    with pytest.raises(InsufficientData):
        fit_model(samples(20), START + timedelta(minutes=400))
    rows = samples()
    for row in rows:
        row.soil_raw = 3500
    with pytest.raises(InsufficientData, match="variação"):
        fit_model(rows, START + timedelta(minutes=400))


def test_forest_uses_only_training_data():
    rows = samples()
    now = START + timedelta(minutes=400)
    artifact = fit_model(rows, now)
    for row in rows:
        if row.measured_at >= START + timedelta(minutes=330):
            row.soil_raw += 1000
    altered = fit_model(rows, now)
    assert artifact["trees"] == altered["trees"]
    assert artifact["metrics"] != altered["metrics"]


def test_json_forest_matches_sklearn_predictions():
    import json
    from sklearn.ensemble import RandomForestRegressor
    from app.forecasting import export_trees, predict_trees
    x = [[i / 7, i % 3, i / 13, i % 7, i * 2] for i in range(80)]
    y = [math.sin(i / 8) * 100 + i for i in range(80)]
    model = RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42).fit(x, y)
    trees = json.loads(json.dumps(export_trees(model)))
    probes = x + [[-100, 2, 0, 6, 400], [1000, 0, 3, 0, -100]]
    for row, expected in zip(probes, model.predict(probes)):
        assert predict_trees(trees, row) == pytest.approx(expected, abs=1e-10)


def test_old_ridge_artifact_requires_retraining():
    with pytest.raises(InsufficientData, match="novamente o treino"):
        forecast({"schema_version": 1}, samples(), START + timedelta(minutes=400))


def test_temperature_model_trains_when_soil_is_constant():
    rows=samples()
    for row in rows:row.soil_raw=4095
    now=START+timedelta(minutes=400)
    artifact=fit_model(rows,now,target='temperature_c')
    result=forecast(artifact,rows,now)
    assert artifact['target']=='temperature_c'
    assert artifact['horizon_minutes']==5
    assert artifact['metrics']['unit']=='celsius'
    assert 'soil_raw' not in artifact['features']
    assert math.isfinite(result['predicted_temperature_c'])
    assert 'predicted_soil_raw' not in result


def test_temperature_gaps_are_bounded_without_interpolation():
    from app.forecasting import feature_at
    buckets=aggregate(samples(30),START+timedelta(minutes=30))
    at=START+timedelta(minutes=20)
    del buckets[at-timedelta(minutes=2)]
    assert feature_at(buckets,at,'temperature_c')
    del buckets[at-timedelta(minutes=3)]
    with pytest.raises(InsufficientData):feature_at(buckets,at,'temperature_c')


def test_temperature_purge_keeps_test_features_after_train_labels():
    examples=make_examples(aggregate(samples(),START+timedelta(minutes=400)),'temperature_c')
    train,test=chronological_split(examples,'temperature_c')
    assert train[-1][1] < test[0][0]-timedelta(minutes=5)
    assert all(e[1]-e[0]==timedelta(minutes=5) for e in examples)
