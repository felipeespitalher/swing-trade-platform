import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const CHUNK_MAP: Record<string, string> = {
  react: 'vendor-react',
  'react-dom': 'vendor-react',
  'react-router-dom': 'vendor-react',
  recharts: 'vendor-charts',
  'framer-motion': 'vendor-motion',
  '@tanstack/react-query': 'vendor-query',
  zustand: 'vendor-zustand',
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          for (const [pkg, chunk] of Object.entries(CHUNK_MAP)) {
            if (id.includes(`/node_modules/${pkg}/`) || id.includes(`/node_modules/${pkg.replace('/', path.sep)}/`)) {
              return chunk;
            }
          }
        },
      },
    },
  },
});
