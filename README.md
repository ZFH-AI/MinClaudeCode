# MinClaudeCode
记录AI Agent的学习历程和学习心得，仿写0.0.0版的ClaudeCode
## 目录介绍
```shell
MinClaudeCode
|
|-- log  -- 日志记录
|
|-- spec -- 需求文档说明书
|
|-- src
|   |-- cmdLine  --> Agent的启动和打印输出目录
|   |
|   |-- config   --> 项目的主配置目录
|   |
|   |-- llm      --> Agent实现和与LLM交互的目录
|   |
|   |-- message  --> 与LLM交互的上下文管理
|   |
|   |-- output   ---> 输出保存目录
|   |
|   |-- skills   ---> skill加载目录
|   |
|   |-- utility  ---> 辅助工具目录
|
|__ main.py   -- 主程序
```

## 示例

```shell
将 src/config/config.yaml文件

# 模型类型
DeepSeek:
  api_key: "sk-xx"

在运行时需要将这里修改为自己申请的API-KEY
```



运行 python main.py
```shell
➤ You: (): 写个网页注册界面

👤 You 2026-05-27 15:43:34
┌───────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  写个网页注册界面                                                         │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘

    ✓ Wrote 12132 bytes

✅ LLM 未调用工具，任务自动结束。
```
