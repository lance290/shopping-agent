#!/usr/bin/env bash
# Analyze codebase structure for validation planning
# Used by /validation workflow Phase 1

set -euo pipefail

PROJECT_ROOT="${1:-.}"

analyze_languages() {
  echo "=== Languages Detected ==="
  
  local has_ts=false has_js=false has_py=false has_go=false has_rust=false has_java=false
  
  # TypeScript
  if find "$PROJECT_ROOT" -name "*.ts" -o -name "*.tsx" 2>/dev/null | head -1 | grep -q .; then
    has_ts=true
    local count=$(find "$PROJECT_ROOT" -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l | tr -d ' ')
    echo "typescript|$count files"
  fi
  
  # JavaScript
  if find "$PROJECT_ROOT" -name "*.js" -o -name "*.jsx" 2>/dev/null | head -1 | grep -q .; then
    has_js=true
    local count=$(find "$PROJECT_ROOT" -name "*.js" -o -name "*.jsx" 2>/dev/null | wc -l | tr -d ' ')
    echo "javascript|$count files"
  fi
  
  # Python
  if find "$PROJECT_ROOT" -name "*.py" 2>/dev/null | head -1 | grep -q .; then
    has_py=true
    local count=$(find "$PROJECT_ROOT" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
    echo "python|$count files"
  fi
  
  # Go
  if find "$PROJECT_ROOT" -name "*.go" 2>/dev/null | head -1 | grep -q .; then
    has_go=true
    local count=$(find "$PROJECT_ROOT" -name "*.go" 2>/dev/null | wc -l | tr -d ' ')
    echo "go|$count files"
  fi
  
  # Rust
  if find "$PROJECT_ROOT" -name "*.rs" 2>/dev/null | head -1 | grep -q .; then
    has_rust=true
    local count=$(find "$PROJECT_ROOT" -name "*.rs" 2>/dev/null | wc -l | tr -d ' ')
    echo "rust|$count files"
  fi
  
  # Java/Kotlin
  if find "$PROJECT_ROOT" -name "*.java" -o -name "*.kt" 2>/dev/null | head -1 | grep -q .; then
    has_java=true
    local count=$(find "$PROJECT_ROOT" \( -name "*.java" -o -name "*.kt" \) 2>/dev/null | wc -l | tr -d ' ')
    echo "java/kotlin|$count files"
  fi
}

analyze_frameworks() {
  echo "=== Frameworks Detected ==="
  
  # Node.js frameworks
  if [ -f "$PROJECT_ROOT/package.json" ]; then
    local deps=$(cat "$PROJECT_ROOT/package.json" 2>/dev/null)
    
    # Next.js
    if echo "$deps" | grep -q '"next"'; then
      echo "nextjs|$(echo "$deps" | grep -o '"next": "[^"]*"' | cut -d'"' -f4)"
    fi
    
    # React
    if echo "$deps" | grep -q '"react"'; then
      echo "react|$(echo "$deps" | grep -o '"react": "[^"]*"' | cut -d'"' -f4)"
    fi
    
    # Express
    if echo "$deps" | grep -q '"express"'; then
      echo "express|$(echo "$deps" | grep -o '"express": "[^"]*"' | cut -d'"' -f4)"
    fi
    
    # Fastify
    if echo "$deps" | grep -q '"fastify"'; then
      echo "fastify|$(echo "$deps" | grep -o '"fastify": "[^"]*"' | cut -d'"' -f4)"
    fi
    
    # NestJS
    if echo "$deps" | grep -q '"@nestjs/core"'; then
      echo "nestjs|$(echo "$deps" | grep -o '"@nestjs/core": "[^"]*"' | cut -d'"' -f4)"
    fi
    
    # Hono
    if echo "$deps" | grep -q '"hono"'; then
      echo "hono|$(echo "$deps" | grep -o '"hono": "[^"]*"' | cut -d'"' -f4)"
    fi
  fi
  
  # Python frameworks
  if [ -f "$PROJECT_ROOT/requirements.txt" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    local reqs=""
    [ -f "$PROJECT_ROOT/requirements.txt" ] && reqs=$(cat "$PROJECT_ROOT/requirements.txt" 2>/dev/null)
    [ -f "$PROJECT_ROOT/pyproject.toml" ] && reqs="$reqs $(cat "$PROJECT_ROOT/pyproject.toml" 2>/dev/null)"
    
    # FastAPI
    if echo "$reqs" | grep -qi "fastapi"; then
      echo "fastapi|detected"
    fi
    
    # Django
    if echo "$reqs" | grep -qi "django"; then
      echo "django|detected"
    fi
    
    # Flask
    if echo "$reqs" | grep -qi "flask"; then
      echo "flask|detected"
    fi
  fi
  
  # Go frameworks
  if [ -f "$PROJECT_ROOT/go.mod" ]; then
    local gomod=$(cat "$PROJECT_ROOT/go.mod" 2>/dev/null)
    
    # Gin
    if echo "$gomod" | grep -q "gin-gonic/gin"; then
      echo "gin|detected"
    fi
    
    # Echo
    if echo "$gomod" | grep -q "labstack/echo"; then
      echo "echo|detected"
    fi
    
    # Fiber
    if echo "$gomod" | grep -q "gofiber/fiber"; then
      echo "fiber|detected"
    fi
  fi
}

analyze_architecture() {
  echo "=== Architecture Pattern ==="
  
  # Monorepo detection
  if [ -f "$PROJECT_ROOT/pnpm-workspace.yaml" ] || \
     [ -f "$PROJECT_ROOT/lerna.json" ] || \
     [ -d "$PROJECT_ROOT/packages" ] || \
     [ -d "$PROJECT_ROOT/apps" ]; then
    echo "pattern|monorepo"
  else
    echo "pattern|single-repo"
  fi
  
  # API style detection
  if find "$PROJECT_ROOT" -name "*.graphql" -o -name "*.gql" 2>/dev/null | head -1 | grep -q .; then
    echo "api-style|graphql"
  elif grep -r "grpc" "$PROJECT_ROOT" --include="*.proto" 2>/dev/null | head -1 | grep -q .; then
    echo "api-style|grpc"
  elif grep -rE "(app\.(get|post|put|delete)|router\.(get|post|put|delete)|@(Get|Post|Put|Delete))" "$PROJECT_ROOT" \
       --include="*.ts" --include="*.js" --include="*.py" --include="*.go" 2>/dev/null | head -1 | grep -q .; then
    echo "api-style|rest"
  fi
  
  # Database detection
  if grep -rE "(prisma|@prisma/client)" "$PROJECT_ROOT" --include="*.ts" --include="*.js" 2>/dev/null | head -1 | grep -q .; then
    echo "database|prisma"
  elif grep -rE "(typeorm|TypeORM)" "$PROJECT_ROOT" --include="*.ts" --include="*.js" 2>/dev/null | head -1 | grep -q .; then
    echo "database|typeorm"
  elif grep -rE "(sequelize|Sequelize)" "$PROJECT_ROOT" --include="*.ts" --include="*.js" 2>/dev/null | head -1 | grep -q .; then
    echo "database|sequelize"
  elif grep -rE "(mongoose|mongodb)" "$PROJECT_ROOT" --include="*.ts" --include="*.js" 2>/dev/null | head -1 | grep -q .; then
    echo "database|mongodb"
  elif grep -rE "(sqlalchemy|SQLAlchemy)" "$PROJECT_ROOT" --include="*.py" 2>/dev/null | head -1 | grep -q .; then
    echo "database|sqlalchemy"
  fi
}

analyze_entry_points() {
  echo "=== Entry Points ==="
  
  # API routes (approximate count)
  local route_count=0
  
  # Express/Fastify routes
  route_count=$(grep -rE "(app|router)\.(get|post|put|patch|delete)\s*\(" "$PROJECT_ROOT" \
    --include="*.ts" --include="*.js" 2>/dev/null | wc -l | tr -d ' ')
  
  # Next.js API routes
  if [ -d "$PROJECT_ROOT/pages/api" ] || [ -d "$PROJECT_ROOT/app/api" ]; then
    local nextjs_routes=$(find "$PROJECT_ROOT/pages/api" "$PROJECT_ROOT/app/api" \
      -name "*.ts" -o -name "*.js" 2>/dev/null | wc -l | tr -d ' ')
    route_count=$((route_count + nextjs_routes))
  fi
  
  echo "api-routes|$route_count"
  
  # CLI commands
  if [ -f "$PROJECT_ROOT/package.json" ]; then
    local bin_count=$(grep -c '"bin"' "$PROJECT_ROOT/package.json" 2>/dev/null || echo "0")
    echo "cli-commands|$bin_count"
  fi
  
  # Event handlers (approximate)
  local event_count=$(grep -rE "(\.on\(|addEventListener|@EventPattern|@MessagePattern)" "$PROJECT_ROOT" \
    --include="*.ts" --include="*.js" 2>/dev/null | wc -l | tr -d ' ')
  echo "event-handlers|$event_count"
}

analyze_test_structure() {
  echo "=== Test Structure ==="
  
  # Test directories
  for dir in "__tests__" "test" "tests" "spec" "specs"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
      local count=$(find "$PROJECT_ROOT/$dir" -name "*.test.*" -o -name "*.spec.*" 2>/dev/null | wc -l | tr -d ' ')
      echo "test-dir|$dir|$count files"
    fi
  done
  
  # Co-located tests
  local colocated=$(find "$PROJECT_ROOT" -name "*.test.ts" -o -name "*.test.js" -o -name "*.spec.ts" -o -name "*.spec.js" 2>/dev/null | \
    grep -v "node_modules" | grep -v "__tests__" | grep -v "/test/" | wc -l | tr -d ' ')
  echo "colocated-tests|$colocated files"
  
  # E2E tests
  if [ -d "$PROJECT_ROOT/e2e" ] || [ -d "$PROJECT_ROOT/cypress" ] || [ -f "$PROJECT_ROOT/playwright.config.ts" ]; then
    echo "e2e-tests|detected"
  fi
}

# Main execution
main() {
  analyze_languages
  echo ""
  analyze_frameworks
  echo ""
  analyze_architecture
  echo ""
  analyze_entry_points
  echo ""
  analyze_test_structure
}

main
