import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/run': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 30000,
        proxyTimeout: 30000,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 300000,
        proxyTimeout: 300000,
      },
      '/dashboard': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 30000,
        proxyTimeout: 30000,
      },
    },
  },
})



