const fs = require("fs"),
  cp = require("child_process");
const root = cp.execSync("git rev-parse --show-toplevel").toString().trim();
const flag = root + "/.checkpoint";
if (fs.existsSync(flag)) fs.unlinkSync(flag);
