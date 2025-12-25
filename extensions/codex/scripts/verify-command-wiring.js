const fs = require("fs");
const path = require("path");

const extensionRoot = path.resolve(__dirname, "..");
const packageJsonPath = path.join(extensionRoot, "package.json");
const extensionSourcePath = path.join(extensionRoot, "src", "extension.ts");

const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
const source = fs.readFileSync(extensionSourcePath, "utf8");

const registerCommandRe = /registerCommand\(\s*['"`]([^'"`]+)['"`]/g;
const registeredCommands = new Set();
let match;

while ((match = registerCommandRe.exec(source)) !== null) {
  registeredCommands.add(match[1]);
}

const contributedCommands = new Set(
  (packageJson.contributes?.commands ?? []).map((command) => command.command)
);

const missingRegistrations = [...contributedCommands].filter(
  (command) => !registeredCommands.has(command)
);

const missingContributions = [...registeredCommands].filter(
  (command) => command.startsWith("codex.") && !contributedCommands.has(command)
);

if (missingRegistrations.length || missingContributions.length) {
  console.error("Command wiring mismatch detected.");
  if (missingRegistrations.length) {
    console.error("Missing registrations:", missingRegistrations.join(", "));
  }
  if (missingContributions.length) {
    console.error("Missing contributions:", missingContributions.join(", "));
  }
  process.exit(1);
}

console.log("Command wiring OK.");
