import os
from typing import Annotated, TypedDict, Literal

# LangChain / LangGraph 相关导入
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

# ==========================================
# 1. 配置部分 (请根据你的 Self-hosted 环境修改)
# ==========================================

from settings import MY_BASE_URL, MY_API_KEY, MY_MODEL_NAME

# ==========================================
# 2. 定义工具与模型
# ==========================================

@tool
def multiply(a: int, b: int) -> int:
    """计算两个整数的乘积。"""
    print(f"\n[系统日志] 正在执行工具 multiply: {a} * {b} ...")
    return a * b

tools = [multiply]

# 初始化模型
llm = ChatOpenAI(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME,
    temperature=0
)

# 绑定工具到模型
llm_with_tools = llm.bind_tools(tools)

# ==========================================
# 3. 构建 LangGraph 图
# ==========================================

# 定义状态：存储消息列表
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 定义节点：AI 思考节点
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 构建图结构
graph_builder = StateGraph(State)

# 添加节点
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))

# 定义边
graph_builder.add_edge(START, "chatbot")

# 条件边：Chatbot 结束后，是去执行工具，还是结束？
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition, 
)

# 工具执行完，必须回到 Chatbot 生成最终回复
graph_builder.add_edge("tools", "chatbot")

# ==========================================
# 4. 设置记忆与中断 (关键步骤)
# ==========================================

# 初始化内存检查点保存器
memory = MemorySaver()

# 编译图：
# - checkpointer: 启用记忆，允许暂停和恢复
# - interrupt_before: 在进入 "tools" 节点之前，强制暂停！
graph = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["tools"]
)

# ==========================================
# 5. 运行流程演示
# ==========================================

def run_interactive_demo():
    # 线程 ID 用于区分不同的对话上下文，也是恢复状态的关键
    thread_config = {"configurable": {"thread_id": "demo-thread-001"}}
    
    # --- 第一阶段：提出问题 ---
    user_input = "帮我计算 42 乘以 3"
    print(f"--- 用户输入: {user_input} ---")
    
    initial_input = {"messages": [HumanMessage(content=user_input)]}
    
    print(">>> AI 开始思考...")
    
    # 运行图。由于设置了 interrupt_before=['tools']，如果 AI 决定调用工具，
    # 它会在 chatbot 节点执行完、tools 节点执行前停下来。
    for event in graph.stream(initial_input, config=thread_config):
        # 这里只打印一下过程，实际暂停是在循环结束后
        for k, v in event.items():
            if "messages" in v:
                last_msg = v["messages"][-1]
                print(f"   (节点 {k}) 生成内容: {last_msg.content if last_msg.content else '[请求调用工具]'}")

    # --- 第二阶段：检查状态 ---
    print("\n>>> 流程已暂停。检查当前状态...")
    snapshot = graph.get_state(thread_config)
    
    # snapshot.next 告诉我们下一个要执行的节点是什么
    if snapshot.next:
        print(f"   下一步计划执行的节点: {snapshot.next}")
    
    # 获取 AI 的最后一条消息，看看它想干什么
    last_message = snapshot.values["messages"][-1]
    
    # 检查是否有工具调用请求
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_call = last_message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        print(f"   [安全审查] AI 申请调用工具: 【{tool_name}】 参数: {tool_args}")
        
        # --- 第三阶段：人类介入 ---
        user_approval = input("\n>>> 是否批准执行？(输入 'y' 继续，其他键取消): ")
        
        if user_approval.lower() == 'y':
            print("\n>>> 已批准。恢复执行中...")
            
            # 传入 None 表示"不添加新消息，直接从断点处继续"
            # 图会执行 tools 节点，然后回到 chatbot 节点
            for event in graph.stream(None, config=thread_config):
                for k, v in event.items():
                    if "messages" in v:
                        print(f"   (节点 {k}) 生成内容: {v['messages'][-1].content}")
            
            print("\n--- 流程结束 ---")
            
        else:
            print(">>> 操作被用户拒绝。流程终止。")
    else:
        print(">>> AI 不需要调用工具，直接给出了回复。")

if __name__ == "__main__":
    try:
        run_interactive_demo()
    except Exception as e:
        print(f"\n[错误] 运行失败: {e}")
        print("请检查：\n1. API 地址是否正确\n2. 模型是否已启动\n3. 模型是否支持 Tool Calling 功能")