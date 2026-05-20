from contextlib import AbstractContextManager
from enum import Enum
from typing import Callable, Dict
from llm_model import *
from message import msg_mng
from utility.config_load import get_global_cfg
from datetime import datetime

class ChatModelState(Enum):
    quit_by_no_tool = 1
    quit_by_done = 2
    keep_continue = 3

# 负责与LLM交互
class AgentLoop:
    def __init__(self, print_think :bool = False):
        self.print_think = print_think
        self.api_messages = None
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
        self.api_messages = msg_mng.Messages()
        # self.session = SessionLog()
        self.max_turns = get_global_cfg.cli.max_turns
        self.is_chat_mode = True

        while turn < self.max_turns:
            turn += 1

            # 1、与LLM交互，优化界面显示， 界面显示 "Thinking"
            with on_context_mgr(f"Thinking-{turn}"):
                thinking_begin = self._on_llm_req(turn, message)
                ai_response, is_truncated, reasoning_content = chat_llm.chat_with_retry(self.api_messages.get_msg())

            # 解析LLM的反馈
            tools = self._on_llm_rsp(turn, thinking_begin, ai_response, reasoning_content)

            # 工具处理
            quit_chat = self._handle_tools(tools)

            if not quit_chat == ChatModelState.keep_continue:  # 如果不是继续chat，那就break循环
                break

        # 查看退出循环是否是达到循环上限
        if turn >= self.max_turns and quit_chat == ChatModelState.keep_continue:
            self._print_info(f"达到最大轮次限制 ({self.max_turns})，强制结束!")

        # 确保最后一个 Turn 的内容被持久化
        # self.session.flush_turn()

        # 估算tokens
        #req_tokens, rsp_tokens = self.session.get_tokens()
        #self.req_tokens += req_tokens
        #self.rsp_tokens += rsp_tokens

    def _on_llm_req(self, turn:int, message):
        # 首次运行，赋初值
        if turn == 1:
            self.api_messages.init_msg(message)
            # self.session.init_session()

        # 倒数最后一轮，插入提醒命令
        if turn == self.max_turns and not self.is_chat_mode:
            command = "命令：如果你已完成所有修改，请立即调用 <llm_tool>done</llm_tool> 结束任务。不要继续调用其他工具。"
            self.api_messages.append_micro_info("user", command)

        # 事前记录轮次及发送给LLM的req
        #self.session.log_turn(turn)
        #self.session.log_llm_req(self.api_messages.get_msg())

        # LLM开启回答时间戳
        thinking_begin = datetime.now().strftime("%Y-%m-%d %H : %M : %S")

        return thinking_begin

    def _on_llm_rsp(self, turn, thinking_begin, ai_response, reasoning_content):
        # LLM结束回答时间戳
        thinking_end = datetime.now().strftime("%Y-%m-%d %H : %M : %S")

        # 记录推理内容（如果提供商支持）
        #self.session.log_reasoning_content(reasoning_content)

        # 记录LLM回应的原始内容（日志保留完整内容）
        #self.session.log_llm_rsp(ai_response)
