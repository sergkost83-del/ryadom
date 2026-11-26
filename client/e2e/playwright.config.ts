import { defineConfig } from "@playwright/test";

// Сценарии браузера. Сервер и веб поднимает CI (см. .github/workflows/ci.yml, задание «Сквозной сценарий»).
export default defineConfig({
  testDir: "tests",
  timeout: 120_000,
  retries: 0,
  workers: 1,
  outputDir: "../../reports/e2e-results",
  reporter: [["list"], ["html", { outputFolder: "../../reports/e2e-html", open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8081",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
