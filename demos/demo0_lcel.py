
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from settings import MY_BASE_URL, MY_API_KEY, MY_MODEL_NAME

# 1. 定义模型 (连接到 Self-hosted API)
model = ChatOpenAI(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME,
    temperature=0.7
)

# 2. 定义提示词模板
prompt = ChatPromptTemplate.from_template("请用一句话通过{topic}这个主题讲一个笑话。")

# 3. 定义输出解析器
parser = StrOutputParser()

# 4. 构建链
chain = prompt | model | parser

# 5. 调用
try:
    result = chain.invoke({"topic": "程序员"})
    print(f"输出结果: {result}")
except Exception as e:
    print(f"连接错误，请检查 URL 和模型名称: {e}")