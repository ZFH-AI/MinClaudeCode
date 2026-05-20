import re
from pathlib import Path
from typing import Dict, List, Optional
from unittest import result

"""
渐进式加载SKILL
  - 1、元数据层：扫描所有SKILL的name + description
  - 2、完整指令层：加载指定SKILL的完整操作手册
  - 3、资源层：按需读取SKILL目录下的资源文件
"""

# 解析文件，将其
def _parse_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta, match.group(2)


class SkillLoader:
    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        # 元数据
        self._metadata_cache: Optional[List[Dict[str, str]]] = None
        # 完整指令数据
        self._full_content_cache: Dict[str, Optional[str]] = {}

    def _scan_skill_md(self) -> List[Dict[str, str]] | None:
        if self._metadata_cache is not None:
            return self._metadata_cache

        result: List[Dict[str, str]] = []
        # 判断传入的路径是否合法
        if not self.skill_path.exists() or not self.skill_path.is_dir():
            self._metadata_cache = result
            return result

        for skill_path in sorted(self.skill_path.iterdir()):
            if not skill_path.is_dir():
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists() or not skill_md.is_file():
                continue

            try
                content = skill_md.read_text(encoding="utf-8")
                # 按照skill的路径读取skill的内容，将元数据保存在meta中，其他完整信息保存在body中
                meta, body = _parse_frontmatter(content)
                if meta and "name" in meta:
                    result.append({"name": meta["name"], "description": meta["description"]})
            except Exception:
                continue

        self._metadata_cache = result
        return result
