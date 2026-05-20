import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from utility.config_load import get_global_cfg
"""
渐进式加载SKILL
  - 1、元数据层：扫描所有SKILL的name + description
  - 2、完整指令层：加载指定SKILL的完整操作手册
  - 3、资源层：按需读取SKILL目录下的资源文件
"""

# 解析文件，将其
def _parse_frontmatter(text: str) -> dict[Any, Any]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {}

    meta = {}
    for line in match.group(1).strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta


class SkillLoader:
    def __init__(self, skill_path: Path):
        self.skill_path = Path(skill_path)
        # 元数据
        self._metadata_cache: Optional[List[Dict[str, str]]] = None
        # 完整指令数据
        self._full_content_cache: Dict[str, Optional[str]] = {}

    # 1、加载SKILL的元数据
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

            try:
                content = skill_md.read_text(encoding="utf-8")
                # 按照skill的路径读取skill的内容，将元数据保存在meta中，其他完整信息保存在body中
                meta = _parse_frontmatter(content)
                if meta and "name" in meta:
                    result.append({"name": meta["name"], "description": meta["description"]})
            except Exception:
                continue

        self._metadata_cache = result
        return result

    # 2、加载SKILL 完整指令层
    def load_full_content(self, skill_name: str) -> Optional[str]:
        if skill_name in self._full_content_cache:
            return self._full_content_cache[skill_name]

        skill_md = self.skill_path / skill_name / "SKILL.md"
        if not skill_md.exists() or not skill_md.is_file():
            self._full_content_cache[skill_name] = None
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
            body = re.sub(
                r'^---\s*\n.*?\n---\s*\n', '', content, count=1, flags=re.DOTALL
            )
            self._full_content_cache[skill_name] = body.strip()

        except Exception:
            self._full_content_cache[skill_name] = None

        return self._full_content_cache[skill_name]

    # 3、加载资源层
    def load_resource(self, skill_name: str, relative_path: str) -> Optional[str]:
        try:
            skill_dir = (self.skill_path / skill_name).resolve()
            resource_path = (skill_dir / relative_path).resolve()
            # 安全检查：防止路径遍历攻击（Python 3.9+）
            if not resource_path.is_relative_to(skill_dir):
                return None
        except Exception:
            return None

        if not resource_path.exists() or not resource_path.is_file():
            return None

        try:
            return resource_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    # 提供对外函数
    def get_metadata(self) -> List[Dict[str, str]] | None:
       return self._scan_skill_md()

    def format_skill_to_prompt(self) -> str:
        metadate = self._scan_skill_md()
        if not metadate:
            return ""

        lines = [
            "## Installed Skills (L1 Metadata)",
            """当用户请求匹配以下任一技能时，你**必须首先调用 `<use_skill name="技能名"/>` 加载完整指令，
            然后严格按照返回的内容执行。禁止凭记忆或自行发挥。
            如果技能加载失败（系统返回包含 `[CRITICAL ERROR]` 的错误信息），你必须立即输出 `<done>` 并停止，不得以任何方式继续处理。""",
        ]
        for meta in metadate:
            lines.append(f"- **{meta['name']}**: {meta['description']}")
        lines.append("")
        lines.append("*(完整技能指令在匹配后自动加载)*")

        return "\n".join(lines)

#  全局获取 SkillLoader 单例，确保整个进程共用一个实例
_skill_loader: Optional[SkillLoader] = None
def get_skill_loader() -> SkillLoader | None:
    global _skill_loader
    if _skill_loader is None:
        skill_root = Path(get_global_cfg.base_path.skill_root) / "skill"
        _skill_loader = SkillLoader(skill_root)
    return _skill_loader
