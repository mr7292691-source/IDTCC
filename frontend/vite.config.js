import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The backend does not enable CORS, so in dev we proxy API calls through Vite to
// keep everything same-origin. Leave VITE_API_URL unset (default '') to use the
// proxy; set it to an absolute URL only when the backend is same-origin already.
const BACKEND = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api':    { target: BACKEND, changeOrigin: true },
      '/health': { target: BACKEND, changeOrigin: true },
      '/metrics':{ target: BACKEND, changeOrigin: true },
    },
  },
});
