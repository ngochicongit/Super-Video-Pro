import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    testTimeout: process.env.CI ? 30_000 : 5_000,
    hookTimeout: process.env.CI ? 30_000 : 10_000,
  },
});
