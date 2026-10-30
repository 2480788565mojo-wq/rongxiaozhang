export type VoiceState = 'idle' | 'starting' | 'listening' | 'stopping';
interface Callbacks { onText: (text: string) => void; onState: (state: VoiceState) => void; onError: (code: string) => void }
interface Runtime { Recognition?: new () => any; getWechatManager?: () => any }
export interface VoiceInput { start(): void; stop(): void; cancel(): void }
// 微信插件的识别管理器是单例，上一段停止前不能让另一页面接管它。
let wechatOwner: object | null = null;
export function createVoiceInput(callbacks: Callbacks, runtime: Runtime): VoiceInput {
  let session: { driver: any; cancelled: boolean; wechat: boolean; timer: ReturnType<typeof setTimeout> | null } | null = null;
  let state: VoiceState = 'idle';
  const updateState = (value: VoiceState) => { state = value; callbacks.onState(value); };
  function finish(current: NonNullable<typeof session>, error?: string, driverEnded = true) {
    // 超时只结束界面等待，驱动真正结束前保留占用，防止旧结果串到新录音。
    if (driverEnded && wechatOwner === current) wechatOwner = null;
    if (session !== current) return;
    if (current.timer) clearTimeout(current.timer);
    session = null;
    updateState('idle');
    if (error && !current.cancelled) callbacks.onError(error);
  }
  function arm(current: NonNullable<typeof session>, ms: number) {
    if (current.timer) clearTimeout(current.timer);
    current.timer = setTimeout(() => {
      if (session !== current) return;
      try { current.driver?.abort?.(); current.driver?.stop?.(); } catch { /* 驱动可能已自行结束。 */ }
      finish(current, 'timeout', false);
    }, ms);
  }
  function start() {
    if (session) return;
    const current = { driver: null as any, cancelled: false, wechat: !runtime.Recognition, timer: null as ReturnType<typeof setTimeout> | null };
    session = current; updateState('starting');
    const deliver = (value: string) => { if (session === current && !current.cancelled && value) callbacks.onText(value); };
    const started = () => {
      if (session !== current) return;
      if (current.cancelled || state === 'stopping') { try { current.driver.stop(); } catch { finish(current); } return; }
      updateState('listening'); arm(current, 65000);
    };
    if (runtime.Recognition) {
      try {
        const driver = current.driver = new runtime.Recognition();
        driver.lang = 'zh-CN'; driver.continuous = false; driver.interimResults = true;
        driver.onstart = started;
        driver.onresult = (event: any) => deliver(Array.from(event.results as any[]).map(result => result[0]?.transcript || '').join(''));
        driver.onerror = (event: any) => finish(current, event.error || 'unknown');
        driver.onend = () => finish(current);
        arm(current, 15000); driver.start();
      } catch { finish(current, 'unknown'); }
      return;
    }
    if (!runtime.getWechatManager) { finish(current, 'unsupported'); return; }
    if (wechatOwner) { current.wechat = false; finish(current, 'busy'); return; }
    try {
      const manager = current.driver = runtime.getWechatManager();
      wechatOwner = current;
      manager.onStart = started;
      manager.onRecognize = (event: any) => deliver(event.result || '');
      manager.onStop = (event: any) => { deliver(event.result || ''); finish(current); };
      manager.onError = (event: any) => {
        const message = String(event.msg || event.errMsg || '');
        finish(current, /auth|permission|denied|授权|拒绝/i.test(message) ? 'auth-denied' : 'unknown');
      };
      arm(current, 15000); manager.start({ duration: 60000, lang: 'zh_CN' });
    } catch { finish(current, 'plugin-unavailable'); }
  }
  function stop() {
    const current = session;
    if (!current || state === 'stopping') return;
    updateState('stopping'); arm(current, 10000);
    try { current.driver?.stop(); } catch { finish(current, 'unknown'); }
  }
  function cancel() {
    const current = session;
    if (!current) return;
    current.cancelled = true;
    if (current.wechat) { stop(); updateState('idle'); }
    else { finish(current); try { current.driver?.abort?.(); } catch { /* 已停止时忽略。 */ } }
  }
  return { start, stop, cancel };
}
