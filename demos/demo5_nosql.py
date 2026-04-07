# 1. 首先，安装依赖
# pip install tinydb langchain langchain-openai

from tinydb import TinyDB, Query
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import settings

# 2. 初始化 TinyDB
db = TinyDB("db.json")
User = Query()


@tool
def upsert_user(name: str, age: int, city: str) -> str:
    """
    新增或更新一个用户的信息。
    当需要添加新用户或更新现有用户信息时使用此工具。
    """
    db.upsert({"name": name, "age": age, "city": city}, User.name == name)
    return f"用户 {name} 的信息已成功添加/更新。"


@tool
def get_user_info(name: str) -> str:
    """
    根据用户名获取用户信息。
    """
    result = db.search(User.name == name)
    if result:
        return f"用户信息: {result[0]}"
    else:
        return f"未找到用户 {name}。"


# 3. 初始化模型
llm = ChatOpenAI(
    model=settings.MY_MODEL_NAME,
    temperature=0,
    api_key=settings.MY_API_KEY,
    base_url=settings.MY_BASE_URL,
)

tools = [upsert_user, get_user_info]

# 4. 创建 Agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="你是一个可以管理用户信息的得力助手。"
)


def print_last_message(result: dict):
    messages = result.get("messages", [])
    if messages:
        last_msg = messages[-1]
        print(f"Agent输出: {last_msg.content}")
    else:
        print("Agent输出: 无返回内容")


if __name__ == "__main__":
    chat_history = []

    print("--- 场景1: 添加一个新用户 ---")
    chat_history.append({
        "role": "user",
        "content": "你好，我叫 Carl，今年 30 岁，住在上海。"
    })
    result = agent.invoke({"messages": chat_history})
    print_last_message(result)
    chat_history = result["messages"]

    print("\n--- 场景2: 查询用户信息 ---")
    chat_history.append({
        "role": "user",
        "content": "Carl 的年龄是多少？"
    })
    result = agent.invoke({"messages": chat_history})
    print_last_message(result)
    chat_history = result["messages"]

    print("\n--- 场景3: 更新用户信息 ---")
    chat_history.append({
        "role": "user",
        "content": "哦，不对，我今年其实 31 岁了。"
    })
    result = agent.invoke({"messages": chat_history})
    print_last_message(result)
    chat_history = result["messages"]

    print("\n--- 场景4: 再次查询以确认更新 ---")
    chat_history.append({
        "role": "user",
        "content": "我现在几岁了？"
    })
    result = agent.invoke({"messages": chat_history})
    print_last_message(result)

    db.close()