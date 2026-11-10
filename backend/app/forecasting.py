"""Minute aggregates, chronological evaluation and versioned soil forecasts."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from statistics import mean

HORIZON = 30
LAG = 5
FEATURES = ["soil_raw", "temperature_c", "air_humidity_pct", "soil_raw_5min_ago", "soil_change_5min"]


class InsufficientData(ValueError):
    pass


def minute_start(value):
    return value.astimezone(timezone.utc).replace(second=0, microsecond=0)


def aggregate(rows, now):
    groups = defaultdict(list)
    for row in rows:
        if row.measured_at.tzinfo is None:
            continue
        end = minute_start(row.measured_at) + timedelta(minutes=1)
        values = (row.soil_raw, row.temperature_c, row.air_humidity_pct)
        if end <= minute_start(now) and all(math.isfinite(v) for v in values):
            if row.soil_raw >= 0 and 0 <= row.air_humidity_pct <= 100:
                groups[end].append(values)
    return {end: [mean(v[i] for v in values) for i in range(3)]
            for end, values in groups.items()}


def feature_at(buckets, at):
    if any(at - timedelta(minutes=i) not in buckets for i in range(LAG + 1)):
        raise InsufficientData("Faltam seis minutos consecutivos de leituras válidas")
    soil, temp, humidity = buckets[at]
    previous = buckets[at - timedelta(minutes=LAG)][0]
    return [soil, temp, humidity, previous, soil - previous]


def make_examples(buckets):
    examples = []
    for at in sorted(buckets):
        # No interpolation across a communication gap, including the future horizon.
        if any(at + timedelta(minutes=i) not in buckets for i in range(HORIZON + 1)):
            continue
        try:
            features = feature_at(buckets, at)
        except InsufficientData:
            continue
        target_at = at + timedelta(minutes=HORIZON)
        examples.append((at, target_at, features, buckets[target_at][0]))
    return examples


def chronological_split(examples):
    if len(examples) < 120:
        raise InsufficientData("Necessárias pelo menos 120 janelas válidas de histórico")
    split = int(len(examples) * .75)
    test = examples[split:]
    # Purge examples whose labels overlap the test feature window.
    boundary = test[0][0] - timedelta(minutes=LAG)
    train = [example for example in examples[:split] if example[1] < boundary]
    if len(train) < 60 or len(test) < 20:
        raise InsufficientData("Histórico insuficiente após separar treino e teste no tempo")
    return train, test


def fit_model(rows, now):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, root_mean_squared_error
    import sklearn

    if len({row.device_id for row in rows}) != 1:
        raise InsufficientData("Treine com dados de exatamente um dispositivo")
    buckets = aggregate(rows, now)
    examples = make_examples(buckets)
    train, test = chronological_split(examples)
    y_train = [e[3] for e in train]
    if max(y_train) - min(y_train) < 1:
        raise InsufficientData("Solo sem variação suficiente no conjunto de treino")
    model = RandomForestRegressor(n_estimators=100, max_depth=8,
                                  min_samples_leaf=3, random_state=42, n_jobs=1)
    model.fit([e[2] for e in train], y_train)
    predictions = model.predict([e[2] for e in test])
    actual = [e[3] for e in test]
    baseline = [e[2][0] for e in test]
    metrics = {
        "model_mae": float(mean_absolute_error(actual, predictions)),
        "model_rmse": float(root_mean_squared_error(actual, predictions)),
        "baseline_mae": float(mean_absolute_error(actual, baseline)),
        "baseline_rmse": float(root_mean_squared_error(actual, baseline)),
        "unit": "soil_raw",
    }
    dataset = [[e[0].isoformat(), e[1].isoformat(), e[2], e[3]] for e in examples]
    return {
        "schema_version": 2, "algorithm": "RandomForestRegressor",
        "parameters": model.get_params(),
        "sklearn_version": sklearn.__version__, "features": FEATURES,
        "horizon_minutes": HORIZON,
        "trees": export_trees(model),
        "feature_importances": dict(zip(FEATURES, model.feature_importances_.tolist())),
        "metrics": metrics,
        "beats_baseline": metrics["model_mae"] < metrics["baseline_mae"],
        "train_samples": len(train), "test_samples": len(test),
        "purged_samples": len(examples) - len(train) - len(test),
        "train_start": train[0][0].isoformat(), "train_target_end": train[-1][1].isoformat(),
        "test_start": test[0][0].isoformat(), "test_end": test[-1][1].isoformat(),
        "dataset_sha256": hashlib.sha256(json.dumps(dataset, separators=(",", ":")).encode()).hexdigest(),
        # Informational only: changing calibration requires a new experiment.
        "calibration": {"dry": 4095, "wet": 2901, "source": "firmware supplied by user; validate in field"},
    }



def export_trees(model):
    """Persist numeric tree arrays in JSON instead of executable model files."""
    return [{"left": tree.tree_.children_left.tolist(),
             "right": tree.tree_.children_right.tolist(),
             "feature": tree.tree_.feature.tolist(),
             "threshold": tree.tree_.threshold.tolist(),
             "value": tree.tree_.value[:, 0, 0].tolist()}
            for tree in model.estimators_]


def predict_trees(trees, features):
    import numpy as np
    # Match sklearn's float32 conversion at prediction time, including thresholds.
    values = np.asarray(features, dtype=np.float32)
    predictions = []
    for tree in trees:
        node = 0
        while tree["left"][node] != -1:
            feature = tree["feature"][node]
            node = (tree["left"][node] if float(values[feature]) <= tree["threshold"][node]
                    else tree["right"][node])
        predictions.append(tree["value"][node])
    if not predictions:
        raise InsufficientData("Modelo sem árvores; execute novamente o treino")
    return mean(predictions)


def forecast(artifact, rows, now):
    if artifact.get("schema_version") != 2 or artifact.get("algorithm") != "RandomForestRegressor" or artifact.get("features") != FEATURES:
        raise InsufficientData("Modelo antigo ou incompatível; execute novamente o treino com Random Forest")
    buckets = aggregate(rows, now)
    if not buckets:
        raise InsufficientData("Sem leituras recentes em minutos completos")
    at = max(buckets)
    if now - at > timedelta(minutes=5):
        raise InsufficientData("Últimas leituras atrasadas; previsão suspensa")
    features = feature_at(buckets, at)
    estimate = predict_trees(artifact["trees"], features)
    if not math.isfinite(estimate):
        raise InsufficientData("Modelo produziu resultado inválido")
    calibration = artifact["calibration"]
    pct = max(0, min(100, 100 * (calibration["dry"] - estimate) /
                         (calibration["dry"] - calibration["wet"])))
    trusted = artifact["beats_baseline"]
    return {
        "status": "available" if trusted else "experimental",
        "based_on": at.isoformat(),
        "target_at": (at + timedelta(minutes=artifact["horizon_minutes"])).isoformat(),
        "horizon_minutes": artifact["horizon_minutes"],
        "predicted_soil_raw": round(estimate, 2),
        "estimated_soil_pct": round(pct, 1),
        "current_soil_pct": round(max(0, min(100, 100 * (calibration["dry"] - features[0]) /
                                                   (calibration["dry"] - calibration["wet"]))), 1),
        "air_humidity_pct": round(features[2], 1),
        "calibration": calibration,
        "notice": ("Possível solo seco no horizonte previsto; verificar o solo" if pct < 30
                   else "Sem aviso de solo seco pela previsão" ) if trusted else
                  "Modelo não superou o baseline; previsão experimental",
        "metrics": artifact["metrics"],
        "beats_baseline": trusted,
    }
