import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    host: '0.0.0.0',
    allowedHosts: ['linx.spotted-truck.ts.net', 'localhost', 'linx', 'novatrader.rohitkhullar.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:5181',
        changeOrigin: true,
        proxyTimeout: 120000,
        timeout: 120000,
      }
    }
  },
  preview: {
    port: 5187,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:5181',
        changeOrigin: true,
        proxyTimeout: 120000,
        timeout: 120000,
      }
    }
  }
})
