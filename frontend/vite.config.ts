import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    watch: {
      usePolling: true,
      interval: 1000,
    },
    hmr: {
      overlay: true,
    }
  },
  preview: {
    port: 3001,
  },
  build: {
    target: 'esnext',
    modulePreload: false,
    rollupOptions: {
      output: {
        format: 'es',
        entryFileNames: '[name].[hash].js',
        chunkFileNames: '[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  }
})
