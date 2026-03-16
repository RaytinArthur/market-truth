import os
from dotenv import load_dotenv
from openai import OpenAI

# load env var from .env
load_dotenv()

# init client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

print("正在连接大模型...")

#send req
response = client.chat.completions.create(
    model=os.getenv("MODEL_NAME"),
    messages=[
        {"role": "system", "content": "你是一个极客风格的金融异动归因Agent核心。"},
        {"role": "user", "content": "请用简短的一句话跟我打个招呼，宣布 Market Truth 项目正式启动！"}
    ]
)

# 打印回复
print("🤖 模型回复:", response.choices[0].message.content)