

# 2、Agent记忆系统的模式
## 2.1、AI Agent记忆系统进化论：从上下文堆砌到智能记忆管理 
链接：https://developer.baidu.com/article/detail.html?id=6986045

主要观点：借鉴认知系统提供借鉴模型
- 感觉记忆（0.5-3秒）对应Agent的实时输入缓冲区
- 工作记忆（20-30秒）通过注意力机制处理的当前上下文
- 长时记忆（持久化存储）结构化知识库与经验沉淀


  
## 2.2、给Agent装上“海马体”！上海AILab开源MemVerse，定义多模态记忆新范式
链接：https://developer.baidu.com/article/detail.html?id=6986045

主要观点：三层仿生记忆架构，模拟了人类信息从暂存、结构化到内化的完整认知过程
- 中央协调器（Orchestrator）作为系统的前额叶，它主动感知交互情景，智能决策记忆的读取、写入与更新，并动态调度不同记忆模块。这改变了传统Agent被动查询数据库的模式。
- 短期记忆（STM）：采用滑动窗口机制，像“工作记忆”一样保持对话的即时连贯性，确保智能体不会“忘了上一句说了什么”
- 长期记忆（LTM）：构建多模态知识图谱，将记忆结构化为核心记忆（用户画像）、情景记忆（事件时间线）和语义记忆（抽象概念）。这使智能体能进行深度的关联推理，从根本上缓解“幻觉”问题
- 参数化记忆与周期性蒸馏：这是MemVerse的高效来源。系统会定期将长期记忆中的高价值知识，通过轻量微调“蒸馏”到一个专用的小模型中，实现知识的参数化内化。相当于让智能体将常用知识转化为“肌肉记忆”，检索响应速度提升10倍以上，解决了结构化存储的性能瓶颈


## 2.3、Claude Code Context Window: Limits, Compaction, and How to Manage It
链接：https://www.morphllm.com/claude-code-context-window

### 1、Claude Code 20万窗口的分配
Claude Code's 200K tokens are not all yours. The window is shared across every component the agent needs to function. Run /context in any Claude Code session to see the exact breakdown.
| Component | Tokens | % of Window | Notes |
| :--| :--:|:--:|:--:|
|System prompt |  ~2,600	| 1.3% |  Base instructions for the agent|
|System tools |  ~17,600	 |  8.8% | Read, Write, Bash, Grep, etc.|
|MCP tools | 900-51,000  | 0.5-25%	| Varies wildly by server count|
|Custom agents |   ~935 |  0.5%	        | Subagent definitions|
| Memory files	           |  ~302	       |  0.2%	        | CLAUDE.md content|
| Autocompact buffer       | 	~33,000	     |  16.5%	        | Reserved for compaction process
| Free for conversation    |	~114,000	   |  57%	          | What you actually get to use

### 2、自动压缩实现原理
当 Claude Code 接近上下文限制时，它会运行自动压缩功能：这是一个自动过程，用于汇总对话历史记录以释放空间。这可以确保会话无限期运行而不会崩溃，但这种汇总是有损的
- 1、Tool outputs cleared first. Old file reads, grep results, and bash outputs are removed or truncated. These are the largest and least valuable tokens in a long session.

  首先清除工具输出。旧的文件读取记录、grep 结果和 bash 输出会被移除或截断。这些是长时间会话中最大且价值最低的记录
- 2、Conversation summarized. The full conversation history gets condensed into a structured summary: what was completed, what is in progress, what files were modified.

  对话总结。完整的对话历史记录将被浓缩成结构化的摘要：已完成的内容、正在进行的内容、修改了哪些文件
- 3、Session restarts with summary. The compacted summary becomes the new context baseline. The agent continues from there.

  会话以摘要形式重新启动。精简后的摘要将成为新的上下文基线。代理程序将从此处继续执行

### 3、自动压缩的触发时机
Older versions of Claude Code waited until 90%+ capacity to compact. Current versions trigger much earlier, at 64-75% capacity. Anthropic's engineers built in a completion buffer so the agent has enough room to finish its current task before compaction interrupts.

| Dimension	| Auto-Compact	| Manual /compact |
| :-- |:--:|:--:|
|Trigger	|Automatic at 64-75% capacity	|You decide when|
|Timing	|Can interrupt mid-task	|You pick a clean break point|
|Preservation	|Generic summary	|Custom: '/compact preserve file paths and error codes'|
|Risk	|May lose critical details	|You control what matters|

### 4、隐藏的上下文损耗：MCP 工具和工具定义
现在，当 MCP 工具占用的上下文资源超过 10% 时，Claude Code 会自动启用工具搜索功能。工具搜索功能不会预先加载所有工具模式，而是延迟加载工具定义，并在需要时才加载。在一次基准测试中，这使得 MCP 令牌开销从 51K 减少到 8.5K，总上下文资源使用量降低了 46.9%

其他隐藏的消耗
- 1、大文件读取：
读取一个 400 行的文件会消耗数千个标记。使用 `--lines` 参数或指定范围可以只读取相关部分。定向读取比读取整个文件节省 70% 的标记

- 2、详细命令输出：
输出数百行信息的 Bash 命令（例如 npm install、测试运行器、构建日志）会迅速填充上下文。在将结果返回给代理之前，请使用 tail 或 grep 命令进行处理。

- 3、累积对话：
每条信息，包括你的一字确认，都会保持上下文关联。长时间的来回沟通会积累成千上万条低效的对话，从而稀释重要的信息。

### 5、管理 Claude 代码上下文的七种策略
- 1、 **将持久化指令放入到CLAUDE.md文件中** CLAUDE.md 是一个特殊文件，Claude Code 会在每次会话开始时读取该文件，并在每次压缩周期中保留它。它是存放必须在整个会话期间保留的指令的唯一可靠位置。请将您的编码规范、项目结构、关键文件路径、常用命令和工作流程规则放在这里

  CLAUDE.md 文件应控制在 200 行以内，2000 个标记以内。它会在每次请求时加载到上下文中，因此臃肿的 CLAUDE.md 文件会占用额外的窗口资源。编写时应面向模型，而非面向人类：简洁、结构化、具体。

- 2、**在不同任务之间使用 /clear** 当你完成一项功能的实现并开始调试其他无关任务时，运行以下命令/clear。这将完全重置上下文窗口。第一个任务的上下文对于第二个任务来说完全是噪声
- 3、**在逻辑断点处手动压缩** 不要等待自动压缩。完成一项功能、修复一个错误或达到任何自然停止点后，请/compact使用自定义的保存指令运行。此时上下文干净，因此生成的摘要质量会更高
- 4、**将高输出任务委派给子代理** 每个子代理（通过任务工具）都拥有自己独立的 200K 上下文窗口。在子代理中运行测试、获取文档、处理日志文件或搜索大型代码库，都会将冗长的输出限制在子代理内部。只有相关的摘要会返回到您的主对话中。

  最多可同时运行 10 个子代理。对于复杂任务，三个并行运行的子代理即可提供 60 万个有效上下文令牌，而不会污染主会话
- 5、**禁用未使用的 MCP 服务器** 行命令/context查看哪些 MCP 服务器正在消耗令牌。如果您在当前会话中未使用某个服务器的工具，请将其禁用。每个被禁用的服务器都会释放其全部模式空间，通常为 2,000 到 10,000 个令牌。
- 6、**使用目标文件读取** 与其读取整个文件，不如指定行范围。Read lines 40-90 of src/api/handler.ts这样使用的代码标记数量远少于读取全部 500 行。这对于调试循环中的重复读取尤为重要，因为在调试循环中，代理会多次重新读取同一个文件。
- 7、**使用 Morph Compact 压缩工具输出** 上下文压缩会在工具输出进入主对话之前对其进行缩减。例如，原本读取一个包含 5000 个标记的文件会占用 2.5% 的上下文空间，而压缩后则将其减少到 1500-2500 个标记，同时保留代理所需的确切代码、文件路径和错误消息。
