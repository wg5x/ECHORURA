import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [react()],
  build: {
    target: "chrome64",
  },
  resolve: {
    alias: {
      "@ai-engine/shared": fileURLToPath(new URL("./src/shared/index.ts", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
  },
});
