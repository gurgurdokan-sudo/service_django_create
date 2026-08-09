import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: "./src/main.jsx",
    },
    outDir: "dist",   // ← rollupOptions の外に置く
  },
});
