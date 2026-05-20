"""
Agent 与 Mode交互时，Message的管理模块

"""
from pathlib import Path
import os
from utility.skill_load import get_skill_loader

# 读取system prompt 的markdown文件 + 读取skill的markdown文件（如果有）
# 将读取的内容作为 system prompt 以供LLM使用
def load_system_prompt() -> list[dict]:
    md_path = Path(__file__).with_name("sys_prompt.md")
    base_prompt = ""
    if md_path.exists():
        base_prompt = md_path.read_text(encoding="utf-8")

    # 追加 L1 技能清单（如果有）
    skill_loader = get_skill_loader()
    skills_section = skill_loader.format_skills_prompt()
    if skills_section:
        base_prompt = base_prompt + "\n\n" + skills_section

    return [{"role": "system", "content": base_prompt}]

# 读取 MinClaude.md 作为上下文注入
def load_context(filename:str) -> dict[str,str]:
    try:
        # 从 src/config/fileName
        project_root = Path(__file__).resolve().parent.parent
        config_path = os.path.join(str(project_root), "config", filename)

        if not os.path.exists(config_path):
            return {"role": "user", "content": ""}

        with open(config_path, "r", encoding="utf-8") as f:
            project_context = f.read()
            context_msg = {
                "role": "user",
                "content": f"[项目上下文]\n{project_context}"
            }
            return context_msg
    except (OSError, UnicodeDecodeError) as e:
        # 可选：打印警告，但不阻断主流程
        print(f"[warn] 加载 {filename} 失败: {e}")
        return {"role": "user", "content": ""}

class Messages:
    def __init__(self):
        # 1、从同目录加载 sys_prompt.md + skill 作为系统提示词
        self.input_to_model_msg = load_system_prompt()

        # 2、注入项目上下文（放在系统提示词之后、用户输入之前）
        project_context = load_context("MinClaudeCode.md")
        self.update_msg(project_context)

        # 3、注入目录树缓存（放在项目上下文之后、用户输入之前）
        tree_cache = load_context(".tree_cache.md")
        self.update_msg(tree_cache)

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
        if msg["content"] is not None:
            self.input_to_model_msg.append(msg)

    def get_msg(self):
        return self.input_to_model_msg
