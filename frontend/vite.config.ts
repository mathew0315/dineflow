import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// build 產物輸出到 FastAPI 的 app/static，由同一個服務提供（部署只需一個 web service）
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../app/static", emptyOutDir: true },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
