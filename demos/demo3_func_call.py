from typing import Annotated, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from settings import MY_BASE_URL, MY_API_KEY, MY_MODEL_NAME

# 1. 定义工具
@tool
def multiply(a: int, b: int) -> int:
    """计算两个数字的乘积。"""
    return a * b

tools = [multiply]

# 2. 初始化支持工具调用的自定义模型
llm = ChatOpenAI(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME,
    temperature=0
)
llm_with_tools = llm.bind_tools(tools)

# 3. 定义状态
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 4. 定义节点
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 5. 构建图
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

graph = graph_builder.compile()

# 图结构可视化
graph.get_graph().draw_mermaid_png(output_file_path="graph.png")

# 6. 运行
# 注意：如果模型不支持 function calling，它可能会直接用自然语言回复"结果是60"，而不是触发工具
print("--- 开始 Agent 对话 ---")
event = graph.invoke({"messages": [("user", "15 乘以 4 等于多少？")]})
# event = graph.invoke({"messages": [("user", "15 除以 4 等于多少？")]})
for msg in event["messages"]:
    print(f"[{msg.type}]: {msg.content}")