---
name: read_file
description: "读取指定路径的文件内容。支持文本文件，可指定编码、起始偏移量和读取长度。适用于查看代码、日志、配置文件等场景。"
input_schema:
  type: object
  properties:
    file_path:
      type: string
      description: "目标文件的绝对路径或相对于工作区根目录的路径。例如: \"src/main.py\" 或 \"/var/log/app.log\""
    encoding:
      type: string
      description: "文件编码，默认为 utf-8"
      default: "utf-8"
    offset:
      type: integer
      description: "从文件开头的字节偏移量（非字符数），从0开始。用于读取大文件的部分内容。默认0"
      default: 0
      minimum: 0
    length:
      type: integer
      description: "最多读取的字节数（非字符数）。不指定则读取至文件末尾。"
      nullable: true
      minimum: 1
  required:
    - file_path
---

# 读文件工具详细说明

## 功能
安全地读取本地文件系统中的文本文件内容。适用于查看源代码、读取日志、加载配置等任务。

## 执行逻辑
1. 解析 `file_path`，确保路径合法且不包含路径穿越风险（如 `../`）。
2. 检查文件是否存在且为普通文件（非目录）。
3. 按 `encoding` 指定的编码打开文件。
4. 如果指定了 `offset` 和 `length`，则使用字节偏移读取（注意：对于 UTF-8 等多字节编码，偏移可能切分字符，此时会降级为重新从字符边界开始）。
5. 返回文件内容（字符串），如果文件过大则建议使用 `offset`/`length` 分段读取。

## 错误处理
- 文件不存在：返回 `[ERROR: 文件不存在]`
- 路径非法或受保护：返回 `[ERROR: 路径被拒绝]`
- 权限不足：返回 `[ERROR: 无法读取，权限被拒绝]`
- 编码错误：返回 `[ERROR: 编码错误，详情...]`
- 偏移量超出文件大小：返回 `[ERROR: 偏移量超出文件长度]`

## 示例
用户请求：“读取当前目录下的 config.json”
模型应调用：
```json
{
  "name": "read_file",
  "input": {
    "file_path": "config.json",
    "encoding": "utf-8"
  }
}
