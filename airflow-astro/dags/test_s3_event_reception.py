"""
## Test S3 event reception (Lambda -> Airflow API)

This DAG is intended to be triggered externally via the Airflow REST API.
It reads `dag_run.conf` and logs the received S3 bucket/key to confirm that
the event payload was delivered correctly.
"""

from __future__ import annotations

import json

from airflow.sdk import dag, task
from pendulum import datetime


@dag(
    dag_id="test_s3_event_reception",
    start_date=datetime(2025, 1, 1),
    schedule=None,  # only triggered via API
    catchup=False,
    tags=["test", "event-driven", "s3"],
)
def test_s3_event_reception():
    @task
    def log_conf(**context) -> dict:
        conf = (context.get("dag_run").conf if context.get("dag_run") else {}) or {}
        bucket = conf.get("bucket")
        key = conf.get("key")

        print("Received dag_run.conf:")
        print(json.dumps(conf, indent=2, sort_keys=True))
        print(f"Parsed bucket={bucket!r} key={key!r}")

        return {"bucket": bucket, "key": key, "raw_conf": conf}

    log_conf()


test_s3_event_reception()

