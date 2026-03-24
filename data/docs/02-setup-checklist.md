# 实验准备清单

开始实验前，请按下面顺序完成：

1. 创建并激活 `venv`
2. 安装 `requirements.txt` 里的依赖
3. 从 `.env.example` 复制出 `.env`
4. 在 `.env` 中填入可用的 `OPENAI_API_KEY`
5. 如果你使用的是 OpenAI 兼容平台，再补上 `OPENAI_BASE_URL`
6. 运行 `python scripts/prepare_lab.py` 初始化本地 SQLite

建议统一使用 Python 3.11 及以上版本。只要你的环境能创建 `venv`，就不需要先装 conda。

参加 2026-04-18 下午的实验时，建议额外准备下面这些内容：

- 能正常访问模型服务的 API Key
- 一个可以运行 `venv` 的 Python 环境
- 电源适配器
- 你自己的 1 份文本资料，方便课后自己扩展到向量库中

如果时间很紧，优先先跑通“单问单答”，再考虑修改 prompt 或增加表结构。
