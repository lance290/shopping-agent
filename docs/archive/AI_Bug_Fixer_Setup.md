# AI Bug Fixer Setup (Project-Agnostic)

This document describes how to add an end-to-end “AI Bug Fixer” loop to any GitHub repo:

- Bug report becomes a GitHub Issue
- Adding a label (for example `ai-fix`) triggers a GitHub Action
- The action runs an AI code fixer (for example Claude Code)
- The action pushes a deterministic branch (`fix/bug-<issue_number>`)
- The action creates a PR targeting your chosen base branch (for example `dev`)
- The action enables auto-merge using a merge method that matches repo policy (recommended: squash)

This guide is **architecture-agnostic** and **deployment-platform-agnostic**.

---

## 0) What you are building (contract)

You need four building blocks:

1) **Bug intake**
- A way to create a GitHub Issue and apply a trigger label (for example `ai-fix`)

2) **AI fixer workflow**
- A GitHub Action triggered on `issues:labeled` for the trigger label
- It checks out a base branch
- It runs the AI tool to produce changes
- It pushes a deterministic branch
- It creates a PR targeting the base branch
- It enables auto-merge

3) **Permissions + secrets**
- GitHub Actions must be allowed to create PRs
- The workflow must have access to the AI provider key (for example `ANTHROPIC_API_KEY`)

4) **A verification + messaging loop**
- If AI fails, comment on the issue with actionable error output
- If PR already exists, do not fail the job
- If PR creation is forbidden by repo settings, comment with exact fix + manual PR link
- If merge method conflicts with repo policy, change workflow merge method (recommended squash)

---

## 1) Repository prerequisites (must-do settings)

### 1.1 Enable GitHub Actions PR creation

In the repo:

- Settings -> Actions -> General -> Workflow permissions
  - Enable **Read and write permissions**
  - Enable **Allow GitHub Actions to create and approve pull requests**

If you skip this, the workflow will fail PR creation with an error like:

- `createPullRequest`

### 1.2 Choose a merge policy and match it in automation

In the repo:

- Settings -> General -> Pull Requests

Recommended default for automation:

- Disallow merge commits
- Use squash merging

If your repo disallows merge commits, your workflow must use squash:

- `gh pr merge --squash --auto --delete-branch`

If you mismatch, you will see errors like:

- `Merge commits are not allowed on this repository. (mergePullRequest)`

### 1.3 Required secrets

In the repo:

- Settings -> Secrets and variables -> Actions

Add:

- `ANTHROPIC_API_KEY`

If the account has insufficient credits, you will see failures like:

- `Credit balance is too low`

---

## 2) Conventions (recommended)

### 2.1 Labels

Create a label:

- `ai-fix`

This label is the single trigger for the workflow.

### 2.2 Branch naming

Use:

- `fix/bug-<issue_number>`

This ensures:

- Re-runs are idempotent
- The workflow can reliably detect whether a PR already exists

---

## 3) Workflow blueprint (implementation checklist)

Create a workflow file, for example:

- `.github/workflows/ai-bug-fixer.yml`

### 3.1 Trigger

- Trigger on `issues` with `types: [labeled]`
- Guard the job to only run if the label is your trigger label

### 3.2 Permissions

At workflow top-level set:

- `contents: write`
- `pull-requests: write`
- `issues: write`

### 3.3 Concurrency (avoid duplicate runs)

Use concurrency keyed by issue number:

- group: `ai-bug-fixer-${{ github.event.issue.number }}`
- cancel-in-progress: `true`

### 3.4 Core job steps (behavior)

1) Checkout base branch
- Use `actions/checkout`
- Checkout your base branch (for example `dev`)
- Use `fetch-depth: 0`

2) Create deterministic branch
- `BRANCH="fix/bug-${ISSUE_NUMBER}"`
- `git checkout -b "${BRANCH}"`

3) Run AI tool
- Run your AI tool (for example Claude Code)
- Capture output
- If it fails:
  - comment on the GitHub issue with the last N lines of output
  - exit non-zero

4) Commit changes (only if present)
- `git add -A`
- If staged changes exist, commit

5) Decide whether there is anything to PR

Do not rely on `git diff` alone.

Use:

- `git rev-list --count <base>..HEAD`

If count is 0:

- comment or log “no commits ahead of base; skipping PR creation”
- exit 0

6) Push branch

- `git push --set-upstream origin "${BRANCH}"`

7) Create PR (robustly)

- If PR exists for that branch head, do not error
- If PR creation fails due to repo settings (`createPullRequest`), comment on the issue with:
  - the compare URL
  - the exact repo setting to enable

Compare URL pattern:

- `https://github.com/<owner>/<repo>/compare/<base>...<branch>`

8) Auto-merge (optional)

Recommended:

- `gh pr merge "${BRANCH}" --squash --auto --delete-branch`

Notes:

- `--auto` means it merges only after required checks pass
- If branch protection requires approvals, auto-merge may still be blocked

---

## 4) Bug intake options (how issues get created)

### Option A: Manual triage (lowest friction)

- Users file issues normally
- You apply the `ai-fix` label manually

### Option B: App-integrated bug report (best UX)

Your app submits:

- title
- repro steps
- expected vs actual
- environment details (url, user agent)
- screenshots / attachments
- optional diagnostics (logs, network traces)

Then your backend (or serverless function) uses the GitHub API to create the issue and applies:

- `labels: ["ai-fix"]`

Important:

- Be cautious applying multiple labels that might trigger multiple workflows.

---

## 5) Troubleshooting (common failures)

### 5.1 Insufficient AI credits

Symptom:

- `Credit balance is too low`

Fix:

- Top up provider credits
- Or update the repo secret (for example `ANTHROPIC_API_KEY`)

### 5.2 GitHub forbids PR creation

Symptom:

- `createPullRequest`

Fix:

- Settings -> Actions -> General
- Workflow permissions:
  - Read and write permissions
  - Allow GitHub Actions to create and approve pull requests

### 5.3 Repo disallows merge commits

Symptom:

- `Merge commits are not allowed on this repository. (mergePullRequest)`

Fix:

- Use squash merges in automation:
  - `gh pr merge --squash --auto`

### 5.4 PR already exists

Symptom:

- `a pull request for branch ... already exists`

Fix:

- Treat as success (do not fail the workflow)
- Continue to merge step

---

## 6) Suggested defaults

If you want “drop-in with minimal surprises” defaults:

- Trigger label: `ai-fix`
- Base branch: `dev`
- Branch naming: `fix/bug-<issue_number>`
- Auto-merge: enabled
- Merge method: squash (`--squash --auto`)
