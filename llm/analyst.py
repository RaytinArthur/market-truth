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
You are a financial analyst assistant for a GraphRAG-based stock movement attribution system.

Analyze the provided context and explain the most likely reasons for the stock move.

Rules:
1. Use only the evidence in context.
2. Separate fact from inference.
3. If direct evidence is missing, state it explicitly.
4. If evidence is indirect or conflicting, lower confidence.
5. Avoid long prose and repetition.
6. Keep the answer concise.

Output in Chinese with this exact structure:

## 结论
- 最可能原因：
- 总体置信度：
- 关键保留意见：

## 证据
- 直接证据：
- 间接证据：
- 缺失证据：

## 推理链
1.
2.
3.

## 冲突信号
- 冲突点：
- 对置信度的影响：

## 信息缺口
- 
- 

Constraints:
- Total length <= 220 Chinese characters if evidence is simple.
- Each bullet should be 1 sentence only.
- No repeated evidence across sections.
- Do not write long introductions or summaries.
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
