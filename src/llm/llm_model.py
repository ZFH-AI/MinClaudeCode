import httpx
from anthropic import Anthropic
from typing import List, Dict, Any, Tuple
from llm.comm import *
from message.memory_mng import MemoryManager
from utility.config_load import get_global_cfg
import json

# 流式打字机式输出
def on_text_chunk(text: str):
    print(text, end="", flush=True)

class LLMClient:
    def __init__(self):
        # 读取配置信息中的链接模型的的相关参数
        self.MODEL_PROVIDER = get_global_cfg.model.provider
        self.provider_cfg = getattr(get_global_cfg, self.MODEL_PROVIDER, None)
        if not self.provider_cfg:
            raise ValueError(f"未知的模型供应商: {self.MODEL_PROVIDER}")

        self.api_key = getattr(self.provider_cfg, "api_key", None)
        self.base_url = getattr(self.provider_cfg, "base_url", None)
        self.model_name = getattr(self.provider_cfg, "model_name", "deepseek-chat")
        self.temperature = get_global_cfg.model_chat.temperature
        self.choice_stream = getattr(self.provider_cfg, "choice_stream", True)
        self.http_client = httpx.Client(verify=False)

        # 创建交互窗口
        self.client = Anthropic(api_key=self.api_key, base_url=self.base_url, http_client=self.http_client)

        # Agent的上下文记忆管理
        self.memory_manager = MemoryManager(self.model_name, model_context_limit=80000, llm_client=self.client)

    def stream_chat(self, messages, system, tools, max_tokens) -> Tuple[str, List[Dict], str]:
        try:
            response = self.client.messages.create(model=self.model_name, system=system, messages=messages,
                tools=tools,  max_tokens=max_tokens, temperature=self.temperature, stream=self.choice_stream)
        except Exception as e:
            raise RuntimeError(f"LLM API 调用失败: {e}") from e

        full_text = ""
        current_tool = None  # 正在构建的工具调用
        tool_calls: List[Dict] = []
        stop_reason = None
        incomplete_tool = False  # 标记是否存在未完成的工具调用

        for chunk in response:
            chunk_type = chunk.type
            if chunk_type == "message_start":
                continue

            elif chunk_type == "content_block_start":
                block = chunk.content_block
                if block.type == "tool_use":
                    current_tool = {
                        "id": block.id,
                        "name": block.name,
                        "input": ""  # 先累积 JSON 字符串
                    }

            elif chunk_type == "content_block_delta":
                delta = chunk.delta
                if delta.type == "text_delta":
                    full_text += delta.text
                    on_text_chunk(delta.text)
                elif delta.type == "input_json_delta":
                    if current_tool is not None:
                        current_tool["input"] += delta.partial_json

            elif chunk_type == "content_block_stop":
                if current_tool is not None:
                    try:
                        # 解析工具输入的 JSON
                        current_tool["input"] = json.loads(current_tool.pop("input"))
                    except json.JSONDecodeError as e:
                        # 解析失败时可选择丢弃或保留原始字符串，这里丢弃并继续
                        current_tool = None
                        continue
                    tool_calls.append(current_tool)
                    current_tool = None

            elif chunk_type == "message_delta":
                stop_reason = getattr(chunk.delta, 'stop_reason', stop_reason)

            elif chunk_type == "message_stop":
                # 流结束时，若 current_tool 仍有值，说明工具调用不完整
                if current_tool is not None:
                    incomplete_tool = True
                    current_tool = None  # 丢弃不完整调用
                break

        # 统一处理 stop_reason
        if stop_reason is None:
            stop_reason = "end_turn"  # 默认正常结束

        # 若因 max_tokens 截断且有不完整工具调用，视为无效，清空工具列表
        if stop_reason == "max_tokens" and incomplete_tool:
            print("max_tokens 截断导致不完整工具调用，丢弃该调用。")
            tool_calls = []

        return full_text, tool_calls, stop_reason

    """
    带重试的 LLM 交互：
     - 若输出截断（max_tokens）且未产生工具调用，尝试续写文本；
     - 若截断且工具调用不完整（已被 stream_chat 丢弃），则增加 max_tokens 重试；
     - 达到最大重试或限制时返回当前结果。
    """
    def interaction_with_retry(self, messages: List[Dict], tools: List[Dict], system: str) -> Tuple[str, List[Dict], str]:
        max_retries = get_global_cfg.model_chat.max_retries
        max_tokens_limit = get_global_cfg.model_chat.max_tokens_limit
        current_max_tokens = get_global_cfg.model_chat.initial_max_tokens

        # 在每次请求前，获取用户最新输入（最后一条 user 消息）
        last_user_query = messages[-1]["content"] if messages else ""

        # 获取处理后的上下文（包含短期压缩和长期记忆）
        processed_messages = self.memory_manager.get_context(messages, last_user_query)
        print(processed_messages)
        # 保留原始消息副本，用于可能的重试/续写
        working_messages = [m.copy() for m in processed_messages]
        for attempt in range(max_retries + 1):
            try:
                full_text, tool_calls, stop_reason = self.stream_chat(working_messages, system, tools, current_max_tokens)
            except Exception:
                if attempt >= max_retries:
                    raise  # 最终失败，向上抛出
                continue  # 网络等问题可重试

            # 非截断，或已无可用的增加空间，直接返回
            if stop_reason != "max_tokens":
                # 将本次对话的重要信息存入长期记忆
                self._store_conversation_memory(messages, full_text)
                return full_text, tool_calls, stop_reason

            # 截断处理
            if attempt >= max_retries:
                print("达到最大重试次数，返回截断结果")
                return full_text, tool_calls, stop_reason

            # 如果有工具调用，则说明截断发生在文本部分（工具已完整）
            if tool_calls:
                # 将已生成的文本追加到对话，并要求继续
                assistant_msg = build_assistant_message(full_text, [])
                working_messages.append(assistant_msg)
                working_messages.append({"role": "user", "content": "请继续输出剩余内容。"})
                # 重置 max_tokens 为初始值，或适当增加
                current_max_tokens = get_global_cfg.model_chat.initial_max_tokens
                print("截断文本，使用续写策略继续生成。")
            else:
                # 没有工具调用，可能是纯文本截断或工具不完整已被丢弃
                # 这里统一增加 max_tokens 并重试
                next_tokens = current_max_tokens * 2
                if next_tokens > max_tokens_limit:
                    print("max_tokens 已达上限，返回截断结果")
                    return full_text, tool_calls, stop_reason
                current_max_tokens = next_tokens
                # 注意：重试时不修改消息历史，即丢弃本次不完整输出
                print("max_tokens 不足，增加至 %d 重试", current_max_tokens)

        # 兜底
        return "", [], "end_turn"

    def _store_conversation_memory(self, messages, final_response):
        # 简单策略：如果对话较长或涉及决策，生成摘要并存储
        if len(messages) > 10:
            summary = self.memory_manager.generate_summary(messages[-10:])
            self.memory_manager.store_memory(messages, summary)
