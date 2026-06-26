# 1、 MinClaudeCode
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

## 2、示例

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
<img width="2316" height="1690" alt="image" src="https://github.com/user-attachments/assets/9ec6b28e-1811-43d5-ac88-3f7d9c250c0b" />


# 3、Memory管理

一个工业级的记忆系统，通常会借鉴认知科学理论，采用分层架构，本 .src/message/memory_mng.py 文件采用的是三层记忆

- 短期记忆 (STM - Working Memory)：就是当前交互的上下文里的内容，负责维持对话的即时连贯性
- 中期记忆/摘要记忆 (MTM - Episodic Summary)：通过将早期的对话历史压缩成摘要，来替代简单粗暴的截断，保留关键信息
- 长期记忆 (LTM - Long-term Memory)：这是一个跨会话的持久化存储，用于保存用户的偏好、项目决策等重要知

**短期记忆：滑动窗口 + 智能压缩**
- 维护一个固定大小的滑动窗口，比如保留最近的 10-30 轮对话，当超过窗口大小时，则只报最近的窗口大小的消息
- 智能压缩：当有效窗口 Token 超过预设阈值时，不要简单地删除，而是触发摘要压缩

  1、调用LLM生成摘要：将窗口之外的历史记录压缩成一段摘要文本

  2、替换历史消息：用一个system或assistant角色的消息（内容为“历史摘要：... ”）替换掉被压缩的原始消息

**长期记忆：向量语义存储+智能注入**
- 存储层 (Storage Layer)：包含原始事件日志（完整记录所有交互）和结构化记忆（从日志中提取的关键信息）。对于后者，可以用 SQLite 存储关键词，同时生成 Embedding 存入向量数据库（如 Chroma、Qdrant）供语义检索
- 操作层 (Operation Layer)：包含记忆抽取器（分析对话，决策是否提取记忆）和检索注入器（在每次请求前检索相关记忆）

## 3.1 本项目中的记忆管理


```shell
four-layer compression pipeline so the agent can work forever

   Every Turn:
   +----------------------------+
   | User + Tool call result    |
   +----------------------------+
            |
            V
    Layer 0 : Micro_compact (silent every turn)
    +---------------------------------------------------------------------+
    | replace non-read_file tool_result content older                     |
    | than keep_recent_tool_results with "[Previous: used {tool_name}]"   |
    +---------------------------------------------------------------------+
            |
            V
    +--------------------------------------------------------------------+
    | Only retain the most recent N rounds of conversation.              |
    | Early messages that exceed the window are directly discarded       |
    |                                                                    |
    | Check: SlidingWindowMemory  > short_term_window_messages ?         |
    +--------------------------------------------------------------------+
        |                                      |
        no                                     yes
        |                                      |
        V                                      V
    continue                      Layer1 ： Sliding Window
+------------+                    +----------------------------------------------+
| messages   |                    | messages[-self.short_term_window_messages:]  |
+------------+                    +----------------------------------------------+
                                                |
                                                |
                                                V
                                  +-------------------------------------------------------+
                                  | Check used token and token_limit                      |
                                  | user_token > model_context_limit * compression_ratio  |
                                  +-------------------------------------------------------+
                                                |
                                                |
                                                V
                                   Layer 2 : auto_compact
                                    +------------------------------------------------------------------------+
                                    |    keep = min(self.keep_recent_messages, len(candidate_messages))      |
                                    |    to_summarize = candidate_messages[:-keep]                           |
                                    |    recent = candidate_messages[-keep:]                                 |
                                    |                                                                        |
                                    |    Ask LLM to summerize  to_summarize  conversation                    |
                                    |    Replace all message with [summaey]                                  |
                                    |                                                                        |
                                    |   recent: Retain the original text portion.                            |
                                    +------------------------------------------------------------------------+
                                                       |
                                                       V
                                   +-------------------------------------------------------+
                                   | Inject into long-term memory.                         |
                                   |                                                       |
                                   +-------------------------------------------------------+
                                                       |
                                                       |
                                                       V
                                  +-------------------------------------------------------+
                                  | Check used token and token_limit                      |
                                  | user_token > model_context_limit                      |
                                  +-------------------------------------------------------+
                                                       |
                                                       |
                                                       V
                                    Layer 3: compact tool
                                    +-------------------------------------------------+
                                    | Final hard cropping                             |
                                    |                                                 |
                                    +-------------------------------------------------+
                  
Key insight :"The agent can forget strategically and keep working forever"
             
```

## 3.2、六维度记忆架构

- **休眠重塑**

  1、AutoDream 自动整理
  
- **摘要记忆**

  1、Session Memory 压缩机制
  
- **长期记忆**

  1、memdir 分层知识库

     /.claude/memory/

        user / 用户画像

        feedback / 行为反馈

        project / 项目上下文

        reference / 外部引用

     MEMORY.md  全局索引，自动维护
  
- **工作记忆**

   1、当前正在执行的任务

- **短期记忆**
  
  1、完整对话历史，零压缩

- **指令记忆**

  1、4层级优先加载
  
       1）、etc/.../CLAUDE.md  组织策略
  
       2）、/.claude/CLAUDE.md  个人偏好
  
       3）、./CLAUDE.md   团队共享
  
       4)、CLAUDE.local.md    私有本地


上述的完整记忆体系解决的核心问题：1、上下文遗忘；2、多终端同步；3、Token预算控制
https://www.tgltommy.com
https://github.com/ultraworkers/claw-code
### 指令记忆 CLAUDE.md体系

