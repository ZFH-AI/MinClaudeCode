"""
Agent主程序  与LLM交互
"""

from typing import Any
from llm.llm_model import LLMClient
from llm.llm_tool import TOOL_HANDLERS
from message import msg_mng
from llm.comm import *

# 负责与LLM交互
class AgentLoop:
    def __init__(self, print_think :bool = False):
        self.print_think = print_think
        self.mng_msg = None
        self._print_info: Callable[[str], None] = lambda _: None
        self._print_llm_rsp: Callable[[str], None] = lambda _: None
        self._print_tool_call: Callable[[str, Dict], None] = lambda _, __: None
        self._print_tool_result: Callable[[str, str], None] = lambda _, __: None
        self.is_chat_mode = True
        self.max_turns = 0

    def run(self,
            message,
            on_context_mgr: Callable[[str], Any],
            print_info: Callable[[str], None],
            print_llm_rsp: Callable[[str], None],
            print_tool_call: Callable[[str, Dict], None],
            print_tool_result: Callable[[str, str],None]
            ):

        # 绑定回调函数
        self._print_info = print_info
        self._print_llm_rsp = print_llm_rsp
        self._print_tool_call = print_tool_call
        self._print_tool_result = print_tool_result

        # 初始化消息管理器
        self.mng_msg = msg_mng.Messages()
        self.max_turns = get_global_cfg.cli.max_turns
        self.is_chat_mode = True

        # 初始化可用工具列表和系统提示词
        tools = get_skills_input_schema()
        system_prompt  = self.mng_msg.get_system_prompt()

        # 初始化 LLM 客户端
        llm_client = LLMClient()

        # 将用户消息加入到对话
        self.mng_msg.init_msg(message)
        for turn in range(1, self.max_turns + 1):
            with on_context_mgr(f"Thinking-{turn}"):
                try:
                    full_text, tool_calls, stop_reason = llm_client.interaction_with_retry(self.mng_msg.get_msg(), tools, system_prompt)
                except Exception as e:
                    self._print_info(f"[turn]轮 LLM 交互异常: {e}, 继续尝试")
                    continue

            # 构建正确的 assistant 消息，包含工具调用信息
            assistant_msg = build_assistant_message(full_text, tool_calls)
            self.mng_msg.update_msg(assistant_msg)

            # 处理工具调用
            if tool_calls:
                self._handle_tools(tool_calls)
            else:
                # 无工具调用
                if not self.is_chat_mode:
                    self._print_info("LLM 未调用工具，任务自动结束。")
                # 若是 end_turn 或正常，退出循环
                if stop_reason in ("end_turn", "stop_sequence"):
                    break

            # 若 stop_reason 为 end_turn，也可以结束
            if stop_reason in ("end_turn", "stop_sequence"):
                break

            if turn >= self.max_turns:
                self._print_info(f"达到最大轮次限制 ({self.max_turns})，强制结束。")
                break

    # 工具执行的的反馈
    def _handle_tools(self, tools):
        self.is_chat_mode = False
        results = []
        for tool in tools:
            tool_name = tool.get("name", "unknown")
            handler = TOOL_HANDLERS.get(tool["name"])
            if handler:
                try:
                    output = handler(**tool["input"])
                except Exception as e:
                    output = f"工具执行出错: {str(e)}"
            else:
                output = f"未知工具: {tool_name}"
                # 输出结果日志，截断显示

            output_str = str(output)
            self._print_tool_result(tool_name, output_str[:500])
            results.append({"tool_use_id": tool["id"], "content": output_str})

        if results:
            # 将工具执行的结果反馈值添加到message中
            user_msg = build_tool_result_message(results)
            self.mng_msg.update_msg(user_msg)
