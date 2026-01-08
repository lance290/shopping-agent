const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const root = execSync("git rev-parse --show-toplevel").toString().trim();
const flag = root + "/.checkpoint";

let buildFailed = false;

// Detect and build all project types (monorepo support)
console.log("[pre-push] 🔍 Detecting project types...");

// Node.js/Frontend
if (fs.existsSync(path.join(root, "package.json"))) {
  try {
    const scripts = execSync("npm run -s", { encoding: "utf8" });
    if (scripts.includes("build")) {
      console.log("[pre-push] 📦 Node.js: running build…");
      try {
        execSync("npm run build", { stdio: "inherit" });
        console.log("[pre-push] ✅ Node.js build passed");
      } catch (e) {
        console.error("[pre-push] ❌ Node.js build failed");
        buildFailed = true;
      }
    } else {
      console.log("[pre-push] ⏭️ Node.js: no build script");
    }
  } catch (e) {
    console.log("[pre-push] ⏭️ Node.js: no build script");
  }
}

// Go backend
if (fs.existsSync(path.join(root, "go.mod"))) {
  console.log("[pre-push] 🐹 Go: running build…");
  try {
    execSync("go build ./...", { stdio: "inherit", cwd: root });
    console.log("[pre-push] ✅ Go build passed");
  } catch (e) {
    console.error("[pre-push] ❌ Go build failed");
    buildFailed = true;
  }
}

// Rust
if (fs.existsSync(path.join(root, "Cargo.toml"))) {
  console.log("[pre-push] 🦀 Rust: running build…");
  try {
    execSync("cargo build", { stdio: "inherit", cwd: root });
    console.log("[pre-push] ✅ Rust build passed");
  } catch (e) {
    console.error("[pre-push] ❌ Rust build failed");
    buildFailed = true;
  }
}

// C/C++ with CMake
if (fs.existsSync(path.join(root, "CMakeLists.txt"))) {
  console.log("[pre-push] 🔧 C/C++: running cmake build…");
  try {
    const buildDir = path.join(root, "build");
    if (!fs.existsSync(buildDir)) fs.mkdirSync(buildDir);
    execSync("cmake .. && make", { stdio: "inherit", cwd: buildDir });
    console.log("[pre-push] ✅ C/C++ build passed");
  } catch (e) {
    console.error("[pre-push] ❌ C/C++ build failed");
    buildFailed = true;
  }
}

// Generic Makefile (only if no other build system detected)
if (fs.existsSync(path.join(root, "Makefile"))) {
  const hasOtherBuildSystem =
    fs.existsSync(path.join(root, "package.json")) ||
    fs.existsSync(path.join(root, "go.mod")) ||
    fs.existsSync(path.join(root, "Cargo.toml")) ||
    fs.existsSync(path.join(root, "CMakeLists.txt"));

  if (!hasOtherBuildSystem) {
    console.log("[pre-push] 🔨 Makefile: running build…");
    try {
      execSync("make", { stdio: "inherit", cwd: root });
      console.log("[pre-push] ✅ Makefile build passed");
    } catch (e) {
      console.error("[pre-push] ❌ Makefile build failed");
      buildFailed = true;
    }
  }
}

if (buildFailed) {
  console.error("[pre-push] ❌ One or more builds failed");
  process.exit(1);
}

// Detect and test all project types (monorepo support)
console.log("[pre-push] 🧪 Running tests...");
let testFailed = false;
let anyTestsRun = false;

// Node.js tests
if (fs.existsSync(path.join(root, "package.json"))) {
  try {
    const scripts = execSync("npm run -s", { encoding: "utf8" });
    if (scripts.includes("test:all")) {
      console.log("[pre-push] 📦 Node.js: running tests…");
      anyTestsRun = true;
      try {
        execSync("npm run -s test:all", { stdio: "inherit" });
        console.log("[pre-push] ✅ Node.js tests passed");
      } catch (e) {
        console.error("[pre-push] ❌ Node.js tests failed");
        testFailed = true;
      }
    } else {
      console.log("[pre-push] ⏭️ Node.js: no test:all script");
    }
  } catch (e) {
    console.log("[pre-push] ⏭️ Node.js: no test:all script");
  }
}

// Go tests
if (fs.existsSync(path.join(root, "go.mod"))) {
  console.log("[pre-push] 🐹 Go: running tests…");
  anyTestsRun = true;
  try {
    execSync("go test ./...", { stdio: "inherit", cwd: root });
    console.log("[pre-push] ✅ Go tests passed");
  } catch (e) {
    console.error("[pre-push] ❌ Go tests failed");
    testFailed = true;
  }
}

// Rust tests
if (fs.existsSync(path.join(root, "Cargo.toml"))) {
  console.log("[pre-push] 🦀 Rust: running tests…");
  anyTestsRun = true;
  try {
    execSync("cargo test", { stdio: "inherit", cwd: root });
    console.log("[pre-push] ✅ Rust tests passed");
  } catch (e) {
    console.error("[pre-push] ❌ Rust tests failed");
    testFailed = true;
  }
}

// Python tests
if (
  fs.existsSync(path.join(root, "pytest.ini")) ||
  fs.existsSync(path.join(root, "setup.py"))
) {
  console.log("[pre-push] 🐍 Python: running tests…");
  anyTestsRun = true;
  try {
    execSync("pytest", { stdio: "inherit", cwd: root });
    console.log("[pre-push] ✅ Python tests passed");
  } catch (e) {
    console.error("[pre-push] ❌ Python tests failed");
    testFailed = true;
  }
}

// C++ tests (CTest)
if (fs.existsSync(path.join(root, "CMakeLists.txt"))) {
  const buildDir = path.join(root, "build");
  if (fs.existsSync(buildDir)) {
    // Check if CTest is configured
    const hasCTest =
      fs.existsSync(path.join(buildDir, "CTestTestfile.cmake")) ||
      (fs.existsSync(path.join(root, "CMakeLists.txt")) &&
        fs
          .readFileSync(path.join(root, "CMakeLists.txt"), "utf8")
          .includes("enable_testing()"));

    if (hasCTest) {
      console.log("[pre-push] 🔧 C++: running tests…");
      anyTestsRun = true;
      try {
        execSync("ctest --output-on-failure", {
          stdio: "inherit",
          cwd: buildDir,
        });
        console.log("[pre-push] ✅ C++ tests passed");
      } catch (e) {
        console.error("[pre-push] ❌ C++ tests failed");
        testFailed = true;
      }
    } else {
      console.log("[pre-push] ⏭️ C++: no tests configured");
    }
  }
}

// Makefile tests (only if no other test framework detected)
if (fs.existsSync(path.join(root, "Makefile"))) {
  const hasOtherTestFramework =
    fs.existsSync(path.join(root, "package.json")) ||
    fs.existsSync(path.join(root, "go.mod")) ||
    fs.existsSync(path.join(root, "Cargo.toml")) ||
    fs.existsSync(path.join(root, "CMakeLists.txt"));

  if (!hasOtherTestFramework) {
    try {
      execSync("make -n test", { cwd: root, stdio: "ignore" });
      console.log("[pre-push] 🔨 Makefile: running tests…");
      anyTestsRun = true;
      try {
        execSync("make test", { stdio: "inherit", cwd: root });
        console.log("[pre-push] ✅ Makefile tests passed");
      } catch (e) {
        console.error("[pre-push] ❌ Makefile tests failed");
        testFailed = true;
      }
    } catch (e) {
      console.log("[pre-push] ⏭️ Makefile: no test target");
    }
  }
}

if (!anyTestsRun) {
  console.log("[pre-push] ⏭️ No test frameworks detected, skipping tests");
}

if (testFailed) {
  if (fs.existsSync(flag)) {
    console.log(
      "[pre-push] ⚠️ tests failed, checkpoint active — allowing push",
    );
    process.exit(0);
  } else {
    console.error("[pre-push] ❌ One or more test suites failed");
    process.exit(1);
  }
} else {
  console.log("[pre-push] ✅ All tests passed");
}
