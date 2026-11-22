import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies avoid CORS in dev (neither FastAPI service enables CORS yet).
// Ports are assumptions: change to wherever each service runs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // matches FRONTEND_VERIFY_BASE_URL in blockchain-service/.env.example
    proxy: {
      '/svc/auth': { target: 'http://localhost:8000', rewrite: p => p.replace(/^\/svc\/auth/, '') }, // health checks
      '/svc/chain': { target: 'http://localhost:8001', rewrite: p => p.replace(/^\/svc\/chain/, '') },
      '/api/auth': 'http://localhost:8000',
      '/api/blockchain': 'http://localhost:8001',
      '/api/resume': 'http://localhost:8002',
    },
  },
})
