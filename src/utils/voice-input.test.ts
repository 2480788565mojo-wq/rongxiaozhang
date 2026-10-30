import { afterEach, describe, expect, it, vi } from 'vitest';
import { createVoiceInput } from './voice-input';
afterEach(() => vi.useRealTimers());
describe('语音输入会话', () => {
  it('浏览器结果保留完整识别文本，取消后忽略迟到的结果', () => {
    let recognition: any;
    class Recognition { start = vi.fn(); stop = vi.fn(); abort = vi.fn(); constructor() { recognition = this; } }
    const onText = vi.fn(); const onState = vi.fn();
    const voice = createVoiceInput({ onText, onState, onError: vi.fn() }, { Recognition });
    voice.start(); expect(onState).toHaveBeenLastCalledWith('starting');
    recognition.onstart(); expect(onState).toHaveBeenLastCalledWith('listening');
    recognition.onresult({ results: [[{ transcript: '午饭' }], [{ transcript: '28元' }]] });
    expect(onText).toHaveBeenLastCalledWith('午饭28元');
    voice.cancel(); recognition.onresult({ results: [[{ transcript: '迟到结果' }]] });
    expect(onText).toHaveBeenCalledTimes(1); expect(onState).toHaveBeenLastCalledWith('idle');
  });
  it('微信插件接收中间和最终结果，停止后才能开始下一次', () => {
    const manager: any = { start: vi.fn(), stop: vi.fn() };
    const onText = vi.fn(); const onState = vi.fn();
    const voice = createVoiceInput({ onText, onState, onError: vi.fn() }, { getWechatManager: () => manager });
    voice.start(); manager.onStart(); manager.onRecognize({ result: '午饭' }); voice.stop(); voice.start();
    expect(manager.start).toHaveBeenCalledTimes(1); expect(onState).toHaveBeenLastCalledWith('stopping');
    manager.onStop({ result: '午饭28元' }); expect(onText).toHaveBeenLastCalledWith('午饭28元');
    expect(onState).toHaveBeenLastCalledWith('idle');
  });
  it('微信停止超时后仍隔离旧录音，迟到结果不能写入另一页面', () => {
    vi.useFakeTimers();
    const manager: any = { start: vi.fn(), stop: vi.fn() };
    const firstText = vi.fn(); const secondText = vi.fn(); const secondError = vi.fn();
    const first = createVoiceInput({ onText: firstText, onState: vi.fn(), onError: vi.fn() }, { getWechatManager: () => manager });
    const second = createVoiceInput({ onText: secondText, onState: vi.fn(), onError: secondError }, { getWechatManager: () => manager });
    first.start(); manager.onStart(); first.cancel(); vi.advanceTimersByTime(10000);
    second.start(); expect(secondError).toHaveBeenLastCalledWith('busy');
    manager.onStop({ result: '旧页面迟到的录音内容' });
    expect(firstText).not.toHaveBeenCalled(); expect(secondText).not.toHaveBeenCalled();
    second.start(); manager.onStart(); manager.onStop({ result: '新录音' });
    expect(secondText).toHaveBeenLastCalledWith('新录音');
  });
  it('权限拒绝、插件未开通和识别超时均结束等待', () => {
    vi.useFakeTimers(); const onError = vi.fn(); const onState = vi.fn();
    const voice = createVoiceInput({ onText: vi.fn(), onState, onError }, { getWechatManager: () => { throw new Error('plugin missing'); } });
    voice.start(); expect(onError).toHaveBeenLastCalledWith('plugin-unavailable'); expect(onState).toHaveBeenLastCalledWith('idle');
    let recognition: any;
    class Recognition { start = vi.fn(); stop = vi.fn(); abort = vi.fn(); constructor() { recognition = this; } }
    const browser = createVoiceInput({ onText: vi.fn(), onState, onError }, { Recognition });
    browser.start(); recognition.onerror({ error: 'not-allowed' }); expect(onError).toHaveBeenLastCalledWith('not-allowed');
    browser.start(); vi.advanceTimersByTime(15000); expect(onError).toHaveBeenLastCalledWith('timeout');
    expect(onState).toHaveBeenLastCalledWith('idle');
  });
});
