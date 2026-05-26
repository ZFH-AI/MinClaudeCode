import httpx
from anthropic import Anthropic
from utility.config_load import get_global_cfg
import json
from typing import List, Dict, Any, Tuple

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
    try:
        response = client.messages.create(
            model=model_name,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        # 解析流式输出
        full_content = ""
        current_tool_call = None
        tool_calls = []
        stop_reason = None

        for chunk in response:
            # 调试用，生产环境可注释
            # print(">>", chunk.type)

            # 匹配流反馈中的各个类型
            match chunk.type:
                case "message_start":
                    continue
                case "content_block_start":
                    if chunk.content_block.type == "tool_use":
                        current_tool_call = {
                            "id": chunk.content_block.id,
                            "name": chunk.content_block.name,
                            "input": ""
                        }

                case "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        full_content += chunk.delta.text

                    if chunk.delta.type == "input_json_delta":
                        if current_tool_call:
                            current_tool_call["input"] += chunk.delta.partial_json

                case "content_block_stop":
                    if current_tool_call:
                        #tool_calls.append(current_tool_call)
                        #current_tool_call = None
                        # 解析 JSON 字符串为字典
                        try:
                            current_tool_call["input"] = json.loads(current_tool_call["input"])
                        except json.JSONDecodeError:
                            # 保持原始字符串，上层自行处理
                            pass
                        tool_calls.append(current_tool_call)
                        current_tool_call = None

                case "message_delta":
                    if hasattr(chunk.delta, 'stop_reason'):
                        stop_reason = chunk.delta.stop_reason

                case "message_stop":
                    break

                case _ :
                    continue
                
        is_truncated = (stop_reason == "max_tokens")
        if is_truncated:
            full_content += "\n[注意：输出被 max_tokens 截断]"

        return full_content, tool_calls, is_truncated
    except Exception as e:
        return f"[API_ERROR: 流式读取异常，{e}]", "", True


# 可选：衔接截断内容的辅助函数（解决重试时的“续写”问题）
def append_continuation(original_messages, already_generated_content):
    """
    当因 max_tokens 截断时，将已生成的内容作为 assistant 消息追加，
    再追加一条 user 消息要求继续，实现无缝续写。
    """
    new_messages = original_messages.copy()
    new_messages.append({"role": "assistant", "content": already_generated_content})
    new_messages.append({"role": "user", "content": "请继续输出，不要重复已给出的内容。"})
    return new_messages

# 带重试的主流程
def llm_interaction_retry(messages, TOOLS, SYSTEM):
    max_token = initial_max_tokens
    for attempt in range(max_retries + 1):
        full_content, tool_calls, is_truncated = stream_chat_anthropic(messages, SYSTEM, TOOLS, max_token)

        # 成功（未截断）或已达最大重试次数，直接返回
        if not is_truncated or attempt >= max_retries:
            return full_content, tool_calls

        next_tokens = max_token * 2
        if next_tokens > max_tokens_limit:
            return full_content, tool_calls

        max_token = next_tokens

        # 可选：追加用户消息让模型继续（见下文优化说明）
        # messages = append_continuation(messages, full_content)

    return "", []


