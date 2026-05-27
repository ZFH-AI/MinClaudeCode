import os
from pathlib import Path

""""
 读取系统提示词
Anthropic 的 system 参数接受两种格式
-1、system="You are a helpful assistant."
-2、数组（用于多段系统提示）：system=[{"type": "text", "text": "第一段"}, {"type": "text", "text": "第二段"}]
"""
def load_system_prompt(system_prompt_path: Path):
    system_prompt = None
    if system_prompt_path.exists():
        sys_prompt = system_prompt_path.read_text(encoding="utf-8")
        system_prompt =[{"type": "text", "text": sys_prompt}]
    return system_prompt


# 从 src/config/ 中读取指定文件 fileName
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
