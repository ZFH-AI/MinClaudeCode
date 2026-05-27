---
name: edit_file
description: "在文件中查找并替换指定的文本内容。支持精确字符串替换，可选择正则表达式模式。适用于修复错误、批量替换、更新配置等场景。"
---

# 编辑文件工具详细说明

## 功能
对单个文件进行文本替换编辑。支持精确匹配或正则表达式匹配，可控制替换次数，修改前可选择性备份。所有操作在内存中完成替换后统一写回文件。

## 执行逻辑
1. 验证 `path` 合法性（拒绝路径穿越如 `../`）。
2. 读取文件内容（按 `encoding`）。
3. 如果 `backup` 为 true，备份原文件为 `path.bak`（若已存在则覆盖）。
4. 执行替换：
   - 若 `use_regex` 为 true，使用 `re.sub(old_text, new_text, content, count=count if count>0 else 0)`
   - 否则使用 `content.replace(old_text, new_text, count if count>0 else -1)`
5. 将替换后的内容写回原文件。
6. 返回替换结果（成功替换次数或错误信息）。

## 错误处理
- 文件不存在 → `[ERROR: 文件不存在]`
- 正则表达式编译错误 → `[ERROR: 无效的正则表达式: ...]`
- 权限不足 → `[ERROR: 无法写入文件，权限被拒绝]`

## 示例

### 基础用法（精确替换）
用户请求：“将 README.md 中的 'foo' 全部替换为 'bar'”
模型调用：
```json
{
  "name": "edit_file",
  "input": {
    "path": "README.md",
    "old_text": "foo",
    "new_text": "bar"
  }
}
