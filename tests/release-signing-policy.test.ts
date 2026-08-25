import fs from "node:fs";
import { describe, expect, it } from "vitest";

describe("Windows release signing policy", () => {
  const workflow = fs.readFileSync(".github/workflows/release-candidate.yml", "utf8");
  const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8")) as { scripts: Record<string, string> };
  const verification = fs.readFileSync("scripts/verify-authenticode.ps1", "utf8");

  it("gates signing secrets behind the Windows signing environment", () => {
    expect(workflow).toContain("environment: windows-signing");
    expect(workflow).toContain("secrets.WIN_CSC_LINK");
    expect(workflow).toContain("secrets.WIN_CSC_KEY_PASSWORD");
    expect(workflow).toContain("secrets.SVP_UPDATE_ED25519_PRIVATE_KEY_PEM");
  });

  it("fails closed and verifies both Authenticode targets", () => {
    expect(packageJson.scripts["package:signed"]).toContain("--config.forceCodeSigning=true");
    expect(packageJson.scripts["package:signed"]).toContain("verify-authenticode.ps1");
    expect(verification).toContain('if ($signature.Status -ne "Valid")');
    expect(verification).toContain("TimeStamperCertificate");
    expect(verification).toContain('"Super Video Pro Setup *.exe"');
    expect(verification).toContain('"Super Video Pro.exe"');
  });
});
