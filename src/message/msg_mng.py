"""
Agent 与 Mode交互时，Message的管理模块

"""
from pathlib import Path
import os
from utility.skill_load import get_skill_loader

""""
 读取系统提示词
Anthropic 的 system 参数接受两种格式
-1、system="You are a helpful assistant."
-2、数组（用于多段系统提示）：system=[{"type": "text", "text": "第一段"}, {"type": "text", "text": "第二段"}]
"""
def load_system_prompt():
    system_prompt = None
    md_path = Path(__file__).with_name("sys_prompt.md")
    if md_path.exists():
        sys_prompt = md_path.read_text(encoding="utf-8")
        system_prompt =[{"type": "text", "text": sys_prompt}]

    return system_prompt

# 读取src/skill目录下的所有 SKILLS的meta data数据
def load_skills_meta_data():
    skill_meta_data = None
    skill_loader = get_skill_loader()
    if skill_loader is not None:
        skill_meta_data = skill_loader.get_metadata()

    return skill_meta_data


# 从 src/config/中读取指定文件 fileName
def load_context(filename:str, prefix_str:str) -> dict[str,str]:
    try:
        project_root = Path(__file__).resolve().parent.parent
        config_path = os.path.join(str(project_root), "config", filename)

        if not os.path.exists(config_path):
            return {"role": "user", "content": ""}

        with open(config_path, "r", encoding="utf-8") as f:
            project_context = f.read()
            context_msg = {
                "role": "user",
                "content": f"[{prefix_str}]\n{project_context}"
            }
            return context_msg
    except (OSError, UnicodeDecodeError) as e:
        print(f"[warn] 加载 {filename} 失败: {e}")
        return {"role": "user", "content": ""}

class Messages:
    def __init__(self):
        # 用户输入
        self.input_to_model_msg = []

        # 1、加载 system prompt
        self.system_prompt = load_system_prompt()

        # 2、加载 skills 的元数据
        self.skills_meta_data = load_skills_meta_data()

        # 3、注入项目上下文
        self.project_context = load_context("MinClaudeCode.md", "项目上下文")
        self.update_msg(self.project_context)

        # 4、注入目录树缓存（放在项目上下文之后）
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

    def get_skills_meta_data(self):
        return self.skills_meta_data

    def get_system_prompt(self):
        return self.system_prompt
