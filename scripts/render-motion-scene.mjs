import { mkdir, mkdtemp, readdir, rm, stat } from "node:fs/promises";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const requireFromWorkspace = createRequire(join(process.env.NEWSVID_NODE_ROOT || process.cwd(), "package.json"));
const { chromium } = requireFromWorkspace("playwright");

function args(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) out[argv[i].replace(/^--/, "")] = argv[i + 1];
  return out;
}

function ffmpeg(binary, values) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(binary, values, { shell: false, stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    child.stderr.on("data", chunk => { stderr += chunk.toString("utf8"); });
    child.on("error", reject);
    child.on("exit", code => code === 0 ? resolveRun() : reject(new Error(stderr.slice(-3000))));
  });
}

const input = args(process.argv);
const html = resolve(input.html || "");
const output = resolve(input.output || "");
const width = Number(input.width || 1080);
const height = Number(input.height || 1920);
const fps = Number(input.fps || 30);
const duration = Number(input.duration || 5);
const ffmpegBin = input.ffmpeg || "ffmpeg";
const edge = input.chromium || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
if (!html || !output || !Number.isFinite(duration) || duration <= 0) throw new Error("Invalid motion render arguments");
await mkdir(dirname(output), { recursive: true });
const recordDir = await mkdtemp(join(tmpdir(), "newsvid-hf-"));
let browser;
try {
  browser = await chromium.launch({ executablePath: edge, headless: true,
    args: ["--no-sandbox", "--disable-background-timer-throttling"] });
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1,
    recordVideo: { dir: recordDir, size: { width, height } } });
  const page = await context.newPage();
  await page.addInitScript(() => {
    const style = document.createElement("style");
    style.id = "__newsvid_freeze";
    style.textContent = "*,*::before,*::after{animation-play-state:paused!important}";
    document.documentElement.appendChild(style);
  });
  await page.goto(pathToFileURL(html).href, { waitUntil: "domcontentloaded" });
  await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });
  await page.evaluate(() => {
    document.getElementById("__newsvid_freeze")?.remove();
    window.__newsvidPlay?.();
  });
  await page.waitForTimeout(Math.round(duration * 1000));
  await context.close();
  const webm = (await readdir(recordDir)).find(name => name.endsWith(".webm"));
  if (!webm) throw new Error("Chromium produced no WebM recording");
  await ffmpeg(ffmpegBin, ["-y", "-i", join(recordDir, webm), "-vf",
    `tpad=stop_mode=clone:stop_duration=${duration},scale=${width}:${height}`,
    "-t", String(duration), "-r", String(fps), "-c:v", "libx264", "-preset", "fast",
    "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", output]);
  const result = await stat(output);
  process.stdout.write(JSON.stringify({ output, bytes: result.size, width, height, fps, duration,
    engine: "html-video-playwright-hyperframes-adapter" }));
} finally {
  await browser?.close().catch(() => {});
  await rm(recordDir, { recursive: true, force: true }).catch(() => {});
}
