# --- Self-hosted 模型配置 ---
# 你的 API 服务地址，通常以 /v1 结尾
# 例如 Ollama: "http://localhost:11434/v1"
# 例如 vLLM/LM Studio: "http://localhost:8000/v1"
MY_BASE_URL = "https://api.lkeap.cloud.tencent.com/v1" 

# 你的 API Key
# 本地模型通常可以随便填（如 "sk-123"），除非你设置了鉴权
MY_API_KEY = "sk-OuACnvgF0BAoYRWRtmYSiwkhoGIEtOuIVANN4V68DpfvF8LB"

# 你的模型名称
# 必须与你服务中加载的模型名称一致 (如 "llama3", "qwen-72b", "mistral")
MY_MODEL_NAME = "deepseek-v3.2" # 这里替换为你实际的模型名