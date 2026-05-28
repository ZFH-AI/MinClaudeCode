from typing import List, Dict, Any, Tuple

class MemoryManager:
    def __init__(self,model_context_limit: int = 80000,
                 short_term_window_messages: int = 20,    # 保留最近多少条消息
                 keep_recent_messages: int = 6,           # 摘要后保留多少条原始消息
                 compression_ratio: float = 0.7,     # 达到上下文限制的多少比例时触发压缩
                 llm_client = None):                      # 用于生成摘要的 LLM 客户端
        self.model_context_limit = model_context_limit
        self.short_term_window_messages = short_term_window_messages
        self.keep_recent_messages = keep_recent_messages
        self.compression_threshold = model_context_limit * compression_ratio

        # LLm 客户端
        self.llm_client = llm_client

        # 长期记忆：向量数据库
        self.long_term_memory = LongTermMemory()

    def count_tokens(self, working_messages) -> int:
        total  = 10   # 消息列表开销
        return total


    """将消息列表格式化为文本（用于摘要生成）"""
    @staticmethod
    def _format_messages(self, messages: List[Dict]) -> str:
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def generate_summary(self, working_messages) -> str:
        if not self.llm_client:
            raise RuntimeError("LLM client not provided for summary generation")

        system_prompt ="""
                        请将以下对话历史压缩为结构化摘要，严格遵循以下格式：
                        
                        === 核心任务与目标 ===
                        （用户的核心请求/任务是什么？）
                        
                        === 已完成的步骤 ===
                        1. 步骤描述 | 结果/产出
                        2. ...
                        
                        === 关键决策/结论 ===
                        - 决策1
                        - 决策2
                        
                        === 待办事项 ===
                        - 未完成的任务
                        - 需要继续跟进的内容
                        
                        === 重要上下文 ===
                        （文件路径、代码标识符、配置参数、用户偏好等需要精确保留的信息）
                        """

        user_prompt = f"对话历史：\n{self._format_messages(messages)}"

        response = self.llm_client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], temperature=0.3)

        return response["content"]

    """
    获取处理后的上下文（短期记忆 + 长期记忆）
    1、长期记忆检索（基于用户当前查询）
    2、短期记忆：滑动窗口 + 摘要压缩 + 硬剪裁
    """
    def get_contex(self, working_messages: List[Dict], user_query: str = "") -> List[Dict]:
        # 1、 长期记忆检索
        lt_memories = []
        if user_query:
            lt_memories = self.long_term_memory.retrieve(user_query, top_k=3)

        # 2、短期记忆处理
        # 2.1、 滑动窗口：只保留最近N条信息
        message_len = len(working_messages)
        if message_len > self.short_term_window_messages:
            candidate_messages = working_messages[-self.short_term_window_messages:]
        else:
            candidate_messages = working_messages.copy()

        # 2.2、 检查是否超过压缩阈值
        if self.count_tokens(candidate_messages) > self.compression_threshold:
            # 划分：待压缩部分 + 保留原文部分
            # 确保 keep_recent_messages 不超过 candidate_messages 长度
            keep = min(self.keep_recent_messages, len(candidate_messages))
            to_summarize = candidate_messages[:-keep]
            recent = candidate_messages[-keep:]

            # 生成摘要
            summary = self.generate_summary(to_summarize)

            # 构建新消息列表：历史摘要 + 长期记忆 + 最近消息
            final_messages = [{"role": "system", "content": f"[历史摘要]\n{summary}"}]
        else:
            final_messages = candidate_messages.copy()
            summary, recent = None, None  # 未压缩，无摘要

        # 2.3 注入长期记忆（如果存在）
        if lt_memories:
            memory_text = "\n".join([f"- {mem}" for mem in lt_memories])
            memory_system_msg = {"role": "system", "content": f"[长期记忆]\n{memory_text}"}
            # 将长期记忆插入到摘要之后、最近消息之前
            if summary:
                final_messages.insert(1, memory_system_msg)
            else:
                final_messages.insert(0, memory_system_msg)

        # 2.4 如果有保留的最近消息，追加到 final_messages 末尾
        if summary and recent:
            final_messages.extend(recent)


        # 3、 最终硬裁剪（fallback）
        # 如果构建后的消息仍然超过上下文限制，则截断 recent 中的旧消息
        while self.count_tokens(final_messages) > self.model_context_limit:
            # 找到第一个非 system 的消息（即 recent 中的最旧消息）并移除
            for i, msg in enumerate(final_messages):
                if msg["role"] != "system":
                    final_messages.pop(i)
                    break

        return final_messages

    """将重要信息存入长期记忆（由上层在对话结束后调用）"""
    def store_memory(self, conversation_chunk: List[Dict], summary: str):
        # 简单实现：将摘要整体存入，也可以抽取出关键点
        self.long_term_memory.add_memory(summary)


"""长期记忆：基于 Chroma 向量数据库"""
class LongTermMemory:
    def __init__(self, collection_name: str = "agent_memories", persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        # 使用默认的 all-MiniLM-L6-v2 embedding 函数（轻量）
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        self.counter = 0

    def add_memory(self, memory_text: str, metadata: Optional[Dict] = None):
        """添加一条记忆"""
        self.collection.add(
            documents=[memory_text],
            metadatas=[metadata or {}],
            ids=[f"mem_{self.counter}"]
        )
        self.counter += 1

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """检索与查询最相关的 top_k 条记忆"""
        if self.collection.count() == 0:
            return []
        results = self.collection.query(query_texts=[query], n_results=top_k)
        # results["documents"] 是一个列表的列表，取第一个查询的结果
        documents = results["documents"][0] if results["documents"] else []
        return documents
