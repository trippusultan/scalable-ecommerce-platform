import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api/* to the running gateway at :8000.
// base defaults to /ui/ (served under the gateway at /ui/*). For standalone
// hosting (e.g. Firebase Hosting at the domain root) build with VITE_BASE=/.
export default defineConfig({
  base: process.env.VITE_BASE || "/ui/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
