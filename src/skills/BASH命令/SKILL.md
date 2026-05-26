---
name: bash
description: "执行 Bash 命令并返回输出。支持设置工作目录、超时和环境变量。适用于运行脚本、编译代码、安装依赖、文件操作等任务。"
input_schema:
  type: object
  properties:
    command:
      type: string
      description: "要执行的 Bash 命令，例如 'ls -la' 或 'python script.py'。支持多行命令（用 \\n 分隔）。"
  required: 
   - command
---


# Bash 命令执行技能详细说明

## 功能
在隔离的子进程中执行任意 Bash 命令，实时捕获输出。适用于运行测试、执行构建脚本、管理文件、调用 CLI 工具等。

## 执行逻辑
1. 解析 `command`，检查是否包含危险操作（如 `rm -rf /`，根据安全策略可阻止）。
2. 切换到 `work_dir`（如不存在则报错）。
3. 合并 `env_vars` 到当前环境变量（若变量中包含 `$PATH`，会进行替换）。
4. 使用 `subprocess.Popen` 启动命令，设置 `timeout` 秒。
5. 实时读取 stdout/stderr，若 `capture_output` 为 True 则记录完整输出。
6. 等待进程结束，返回输出内容和退出码（0 表示成功）。

## 错误处理
- 命令不存在或无法执行 → 返回 `[ERROR: 命令未找到]`
- 超时 → 返回 `[ERROR: 命令执行超时（超过 {timeout} 秒）]`
- 工作目录不存在 → `[ERROR: 工作目录不存在]`
- 被安全策略拦截（如 `rm -rf /*`）→ `[ERROR: 命令被安全策略拒绝]`

## 输出格式
正常返回：
