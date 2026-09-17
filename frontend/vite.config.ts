import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/patients': 'http://localhost:8000',
      '/screenings': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
      '/reviews': 'http://localhost:8000',
      '/referrals': 'http://localhost:8000',
      '/telemedicine': 'http://localhost:8000',
      '/sync': 'http://localhost:8000',
      '/simulation': 'http://localhost:8000',
      '/training': 'http://localhost:8000',
      '/validation': 'http://localhost:8000',
      '/devices': 'http://localhost:8000',
      '/audit': 'http://localhost:8000',
      '/realtime': 'http://localhost:8000',
      '/demo': 'http://localhost:8000',
      '/storage': 'http://localhost:8000'
    }
  }
})
