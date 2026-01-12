import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
	plugins: [react()],
	server: {
		port: 5173,
		host: '0.0.0.0',
		proxy: {
			// Proxy API requests to the backend
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				secure: false
			},
			// Proxy WebSocket connections to the backend
			'/api/v1/ws': {
				target: 'ws://localhost:8000',
				ws: true,
				changeOrigin: true
			}
		}
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, './src')
		},
		extensions: ['.ts', '.tsx', '.js', '.jsx']
	}
});