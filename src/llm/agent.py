from contextlib import AbstractContextManager
from enum import Enum
from typing import Callable, Dict

from llm import llm_model
from message import msg_mng
from utility.config_load import get_global_cfg
from datetime import datetime

"""
Agent主程序  与LLM交互
"""
class ChatModelState(Enum):
    quit_by_no_tool = 1
    quit_by_done = 2
    keep_continue = 3

# 将 Skills 元数据转换为 tools 列表
def build_tools_from_skills(meta_data):
    tools = []
    for skill in meta_data:
        tool = {
            "name": skill["name"],
            "description": skill["description"],
            "input_schema": skill["input_schema"]  # 动态生成的部分
        }
        tools.append(tool)
    return tools

# 负责与LLM交互
class AgentLoop:
    def __init__(self, print_think :bool = False):
        self.print_think = print_think
        self.api_messages = None
        self.mng_msg = None
        self.session = None
        self._print_info = None
        self._print_llm_rsp = None
        self._print_tool_call = None
        self._print_tool_result = None
        self.is_chat_mode = True
        self.max_turns = 0
        self.req_tokens = 0
        self.rsp_tokens = 0

    def get_tokens(self):
        return self.req_tokens, self.rsp_tokens

    def run(self,
            message,
            on_context_mgr: Callable[[str], AbstractContextManager],
            print_info: Callable[[str], None],
            print_llm_rsp: Callable[[str], None],
            print_tool_call: Callable[[str, Dict], None],
            print_tool_result: Callable[[str, str],None]):

        self._print_info = print_info
        self._print_llm_rsp = print_llm_rsp
        self._print_tool_call = print_tool_call
        self._print_tool_result = print_tool_result

        turn = 0
        quit_chat = ChatModelState.keep_continue
        self.mng_msg = msg_mng.Messages()
        # self.session = SessionLog()
        self.max_turns = get_global_cfg.cli.max_turns
        self.is_chat_mode = True

        # skill中MetaData转成deepseek中的TOOLS，在于LLM交互时使用
        TOOLS = build_tools_from_skills(self.mng_msg.get_skills_meta_data())
        SYSTEM = self.mng_msg.get_system_prompt()

        while turn < self.max_turns:
            turn += 1
            # 1、与LLM交互，优化界面显示， 界面显示 "Thinking"
            with on_context_mgr(f"Thinking-{turn}"):
                response = llm_model.llm_interaction_retry(self.mng_msg.get_msg(), TOOLS, SYSTEM)
                print(response)
                break


            if not quit_chat == ChatModelState.keep_continue:  # 如果不是继续chat，那就break循环
                break

        # 查看退出循环是否是达到循环上限
        if turn >= self.max_turns and quit_chat == ChatModelState.keep_continue:
            self._print_info(f"达到最大轮次限制 ({self.max_turns})，强制结束!")
