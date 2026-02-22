import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// When VITE_API_URL is not set (local dev / preview), proxy all API calls to
// the local backend so the dev server never intercepts them with index.html.
const BACKEND = 'http://localhost:8000'

const proxy = {
  '/api': { target: BACKEND, changeOrigin: true },
  '/health': { target: BACKEND, changeOrigin: true },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy },   // npm run dev
  preview: { proxy },  // npm run preview
})
