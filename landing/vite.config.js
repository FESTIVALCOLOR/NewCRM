import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE_PATH || '/beta/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        admin: resolve(__dirname, 'admin.html'),
      },
    },
  },
  server: {
    port: 3030,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})
