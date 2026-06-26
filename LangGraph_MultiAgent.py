"""
 使用LangGraph实现多智能协作
"""

import asyncio
from typing import TypedDict,Annotated
import httpx
from httpcore._async import http_proxy
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, content
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from operator import add
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

http_client = httpx.Client(verify=False)

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key="sk-d6545a933eee4b429bd43c198c4026d7",
    base_url="https://api.deepseek.com/v1",
    http_client = http_client,
    temperature = 0.7,
    max_tokens = 1024
)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add]
    type : str

# 定义节点
def supervisor_node(state: State):
    writer = get_stream_writer()
    writer({"node" : ">> supervisor_node"})

    system_prompt = """你是一个专业的客服助手，负责对用户的问题进行分类，并将任务分给其他Agent执行。
                    如果用户的问题是和旅游路线规划相关的，那就返回 travel。
                    如果用户的问题是希望讲一个笑话，那就返回 joke。
                    如果用户的问题是希望对一个对联，那就返回 couplet。
                    如果是其他的问题，返回 other。
                    除了这几个选项外，不要返回任何其他的内容。
                    """

    prompts = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["messages"][0]},
    ]
    # 如果改值存在，则说明已交由其他节点处理
    if "type" in state:
        return {"type": END}
    else:
        response = llm.invoke(prompts)
        writer({"supervisor_node type": f">> {response.content}"})
        if response.content in ["supervisor", "travel", "joke", "couplet"]:
            return {"type": response.content}
        else:
            raise ValueError("type is not in [supervisor, travel, joke, couplet]")

def travel_node(state: State):
    writer = get_stream_writer()
    writer({"node": ">> travel_node"})

    system_prompt = "你是一个专业的旅行规划助手，根据用户问题，生成路线规划，请使用中文回答。"

    prompts = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["messages"][0]},
    ]

    # 使用高德地图的MCP 服务
    client = MultiServerMCPClient(
        {
            "mcpServers": {
                "amap-maps": {
                    "command": "npx",
                    "args": ["-y", "@amap/amap-maps-mcp-server"],
                    "env": {
                        "AMAP_MAPS_API_KEY": "f124e073db66b4384255b42823e1ecdc"
                    }
                }
            }
        }
    )

    tools = asyncio.run(client.get_tools())
    agent = create_agent(
        model=llm,
        tools=tools
    )
    response = agent.ainvoke({"messages": prompts})
    return {"messages":[HumanMessage(content = response["messages"][-1].content)], "type":"travel"}


def joke_node(state: State):
    writer = get_stream_writer()
    writer({"node": ">> joke_node"})

    system_prompt = """你是一个笑话大师，根据用户要求，写一个不超过100个字的笑话"""
    prompts = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["messages"][0]},
    ]

    response = llm.invoke(prompts)

    return {"messages":[HumanMessage(content = response.content)], "type":"joke"}


def couplet_node(state: State):
    writer = get_stream_writer()
    writer({"node": ">> couplet_node"})

    return {"messages":[HumanMessage(content="couplet_node")], "type":"couplet"}


def other_node(state: State):
    writer = get_stream_writer()
    writer({"node": ">> other_node"})

    return {"messages":[HumanMessage(content="我暂时无法回答这个问题")], "type":"other"}

# 路由函数
def routing(state: State):
    writer = get_stream_writer()
    writer({"node": ">> routing"})

    if state["type"] == END:
        return END

    if state["type"] in ["travel", "joke", "couplet"]:
        return  state["type"] + "_node"

    return "other_node"


# 构建图
builder = StateGraph(State)

# 增加节点
builder.add_node("supervisor_node", supervisor_node)
builder.add_node("travel_node", travel_node)
builder.add_node("joke_node", joke_node)
builder.add_node("couplet_node", couplet_node)
builder.add_node("other_node", other_node)

# 增加边
builder.add_edge(START, "supervisor_node")
builder.add_conditional_edges("supervisor_node", routing,["travel_node","joke_node","couplet_node","other_node", END])
builder.add_edge("travel_node", "supervisor_node")
builder.add_edge("joke_node", "supervisor_node")
builder.add_edge("couplet_node", "supervisor_node")
builder.add_edge("other_node", "supervisor_node")

# 构建Graph
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer= checkpointer)

# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    config = {
        "configurable" :{"thread_id":"1"}
    }
    for chunk in graph.stream({"messages":["讲个马三立式的笑话"]}, config, stream_mode="custom"):
        print(chunk)

