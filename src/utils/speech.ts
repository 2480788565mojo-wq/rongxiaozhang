export function joinSpeechText(baseText: string, speechText: string): string {
  const base = baseText.trimEnd();
  const speech = speechText.trim();
  if (!base) return speech;
  if (!speech) return base;
  const needsSeparator = !/[，。！？；、,.!?;\s]$/.test(base);
  return `${base}${needsSeparator ? "，" : ""}${speech}`;
}

export function speechErrorMessage(error: string): string {
  if (["not-allowed", "service-not-allowed", "auth-denied"].includes(error)) {
    return "没有麦克风权限，请在设置中允许录音";
  }
  if (error === "no-speech") return "没有听到声音，请靠近麦克风再试一次";
  if (error === "audio-capture") return "没有找到可用的麦克风";
  if (error === "network") return "语音识别网络连接失败，请稍后重试";
  return "语音识别失败，请重试或手动输入";
}
