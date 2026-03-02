# PRD: AI Bug Fixer Pattern

**Version:** 1.0
**Status:** Approved
**Goal:** Enable any development team to automate bug fixing by connecting user reports directly to an AI agent (Claude Code) via GitHub Actions.

---

## 1. Executive Summary
This pattern reduces the "Time to Fix" for reported bugs from days to minutes. By standardizing the flow of **Report -> GitHub Issue -> AI Agent -> Pull Request**, developers can focus on reviewing fixes rather than investigating them.

## 2. Architecture

### High-Level Flow
1.  **User** submits a bug report (with screenshot/logs) via the web application.
2.  **Backend** saves the report and creates a GitHub Issue with the label `ai-fix`.
3.  **GitHub Actions** detects the label and triggers the workflow.
4.  **Claude Code** (running in the Action) reads the issue, analyzes the code, reproduces the bug, and commits a fix.
5.  **GitHub Actions** opens a Pull Request targeting the development branch.

### Core Components
1.  **Reporting Widget:** A frontend component to capture context (screenshots, logs).
2.  **API Handler:** A backend endpoint to upload files and call the GitHub API.
3.  **The Workflow:** A generic GitHub Action that orchestrates Claude Code.

---

## 3. Prerequisites

### 3.1. Secrets
You need one secret in your GitHub repository:
-   **`ANTHROPIC_API_KEY`**: An API key from the [Anthropic Console](https://console.anthropic.com/) with available credits.

### 3.2. Repository Settings
To allow the AI to open Pull Requests, you must update your repository settings:
1.  Go to **Settings** -> **Actions** -> **General**.
2.  Scroll to **Workflow permissions**.
3.  Select **"Allow GitHub Actions to create and approve pull requests"**.
4.  Click **Save**.

---

## 4. Implementation Guide

### Step 1: The GitHub Workflow
Create a file at `.github/workflows/fix-bug.yml` in your repository. This workflow is stack-agnostic (works for Node, Python, Go, etc.).

**Note:** You may need to adjust the "Install Dependencies" step for your specific stack.

```yaml
name: AI Bug Fixer

on:
  issues:
    types: [labeled]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  fix-bug:
    if: github.event.label.name == 'ai-fix'
    runs-on: ubuntu-latest
    concurrency:
      group: ai-bug-fixer-${{ github.event.issue.number }}
      cancel-in-progress: true
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          ref: dev # IMPORTANT: Change this if your dev branch is named 'main' or 'master'
          fetch-depth: 0
      
      # --- STACK SETUP (Modify this section for your language) ---
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Dependencies
        run: npm ci # or 'pip install -r requirements.txt', 'go mod download', etc.
      # -----------------------------------------------------------

      - name: Run Claude Code to Fix Bug
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ github.token }} # Automatically provided by GitHub
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          ISSUE_TITLE: ${{ github.event.issue.title }}
          ISSUE_BODY: ${{ github.event.issue.body }}
        run: |
          set -euo pipefail

          # 1. Configure Git
          git config user.name "ai-fixer[bot]"
          git config user.email "ai-fixer[bot]@users.noreply.github.com"

          # 2. Create a Feature Branch
          BRANCH_NAME="fix/issue-${ISSUE_NUMBER}"
          git checkout -b "${BRANCH_NAME}"

          # 3. Construct the Prompt
          # We explicitly tell Claude what to do with the issue content.
          PROMPT="I have a bug report from GitHub Issue #${ISSUE_NUMBER}.
          
          Title: ${ISSUE_TITLE}
          
          Description:
          ${ISSUE_BODY}
          
          Your Task:
          1. Analyze the provided description and codebase.
          2. Reproduce the issue with a test case if possible.
          3. Modify the code to fix the bug.
          4. Verify the fix.
          
          Constraints:
          - You are already on the branch '${BRANCH_NAME}'.
          - Do not switch branches."

          # 4. Run Claude Code
          # --dangerously-skip-permissions allows it to edit files without interactive confirmation
          npx @anthropic-ai/claude-code@latest \
            --print \
            --dangerously-skip-permissions \
            -p "$PROMPT"

          # 5. Commit and Push
          git add -A
          if ! git diff --cached --quiet; then
            git commit -m "fix: resolve issue #${ISSUE_NUMBER}"
            git push origin "${BRANCH_NAME}" --force
            
            # 6. Create Pull Request
            gh pr create \
              --base dev \
              --head "${BRANCH_NAME}" \
              --title "fix: ${ISSUE_TITLE}" \
              --body "Automated fix for issue #${ISSUE_NUMBER} generated by Claude Code." \
              --label "ai-fix-review" || echo "PR already exists"
          else
            echo "No changes made by Claude."
          fi
```

### Step 2: The Backend API (Concept)
Your application needs an API endpoint (e.g., `POST /api/report-bug`) that:
1.  Receives the form data (description, screenshot).
2.  Uploads the screenshot to public storage (or keeps it local if running in the same context).
3.  Calls the GitHub API to create an issue.

**Critical Requirement:** When creating the issue via the GitHub API, you must apply the label `ai-fix`.

Example Payload to GitHub API:
```json
POST /repos/:owner/:repo/issues
{
  "title": "[Bug] Navigation broken on mobile",
  "body": "User reported...\n\n![Screenshot](https://...)",
  "labels": ["ai-fix"]
}
```

---

## 5. Client-Side Component

Below is a standalone, dependency-free HTML/JS component you can embed in any web application. It creates a floating "Report Bug" button that captures a screenshot and submits the report.

**Usage:**
1.  Include this HTML in your main layout.
2.  Update the `SUBMIT_URL` constant to point to your backend API.
3.  Ensure your backend accepts `multipart/form-data`.

```html
<!-- AI Bug Reporter Widget -->
<div id="ai-bug-reporter">
  <!-- Trigger Button -->
  <button id="abr-trigger" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999; padding: 10px 15px; background: #000; color: #fff; border: none; border-radius: 50px; cursor: pointer; font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    🐞 Report Bug
  </button>

  <!-- Modal -->
  <div id="abr-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; align-items: center; justify-content: center;">
    <div style="background: #fff; width: 400px; max-width: 90%; padding: 20px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 10px 25px rgba(0,0,0,0.2);">
      <h3 style="margin-top: 0;">Report a Bug</h3>
      
      <form id="abr-form">
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">What went wrong?</label>
          <textarea id="abr-desc" required style="width: 100%; height: 80px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;" placeholder="Describe what happened..."></textarea>
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">Expected Behavior</label>
          <textarea id="abr-expected" style="width: 100%; height: 60px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;" placeholder="What should have happened?"></textarea>
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">Screenshot</label>
          <input type="file" id="abr-file" accept="image/*" style="width: 100%;">
          <p style="font-size: 12px; color: #666; margin-top: 4px;">Tip: You can also paste (Ctrl+V) an image anywhere on this form.</p>
        </div>

        <div style="text-align: right; margin-top: 20px;">
          <button type="button" id="abr-cancel" style="padding: 8px 15px; margin-right: 10px; background: #eee; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
          <button type="submit" id="abr-submit" style="padding: 8px 15px; background: #000; color: #fff; border: none; border-radius: 4px; cursor: pointer;">Submit Report</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
(function() {
  // CONFIGURATION
  const SUBMIT_URL = '/api/report-bug'; // Replace with your actual backend endpoint

  const trigger = document.getElementById('abr-trigger');
  const modal = document.getElementById('abr-modal');
  const cancelBtn = document.getElementById('abr-cancel');
  const form = document.getElementById('abr-form');
  const fileInput = document.getElementById('abr-file');

  // Toggle Modal
  trigger.onclick = () => modal.style.display = 'flex';
  cancelBtn.onclick = () => modal.style.display = 'none';

  // Handle Paste (Screenshot)
  document.addEventListener('paste', (e) => {
    if (modal.style.display === 'none') return;
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (const item of items) {
      if (item.type.indexOf('image') !== -1) {
        const file = item.getAsFile();
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        alert('Screenshot pasted successfully!');
      }
    }
  });

  // Handle Submit
  form.onsubmit = async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('abr-submit');
    const originalText = submitBtn.innerText;
    submitBtn.innerText = 'Submitting...';
    submitBtn.disabled = true;

    const formData = new FormData();
    formData.append('notes', document.getElementById('abr-desc').value);
    formData.append('expected', document.getElementById('abr-expected').value);
    
    // Add Context
    formData.append('url', window.location.href);
    formData.append('userAgent', navigator.userAgent);
    
    if (fileInput.files[0]) {
      formData.append('attachment', fileInput.files[0]);
    }

    try {
      const response = await fetch(SUBMIT_URL, {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        alert('Bug reported! The AI agent will start working on it shortly.');
        modal.style.display = 'none';
        form.reset();
      } else {
        throw new Error('Server returned ' + response.status);
      }
    } catch (err) {
      alert('Failed to send report: ' + err.message);
    } finally {
      submitBtn.innerText = originalText;
      submitBtn.disabled = false;
    }
  };
})();
</script>
```
