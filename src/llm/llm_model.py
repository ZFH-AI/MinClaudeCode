import httpx
from anthropic import Anthropic
from utility.config_load import get_global_cfg

# 读取配置信息中的链接模型的的相关参数
MODEL_PROVIDER = get_global_cfg.model.provider
provider_cfg = getattr(get_global_cfg, MODEL_PROVIDER, None)
if provider_cfg:
    api_key = getattr(provider_cfg, "api_key", None)
    base_url = getattr(provider_cfg, "base_url", None)
    model_name = getattr(provider_cfg, "model_name", "deepseek-chat")
else:
    raise ValueError(f"未知的模型供应商: {MODEL_PROVIDER}")

initial_max_tokens = get_global_cfg.model_chat.initial_max_tokens
max_retries = get_global_cfg.model_chat.max_retries
max_tokens_limit = get_global_cfg.model_chat.max_tokens_limit
temperature=get_global_cfg.model_chat.temperature

# 创建交互客户端
http_client = httpx.Client(verify=False)
client = Anthropic(api_key=api_key, base_url=base_url, http_client=http_client)


def stream_chat_anthropic(messages, system, tools, max_tokens):
    stream = client.messages.create(
        model=model_name,
        system=system,
        messages=messages,
        tools=tools,
        max_tokens=max_tokens,
        stream=True
    )

    full_content = ""
    current_tool_call = None
    tool_calls = []
    stop_reason = None

    for event in stream:
        if event.type == "message_start":
            # 可以获取初始消息信息
            pass

        elif event.type == "content_block_start":
            if event.content_block.type == "tool_use":
                # 开始一个新工具调用
                current_tool_call = {
                    "id": event.content_block.id,
                    "name": event.content_block.name,
                    "input": ""
                }

        elif event.type == "content_block_delta":
            if event.delta.type == "text_delta":
                full_content += event.delta.text
                print(event.delta.text, end="")

            elif event.delta.type == "input_json_delta":
                # 累积工具调用的 JSON 参数片段
                if current_tool_call:
                    current_tool_call["input"] += event.delta.partial_json

        elif event.type == "content_block_stop":
            if current_tool_call:
                # 工具调用结束，保存
                tool_calls.append(current_tool_call)
                current_tool_call = None

        elif event.type == "message_delta":
            # 此处可以获取 stop_reason
            if hasattr(event.delta, 'stop_reason'):
                stop_reason = event.delta.stop_reason

        elif event.type == "message_stop":
            # 最终结束
            break

    # 处理截断
    is_truncated = (stop_reason == "max_tokens")
    if is_truncated:
        full_content += "\n[注意：输出被 max_tokens 截断]"

    return full_content, tool_calls, is_truncated

# 与LLM交互主流程
def llm_interaction_retry(messages, TOOLS, SYSTEM):
    max_token = initial_max_tokens
    for message in range(max_retries + 1):
        ull_content, tool_calls, is_truncated = stream_chat_anthropic(messages, SYSTEM, TOOLS, max_token)
        print(ull_content)
        print(tool_calls)
        print(is_truncated)
        break

