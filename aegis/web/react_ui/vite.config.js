import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Explicitly set the project root. This is crucial for Docker builds.
  root: '.',
  build: {
    // Tell Vite to use `index.html` in the root as the entry point.
    rollupOptions: {
      input: 'index.html',
    },
    // Specify the output directory.
    outDir: 'dist',
  },
});