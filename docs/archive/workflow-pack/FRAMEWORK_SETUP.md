# Framework Setup - Global vs Project vs Branch

**Problem:** You don't want framework files (workflows, constitution, tools) to be per-branch. You want them project-wide or global.

**Solution:** Separate framework files from work artifacts using `.git/info/exclude` so developers keep private artifacts local without touching tracked ignore files.

---

## 🎯 **Recommended Structure**

### **Option 1: Project-Wide Framework (Recommended)**

Keep framework in the project but ignore work artifacts:

```
your-project/
├── .windsurf/                    # Tracked in git (framework)
│   ├── constitution.md           # ✅ In git (project rules)
│   ├── workflows/                # ✅ In git (framework)
│   └── macros/                   # ✅ In git (framework)
│
├── .cfoi/                        # NOT in git (work artifacts)
│   └── branches/
│       └── main/
│           ├── plan.md           # ❌ Not in git (per-developer)
│           ├── tasks.md          # ❌ Not in git (per-developer)
│           └── proof/            # ❌ Not in git (manual evidence)
│
├── tools/                        # Tracked in git (framework)
│   ├── verify-implementation.sh  # ✅ In git (project tool)
│   └── ai-checklist-template.md  # ✅ In git (project template)
│
├── docs/                         # Tracked in git (framework)
│   ├── KEEPING_AI_HONEST.md      # ✅ In git (project docs)
│   └── setup/                    # ✅ In git (project docs)
│
└── src/                          # Tracked in git (actual code)
    └── ...                       # ✅ In git (per-branch work)
```

**Add to `.git/info/exclude`:**

```gitexclude
# CFOI work artifacts (per-developer, not shared)
.cfoi/

# Optional: Ignore local AI checklists if you don't want to share them
**/checklist-*.md

# Optional: Ignore local planning notes
**/*-notes.md
```

> Tip: Run `bash tools/setup-framework-gitignore.sh` (or rerun `./install.sh`) to sync these patterns automatically into `.git/info/exclude`.

---

### **Option 2: Global Framework (Advanced)**

Store framework once globally, symlink into projects:

```bash
# 1. Create global framework directory
mkdir -p ~/.windsurf-framework
cd ~/.windsurf-framework

# 2. Clone or copy framework
git clone https://github.com/YOUR_ORG/windsurf-workflow-pack.git .

# 3. In each project, symlink to global framework
cd ~/Projects/my-project
ln -s ~/.windsurf-framework/.windsurf .windsurf
ln -s ~/.windsurf-framework/tools tools

# 4. Add symlinks to git excludes (local only)
echo ".windsurf" >> .git/info/exclude
echo "tools" >> .git/info/exclude
```

**Pros:**

- ✅ Update framework once, all projects get it
- ✅ Zero duplication
- ✅ Easy to maintain consistency

**Cons:**

- ⚠️ Projects must have access to global directory
- ⚠️ Harder to customize per-project
- ⚠️ Team members need same setup

---

### **Option 3: Hybrid (Best of Both)**

Framework in git (shared), work artifacts gitignored (private):

```bash
# Project structure
your-project/
├── .windsurf/              # ✅ In git (shared framework)
├── .cfoi/                  # ❌ Gitignored (private work)
├── tools/                  # ✅ In git (shared tools)
└── src/                    # ✅ In git (actual code)

# .gitignore
.cfoi/
.windsurf/.local/           # Local overrides
```

This lets you:

- ✅ Share framework across branches
- ✅ Keep planning private per-developer
- ✅ Allow project-specific customization
- ✅ Update framework via git pull

---

## 🔧 **Quick Setup for Option 1 (Recommended)**

```bash
cd /path/to/your/project

# Sync local excludes (run once per clone)
bash tools/setup-framework-gitignore.sh

# Remove .cfoi from git if it was tracked
git rm -r --cached .cfoi/ 2>/dev/null || true

# Install or refresh the framework pack
./install.sh --update

# Optional: remove the framework directory copy after install
./install.sh --update --cleanup

# If npm peers clash, the installer retries with --legacy-peer-deps and
# will skip dependency install if conflicts remain. Resolve in package.json
# and rerun: npm install --legacy-peer-deps
```

Now:

- ✅ Framework files (`.windsurf/`, `tools/`) stay in git
- ✅ Work artifacts (`.cfoi/`) are per-developer/branch
- ✅ Each developer can plan independently
- ✅ Framework updates apply to all branches

---

## 📦 **For Your Intern Program**

### **Recommended Approach:**

1. **Framework in git** (`.windsurf/`, `tools/`, docs)
   - All interns get same rules
   - Updates apply to everyone
   - Consistent quality standards

2. **Work artifacts gitignored** (`.cfoi/`)
   - Each intern plans independently
   - No merge conflicts on plans
   - Private notes stay private

3. **Code in git** (actual features)
   - Standard git workflow
   - Code reviews work normally
   - Branch-based development

### **Setup Script:**

```bash
#!/usr/bin/env bash
# Setup framework structure for intern projects

PROJECT_DIR="$1"

if [ -z "$PROJECT_DIR" ]; then
  echo "Usage: $0 /path/to/project"
  exit 1
fi

cd "$PROJECT_DIR"

# Add CFOI to gitignore
if ! grep -q "^.cfoi/" .gitignore 2>/dev/null; then
  echo "" >> .gitignore
  echo "# CFOI work artifacts (per-developer)" >> .gitignore
  echo ".cfoi/" >> .gitignore
  echo "✓ Added .cfoi/ to .gitignore"
fi

# Remove from git if tracked
git rm -r --cached .cfoi/ 2>/dev/null && echo "✓ Removed .cfoi/ from git" || true

# Create local CFOI directory
mkdir -p .cfoi/branches

# Add note
cat > .cfoi/README.md << 'EOF'
# CFOI Work Artifacts

This directory contains your personal planning artifacts.

**Not tracked in git** - your plans are private!

Usage:
- /plan → creates .cfoi/branches/[branch]/plan.md
- /task → creates .cfoi/branches/[branch]/tasks.md
- /implement → creates .cfoi/branches/[branch]/proof/<task-id>/...

These are YOUR notes. Share code, not plans.
EOF

echo "✓ Setup complete!"
echo ""
echo "Framework files (in git):"
echo "  .windsurf/        - Workflows and constitution"
echo "  tools/            - Scripts and templates"
echo ""
echo "Work artifacts (NOT in git):"
echo "  .cfoi/            - Your personal planning notes"
```

---

## 🎯 **What Goes Where**

### **In Git (Shared Framework):**

```
✅ .windsurf/constitution.md          # Project rules
✅ .windsurf/workflows/                # Workflow definitions
✅ .windsurf/macros/                   # Macro definitions
✅ tools/verify-implementation.sh      # Quality scripts
✅ tools/ai-checklist-template.md      # Templates
✅ KEEPING_AI_HONEST.md                # Documentation
✅ env.example                         # Config template
✅ README.md                           # Project docs
```

### **Not in Git (Per-Developer):**

```
❌ .cfoi/branches/*/plan.md            # Your plans
❌ .cfoi/branches/*/tasks.md           # Your tasks
❌ .cfoi/branches/*/proof/**           # Your notes & evidence
❌ checklist-*.md                      # Your checklists
❌ *-scratch.md                        # Your scratchpad
```

### **In Git (Your Work):**

```
✅ src/**/*.js                         # Your code
✅ tests/**/*.test.js                  # Your tests
✅ package.json                        # Dependencies
```

---

## 🔄 **Updating Framework**

### **With Framework in Git (Option 1):**

```bash
cd ~/Projects/windsurf-workflow-pack

# Pull latest framework
git pull origin main

# Import to your project (updates framework only)
./tools/import-ai-accountability.sh ~/Projects/my-project
```

### **With Global Framework (Option 2):**

```bash
# Update global framework
cd ~/.windsurf-framework
git pull origin main

# All projects with symlinks automatically get updates!
```

---

## 💡 **Best Practice Recommendation**

**For your intern program, use Option 1 (Hybrid):**

1. ✅ Keep framework in project git
2. ✅ Exclude `.cfoi/` work artifacts via `.git/info/exclude`
3. ✅ Each project can customize if needed
4. ✅ Interns can plan independently
5. ✅ No merge conflicts on planning
6. ✅ Code reviews focus on code, not plans

**Run the setup helper:**

```bash
bash tools/setup-framework-gitignore.sh
```

Done! Framework is shared, work is private. ✨

---

## 🎓 **For Interns**

**Tell them:**

> "The `.windsurf/` folder has our team's rules and workflows.
>
> The `.cfoi/` folder is YOUR personal notes - not tracked in git.
>
> Plan however you want in `.cfoi/`, then commit your code to `src/`.
>
> We review code, not plans. Your planning process is private."

This gives interns freedom to learn while maintaining quality standards! 🚀
