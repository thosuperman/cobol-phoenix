import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 30_000 },
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: process.env.PHOENIX_WEB_URL ?? "http://localhost:3000", viewport: { width: 1440, height: 900 }, colorScheme: "dark" },
});
