import { describe, expect, it } from "vitest";
import { joinSpeechText, keyboardVoiceHint, speechErrorMessage } from "./speech";

describe("语音输入文本处理", () => {
  it("空输入框直接显示识别文字", () => {
    expect(joinSpeechText("", "午饭 28 元")).toBe("午饭 28 元");
  });

  it("保留原文字并追加语音", () => {
    expect(joinSpeechText("今天", "午饭 28 元")).toBe("今天，午饭 28 元");
  });

  it("已有标点时不重复添加分隔符", () => {
    expect(joinSpeechText("今天，", "午饭 28 元")).toBe("今天，午饭 28 元");
  });

  it("微信端提示使用手机键盘麦克风", () => {
    expect(keyboardVoiceHint()).toContain("手机键盘上的麦克风");
  });

  it("权限错误给出通俗提示", () => {
    expect(speechErrorMessage("not-allowed")).toContain("麦克风权限");
  });
});
