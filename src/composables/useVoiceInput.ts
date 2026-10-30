import { computed, onUnmounted, ref, type Ref } from 'vue';
import { onHide } from '@dcloudio/uni-app';
import { createVoiceInput, type VoiceState } from '@/utils/voice-input';
import { joinSpeechText, speechErrorMessage } from '@/utils/speech';

export function useVoiceInput(target: Ref<string>, maxLength = 500) {
  const state = ref<VoiceState>('idle');
  const status = ref('');
  let baseText = '';
  let hasText = false;
  const runtime: { Recognition?: new () => any; getWechatManager?: () => any } = {};
  // #ifdef H5
  if (typeof window !== 'undefined') runtime.Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  // #endif
  const input = createVoiceInput({
    onText(text) { hasText = true; target.value = joinSpeechText(baseText, text).slice(0, maxLength); },
    onState(value) {
      state.value = value;
      status.value = value === 'starting' ? '正在请求麦克风权限…' : value === 'listening' ? '正在听，再次点击结束' : value === 'stopping' ? '正在完成语音识别…' : hasText ? '已转成文字，请核对后保存' : '';
    },
    onError(code) { status.value = ''; uni.showToast({ title: speechErrorMessage(code), icon: 'none', duration: 3500 }); },
  }, runtime);
  const busy = computed(() => state.value !== 'idle');
  function toggle() {
    if (busy.value) { input.stop(); return; }
    baseText = target.value; hasText = false; input.start();
  }
  function cancel() { input.cancel(); status.value = ''; }
  onHide(cancel); onUnmounted(cancel);
  return { busy, status, state, toggle, cancel, stop: input.stop };
}
