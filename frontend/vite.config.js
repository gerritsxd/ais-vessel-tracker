import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  // IMPORTANT: base only in production
  base: mode === 'production' ? '/ships/' : '/',
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API only, not the frontend path
      '/ships/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/ships/socket.io': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true
      }
    }
  }
}))
