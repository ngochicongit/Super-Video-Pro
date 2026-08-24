import fs from "node:fs/promises";
await fs.mkdir("dist-electron/preload", { recursive: true });
await fs.copyFile("src/preload/index.cjs", "dist-electron/preload/index.cjs");
