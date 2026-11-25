import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: the browser only ever talks to localhost:5173, so no CORS is
// involved. Ports match scripts/dev.py (auth 8000, blockchain 8001, resume 8002).
// In production put the same rules in your reverse proxy (nginx, etc.).
const AUTH = process.env.AUTH_URL || 'http://localhost:8000'
const CHAIN = process.env.CHAIN_URL || 'http://localhost:8001'
const RESUME = process.env.RESUME_URL || 'http://localhost:8002'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // matches FRONTEND_VERIFY_BASE_URL in blockchain-service/.env
    proxy: {
      '/svc/auth': { target: AUTH, rewrite: p => p.replace(/^\/svc\/auth/, '') },
      '/svc/chain': { target: CHAIN, rewrite: p => p.replace(/^\/svc\/chain/, '') },
      '/svc/resume': { target: RESUME, rewrite: p => p.replace(/^\/svc\/resume/, '') },
      '/api/auth': AUTH,
      '/api/blockchain': CHAIN,
      // The resume service's versioned API lives under /api/v1.
      '/api/resume': { target: RESUME, rewrite: p => p.replace(/^\/api\/resume/, '/api/v1') },
    },
  },
})
