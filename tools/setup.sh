#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SCRIPT_NAME="$(basename "$0")"
INSTALL_DEPS=true
INSTALL_PLAYWRIGHT=true
SKIP_HOOKS=false
HAS_PACKAGE_JSON=false
DEPS_INSTALL_ATTEMPTED=false
DEPS_INSTALL_FAILED=false
PKG_MANAGER="npm"
PKG_INSTALL_CMD="npm install --no-audit --no-fund"
PKG_INSTALL_FALLBACK="npm install --no-audit --no-fund --legacy-peer-deps"

if [[ -f package.json ]]; then
  HAS_PACKAGE_JSON=true
fi

# Detect package manager from package.json or lockfiles
detect_package_manager() {
  local project_pkg_manager
  if [[ -f package.json ]]; then
    project_pkg_manager=$(jq -r '.packageManager // empty' package.json | cut -d'@' -f1)
  fi

  if [[ -n "${project_pkg_manager:-}" ]]; then
    PKG_MANAGER="$project_pkg_manager"
    case "$PKG_MANAGER" in
      pnpm)
        PKG_INSTALL_CMD="pnpm install"
        PKG_INSTALL_FALLBACK="pnpm install --no-strict-peer-dependencies"
        ;;
      yarn)
        PKG_INSTALL_CMD="yarn install"
        PKG_INSTALL_FALLBACK="yarn install --ignore-engines"
        ;;
      bun)
        PKG_INSTALL_CMD="bun install"
        PKG_INSTALL_FALLBACK="bun install"
        ;;
      *)
        PKG_INSTALL_CMD="npm install --no-audit --no-fund"
        PKG_INSTALL_FALLBACK="npm install --no-audit --no-fund --legacy-peer-deps"
        ;;
    esac
  elif [[ -f pnpm-lock.yaml ]]; then
    PKG_MANAGER="pnpm"
    PKG_INSTALL_CMD="pnpm install"
    PKG_INSTALL_FALLBACK="pnpm install --no-strict-peer-dependencies"
  elif [[ -f yarn.lock ]]; then
    PKG_MANAGER="yarn"
    PKG_INSTALL_CMD="yarn install"
    PKG_INSTALL_FALLBACK="yarn install --ignore-engines"
  elif [[ -f bun.lockb ]]; then
    PKG_MANAGER="bun"
    PKG_INSTALL_CMD="bun install"
    PKG_INSTALL_FALLBACK="bun install"
  elif [[ -d node_modules/.pnpm ]]; then
    # pnpm structure detected even without lockfile
    PKG_MANAGER="pnpm"
    PKG_INSTALL_CMD="pnpm install"
    PKG_INSTALL_FALLBACK="pnpm install --no-strict-peer-dependencies"
  else
    PKG_MANAGER="npm"
    PKG_INSTALL_CMD="npm install --no-audit --no-fund"
    PKG_INSTALL_FALLBACK="npm install --no-audit --no-fund --legacy-peer-deps"
  fi
  log "Detected package manager: $PKG_MANAGER"
}

log() {
  printf '[setup] %s\n' "$1"
}

err() {
  printf '[setup] ❌ %s\n' "$1" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Missing required command '$1'"
    exit 1
  fi
}

print_usage() {
  cat <<'HELP'
Usage: bash tools/setup.sh [options]

Options:
  --skip-deps        Skip dependency install (useful if dependencies are already installed)
  --skip-npm         Alias for --skip-deps
  --skip-playwright  Skip Playwright browser install
  --skip-hooks       Do not touch git hook configuration
  -h, --help         Show this help message and exit
HELP
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --skip-deps|--skip-npm)
        INSTALL_DEPS=false
        shift
        ;;
      --skip-playwright)
        INSTALL_PLAYWRIGHT=false
        shift
        ;;
      --skip-hooks)
        SKIP_HOOKS=true
        shift
        ;;
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        err "Unknown option: $1"
        print_usage
        exit 1
        ;;
    esac
  done
}

ensure_git_repo() {
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return
  fi

  log "Initializing git repository"
  if git init -b main >/dev/null 2>&1; then
    log "Created git repository with branch 'main'"
  else
    git init >/dev/null
    log "Created git repository"
  fi
}

configure_hooks() {
  if $SKIP_HOOKS; then
    log "Skipping git hook configuration (--skip-hooks)"
    return
  fi

  log "Configuring git hooks"
  git config core.hooksPath .githooks
  chmod +x .githooks/* 2>/dev/null || true
  chmod +x .githooks-node/*.js 2>/dev/null || true
  log "Hooks ready. Use /setup:nodehooks if you prefer Node-based hooks."
}

update_package_json() {
  if [[ ! -f package.json ]]; then
    log "Skipping package.json script sync (no package.json detected)"
    return
  fi

  # Create backup before modifying
  cp package.json package.json.backup 2>/dev/null || true

  node <<'NODE'
const fs = require('fs');
const path = require('path');
const pkgPath = path.join(process.cwd(), 'package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const desiredScripts = {
  format: 'prettier --write .',
  'test:unit': 'vitest --run',
  'test:integration': 'vitest --run --config vitest.integration.config.ts || vitest --run',
  'test:e2e': 'playwright test',
  'test:e2e:docker': 'docker-compose -f docker-compose.playwright.yml run --rm playwright',
  'test:all': 'npm run test:unit && npm run test:integration && npm run test:e2e',
  'gen:contracts': 'npm --workspace packages/contracts run build || echo "contracts: add build script"',
  'seed:pr': 'tsx apps/seed-scripts/seed-pr.ts',
  'slice:new': 'ts-node tools/slice-new.ts'
};

const desiredDevDependencies = {
  prettier: '^3.2.5',
  vitest: '^1.5.0',
  '@vitest/coverage-v8': '^1.5.0',
  playwright: '^1.44.0',
  tsx: '^4.7.1',
  'ts-node': '^10.9.2'
};

pkg.scripts = pkg.scripts || {};
pkg.devDependencies = pkg.devDependencies || {};

let scriptsUpdated = false;
let depsUpdated = false;
const addedScripts = [];
const addedDeps = [];

for (const [script, value] of Object.entries(desiredScripts)) {
  if (!pkg.scripts[script]) {
    pkg.scripts[script] = value;
    scriptsUpdated = true;
    addedScripts.push(script);
  }
}

for (const [dep, version] of Object.entries(desiredDevDependencies)) {
  if (!pkg.devDependencies[dep]) {
    pkg.devDependencies[dep] = version;
    depsUpdated = true;
    addedDeps.push(dep);
  }
}

if (scriptsUpdated || depsUpdated) {
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
  if (scriptsUpdated) {
    console.log(`[setup] Added npm scripts: ${addedScripts.join(', ')}`);
  }
  if (depsUpdated) {
    console.log(`[setup] Added devDependencies: ${addedDeps.join(', ')}`);
  }
} else {
  console.log('[setup] package.json already includes required scripts and devDependencies');
}
NODE
}

install_dependencies() {
  if ! $INSTALL_DEPS; then
    log "Skipping dependency install (--skip-deps)"
    return
  fi

  if ! $HAS_PACKAGE_JSON; then
    log "Skipping dependency install (no package.json detected)"
    return
  fi

  detect_package_manager

  # Check if the detected package manager is installed
  if ! command -v "$PKG_MANAGER" >/dev/null 2>&1; then
    if [[ "$PKG_MANAGER" != "npm" ]]; then
      log "$PKG_MANAGER not installed, falling back to npm"
      PKG_MANAGER="npm"
      PKG_INSTALL_CMD="npm install --no-audit --no-fund"
      PKG_INSTALL_FALLBACK="npm install --no-audit --no-fund --legacy-peer-deps"
    fi
  fi

  require_cmd "$PKG_MANAGER"
  DEPS_INSTALL_ATTEMPTED=true
  
  # Clean up conflicting lockfiles/node_modules if switching package managers
  if [[ "$PKG_MANAGER" == "pnpm" && -f package-lock.json ]]; then
    log "Removing npm lockfile (using pnpm)"
    rm -f package-lock.json
  elif [[ "$PKG_MANAGER" == "npm" && -f pnpm-lock.yaml ]]; then
    log "Removing pnpm lockfile (using npm)"
    rm -f pnpm-lock.yaml
  fi

  # If node_modules has wrong structure, clean it
  if [[ "$PKG_MANAGER" == "npm" && -d node_modules/.pnpm ]]; then
    log "Cleaning pnpm-structured node_modules for npm"
    rm -rf node_modules
  elif [[ "$PKG_MANAGER" == "pnpm" && -d node_modules && ! -d node_modules/.pnpm ]]; then
    log "Cleaning npm-structured node_modules for pnpm"
    rm -rf node_modules
  fi

  log "Installing dependencies with $PKG_MANAGER"
  if $PKG_INSTALL_CMD >/dev/null 2>&1; then
    log "✅ Dependencies installed with $PKG_MANAGER"
    return
  fi

  local primary_status=$?
  log "Initial $PKG_MANAGER install failed (exit $primary_status). Retrying with fallback options"
  if $PKG_INSTALL_FALLBACK >/dev/null 2>&1; then
    log "✅ $PKG_MANAGER install succeeded with fallback options"
    return
  fi

  local fallback_status=$?
  DEPS_INSTALL_FAILED=true
  err "$PKG_MANAGER install failed (exit $fallback_status); skipping dependency install."
  err "Run '$PKG_INSTALL_FALLBACK' manually after resolving conflicts."
}

install_playwright() {
  if ! $INSTALL_PLAYWRIGHT; then
    log "Skipping Playwright install (--skip-playwright)"
    return
  fi

  if ! $HAS_PACKAGE_JSON; then
    log "Skipping Playwright install (no package.json detected)"
    return
  fi

  if $DEPS_INSTALL_FAILED; then
    log "Skipping Playwright install (dependency install previously failed)"
    return
  fi

  require_cmd npx
  
  # Check if Docker is available - recommend it as primary option
  if command -v docker >/dev/null 2>&1; then
    log "✅ Playwright configured for Docker (recommended)"
    log ""
    log "Run tests with: npm run test:e2e:docker"
    log "Or manually: docker-compose -f docker-compose.playwright.yml run --rm playwright"
    log ""
    log "Installing Playwright browsers without system dependencies..."
    
    # Install browsers only (no --with-deps to avoid sudo prompts)
    if npx playwright install >/dev/null 2>&1; then
      log "✅ Playwright browsers installed (basic mode)"
      log "   For full system deps: sudo npx playwright install-deps"
    else
      log "⚠️  Playwright browser install failed"
      log "   Run manually: npx playwright install"
    fi
    return
  fi

  # No Docker - install browsers without system deps
  log "Installing Playwright browsers (without system dependencies)..."
  if npx playwright install >/dev/null 2>&1; then
    log "✅ Playwright browsers installed"
    log "   For system dependencies: sudo npx playwright install-deps"
    log "   Or use Docker: npm run test:e2e:docker (recommended)"
  else
    log "⚠️  Playwright browser install failed"
    log ""
    log "To run tests, choose one option:"
    log "  1. Install Docker and use: npm run test:e2e:docker (recommended)"
    log "  2. Install browsers manually: npx playwright install"
  fi
}

ensure_git_exclude() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "Skipping git exclude configuration (no git repo detected)"
    return
  fi

  local exclude_file=".git/info/exclude"
  mkdir -p .git/info

  if [ ! -f "$exclude_file" ]; then
    touch "$exclude_file"
    log "Created $exclude_file"
  fi

  ensure_line() {
    local pattern="$1"
    if ! grep -Fxq "$pattern" "$exclude_file" 2>/dev/null; then
      printf '%s\n' "$pattern" >> "$exclude_file"
    fi
  }

  ensure_separator() {
    local last_line
    last_line="$(tail -n 1 "$exclude_file" 2>/dev/null || true)"
    if [ -n "$last_line" ]; then
      printf '\n' >> "$exclude_file"
    fi
  }

  ensure_separator
  ensure_line "# CFOI work artifacts (per-developer, local only)"
  ensure_line ".cfoi/"
  ensure_line "# Optional local AI checklists"
  ensure_line "checklist-*.md"
  ensure_line "# Optional personal notes"
  ensure_line "*-notes.md"
  ensure_line "*-scratch.md"
  ensure_line "# Windsurf transient artifacts"
  ensure_line ".swarm/"
  ensure_line ".windsurf/cache/"
  ensure_line ".checkpoint"

  log "Configured $exclude_file for local artifacts"
}

create_slice_scaffold() {
  mkdir -p apps/seed-scripts tools .cfoi/branches

  if [[ ! -f .cfoi/README.md ]]; then
    cat > .cfoi/README.md <<'MD'
# CFOI Work Artifacts

Branch-specific planning artifacts live here and are ignored by git.

- `/plan` → `.cfoi/branches/<branch>/plan.md`
- `/task` → `.cfoi/branches/<branch>/tasks.md`
- `/implement` → `.cfoi/branches/<branch>/proof/<task-id>/...`

Keep manual verification notes and evidence under the `proof/` folders.
MD
  fi

  if [[ ! -f apps/seed-scripts/seed-pr.ts ]]; then
    cat > apps/seed-scripts/seed-pr.ts <<'TS'
console.log('[seed] add synthetic data for PR environments here');
TS
  fi

  if [[ ! -f tools/slice-new.ts ]]; then
    cat > tools/slice-new.ts <<'TS'
#!/usr/bin/env ts-node
// @ts-nocheck
import { promises as fs } from 'node:fs';
import { join } from 'node:path';

const branch = process.argv[2] || 'feature-branch';
const branchDir = `.cfoi/branches/${branch}`;
const files: Array<[string, string]> = [
  [`${branchDir}/plan.md`, `# ${branch}\n\nGenerated: ${new Date().toISOString()}\n`],
  [`${branchDir}/tasks.md`, `# Tasks for ${branch}\n\n- [ ] Define first task\n`],
  [`${branchDir}/proof/.keep`, ``],
  [`e2e/${branch}.spec.ts`, `// TODO: add Playwright happy path for ${branch}\n`]
];

(async () => {
  for (const [filePath, content] of files) {
    await fs.mkdir(join(filePath, '..'), { recursive: true });
    await fs.writeFile(filePath, content, { flag: 'wx' }).catch(() => {});
  }
  console.log('Branch scaffolded:', branch);
})();
TS
    chmod +x tools/slice-new.ts
  fi
}

ensure_constitution() {
  if [[ -f .windsurf/constitution.md ]]; then
    return
  fi

  mkdir -p .windsurf
  cat > .windsurf/constitution.md <<'MD'
# Workspace Constitution (Build-First Delivery)

Priorities
1. Build-first cycle: scope → ship experience → add tests.
2. Keep vertical slices focused and under 45 minutes per task.
3. Guardrails via hooks (formatting, file-size limits, checkpoint mode).
4. Harden after features work: add contracts, seeds, and tests before merge.
5. Prefer pure functions and keep files under 450 lines.

Guardrails
- Secrets never land in code or logs; use Secret Manager or equivalent.
- Every PR provisions an ephemeral Cloud Run environment with synthetic data.
- Crossing service boundaries requires contract updates and regenerated clients.
- Tests target: unit for domain, integration for data edges, E2E for golden flows.
- Default package manager: npm (override in constitution if needed).
MD
}

summary() {
  cat <<'TXT'
[setup] ✅ Build-first workspace ready.
Next steps:
 1. Run /plan to capture the work item.
 2. Follow /task → /implement, committing after each task.
 3. Use /audit and /env before opening your pull request.
TXT

  if $DEPS_INSTALL_FAILED; then
    log "⚠️  Dependency install was skipped due to conflicts. Run '$PKG_INSTALL_FALLBACK' once you've resolved them."
  fi
}

main() {
  parse_args "$@"

  require_cmd git
  if $HAS_PACKAGE_JSON; then
    require_cmd node
  else
    log "No package.json detected; skipping Node-specific setup. Add one later and rerun tools/setup.sh if needed."
  fi

  ensure_git_repo
  ensure_git_exclude
  ensure_constitution
  configure_hooks
  update_package_json
  create_slice_scaffold
  install_dependencies
  install_playwright
  summary
}

main "$@"
