import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      // ✅ absolute Windows-safe paths
      input: {
        sidepanel: './src/sidepanel/index.html',
        'content-script': './src/content-script.js',
        'service-worker': './src/service-worker.js',
      },
      output: {
        entryFileNames: `[name].js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`,
      },
    },
  },
});
