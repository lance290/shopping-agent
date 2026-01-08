const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const root = execSync("git rev-parse --show-toplevel").toString().trim();
const flag = root + "/.checkpoint";
const allowFail = fs.existsSync(flag);

function run(cmd, cwd = root) {
  try {
    execSync(cmd, { stdio: "inherit", cwd });
  } catch (e) {
    if (!allowFail) process.exit(1);
  }
}

// Run all applicable formatters (monorepo support)
let anyFormatterRun = false;

// Node.js/JavaScript/TypeScript formatter
if (fs.existsSync(path.join(root, "package.json"))) {
  try {
    const scripts = execSync("npm run -s", { encoding: "utf8", cwd: root });
    if (scripts.includes("format")) {
      console.log("[pre-commit] 📦 Formatting Node.js code...");
      run("npm run -s format");
      anyFormatterRun = true;
    }
  } catch (e) {
    // No format script
  }
}

// Python formatter (Black)
if (fs.existsSync(path.join(root, ".venv", "bin", "black"))) {
  console.log("[pre-commit] 🐍 Formatting Python code...");
  run(path.join(root, ".venv", "bin", "black") + " .");
  anyFormatterRun = true;
}

// Go formatter
if (fs.existsSync(path.join(root, "go.mod"))) {
  try {
    execSync("command -v gofmt", { stdio: "ignore" });
    console.log("[pre-commit] 🐹 Formatting Go code...");
    run("gofmt -w .");
    anyFormatterRun = true;
  } catch (e) {
    // gofmt not available
  }
}

// Rust formatter
if (fs.existsSync(path.join(root, "Cargo.toml"))) {
  try {
    execSync("command -v cargo", { stdio: "ignore" });
    console.log("[pre-commit] 🦀 Formatting Rust code...");
    run("cargo fmt");
    anyFormatterRun = true;
  } catch (e) {
    // cargo not available
  }
}

// C++ formatter (clang-format)
if (
  fs.existsSync(path.join(root, "CMakeLists.txt")) ||
  fs.existsSync(path.join(root, ".clang-format"))
) {
  try {
    execSync("command -v clang-format", { stdio: "ignore" });
    console.log("[pre-commit] 🔧 Formatting C++ code...");
    run(
      'find . -type f \\( -name "*.cpp" -o -name "*.hpp" -o -name "*.cc" -o -name "*.h" -o -name "*.cxx" \\) -exec clang-format -i {} +'
    );
    anyFormatterRun = true;
  } catch (e) {
    // clang-format not available
  }
}

if (!anyFormatterRun) {
  console.log("[pre-commit] ⏭️ No formatters detected");
}

// ============================================================================
// LINTING (Multi-language support)
// ============================================================================
console.log("[pre-commit] 🔍 Running linters...");
let lintFailed = false;

// Node.js/JavaScript/TypeScript linting
if (fs.existsSync(path.join(root, "package.json"))) {
  try {
    const scripts = execSync("npm run -s", { encoding: "utf8", cwd: root });
    if (scripts.includes("lint")) {
      console.log("[pre-commit] 📦 Node.js: running linter...");
      try {
        execSync("npm run -s lint", { stdio: "inherit", cwd: root });
        console.log("[pre-commit] ✅ Node.js lint passed");
      } catch (e) {
        console.error("[pre-commit] ❌ Node.js lint failed");
        lintFailed = true;
      }
    }
  } catch (e) {
    // No lint script
  }
}

// Go linting
if (fs.existsSync(path.join(root, "go.mod"))) {
  try {
    execSync("command -v golangci-lint", { stdio: "ignore" });
    console.log("[pre-commit] 🐹 Go: running golangci-lint...");
    try {
      execSync("golangci-lint run ./...", { stdio: "inherit", cwd: root });
      console.log("[pre-commit] ✅ Go lint passed");
    } catch (e) {
      console.error("[pre-commit] ❌ Go lint failed");
      lintFailed = true;
    }
  } catch (e) {
    // Try go vet as fallback
    console.log("[pre-commit] 🐹 Go: running go vet...");
    try {
      execSync("go vet ./...", { stdio: "inherit", cwd: root });
      console.log("[pre-commit] ✅ Go vet passed");
    } catch (e) {
      console.error("[pre-commit] ❌ Go vet failed");
      lintFailed = true;
    }
  }
}

// Rust linting (clippy)
if (fs.existsSync(path.join(root, "Cargo.toml"))) {
  console.log("[pre-commit] 🦀 Rust: running clippy...");
  try {
    execSync("cargo clippy -- -D warnings", { stdio: "inherit", cwd: root });
    console.log("[pre-commit] ✅ Rust clippy passed");
  } catch (e) {
    console.error("[pre-commit] ❌ Rust clippy failed");
    lintFailed = true;
  }
}

// Python linting
if (
  fs.existsSync(path.join(root, "pytest.ini")) ||
  fs.existsSync(path.join(root, "setup.py")) ||
  fs.existsSync(path.join(root, "pyproject.toml"))
) {
  try {
    execSync("command -v ruff", { stdio: "ignore" });
    console.log("[pre-commit] 🐍 Python: running ruff...");
    try {
      execSync("ruff check .", { stdio: "inherit", cwd: root });
      console.log("[pre-commit] ✅ Python ruff passed");
    } catch (e) {
      console.error("[pre-commit] ❌ Python ruff failed");
      lintFailed = true;
    }
  } catch (e) {
    // Try flake8 or pylint
    if (fs.existsSync(path.join(root, ".venv", "bin", "flake8"))) {
      console.log("[pre-commit] 🐍 Python: running flake8...");
      try {
        execSync(path.join(root, ".venv", "bin", "flake8") + " .", {
          stdio: "inherit",
          cwd: root,
        });
        console.log("[pre-commit] ✅ Python flake8 passed");
      } catch (e) {
        console.error("[pre-commit] ❌ Python flake8 failed");
        lintFailed = true;
      }
    }
  }
}

// C++ linting (clang-tidy or cppcheck)
if (fs.existsSync(path.join(root, "CMakeLists.txt"))) {
  try {
    execSync("command -v clang-tidy", { stdio: "ignore" });
    console.log("[pre-commit] 🔧 C++: running clang-tidy...");
    try {
      const output = execSync(
        'find . -type f \\( -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" \\) -exec clang-tidy {} -- \\;',
        { encoding: "utf8", cwd: root }
      );
      if (output.includes("error:")) {
        console.error("[pre-commit] ❌ C++ clang-tidy failed");
        lintFailed = true;
      } else {
        console.log("[pre-commit] ✅ C++ clang-tidy passed");
      }
    } catch (e) {
      console.error("[pre-commit] ❌ C++ clang-tidy failed");
      lintFailed = true;
    }
  } catch (e) {
    // Try cppcheck as fallback
    try {
      execSync("command -v cppcheck", { stdio: "ignore" });
      console.log("[pre-commit] 🔧 C++: running cppcheck...");
      try {
        execSync("cppcheck --enable=all --error-exitcode=1 --quiet .", {
          stdio: "inherit",
          cwd: root,
        });
        console.log("[pre-commit] ✅ C++ cppcheck passed");
      } catch (e) {
        console.error("[pre-commit] ❌ C++ cppcheck failed");
        lintFailed = true;
      }
    } catch (e) {
      // cppcheck not available
    }
  }
}

// ============================================================================
// TYPE CHECKING (Multi-language support)
// ============================================================================
console.log("[pre-commit] 🔍 Running type checkers...");
let typeCheckFailed = false;

// TypeScript type checking
if (fs.existsSync(path.join(root, "tsconfig.json"))) {
  console.log("[pre-commit] 📦 TypeScript: running type checker...");
  try {
    execSync("npx tsc --noEmit", { stdio: "inherit", cwd: root });
    console.log("[pre-commit] ✅ TypeScript type checking passed");
  } catch (e) {
    console.error("[pre-commit] ❌ TypeScript type errors found");
    typeCheckFailed = true;
  }
}

// Python type checking (mypy)
if (
  fs.existsSync(path.join(root, "pytest.ini")) ||
  fs.existsSync(path.join(root, "setup.py")) ||
  fs.existsSync(path.join(root, "pyproject.toml"))
) {
  if (fs.existsSync(path.join(root, ".venv", "bin", "mypy"))) {
    console.log("[pre-commit] 🐍 Python: running mypy...");
    try {
      execSync(path.join(root, ".venv", "bin", "mypy") + " .", {
        stdio: "inherit",
        cwd: root,
      });
      console.log("[pre-commit] ✅ Python mypy passed");
    } catch (e) {
      console.error("[pre-commit] ❌ Python mypy failed");
      typeCheckFailed = true;
    }
  }
}

// Rust type checking
if (fs.existsSync(path.join(root, "Cargo.toml"))) {
  console.log("[pre-commit] 🦀 Rust: running type checker...");
  try {
    execSync("cargo check", { stdio: "inherit", cwd: root });
    console.log("[pre-commit] ✅ Rust type checking passed");
  } catch (e) {
    console.error("[pre-commit] ❌ Rust type checking failed");
    typeCheckFailed = true;
  }
}

// Go type checking
if (fs.existsSync(path.join(root, "go.mod"))) {
  console.log("[pre-commit] 🐹 Go: running type checker...");
  try {
    execSync("go build -o /dev/null ./...", { stdio: "ignore", cwd: root });
    console.log("[pre-commit] ✅ Go type checking passed");
  } catch (e) {
    console.error("[pre-commit] ❌ Go type checking failed");
    typeCheckFailed = true;
  }
}

// C++ type checking (compile check)
if (fs.existsSync(path.join(root, "CMakeLists.txt"))) {
  console.log("[pre-commit] 🔧 C++: running type checker...");
  try {
    const buildDir = path.join(root, "build");
    if (!fs.existsSync(buildDir)) fs.mkdirSync(buildDir);
    execSync("cmake .. && make -j$(nproc)", {
      stdio: "ignore",
      cwd: buildDir,
    });
    console.log("[pre-commit] ✅ C++ type checking passed");
  } catch (e) {
    console.error("[pre-commit] ❌ C++ type checking failed");
    typeCheckFailed = true;
  }
}

// Exit if linting or type checking failed (unless checkpoint active)
if ((lintFailed || typeCheckFailed) && !allowFail) {
  console.error("[pre-commit] ❌ Linting or type checking failed");
  process.exit(1);
}

const staged = execSync("git diff --cached --name-only --diff-filter=AM")
  .toString()
  .trim()
  .split("\n")
  .filter(Boolean);
// Exclude binary/media files from all checks
const excludeBinary =
  /(\.lock|\.svg|\.png|\.jpg|\.jpeg|\.gif|\.ico|\.webp|\.mp3|\.mp4|\.mov|\.pdf|\.wasm)$/;

// Exempt documentation and planning files from line limits
const exemptFromLineLimit = [
  // Documentation files
  /^README.*\.md$/i,
  /^CHANGELOG\.md$/i,
  /^CONTRIBUTING\.md$/i,
  /^LICENSE\.md$/i,
  /^.*SETUP\.md$/i,
  /^.*GUIDE\.md$/i,
  /^.*INTEGRATION\.md$/i,
  /^AUDIT.*\.md$/i,
  /^QUICKSTART\.md$/i,
  /^KEEPING.*\.md$/i,
  /^ADDING.*\.md$/i,

  // CFOI workflow planning artifacts
  /\.cfoi\//,
  /cfoi-slice-/,
  /cfoi-plan-/,
  /cfoi-task-/,
  /cfoi-implement-/,

  // Workflow documentation
  /\.windsurf\/workflows\//,
  /\.windsurf\/constitution\.md$/,
  /\.windsurf\/macros/,

  // Environment and config templates
  /env\.example$/,
  /\.env\.example$/,

  // Other documentation directories
  /^docs\//,
  /^examples\//,
];

let fail = 0;
staged.forEach((f) => {
  if (excludeBinary.test(f)) return;
  if (!fs.existsSync(f)) return;

  // Check if file is exempt from line limits
  const isExempt = exemptFromLineLimit.some((pattern) => pattern.test(f));

  const lines = fs.readFileSync(f, "utf8").split(/\r?\n/).length;
  if (lines > 450 && !isExempt) {
    console.error(`[pre-commit] ❌ ${f} has ${lines} lines (>450)`);
    fail++;
  }
});
if (fail > 0 && !fs.existsSync(flag)) {
  console.error("[pre-commit] ❌ split files or use [checkpoint]");
  process.exit(1);
}
console.log("[pre-commit] ✅ OK");
