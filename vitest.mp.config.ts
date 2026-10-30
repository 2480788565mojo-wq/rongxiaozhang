import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'node:path';
import { initPreContext, preJs, preHtml } from '@dcloudio/uni-cli-shared/dist/preprocess';
initPreContext('mp-weixin');
export default defineConfig({
  plugins: [{ name: 'test-wechat-branches', enforce: 'pre', transform(code, id) {
    if (!id.includes('/src/') || id.includes('?') || id.includes('.test.')) return;
    if (id.endsWith('.vue')) return { code: preJs(preHtml(code, id), id), map: null };
    if (id.endsWith('.ts')) return { code: preJs(code, id), map: null };
  } }, vue()],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  test: { environment: 'happy-dom', include: ['src/**/*.mp.test.ts'], setupFiles: ['./vitest.setup.ts', './vitest.mp.setup.ts'], maxWorkers: 1 },
});
