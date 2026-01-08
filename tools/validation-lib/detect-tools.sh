#!/usr/bin/env bash
# Detect available validation tools in the environment
# Used by /validation workflow

set -euo pipefail

# Output format: JSON-like for easy parsing
# Each tool: name|command|available|version

detect_testing_tools() {
  echo "=== Testing Tools ==="
  
  # Jest
  if command -v jest >/dev/null 2>&1 || [ -f "node_modules/.bin/jest" ]; then
    local version=$(npx jest --version 2>/dev/null || echo "unknown")
    echo "jest|npx jest|true|$version"
  else
    echo "jest|npx jest|false|"
  fi
  
  # Vitest
  if command -v vitest >/dev/null 2>&1 || [ -f "node_modules/.bin/vitest" ]; then
    local version=$(npx vitest --version 2>/dev/null || echo "unknown")
    echo "vitest|npx vitest|true|$version"
  else
    echo "vitest|npx vitest|false|"
  fi
  
  # Pytest
  if command -v pytest >/dev/null 2>&1; then
    local version=$(pytest --version 2>/dev/null | head -1 || echo "unknown")
    echo "pytest|pytest|true|$version"
  else
    echo "pytest|pytest|false|"
  fi
  
  # Go test
  if command -v go >/dev/null 2>&1 && [ -f "go.mod" ]; then
    local version=$(go version 2>/dev/null | awk '{print $3}' || echo "unknown")
    echo "go-test|go test ./...|true|$version"
  else
    echo "go-test|go test ./...|false|"
  fi
  
  # Cargo test
  if command -v cargo >/dev/null 2>&1 && [ -f "Cargo.toml" ]; then
    local version=$(cargo --version 2>/dev/null | awk '{print $2}' || echo "unknown")
    echo "cargo-test|cargo test|true|$version"
  else
    echo "cargo-test|cargo test|false|"
  fi
  
  # Playwright
  if [ -f "node_modules/.bin/playwright" ] || [ -f "playwright.config.ts" ] || [ -f "playwright.config.js" ]; then
    local version=$(npx playwright --version 2>/dev/null || echo "unknown")
    echo "playwright|npx playwright test|true|$version"
  else
    echo "playwright|npx playwright test|false|"
  fi
  
  # Cypress
  if [ -f "node_modules/.bin/cypress" ] || [ -f "cypress.config.ts" ] || [ -f "cypress.config.js" ]; then
    local version=$(npx cypress --version 2>/dev/null | head -1 || echo "unknown")
    echo "cypress|npx cypress run|true|$version"
  else
    echo "cypress|npx cypress run|false|"
  fi
}

detect_static_analysis_tools() {
  echo "=== Static Analysis Tools ==="
  
  # TypeScript
  if command -v tsc >/dev/null 2>&1 || [ -f "node_modules/.bin/tsc" ]; then
    local version=$(npx tsc --version 2>/dev/null || echo "unknown")
    echo "typescript|npx tsc --noEmit|true|$version"
  else
    echo "typescript|npx tsc --noEmit|false|"
  fi
  
  # ESLint
  if command -v eslint >/dev/null 2>&1 || [ -f "node_modules/.bin/eslint" ]; then
    local version=$(npx eslint --version 2>/dev/null || echo "unknown")
    echo "eslint|npx eslint .|true|$version"
  else
    echo "eslint|npx eslint .|false|"
  fi
  
  # Prettier
  if command -v prettier >/dev/null 2>&1 || [ -f "node_modules/.bin/prettier" ]; then
    local version=$(npx prettier --version 2>/dev/null || echo "unknown")
    echo "prettier|npx prettier --check .|true|$version"
  else
    echo "prettier|npx prettier --check .|false|"
  fi
  
  # Pylint
  if command -v pylint >/dev/null 2>&1; then
    local version=$(pylint --version 2>/dev/null | head -1 || echo "unknown")
    echo "pylint|pylint **/*.py|true|$version"
  else
    echo "pylint|pylint **/*.py|false|"
  fi
  
  # mypy
  if command -v mypy >/dev/null 2>&1; then
    local version=$(mypy --version 2>/dev/null || echo "unknown")
    echo "mypy|mypy .|true|$version"
  else
    echo "mypy|mypy .|false|"
  fi
  
  # golangci-lint
  if command -v golangci-lint >/dev/null 2>&1; then
    local version=$(golangci-lint --version 2>/dev/null | head -1 || echo "unknown")
    echo "golangci-lint|golangci-lint run|true|$version"
  else
    echo "golangci-lint|golangci-lint run|false|"
  fi
  
  # Clippy (Rust)
  if command -v cargo >/dev/null 2>&1 && [ -f "Cargo.toml" ]; then
    echo "clippy|cargo clippy|true|"
  else
    echo "clippy|cargo clippy|false|"
  fi
}

detect_security_tools() {
  echo "=== Security Tools ==="
  
  # npm audit
  if command -v npm >/dev/null 2>&1 && [ -f "package.json" ]; then
    echo "npm-audit|npm audit --audit-level=high|true|"
  else
    echo "npm-audit|npm audit|false|"
  fi
  
  # Snyk
  if command -v snyk >/dev/null 2>&1; then
    local version=$(snyk --version 2>/dev/null || echo "unknown")
    echo "snyk|snyk test|true|$version"
  else
    echo "snyk|snyk test|false|"
  fi
  
  # Trivy
  if command -v trivy >/dev/null 2>&1; then
    local version=$(trivy --version 2>/dev/null | head -1 || echo "unknown")
    echo "trivy|trivy fs .|true|$version"
  else
    echo "trivy|trivy fs .|false|"
  fi
  
  # Safety (Python)
  if command -v safety >/dev/null 2>&1; then
    local version=$(safety --version 2>/dev/null || echo "unknown")
    echo "safety|safety check|true|$version"
  else
    echo "safety|safety check|false|"
  fi
}

detect_runtime_tools() {
  echo "=== Runtime Tools ==="
  
  # Docker
  if command -v docker >/dev/null 2>&1; then
    local version=$(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',' || echo "unknown")
    echo "docker|docker|true|$version"
  else
    echo "docker|docker|false|"
  fi
  
  # Docker Compose
  if command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1; then
    local version=$(docker compose version 2>/dev/null | awk '{print $4}' || echo "unknown")
    echo "docker-compose|docker compose|true|$version"
  else
    echo "docker-compose|docker compose|false|"
  fi
  
  # curl
  if command -v curl >/dev/null 2>&1; then
    local version=$(curl --version 2>/dev/null | head -1 | awk '{print $2}' || echo "unknown")
    echo "curl|curl|true|$version"
  else
    echo "curl|curl|false|"
  fi
  
  # httpie
  if command -v http >/dev/null 2>&1; then
    local version=$(http --version 2>/dev/null || echo "unknown")
    echo "httpie|http|true|$version"
  else
    echo "httpie|http|false|"
  fi
  
  # jq
  if command -v jq >/dev/null 2>&1; then
    local version=$(jq --version 2>/dev/null || echo "unknown")
    echo "jq|jq|true|$version"
  else
    echo "jq|jq|false|"
  fi
}

detect_external_service_tools() {
  echo "=== External Service Tools ==="
  
  # GitHub CLI
  if command -v gh >/dev/null 2>&1; then
    local version=$(gh --version 2>/dev/null | head -1 | awk '{print $3}' || echo "unknown")
    echo "github-cli|gh|true|$version"
  else
    echo "github-cli|gh|false|"
  fi
  
  # gcloud
  if command -v gcloud >/dev/null 2>&1; then
    local version=$(gcloud --version 2>/dev/null | head -1 | awk '{print $4}' || echo "unknown")
    echo "gcloud|gcloud|true|$version"
  else
    echo "gcloud|gcloud|false|"
  fi
  
  # Railway CLI
  if command -v railway >/dev/null 2>&1; then
    local version=$(railway --version 2>/dev/null || echo "unknown")
    echo "railway|railway|true|$version"
  else
    echo "railway|railway|false|"
  fi
  
  # AWS CLI
  if command -v aws >/dev/null 2>&1; then
    local version=$(aws --version 2>/dev/null | awk '{print $1}' | cut -d'/' -f2 || echo "unknown")
    echo "aws|aws|true|$version"
  else
    echo "aws|aws|false|"
  fi
  
  # psql
  if command -v psql >/dev/null 2>&1; then
    local version=$(psql --version 2>/dev/null | awk '{print $3}' || echo "unknown")
    echo "psql|psql|true|$version"
  else
    echo "psql|psql|false|"
  fi
  
  # mongosh
  if command -v mongosh >/dev/null 2>&1; then
    local version=$(mongosh --version 2>/dev/null || echo "unknown")
    echo "mongosh|mongosh|true|$version"
  else
    echo "mongosh|mongosh|false|"
  fi
  
  # redis-cli
  if command -v redis-cli >/dev/null 2>&1; then
    local version=$(redis-cli --version 2>/dev/null | awk '{print $2}' || echo "unknown")
    echo "redis-cli|redis-cli|true|$version"
  else
    echo "redis-cli|redis-cli|false|"
  fi
}

detect_package_scripts() {
  echo "=== Package Scripts ==="
  
  if [ -f "package.json" ]; then
    # Extract scripts from package.json
    if command -v jq >/dev/null 2>&1; then
      jq -r '.scripts // {} | to_entries[] | "\(.key)|\(.value)"' package.json 2>/dev/null || true
    else
      # Fallback: grep for common scripts
      grep -E '"(test|lint|build|format|coverage|e2e|validate)"' package.json 2>/dev/null | \
        sed 's/.*"\([^"]*\)".*"\([^"]*\)".*/\1|\2/' || true
    fi
  fi
}

# Main execution
main() {
  local output_format="${1:-text}"
  
  case "$output_format" in
    json)
      echo "{"
      echo "  \"testing\": ["
      detect_testing_tools | grep -v "^===" | while IFS='|' read -r name cmd avail ver; do
        echo "    {\"name\": \"$name\", \"command\": \"$cmd\", \"available\": $avail, \"version\": \"$ver\"},"
      done
      echo "  ],"
      # ... similar for other categories
      echo "}"
      ;;
    *)
      detect_testing_tools
      echo ""
      detect_static_analysis_tools
      echo ""
      detect_security_tools
      echo ""
      detect_runtime_tools
      echo ""
      detect_external_service_tools
      echo ""
      detect_package_scripts
      ;;
  esac
}

main "$@"
