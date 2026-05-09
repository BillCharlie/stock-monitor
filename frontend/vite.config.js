import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const isGhPages = process.env.GITHUB_PAGES === 'true'

export default defineConfig({
  plugins: [react()],
  // GitHub Pages needs a base path matching the repo name; local build stays at '/'
  base: isGhPages ? (process.env.VITE_BASE_PATH || '/stock-monitor/') : '/',
  build: {
    // Local build: serve from FastAPI at backend/static
    // GH Pages build: output to frontend/dist for Actions upload
    outDir: isGhPages ? 'dist' : '../backend/static',
    emptyOutDir: true,
  },
})
