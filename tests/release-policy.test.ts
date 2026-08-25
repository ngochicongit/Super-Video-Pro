import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";

describe("release packaging policy", () => {
  it("never lets electron-builder infer publishing from the CI environment", async () => {
    const packageJson = JSON.parse(await readFile("package.json", "utf8")) as {
      scripts?: Record<string, string>;
    };

    expect(packageJson.scripts?.package).toContain("electron-builder --win nsis --publish never");
  });
});
