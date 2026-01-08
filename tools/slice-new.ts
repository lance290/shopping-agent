#!/usr/bin/env ts-node
// @ts-nocheck
import { promises as fs } from "node:fs";
import { join } from "node:path";

let branch = process.argv[2] || "";

if (!branch) {
  try {
    const { execSync } = await import("node:child_process");
    branch = execSync("git rev-parse --abbrev-ref HEAD", {
      cwd: process.cwd(),
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8",
    }).trim();
  } catch {
    branch = "feature-branch";
  }
}

const branchDir = `.cfoi/branches/${branch}`;
const files: Array<[string, string]> = [
  [
    `${branchDir}/plan.md`,
    `# ${branch}\n\nGenerated: ${new Date().toISOString()}\n`,
  ],
  [
    `${branchDir}/tasks.md`,
    `# Tasks for ${branch}\n\n- [ ] Define first task\n`,
  ],
  [`${branchDir}/proof/.keep`, ``],
  [`e2e/${branch}.spec.ts`, `// TODO: add Playwright happy path for ${branch}\n`],
];

void (async () => {
  for (const [filePath, content] of files) {
    await fs.mkdir(join(filePath, ".."), { recursive: true });
    try {
      await fs.writeFile(filePath, content, { flag: "wx" });
    } catch {
      // Ignore existing files to avoid overwriting in-progress work
    }
  }

  console.log("Branch scaffolded:", branch);
})();
