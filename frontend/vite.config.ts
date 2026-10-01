import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const localApi = 'http://127.0.0.1:8000';
export default defineConfig({ plugins: [react()], server: { proxy: { '^/api/analyze$': 'http://127.0.0.1:8787', '^/health$': localApi, '^/analyze$': localApi, '^/detect$': localApi, '^/report$': localApi } } });
