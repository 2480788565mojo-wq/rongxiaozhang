"""本地开发启动器（不要用于生产）。

Windows 上的代理工具经常把 NO_PROXY 写成 ``localhost,127.0.0.1,::1,[::1]``。
httpx 会把 ``[::1]`` 当成 URL 解析，导致模型客户端初始化失败，接口只返回
“AI 解析暂时不可用”。这里在导入应用之前修正代理变量，再启动 uvicorn。

PyCharm 用法：右键本文件 → Run 'run_local'，工作目录选 backend。
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# 必须在导入 app / httpx 之前设置。
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
