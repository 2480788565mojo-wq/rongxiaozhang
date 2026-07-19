import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FabBtn from './FabBtn.vue'

describe('FabBtn 悬浮按钮', () => {
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
})
