from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from settings import MY_BASE_URL, MY_API_KEY, MY_MODEL_NAME

# 初始化模型
model = ChatOpenAI(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个乐于助人的助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | model

store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

chat_chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

# 测试对话
response1 = chat_chain.invoke(
    {"input": "你好，我叫小明。"},
    config={"configurable": {"session_id": "session_local_1"}}
)
print(f"AI: {response1.content}")

response2 = chat_chain.invoke(
    {"input": "我刚才说我是谁？"},
    config={"configurable": {"session_id": "session_local_1"}}
)
print(f"AI: {response2.content}")