const fs = require("fs"),
  cp = require("child_process");
const msgFile = process.argv[2];
const root = cp.execSync("git rev-parse --show-toplevel").toString().trim();
const flag = root + "/.checkpoint";
const msg = fs.readFileSync(msgFile, "utf8");
if (/\[checkpoint\]/i.test(msg)) fs.writeFileSync(flag, "1");
else if (fs.existsSync(flag)) fs.unlinkSync(flag);
