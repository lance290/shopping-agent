#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEFAULT_OUTPUT_ROOT="docs/prd"
TRACE_FILE="$ROOT_DIR/$DEFAULT_OUTPUT_ROOT/TRACEABILITY.md"

read_var() {
  local prompt="$1"; local var
  read -r -p "$prompt" var
  echo "$var"
}

abs_path() {
  local p="$1"
  local d
  d="$(cd "$(dirname "$p")" 2>/dev/null && pwd)" || return 1
  echo "$d/$(basename "$p")"
}

parent_path="${1:-}"
if [[ -z "${parent_path}" ]]; then
  parent_path=$(read_var "Parent PRD path (e.g., docs/prd/prd-core.md): ")
fi
if [[ -z "${parent_path}" ]]; then
  echo "Parent PRD path is required" >&2; exit 1
fi

parent_abs="$(cd "$ROOT_DIR" && abs_path "$parent_path")"
if [[ ! -f "$parent_abs" ]]; then
  echo "Parent PRD not found: $parent_path" >&2; exit 1
fi

slug="${2:-}"
if [[ -z "${slug}" ]]; then
  slug=$(read_var "PRD folder slug (e.g., checkout-v2): ")
fi
if [[ -z "$slug" ]]; then
  echo "Slug is required" >&2; exit 1
fi

output_root="${3:-$DEFAULT_OUTPUT_ROOT}"
OUTPUT_DIR="$ROOT_DIR/$output_root/$slug"

mkdir -p "$OUTPUT_DIR"

parent_dst="$OUTPUT_DIR/parent.md"
if [[ ! -f "$parent_dst" ]]; then
  cp "$parent_abs" "$parent_dst"
fi

echo "Enter child PRD short slugs (comma-separated, e.g., auth,observability,billing):"
read -r child_csv

IFS=',' read -r -a children <<<"$child_csv"
now_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for raw in "${children[@]}"; do
  cslug="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [[ -z "$cslug" ]] && continue
  file="$OUTPUT_DIR/prd-$cslug.md"
  if [[ ! -f "$file" ]]; then
    cat > "$file" <<EOF
# PRD: ${cslug^}

## Outcome
- Measurable impact: <metric tied to Product North Star>
- Success criteria: <quantitative thresholds>

## Scope
- In-scope: <bullets>
- Out-of-scope: <bullets>

## Cross-cutting concerns
- AuthN/AuthZ: <requirements>
- Observability: <metrics/traces/logs and SLOs>
- Billing/Entitlements: <rules>
- Data model & migrations: <ERD changes, migration plan>
- Performance: <targets, load profile>
- UX & Accessibility: <patterns, a11y>
- Privacy/Security/Compliance: <controls>

## Dependencies
- Upstream: <if any>
- Downstream: <if any>

## Risks & Mitigations
- <risk> → <mitigation>

## Acceptance criteria
- [ ] <testable criteria 1>
- [ ] <testable criteria 2>

## Traceability
- Parent PRD: $output_root/$slug/parent.md
- Product North Star: <path>
- Generated: $now_ts
EOF
  fi
done

mkdir -p "$(dirname "$TRACE_FILE")"
if [[ ! -f "$TRACE_FILE" ]]; then
  cat > "$TRACE_FILE" <<EOF
# PRD Traceability

| PRD Folder (slug) | Parent | Children | Updated |
|---|---|---|---|
EOF
fi

child_links=()
for raw in "${children[@]}"; do
  cslug="$(echo "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [[ -z "$cslug" ]] && continue
  child_links+=("[$cslug]($slug/prd-$cslug.md)")
done
children_cell=$(IFS=','; echo "${child_links[*]}")

new_row="| $slug | [$slug/parent.md]($slug/parent.md) | $children_cell | $now_ts |"
escaped_slug="$(printf '%s' "$slug" | sed 's/[^^$.*[\]\|?+(){}]/\\&/g')"
if grep -qE "^\|[[:space:]]*$escaped_slug[[:space:]]*\|" "$TRACE_FILE"; then
  # macOS sed requires in-place suffix argument
  sed -E -i '' "s|^\|[[:space:]]*$escaped_slug[[:space:]]*\|.*$|$new_row|" "$TRACE_FILE"
else
  echo "$new_row" >> "$TRACE_FILE"
fi

echo "OK: Sliced PRD in $output_root/$slug"
