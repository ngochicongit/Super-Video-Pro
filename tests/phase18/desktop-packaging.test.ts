import {describe,expect,it} from "vitest";
import fs from "node:fs";

describe("desktop packaging contract",()=>{
  it("uses one Electron runtime and excludes large AI models",()=>{
    const pkg=JSON.parse(fs.readFileSync("package.json","utf8"));
    expect(pkg.build.win.target).toBe("nsis");
    expect(pkg.build.extraResources.some((item:{to:string})=>item.to.includes("model"))).toBe(false);
    expect(pkg.build.files).toContain("dist/**/*");
    expect(pkg.build.extraResources).toContainEqual(expect.objectContaining({
      from:"vendor/playwright-browsers",to:"playwright-browsers",
    }));
    const main=fs.readFileSync("src/main/index.ts","utf8");
    expect(main).toContain("PLAYWRIGHT_BROWSERS_PATH");
    expect(main).toContain('path.join(process.resourcesPath,"playwright-browsers")');
    const prepare=fs.readFileSync("scripts/prepare-tools.mjs","utf8");
    expect(prepare).toContain('[cli,"install","ffmpeg"]');
  });
});
