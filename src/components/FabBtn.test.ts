import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import FabBtn from './FabBtn.vue'

describe('FabBtn 悬浮按钮', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    ;(uni as any).getSystemInfoSync = vi.fn(() => ({
      windowWidth: 375,
      windowHeight: 667,
      safeArea: { top: 20, bottom: 667 },
    }))
    vi.mocked(uni.getStorageSync).mockReturnValue(undefined)
  })

  it('渲染 + 号按钮', () => {
    const wrapper = mount(FabBtn)
    expect(wrapper.text()).toContain('+')
    expect(wrapper.find('button').attributes('aria-label')).toBe('打开智能记账')
  })

  it('点击后跳转到记账页', async () => {
    const wrapper = mount(FabBtn)
    await wrapper.find('.fab-btn').trigger('click')
    expect(uni.switchTab).toHaveBeenCalledWith({ url: '/pages/transcribe/index' })
  })

  it('拖动后更新位置、持久化且不会误触跳转', async () => {
    vi.useFakeTimers()
    try {
      const wrapper = mount(FabBtn)
      const button = wrapper.find('.fab-btn')

      await button.trigger('touchstart', { touches: [{ clientX: 188, clientY: 540 }] })
      await button.trigger('touchmove', { touches: [{ clientX: 500, clientY: 262 }] })
      await button.trigger('touchend')
      await button.trigger('click')

      expect(button.attributes('style')).toContain('left: 319px')
      expect(button.attributes('style')).toContain('top: 276px')
      expect(uni.setStorageSync).toHaveBeenCalledWith(
        'rxz-fab-position',
        expect.objectContaining({ x: 319, y: 276 }),
      )
      expect(uni.switchTab).not.toHaveBeenCalled()
      vi.runAllTimers()
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('恢复的位置会被限制在完整屏幕安全区内', async () => {
    vi.mocked(uni.getStorageSync).mockReturnValue({ x: 9999, y: 9999 })
    const wrapper = mount(FabBtn)
    await wrapper.vm.$nextTick()
    const style = wrapper.find('.fab-btn').attributes('style')

    expect(style).toContain('left: 319px')
    expect(style).toContain('top: 611px')
  })
})
