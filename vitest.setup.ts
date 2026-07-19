import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { h, defineComponent } from 'vue'

// 全局注册 uni-app 内置组件 view 和 text
const StubView = defineComponent({
  setup(_, { slots, attrs }) {
    return () => h('div', { ...attrs }, slots.default?.())
  }
})
const StubText = defineComponent({
  setup(_, { slots, attrs }) {
    return () => h('span', { ...attrs }, slots.default?.())
  }
})
config.global.components = {
  view: StubView,
  text: StubText,
}

// 模拟本地存储
const storage: Record<string, string> = {}

const uni = {
  getStorageSync: vi.fn((key: string) => storage[key] || ''),
  setStorageSync: vi.fn((key: string, value: string) => { storage[key] = value }),
  removeStorageSync: vi.fn((key: string) => { delete storage[key] }),
  showToast: vi.fn(),
  showToast_noop: vi.fn(),
  navigateTo: vi.fn(),
  switchTab: vi.fn(),
  navigateBack: vi.fn(),
  showModal: vi.fn(),
  authorize: vi.fn(),
  openSetting: vi.fn(),
  request: vi.fn(),
  showActionSheet: vi.fn(),
  createCanvasContext: vi.fn(() => ({
    setStrokeStyle: vi.fn(),
    setFillStyle: vi.fn(),
    setLineWidth: vi.fn(),
    setFontSize: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    stroke: vi.fn(),
    closePath: vi.fn(),
    draw: vi.fn(),
  })),
}

vi.stubGlobal('uni', uni)

// 模拟 getCurrentPages
vi.stubGlobal('getCurrentPages', vi.fn(() => [{ options: {} }]))

// 模拟 @dcloudio/uni-app 模块（避免 vue 实例版本冲突）
vi.mock('@dcloudio/uni-app', () => ({
  onShow: vi.fn((cb: () => void) => cb()),
  onLaunch: vi.fn(),
  onHide: vi.fn(),
}))
