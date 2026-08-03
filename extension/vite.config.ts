import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const webBuild = mode === "web";
  return {
    plugins: [react()],
    publicDir: webBuild ? false : "public",
    build: {
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: mode === "development",
      rollupOptions: {
        input: webBuild
          ? { index: "index.html" }
          : { sidepanel: "sidepanel.html" }
      }
    }
  };
});
