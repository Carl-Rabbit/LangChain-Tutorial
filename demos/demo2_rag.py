from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from settings import MY_BASE_URL, MY_API_KEY, MY_MODEL_NAME

# --- 1. 配置 Embedding ---
# 选项 A: 你的 API 服务支持 embedding (例如 Ollama)
embeddings = OpenAIEmbeddings(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME # 或者是专门的 embedding 模型名，如 "nomic-embed-text"
)

# 选项 B: 如果 API 不支持，使用本地 HuggingFace (需要 pip install sentence-transformers)
# from langchain_community.embeddings import HuggingFaceEmbeddings
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# --- 2. 准备数据 ---
simulated_text = """
LangGraph 是 LangChain 的一个扩展库，专门用于构建有状态的、多参与者的应用程序。
它使用图结构（节点和边）来定义循环计算流程。
"""
splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
docs = splitter.create_documents([simulated_text])

# --- 构建索引 ---
vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
retriever = vectorstore.as_retriever()

# --- 构建 RAG 链 ---
template = """基于以下上下文回答问题:
{context}

问题: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

# 使用自定义 Chat 模型
model = ChatOpenAI(
    base_url=MY_BASE_URL,
    api_key=MY_API_KEY,
    model=MY_MODEL_NAME
)

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

print(rag_chain.invoke("LangChain 是什么？"))