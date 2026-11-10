"""Export real measurements for a reproducible academic submission; no secrets."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Measurement


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device-id',required=True)
    parser.add_argument('--max-id',type=int)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with SessionLocal() as db:
        query=select(Measurement).where(Measurement.device_id==args.device_id)
        if args.max_id is not None:query=query.where(Measurement.id<=args.max_id)
        rows=db.scalars(query.order_by(Measurement.measured_at,Measurement.id)).all()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        fields=['id','device_id','temperature_c','air_humidity_pct','soil_raw','measured_at','received_at']
        with args.output.open('w',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(fields)
            for row in rows:
                writer.writerow([getattr(row,f).isoformat() if f.endswith('_at') else getattr(row,f) for f in fields])
    print(json.dumps({'rows':len(rows),'file':str(args.output),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
