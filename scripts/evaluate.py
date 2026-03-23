import json
import asyncio
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

import sys
import os
# 确保能引到外层目录的模块
sys.path.add(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import app as agent_app
from config import OPENAI_API_KEY, OPENAI_BASE_URL, SMALL_MODEL_NAME

# 1. 裁判员配置 (必须结构化输出，拒绝废话)
class EvalResult(BaseModel):
    score: float = Field(..., description="召回率得分：1.0为完美覆盖，0.5为部分覆盖或含噪音，0.0为完全跑偏。")
    reasoning: str = Field(..., description="一句话简述打分理由")

judge_llm = ChatOpenAI(
    model = SMALL_MODEL_NAME,
    temperature=0.1,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
).with_structured_output(EvalResult)

JUDGE_PROMPT = """
你是客观理性的金融归因裁判。请对比【基准答案】和【Agent提取的证据】，评估Agent是否找出了核心原因。
注意：Agent的证据可能是零散的，只要语义覆盖了基准答案的核心逻辑，即可给高分。

【基准答案】:
{expected}

【Agent提取的证据】:
{evidence}
"""

# 核心评测执行引擎
async def evaluate_single_case(case: dict) -> dict:
    ticker = case["ticker"]
    date = case["date"]
    expected = case["expected_reasons"]

    print(f"开始评测：{ticker} @ {date} ... ", end="", flush=True)

    initial_state = {
        "messages": [HumanMessage(content=f"请调查 {ticker} 在 {date} 的股价异动原因。")],
        "step_count": 0,
        "evidence_pool": [],
        "visited_entities": []
    }

    # 直接调用图谱底层引擎，拿到最终的流转结果 (绕过 SSE)
    try:
        final_state = await agent_app.ainvoke(initial_state)
    except Exception as e:
        print(f"运行崩溃： {e}")
        return {"ticker": ticker, "score": 0.0, "steps": 0, "dead_loop": True, "reason": "Graph Execution Failed"}
    
    step_count = final_state.get("step_count", 0)
    is_dead_loop = step_count >= 5
    evidence_pool = final_state.get("evidence_pool", [])

    evidence_text = "\n".join([f"- {e.claim}" for e in evidence_pool]) if evidence_pool else "未提取到任何有效证据"
    # 召唤 LLM 裁判打分
    prompt = JUDGE_PROMPT.format(expected="\n".join(expected), evidence=evidence_text)
    try:
        eval_res = await judge_llm.ainvoke(prompt)
        score = eval_res.score
        reason = eval_res.reasoning
    except Exception as e:
        score = 0.0
        reason = f"裁判打分失败: {e}"
        
    print(f"得分: {score} | 步数: {step_count} | 死循环: {is_dead_loop}")
    
    return {
        "ticker": ticker,
        "score": score,
        "steps": step_count,
        "dead_loop": is_dead_loop,
        "reason": reason
    }

async def run_benchmark():
    # 读取黄金测试集
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_cases.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    print(f"\n🚀 启动批量回归测试，共 {len(cases)} 个 Case\n" + "="*50)
    
    # 并发执行评测 (如果 API 并发有限制，可以改成 for 循环串行)
    tasks = [evaluate_single_case(case) for case in cases]
    results = await asyncio.gather(*tasks)
    
    # 计算统计指标
    total_cases = len(results)
    avg_score = sum(r["score"] for r in results) / total_cases
    avg_steps = sum(r["steps"] for r in results) / total_cases
    dead_loop_rate = sum(1 for r in results if r["dead_loop"]) / total_cases
    
    # 打印最终雷达图
    print("\n" + "="*50)
    print("🏆 Market Truth 评测报告 (Benchmark Report)")
    print("="*50)
    print(f"📊 平均召回率 (Avg Score)  : {avg_score:.2f} / 1.00")
    print(f"⏱️ 平均流转步数 (Avg Steps) : {avg_steps:.1f} 步")
    print(f"💀 死循环率 (Dead-Loop Rate): {dead_loop_rate * 100:.1f} %")
    print("-" * 50)
    
    # 打印低分预警
    for r in results:
        if r["score"] < 0.8 or r["dead_loop"]:
            loop_str = " [🚨死循环]" if r["dead_loop"] else ""
            print(f"⚠️ 预警: {r['ticker']} 得分 {r['score']}{loop_str} -> {r['reason']}")
            
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_benchmark())