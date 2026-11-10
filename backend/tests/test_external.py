from datetime import datetime, timedelta
import io
import math
import pytest
from app.train_external import read_series, examples_from_series, train_experiment, public_report


def test_public_csv_rejects_missing_invalid_and_conflicting_values():
    stream=io.StringIO('2025-01-01 00:00,20,\n2025-01-01 00:10,,\n2025-01-01 00:20,200,\n2025-01-01 00:30,22,\n2025-01-01 00:30,24,\n')
    values,quality=read_series(stream,0,100)
    assert list(values.values())==[20]
    assert quality['invalid_rows']==2
    assert quality['conflicting_timestamps']==1


def series_fixture():
    start=datetime(2025,1,1)
    return {start+timedelta(minutes=i*10):[30+5*math.sin(i/20),24+math.cos(i/10),60] for i in range(400)}


def test_real_time_horizon_gaps_and_purged_evaluation():
    series=series_fixture()
    examples=examples_from_series(series)
    assert all(e[1]-e[0]==timedelta(minutes=30) for e in examples)
    missing=sorted(series)[100]; del series[missing]
    assert all(not e[0]-timedelta(minutes=30)<=missing<=e[1] for e in examples_from_series(series))
    artifact=train_experiment(series,{'fixture':True})
    assert datetime.fromisoformat(artifact['train_target_end']) < datetime.fromisoformat(artifact['test_start'])-timedelta(minutes=30)
    assert artifact['metrics']['unit']=='percentage_points'
    assert 'trees' not in public_report(artifact)
    assert 'predicted_soil_raw' not in artifact


def test_external_short_dataset_is_not_trained():
    with pytest.raises(ValueError,match='200 janelas'):
        train_experiment({}, {})
