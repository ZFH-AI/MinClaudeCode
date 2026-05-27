from typing import Callable, Dict, List
from utility.config_load import get_global_cfg
from pathlib import Path
import json


"""
读取 .src/skills/skill_input_schema.json
    - 记录每个skill的输入格式
    - 读取之后作为工具列表传给LLM
"""
def get_skills_input_schema() -> List[Dict]:
    skills_input_schema = Path(get_global_cfg.base_path.skill_root) /  "skill_input_schema.json"
    try:
        if not skills_input_schema.exists():
            print(f"Skills的输入配置文件不存在：{skills_input_schema}")
            return []
        return json.loads(skills_input_schema.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Error]没有提供Tools的输入格式{e}")
    return []

"""
LLM 的反馈
 - 构建符合 Anthropic API 格式的 assistant 消息
 - content 为数组，可包含 text 和 tool_use 两种类型
"""
def build_assistant_message(text: str, tool_calls: List[Dict]) -> Dict:

    content = []
    if text:
        content.append({"type": "text", "text": text})
    for tool in tool_calls:
        content.append({
            "type": "tool_use",
            "id": tool["id"],
            "name": tool["name"],
            "input": tool["input"]
        })
    return {"role": "assistant", "content": content}


"""
CALL-TOOLS的反馈结果日添加到MSG中
    - 将工具执行结果列表包装为一条 user 消息
    - 每个结果包含 type: "tool_result", tool_use_id, content
"""
def build_tool_result_message(results: List[Dict]) -> Dict:

    content = []
    for res in results:
        # 确保 content 为字符串，限制长度避免超出上下文
        str_content = str(res["content"])[:5000]  # 可配置截断长度
        content.append({
            "type": "tool_result",
            "tool_use_id": res["tool_use_id"],
            "content": str_content
        })
    return {"role": "user", "content": content}
