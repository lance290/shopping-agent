# Manual Verification - abf-gh-006

## Steps Performed
1.  **Created Workflow**: Added `.github/workflows/fix-bug.yml`.
    -   Triggers on `issues: [opened]`.
    -   Condition: `contains(github.event.issue.body, 'CLAUDE-INSTRUCTION')`.
    -   Steps:
        -   Checkout repo.
        -   Setup Node.js & Python.
        -   Install dependencies (frontend & backend).
        -   Run `npx @anthropic-ai/claude-code` with the issue context as a prompt.

## Verification
-   **File Existence**: Confirmed file is created.
-   **Syntax**: YAML structure is valid.
-   **Secrets**: Workflow references `ANTHROPIC_API_KEY` and `GITHUB_TOKEN`.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
