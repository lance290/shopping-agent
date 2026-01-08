# shellcheck shell=bash

ensure_metrics_file() {
  if [ "$METRICS_AVAILABLE" = false ]; then
    return 1
  fi

  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if [ "$METRICS_AVAILABLE" != false ]; then
      echo "⚠️  Python interpreter ($PYTHON_BIN) not available; metrics will not be updated."
    fi
    METRICS_AVAILABLE=false
    return 1
  fi

  if [ ! -f "$METRICS_FILE" ]; then
    METRICS_INIT_PATH="$METRICS_FILE" "$PYTHON_BIN" <<'PY'
import json
import os
from pathlib import Path

metrics_path = Path(os.environ["METRICS_INIT_PATH"])
metrics_path.parent.mkdir(parents=True, exist_ok=True)

default_metrics = {
    "tasks": {
        "total": 0,
        "completed": 0,
        "inProgress": 0,
        "remaining": 0
    },
    "currentTask": None,
    "errorBudget": {
        "perTask": 3,
        "currentTaskErrors": 0,
        "sessionErrors": 0,
        "maxSession": 10,
        "log": []
    },
    "timeTracking": {
        "events": [],
        "lastTestRun": None,
        "lastCoverageRun": None
    },
    "evidence": {
        "tests": None,
        "coverage": None,
        "manual": {}
    }
}

metrics_path.write_text(json.dumps(default_metrics, indent=2) + "\n", encoding="utf-8")
PY
  fi

  return 0
}

record_test_evidence() {
  local status=$1
  local command=$2
  local logfile=$3

  ensure_metrics_file || return 0

  EVENT_STATUS="$status" \
  EVENT_COMMAND="$command" \
  EVENT_LOG="$logfile" \
  METRICS_PATH="$METRICS_FILE" \
  REPO_ROOT="$ROOT_DIR" \
  "$PYTHON_BIN" <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

metrics_path = Path(os.environ["METRICS_PATH"])
command = os.environ["EVENT_COMMAND"]
status = os.environ["EVENT_STATUS"]
log_path = Path(os.environ["EVENT_LOG"])
repo_root = Path(os.environ["REPO_ROOT"])

now = datetime.now(timezone.utc).isoformat()

if metrics_path.exists():
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        metrics = {}
else:
    metrics = {}

metrics.setdefault("timeTracking", {}).setdefault("events", [])
metrics.setdefault("evidence", {}).setdefault("manual", {})

if log_path.exists():
    try:
        relative_log = str(log_path.relative_to(repo_root))
    except ValueError:
        relative_log = str(log_path)
else:
    relative_log = str(log_path)

event_entry = {
    "type": "test",
    "status": status,
    "command": command,
    "log": relative_log,
    "timestamp": now
}

metrics["timeTracking"].setdefault("events", []).append(event_entry)
metrics["timeTracking"]["lastTestRun"] = now

metrics["evidence"]["tests"] = {
    "status": status,
    "command": command,
    "log": relative_log,
    "timestamp": now
}

metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
PY
}

record_coverage_evidence() {
  local summary_file=$1
  local status=$2
  local command=$3
  local regressions_file=$4

  ensure_metrics_file || return 0

  COVERAGE_SUMMARY_PATH="$summary_file" \
  COVERAGE_STATUS="$status" \
  COVERAGE_COMMAND="$command" \
  COVERAGE_REGRESSIONS="$regressions_file" \
  METRICS_PATH="$METRICS_FILE" \
  REPO_ROOT="$ROOT_DIR" \
  "$PYTHON_BIN" <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

metrics_path = Path(os.environ["METRICS_PATH"])
summary_path = Path(os.environ["COVERAGE_SUMMARY_PATH"])
status = os.environ["COVERAGE_STATUS"]
command = os.environ["COVERAGE_COMMAND"]
reg_path = Path(os.environ["COVERAGE_REGRESSIONS"])
repo_root = Path(os.environ["REPO_ROOT"])

now = datetime.now(timezone.utc).isoformat()

if metrics_path.exists():
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        metrics = {}
else:
    metrics = {}

metrics.setdefault("timeTracking", {}).setdefault("events", [])
metrics.setdefault("evidence", {}).setdefault("manual", {})

coverage_data = None
if summary_path.exists():
    try:
        coverage_data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        coverage_data = None

if summary_path.exists():
    try:
        relative_summary = str(summary_path.relative_to(repo_root))
    except ValueError:
        relative_summary = str(summary_path)
else:
    relative_summary = str(summary_path)

relative_regressions = None
if reg_path.exists() and reg_path.stat().st_size > 0:
    try:
        relative_regressions = str(reg_path.relative_to(repo_root))
    except ValueError:
        relative_regressions = str(reg_path)

event_entry = {
    "type": "coverage",
    "status": status,
    "command": command,
    "summary": relative_summary,
    "regressions": relative_regressions,
    "timestamp": now
}

metrics["timeTracking"].setdefault("events", []).append(event_entry)
metrics["timeTracking"]["lastCoverageRun"] = now

coverage_metrics = None
if isinstance(coverage_data, dict):
    coverage_metrics = coverage_data.get("metrics", coverage_data)

metrics["evidence"]["coverage"] = {
    "status": status,
    "command": command,
    "summary": relative_summary,
    "regressions": relative_regressions,
    "timestamp": now,
    "metrics": coverage_metrics
}

metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
PY
}
