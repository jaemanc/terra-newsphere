import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  // Use Cesium's matched prebuilt bundle; its source ZIP dependency changed exports.
  resolve: { alias: [{ find: /^cesium$/, replacement: fileURLToPath(new URL(
    './node_modules/cesium/Build/Cesium/index.js', import.meta.url)) }] },
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium') },
  server: { proxy: { '/api': { target: process.env.API_PROXY_URL || 'http://localhost:8000' } } },
});
