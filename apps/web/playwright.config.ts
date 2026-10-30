import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const separator = process.platform === "win32" ? ";" : ":";
const python =
  process.env.STITCHORD_PYTHON ??
  (process.platform === "win32"
    ? "D:\\stitchord\\.condaenv\\python.exe"
    : "python3.11");
const pythonPath = [
  path.join(repoRoot, "services", "digitizer"),
  path.join(repoRoot, ".research", "repos", "inkex"),
  path.join(repoRoot, ".research", "repos", "inkstitch"),
].join(separator);

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: process.env.PW_CHANNEL ?? "msedge",
    headless: true,
    viewport: { width: 1440, height: 900 },
    acceptDownloads: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: path.join(repoRoot, "services", "digitizer"),
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { PYTHONPATH: pythonPath },
    },
    {
      command: `node "${path.join(repoRoot, "node_modules", "vite", "bin", "vite.js")}" --host 127.0.0.1 --port 5173`,
      cwd: __dirname,
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
