import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
  base: "./",
  plugins: [react()],
  resolve: { alias: { "@shared": fileURLToPath(new URL("./src/shared", import.meta.url)), "@renderer": fileURLToPath(new URL("./src/renderer", import.meta.url)) } },
  build: { outDir: "dist" }
});
