import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 后端统一前缀为 /api/v1，前端开发环境 baseURL 使用 /api，
// 由下面的代理把 /api/** 重写为 /api/v1/**，避免每个接口都写版本号。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1')
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 使用 Sass 现代 API，避免 legacy JS API 弃用警告
        api: 'modern'
      }
    }
  }
})
