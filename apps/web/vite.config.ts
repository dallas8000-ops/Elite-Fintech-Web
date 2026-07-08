import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8001", changeOrigin: true },
      "/admin": { target: "http://localhost:8001", changeOrigin: true },
      "/static": { target: "http://localhost:8001", changeOrigin: true },
      "/webhooks": { target: "http://localhost:8001", changeOrigin: true },
      "/billing": { target: "http://localhost:8001", changeOrigin: true },
      "/health": { target: "http://localhost:8001", changeOrigin: true },
      "/ws": { target: "ws://localhost:8001", ws: true },
    },
  },
});
