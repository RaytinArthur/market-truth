import os
from openai import OpenAI
from dotenv import load_dotenv

#加载 .env 环境变量
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("MODEL_NAME")

if not api_key:
    raise ValueError("错误!!：未获取到 OPENAI_API_KEY")
if not base_url:
    print("警告：未检测到 OPENAI_BASE_URL，将默认请求 OpenAI 官方接口。")
if not model_name:
    print("警告：未检测到 MODEL_NAME，将默认使用'gpt-5-mini'")
    model_name = "gpt-5-mini"

#初始化 OpenAI Client
client_kwargs = {"api_key": api_key}
if base_url:
    client_kwargs["base_url"] = base_url
client = OpenAI(**client_kwargs)

# 设定系统prompt， 定义Agent的角色和行为边界
SYSTEM_PROMPT = """
你是一名全球顶尖的金融分析师。你只使用用户提供的【股价异动数据】和【相关新闻】做分析。
要求：
1) 明确区分：事实/推测，并给出置信度(High, Medium-High, Medium, Low-Medium, Low)
2) 如果证据不足，必须输出：信息不足,并说明缺少哪些信息
输出格式：
- 结论：
- 主要证据：
- 简要推测链路：
- 不确定性与缺口：
- 置信度：
""".strip()

def analyze(context:str, question:str) -> str:
    """
    调用大模型进行归因分析
    """
    try:
        response = client.chat.completions.create(
            model = model_name,
            max_completion_tokens=4096,
            messages=[
                {"role":"system", "content":SYSTEM_PROMPT},
                {"role": "user", "content": f"上下文：{context}\n 问题：{question}"}
            ]
        )
        content = response.choices[0].message.content or ""
        finish = getattr(response.choices[0], "finish_reason", None)
        usage = getattr(response, "usage", 0)

        #TODO 后续Week4 换车日志/可观测
        debug_tail = []
        if finish:
            debug_tail.append(f"finish_reason={finish}")
        if usage:
            debug_tail.append(f"tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out (total {usage.total_tokens})")
        
        return content + (f"\n\n[debug]"+", ".join(debug_tail) if debug_tail else "")

    except Exception as e:
        return f"LLM 调用失败，错误信息:{e}"
