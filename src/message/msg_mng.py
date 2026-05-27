"""
Agent 与 Mode交互时，Message的管理模块
"""

from utility.skill_load import get_skill_loader
from utility.file_tool import *

class Messages:
    def __init__(self):
        # 用户输入
        self.input_to_model_msg = []

        # 1、加载 system prompt
        self.system_prompt = load_system_prompt(Path(__file__).with_name("sys_prompt.md"))

        # 2、加载 skills 的元数据
        skill_loader = get_skill_loader()
        self.skills_meta_data = skill_loader.get_skill_metadata()

        # 3、往 input_to_model_msg 注入项目上下文
        self.project_context = load_context("MinClaudeCode.md", "项目上下文")
        self.update_msg(self.project_context)

        # 4、往 input_to_model_msg 注入目录树缓存（放在项目上下文之后）
        self.tree_cache = load_context(".tree_cache.md", "项目目录树")
        self.update_msg(self.tree_cache)

    # 尾部添加微信息
    def append_micro_info(self, role, micro_info):
        msg = {
            "role": role,
            "content": micro_info
        }
        self.update_msg(msg)

    # 尾部添加微 LLM 的 response,后续，要考虑转记忆、压缩等等
    def append_llm_response(self, llm_response):
        msg = {
            "role": "assistant",
            "content": llm_response
        }
        self.update_msg(msg)

    def init_msg(self, user_input):
        msg = {
            "role": "user",
            "content": user_input
        }
        self.update_msg(msg)

    def update_msg(self, msg):
        self.input_to_model_msg.append(msg)

    def get_msg(self):
        return self.input_to_model_msg

    def get_system_prompt(self):
        return self.system_prompt

    def get_skills_meta_data(self):
        return self.skills_meta_data
