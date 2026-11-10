"""Train a clearly separated public-data soil experiment, never ESP32 raw values."""
import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

SOURCE = {
    'title': 'Ten-Minute Atmospheric and Soil-Moisture Time Series for the Arta Pilot, Greece (2015–2026)',
    'authors': 'Salmas, Kapsala, Giavis, Pachoulas and Stylios; University of Ioannina',
    'url': 'https://zenodo.org/records/21703750', 'doi': '10.5281/zenodo.21703750',
    'license': 'CC BY 4.0', 'station': 'Kompoti', 'depth_cm': 10,
    'sampling_minutes': 10, 'timestamp_timezone': 'Not specified in source documentation; original timestamps preserved',
}
DEVICE_ID = 'external-arta-kompoti-10cm'
FEATURES = ['soil_moisture_pct', 'temperature_c', 'air_humidity_pct', 'soil_30min_ago_pct', 'soil_change_30min_pp']
ARCHIVE_MD5 = '2ea3b78ec5092b04254a3821b3b0ed1c'


def read_series(stream, lower, upper):
    result, conflicts = {}, set()
    stats = {'invalid_rows': 0, 'conflicting_timestamps': 0}
    for row in csv.reader(stream):
        try:
            at = datetime.strptime(row[0].lstrip('\ufeff').strip(), '%Y-%m-%d %H:%M')
            value = float(row[1])
            if not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError('range')
        except (ValueError, IndexError):
            stats['invalid_rows'] += 1
            continue
        if at in conflicts:
            continue
        if at in result and result[at] != value:
            del result[at]
            conflicts.add(at)
            stats['conflicting_timestamps'] += 1
        else:
            result[at] = value
    return result, stats


def load_archive(path, max_points=10000):
    raw = Path(path).read_bytes()
    if hashlib.md5(raw).hexdigest() != ARCHIVE_MD5:
        raise ValueError('Checksum do ZIP difere do arquivo publicado; download inválido')
    series, quality, names = [], {}, []
    with ZipFile(io.BytesIO(raw)) as archive:
        for variable, low, high in [('soil-moisture-10cm',0,100),('air-temperature',-40,60),('relative-humidity',0,100)]:
            matches = [name for name in archive.namelist() if Path(name).name == f'kompoti_{variable}_openhi_10min_2015-2026.csv']
            if len(matches) != 1:
                raise ValueError('CSV esperado ausente ou duplicado: '+variable)
            names.append(matches[0])
            with archive.open(matches[0]) as stream:
                data, stats = read_series(io.TextIOWrapper(stream, encoding='utf-8-sig'),low,high)
                series.append(data)
                quality[variable] = stats
    aligned = sorted(set(series[0]) & set(series[1]) & set(series[2]))
    selected = aligned[-max_points:]
    return {at: [s[at] for s in series] for at in selected}, {
        'archive_sha256': hashlib.sha256(raw).hexdigest(), 'files': names,
        'aligned_rows_total': len(aligned), 'selected_rows': len(selected),
        'quality': quality, 'max_points': max_points,
    }


def examples_from_series(series):
    examples = []
    for at in sorted(series):
        if any(at+timedelta(minutes=i*10) not in series for i in range(-3,4)):
            continue
        soil,temp,humidity = series[at]
        previous = series[at-timedelta(minutes=30)][0]
        target_at = at+timedelta(minutes=30)
        examples.append((at,target_at,[soil,temp,humidity,previous,soil-previous],series[target_at][0]))
    return examples


def train_experiment(series, provenance):
    import sklearn
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, root_mean_squared_error
    from app.forecasting import export_trees
    examples = examples_from_series(series)
    if len(examples)<200:
        raise ValueError('Menos de 200 janelas contínuas na base pública')
    split = int(len(examples)*.75)
    test = examples[split:]
    train = [e for e in examples[:split] if e[1] < test[0][0]-timedelta(minutes=30)]
    if len(train)<100 or len(test)<50:
        raise ValueError('Histórico insuficiente após purga temporal')
    if max(e[3] for e in train)-min(e[3] for e in train)<.1:
        raise ValueError('Variação insuficiente no treino externo')
    model=RandomForestRegressor(n_estimators=100,max_depth=8,min_samples_leaf=3,random_state=42,n_jobs=1)
    model.fit([e[2] for e in train],[e[3] for e in train])
    predicted=model.predict([e[2] for e in test])
    actual=[e[3] for e in test];baseline=[e[2][0] for e in test]
    metrics={
        'model_mae':float(mean_absolute_error(actual,predicted)),
        'model_rmse':float(root_mean_squared_error(actual,predicted)),
        'baseline_mae':float(mean_absolute_error(actual,baseline)),
        'baseline_rmse':float(root_mean_squared_error(actual,baseline)),
        'unit':'percentage_points',
    }
    prepared=[[e[0].isoformat(),e[1].isoformat(),e[2],e[3]] for e in examples]
    return {
        'schema_version':'external-soil-v1','algorithm':'RandomForestRegressor',
        'target':'soil_moisture_pct','source':SOURCE,'provenance':provenance,
        'features':FEATURES,'parameters':model.get_params(),'sklearn_version':sklearn.__version__,
        'horizon_minutes':30,'trees':export_trees(model),
        'metrics':metrics,'beats_baseline':metrics['model_mae']<metrics['baseline_mae'],
        'train_samples':len(train),'test_samples':len(test),
        'train_start':train[0][0].isoformat(),'train_target_end':train[-1][1].isoformat(),
        'test_start':test[0][0].isoformat(),'test_end':test[-1][1].isoformat(),
        'dataset_sha256':hashlib.sha256(json.dumps(prepared).encode()).hexdigest(),
        'feature_importances':dict(zip(FEATURES,model.feature_importances_.tolist())),
        'test_examples':[{'based_on':e[0].isoformat(),'target_at':e[1].isoformat(),
            'current_soil_pct':e[2][0],'actual_soil_pct':e[3],'predicted_soil_pct':round(float(value),4)}
            for e,value in zip(test[-5:],predicted[-5:])],
        'usage':'External historical experiment only; not calibrated or validated for the ESP32 sensor',
    }


def public_report(artifact):
    return {key:value for key,value in artifact.items() if key!='trees'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--report',type=Path,default=Path('../ml/reports/external-soil.json'))
    parser.add_argument('--max-points',type=int,default=10000)
    parser.add_argument('--publish',action='store_true',help='Salvar modelo externo separado no banco configurado')
    args=parser.parse_args()
    if not 200<=args.max_points<=100000:
        parser.error('max-points deve estar entre 200 e 100000')
    series,provenance=load_archive(args.archive,args.max_points)
    artifact=train_experiment(series,provenance)
    report=public_report(artifact)
    if args.publish:
        from app.database import SessionLocal
        from app.models import ForecastModel
        with SessionLocal() as db:
            model=ForecastModel(id=str(uuid4()),device_id=DEVICE_ID,artifact=artifact)
            db.add(model);db.commit();report['model_id']=model.id
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'report':str(args.report),'metrics':artifact['metrics'],
                      'train_samples':artifact['train_samples'],'test_samples':artifact['test_samples'],
                      'beats_baseline':artifact['beats_baseline']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
