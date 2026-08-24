import {describe,expect,it} from "vitest";
import fs from "node:fs";
import {parseYtDlpProgress} from "../src/main/downloader";

describe("yt-dlp progress contract",()=>{
  it("reports actual bytes and prefers exact total",()=>expect(parseYtDlpProgress("SVP:1048576|2097152|2080000")).toEqual({bytesDownloaded:1048576,totalBytes:2080000}));
  it("uses estimated total only when exact total is unavailable",()=>expect(parseYtDlpProgress("SVP:512|2048|NA")).toEqual({bytesDownloaded:512,totalBytes:2048}));
  it("ignores ordinary yt-dlp output",()=>expect(parseYtDlpProgress("[download] 50.0%")).toBeNull());
  it("keeps resumable part files enabled",()=>{const source=fs.readFileSync(new URL("../src/main/downloaders/external.ts",import.meta.url),"utf8");expect(source).toContain('"--continue"');expect(source).not.toContain('"--no-part"')});
});
