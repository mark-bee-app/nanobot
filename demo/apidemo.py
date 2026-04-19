"""nanobot API 调用示例

前置条件：
    pip install requests openai
    # 本地启动 nanobot 服务
    nanobot serve --port 8900

本 Demo 展示三种调用方式：
1. 原生 requests 调用
2. OpenAI SDK 调用（因为 nanobot 兼容 OpenAI API 格式）
3. httpx 异步调用
"""

import json
import requests

BASE_URL = "http://127.0.0.1:8900"


def _get_model_name() -> str:
    """从 /v1/models 获取实际配置的模型名称，避免硬编码不匹配导致 400。"""
    resp = requests.get(f"{BASE_URL}/v1/models", timeout=5)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    if not models:
        return "nanobot"
    return models[0]["id"]


def demo_health():
    """健康检查"""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    print("=== Health Check ===")
    print(resp.json())
    print()


def demo_models() -> str:
    """查看可用模型列表，返回实际模型名。"""
    model_name = _get_model_name()
    print("=== Models ===")
    print(f"  - {model_name}")
    print()
    return model_name


def demo_chat(message: str, session_id: str | None = None, model: str = "nanobot"):
    """单次对话

    Args:
        message: 用户输入
        session_id: 可选，传入后会话隔离（不同 session_id 之间上下文不共享）
        model: 模型名称，建议从 demo_models() 获取
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
    }
    if session_id:
        payload["session_id"] = session_id

    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    print(f"[User] {message}")
    print(f"[Bot]  {reply}")
    print()
    return reply


def demo_multi_turn():
    """多轮对话演示（使用 session_id 保持上下文）"""
    session = "demo-session-001"
    print("=== Multi-turn Chat (with session_id) ===")
    demo_chat("我叫张三，请记住我的名字", session_id=session)
    demo_chat("我叫什么名字？", session_id=session)
    print()


def demo_isolated_sessions():
    """演示 session 隔离：不同 session_id 之间上下文不共享"""
    print("=== Session Isolation Demo ===")
    demo_chat("我叫李四", session_id="session-a")
    demo_chat("我叫什么名字？", session_id="session-b")  # 不知道
    demo_chat("我叫什么名字？", session_id="session-a")  # 知道
    print()


def demo_error_handling(model: str = "nanobot"):
    """演示常见错误"""
    print("=== Error Handling ===")

    # 1. stream=true 不支持
    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
        timeout=10,
    )
    print(f"stream=true -> {resp.status_code}: {resp.text[:100]}")

    # 2. 空消息列表
    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={"model": model, "messages": []},
        timeout=10,
    )
    print(f"empty messages -> {resp.status_code}: {resp.text[:100]}")
    print()


def demo_openai_sdk(model: str = "nanobot"):
    """使用 OpenAI 官方 SDK 调用（兼容模式）"""
    print("=== OpenAI SDK ===")
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key="sk-dummy",  # nanobot 不校验 key，但 SDK 要求非空
            base_url=f"{BASE_URL}/v1",
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        )
        print(resp.choices[0].message.content)
    except ImportError:
        print("请先安装 openai: pip install openai")
    print()


async def demo_async(model: str = "nanobot"):
    """httpx 异步调用示例"""
    print("=== Async (httpx) ===")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "讲一个程序员笑话"}],
                },
            )
            print(resp.json()["choices"][0]["message"]["content"])
    except ImportError:
        print("请先安装 httpx: pip install httpx")
    print()


def main():
    print("nanobot API Demo\n")
    # demo_health()

    # 获取实际模型名，避免配置中的 model 与 "nanobot" 不一致导致 400
    model = demo_models()

    print("=== Single Chat ===")
    demo_chat("你好，介绍一下你自己", model=model)

    # demo_multi_turn()
    # demo_isolated_sessions()
    # demo_error_handling(model=model)
    # demo_openai_sdk(model=model)

    # 异步示例
    # import asyncio
    #
    # asyncio.run(demo_async(model=model))


if __name__ == "__main__":
    main()