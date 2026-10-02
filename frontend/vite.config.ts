import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            // Gracefully handle backend warm-up without throwing unhandled ECONNREFUSED
            if (res && 'writeHead' in res && !(res as { headersSent?: boolean }).headersSent) {
              ;(res as { writeHead: (code: number, headers: Record<string, string>) => void; end: (body: string) => void }).writeHead(503, { 'Content-Type': 'application/json' })
              ;(res as { writeHead: (code: number, headers: Record<string, string>) => void; end: (body: string) => void }).end(JSON.stringify({ status: 'initializing', error: 'Backend warming up, retrying...' }))
            }
          })
        },
      },
    },
  },
})
