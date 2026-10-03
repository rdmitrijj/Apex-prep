import { defineConfig } from "@playwright/test";

// Runs against an already-running app: BASE_URL=http://localhost:8080 yarn e2e
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: process.env.BASE_URL ?? "http://localhost:5173", screenshot: "only-on-failure" },
});
