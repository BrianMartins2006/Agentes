import pytest
from app.irrigation import irrigation_advice


def prediction(current=50, future=20, air=35):
    return dict(status='available', beats_baseline=True, current_soil_pct=current,
        estimated_soil_pct=future, air_humidity_pct=air, horizon_minutes=30,
        based_on='2026-11-10T10:00:00Z', target_at='2026-11-10T10:30:00Z')


def test_early_warning_comes_from_future_prediction():
    result=irrigation_advice(prediction())
    assert result['state']=='drying_risk'
    assert result['notify'] is True
    assert result['low_air_humidity'] is True


def test_current_and_future_dry_soil_recommends_inspection_and_irrigation():
    result=irrigation_advice(prediction(current=20))
    assert result['state']=='irrigation_recommended'
    assert result['notify'] is True


def test_air_alone_never_triggers_irrigation():
    result=irrigation_advice(prediction(current=60,future=60,air=10))
    assert result['state']=='normal'
    assert result['notify'] is False


@pytest.mark.parametrize('status',['unavailable','experimental','external_experiment'])
def test_unvalidated_or_external_model_cannot_raise_live_alert(status):
    result=irrigation_advice(prediction()|{'status':status})
    assert result['state']=='unavailable'
    assert result['notify'] is False


def test_threshold_and_recovery_do_not_produce_false_alerts():
    assert irrigation_advice(prediction(current=20,future=40))['state']=='inspect'
    assert irrigation_advice(prediction(current=30,future=30))['state']=='normal'
    assert irrigation_advice(prediction(future=20),soil_threshold=15)['notify'] is False
    assert irrigation_advice(prediction(future=float('nan')))['state']=='unavailable'


def test_current_rule_is_useful_but_never_pretends_to_be_ml():
    from app.irrigation import current_condition
    from datetime import datetime,timedelta,timezone
    from types import SimpleNamespace
    now=datetime.now(timezone.utc)
    row=SimpleNamespace(received_at=now,measured_at=now,soil_raw=4095,air_humidity_pct=30)
    result=current_condition(row,now)
    assert result['state']=='attention'
    assert result['is_ml'] is False and result['notify'] is False
    assert current_condition(row,now+timedelta(minutes=6))['state']=='stale'
