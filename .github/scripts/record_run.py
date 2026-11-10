"""Append this run to the dashboard's run log (runs.json), keeping the latest 200 runs.

Allure's own trend data has no dates, so the landing dashboard reads this file for history.
Usage: python record_run.py <previous runs.json or missing path> <allure summary.json> <output runs.json>
Run metadata comes from environment variables set by the workflow.
"""
import json
import os
import sys
from pathlib import Path

previous, summary_path, output = (Path(p) for p in sys.argv[1:4])
runs = json.loads(previous.read_text()) if previous.is_file() else []
summary = json.loads(summary_path.read_text())

runs.append({
    "run": int(os.environ["RUN_NUMBER"]),
    "date": os.environ["RUN_DATE"],              # ISO-8601 UTC
    "trigger": os.environ["TRIGGER"],            # push / schedule / workflow_dispatch / ...
    "commit": os.environ["COMMIT"][:7],
    "ci_url": os.environ["CI_URL"],
    "stats": summary["statistic"],               # passed, failed, broken, skipped (= known bugs), total
    "duration_ms": summary["time"].get("duration", 0),
})
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(runs[-200:], indent=1))
