import {describe,expect,it} from "vitest";
import path from "node:path";
import {resolveTool,runTool,ytDlpRuntimeArgs} from "../src/main/tools";

describe("bundled runtime tools",()=>{
  it("resolves pinned executables from vendor staging",()=>{expect(resolveTool("yt-dlp")).toContain(path.join("vendor","tools","yt-dlp.exe"));expect(resolveTool("deno")).toContain(path.join("vendor","tools","deno.exe"));expect(resolveTool("ffmpeg")).toContain(path.join("vendor","tools","ffmpeg.exe"));expect(ytDlpRuntimeArgs().join(" ")).toContain("deno.exe")});
  it("executes yt-dlp, Deno, FFmpeg and FFprobe",async()=>{const [yt,deno,ffmpeg,ffprobe]=await Promise.all([runTool("yt-dlp",["--version"]),runTool("deno",["--version"]),runTool("ffmpeg",["-version"]),runTool("ffprobe",["-version"])]);expect(yt).toMatchObject({code:0});expect(yt.stdout.trim()).toBe("2026.06.09");expect(deno.code).toBe(0);expect(deno.stdout).toContain("deno 2.9.5");expect(ffmpeg.code).toBe(0);expect(ffmpeg.stdout).toContain("ffmpeg version");expect(ffprobe.code).toBe(0);expect(ffprobe.stdout).toContain("ffprobe version")},30_000);
});
