import {readFile} from "node:fs/promises";
import {describe,expect,it} from "vitest";
describe("tabbed workspace boundaries",()=>{
  it("exposes only the five approved product tabs",async()=>{const source=await readFile("src/renderer/app-tabs.tsx","utf8");expect(source).toContain('["download","composition","tasks","history","settings"]');expect(source).toContain("data-tab={tab}");expect(source).not.toContain("editor")});
  it("keeps download free of settings, tools and Composition",async()=>{const source=await readFile("src/renderer/download-composer.tsx","utf8");expect(source).not.toContain("historyRetentionDays");expect(source).not.toContain("cookiesFromBrowser");expect(source).not.toContain("tool.version");expect(source).not.toContain("CompositionBuilder")});
  it("places privacy, diagnostics and tools only in settings",async()=>{const source=await readFile("src/renderer/settings-panel.tsx","utf8");expect(source).toContain("EvidenceProbe");expect(source).toContain("exportDiagnostics");expect(source).toContain("cookiesFromBrowser");expect(source).toContain("tools.map")});
});
