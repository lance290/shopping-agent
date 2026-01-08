# shellcheck shell=bash

capture_coverage_summary() {
  local summary_found=false
  local summary_file=""

  if [ -f "coverage/coverage-summary.json" ]; then
    summary_found=true
    summary_file="coverage/coverage-summary.json"
  elif [ -f "coverage/coverage-final.json" ]; then
    summary_found=true
    summary_file="coverage/coverage-final.json"
  elif [ -f "coverage.xml" ]; then
    summary_found=true
    summary_file="coverage.xml"
  elif [ -f "lcov.info" ]; then
    summary_found=true
    summary_file="lcov.info"
  fi

  if [ "$summary_found" != true ]; then
    echo "  ⚠️  No coverage summary file detected. Ensure your coverage command outputs a recognised format."
    echo ""
    return
  fi

  local ts
  ts=$(timestamp)
  local raw_dir="$COVERAGE_DIR/raw"
  mkdir -p "$raw_dir"

  local raw_copy="$raw_dir/${ts}-$(basename "$summary_file")"
  cp "$summary_file" "$raw_copy"

  local previous_summary="$COVERAGE_DIR/latest-summary.json"
  local backup_previous="$COVERAGE_DIR/previous-summary.json"
  if [ -f "$previous_summary" ]; then
    mv "$previous_summary" "$backup_previous"
  fi

  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "  ⚠️  Python interpreter ($PYTHON_BIN) not available; stored raw coverage file at $raw_copy but skipped summary normalization."
    if [ -f "$backup_previous" ]; then
      mv "$backup_previous" "$COVERAGE_DIR/latest-summary.json"
    fi
    echo ""
    return
  fi

  SUMMARY_INPUT="$raw_copy" \
  PREVIOUS_SUMMARY="$backup_previous" \
  OUTPUT_DIR="$COVERAGE_DIR" \
  CURRENT_TIMESTAMP="$ts" \
  COVERAGE_TOLERANCE="${CFOI_COVERAGE_TOLERANCE:-0.1}" \
  "$PYTHON_BIN" <<'PY'
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

summary_path = Path(os.environ["SUMMARY_INPUT"])
output_dir = Path(os.environ["OUTPUT_DIR"])
previous_path = Path(os.environ["PREVIOUS_SUMMARY"])
timestamp = os.environ["CURRENT_TIMESTAMP"]
try:
    tolerance = float(os.environ.get("COVERAGE_TOLERANCE", "0"))
except ValueError:
    tolerance = 0.0

def safe_pct(value):
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None

def jest_summary(data):
    total = data.get("total", {})
    return {
        "lines": safe_pct(total.get("lines", {}).get("pct")),
        "statements": safe_pct(total.get("statements", {}).get("pct")),
        "branches": safe_pct(total.get("branches", {}).get("pct")),
        "functions": safe_pct(total.get("functions", {}).get("pct")),
    }

def cobertura_summary(path):
    root = ET.parse(path).getroot()
    lines_valid = int(root.attrib.get("lines-valid", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    branches_valid = int(root.attrib.get("branches-valid", 0))
    branches_covered = int(root.attrib.get("branches-covered", 0))

    def pct(covered, total):
        if total == 0:
            return None
        return round((covered / total) * 100, 2)

    return {
        "lines": pct(lines_covered, lines_valid),
        "branches": pct(branches_covered, branches_valid),
    }

def lcov_summary(path):
    lines_total = lines_hit = branches_total = branches_hit = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("LF:"):
                lines_total += int(line.strip().split(":")[-1])
            elif line.startswith("LH:"):
                lines_hit += int(line.strip().split(":")[-1])
            elif line.startswith("BRF:"):
                branches_total += int(line.strip().split(":")[-1])
            elif line.startswith("BRH:"):
                branches_hit += int(line.strip().split(":")[-1])

    def pct(covered, total):
        if total == 0:
            return None
        return round((covered / total) * 100, 2)

    return {
        "lines": pct(lines_hit, lines_total),
        "branches": pct(branches_hit, branches_total),
    }

def load_summary(path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}

path_str = str(summary_path)
if path_str.endswith(".json"):
    with open(summary_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    metrics = jest_summary(data)
elif path_str.endswith(".xml"):
    metrics = cobertura_summary(summary_path)
elif path_str.endswith("lcov.info"):
    metrics = lcov_summary(summary_path)
else:
    metrics = {}

normalized = {
    "timestamp": timestamp,
    "metrics": metrics,
    "source": summary_path.name,
}

latest_path = output_dir / "latest-summary.json"
with open(latest_path, "w", encoding="utf-8") as handle:
    json.dump(normalized, handle, indent=2)

history_path = output_dir / "coverage-history.json"
history = []
if history_path.exists():
    try:
        with open(history_path, "r", encoding="utf-8") as handle:
            history = json.load(handle)
    except Exception:
        history = []

history.append(normalized)
with open(history_path, "w", encoding="utf-8") as handle:
    json.dump(history[-20:], handle, indent=2)

previous = load_summary(previous_path)
previous_metrics = previous.get("metrics", {})

regressions = []
for metric, value in metrics.items():
    current = safe_pct(value)
    prev = safe_pct(previous_metrics.get(metric))
    if prev is None or current is None:
        continue
    drop = round(prev - current, 2)
    if drop > tolerance:
        regressions.append({
            "metric": metric,
            "previous": prev,
            "current": current,
            "drop": drop,
            "tolerance": tolerance,
        })

regression_path = output_dir / "coverage-regressions.json"
if regressions:
    with open(regression_path, "w", encoding="utf-8") as handle:
        json.dump(regressions, handle, indent=2)
else:
    if regression_path.exists():
        regression_path.unlink()
PY

  local regressions_file="$COVERAGE_DIR/coverage-regressions.json"
  if [ -s "$regressions_file" ]; then
    echo "  ❌ Coverage regression detected (see $regressions_file)"
    FAIL=$((FAIL+1))
  else
    echo "  ✅ Coverage summary stored in $COVERAGE_DIR/latest-summary.json"
  fi

  echo ""
}
