import {describe,expect,it} from "vitest";
import fs from "node:fs";

describe("desktop packaging contract",()=>{
  it("uses one Electron runtime and excludes large AI models",()=>{
    const pkg=JSON.parse(fs.readFileSync("package.json","utf8"));
    expect(pkg.build.win.target).toBe("nsis");
    expect(pkg.build.extraResources.some((item:{to:string})=>item.to.includes("model"))).toBe(false);
    expect(pkg.build.files).toContain("dist/**/*");
  });
});
