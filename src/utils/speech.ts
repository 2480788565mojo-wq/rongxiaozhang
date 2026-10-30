export function joinSpeechText(baseText: string, speechText: string): string {
  const base = baseText.trimEnd();
  const speech = speechText.trim();
  if (!base) return speech;
  if (!speech) return base;
  const needsSeparator = !/[，。！？；、,.!?;\s]$/.test(base);
  return `${base}${needsSeparator ? "，" : ""}${speech}`;
}

export function speechErrorMessage(error: string): string {
  if (error === 'unsupported') return '当前环境不支持语音识别，请使用支持语音的浏览器或键盘语音输入';
  if (error === 'plugin-unavailable') return '语音服务尚未开通，请使用键盘语音输入';
  if (error === 'busy') return '上一段语音正在结束，请稍后再试';
  if (error === 'timeout') return '语音识别超时，请重试或手动输入';
  if (["not-allowed", "service-not-allowed", "auth-denied"].includes(error)) {
    return "没有麦克风权限，请在设置中允许录音";
  }
  if (error === "no-speech") return "没有听到声音，请靠近麦克风再试一次";
  if (error === "audio-capture") return "没有找到可用的麦克风";
  if (error === "network") return "语音识别网络连接失败，请稍后重试";
  return "语音识别失败，请重试或手动输入";
}

export function keyboardVoiceHint(): string {
  return '请点输入框，再点手机键盘上的麦克风说话';
}
