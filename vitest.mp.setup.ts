import { vi } from 'vitest';
// 与微信真机相同：ECharts 加载时可检测到 wx，而非浏览器事件环境。
vi.stubGlobal('wx', { getSystemInfoSync: () => ({ pixelRatio: 2 }) });
