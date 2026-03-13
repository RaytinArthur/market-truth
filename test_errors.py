import os
import json
from llm.analyst import _check_llm_errs
from utils.error_logger import log_error, ErrorType, ERROR_LOG_FILE

def run_test():
    print("开始模拟 Market Truth Agent 运行中的异常情况...\n")

    # 1. 模拟实体对齐失败 (GraphBuilder)
    print("触发 -> 实体对齐失败...")
    log_error(
        error_type=ErrorType.ENTITY_ALIGNMENT_FAILURE,
        query="某未知妖股",
        context="某未知妖股今日暴涨100%，引发市场关注。",
        details={"news_url": "https://finance.example.com/1", "step": "normalizer.normalize"}
    )

    # 2. 模拟图谱证据缺失 (GraphRetriever)
    print("触发 -> 图谱证据缺失...")
    log_error(
        error_type=ErrorType.GRAPH_EVIDENCE_MISSING,
        query="Retrieve Graph Evidence for FAKE_TICKER",
        details={"ticker": "FAKE_TICKER", "target_date": "2026-03-13", "window": 7, "reason": "Cypher query returned 0 matched news nodes."}
    )

    # 3. 模拟大模型幻觉 (Analyst Agent)
    print("触发 -> 大模型幻觉...")
    _check_llm_errs(
        context="无",  # 极短的上下文
        response_text="## 结论\n...\n## 证据\n- 直接证据：财报显示利润翻倍。\n",  # 模型凭空捏造了证据
        question="为什么大涨？"
    )

    # 4. 模拟冲突证据处理错误 (Analyst Agent)
    print("触发 -> 冲突证据处理错误...")
    _check_llm_errs(
        context="新闻A说利好，但新闻B说业绩不及预期，股价暴跌。",  # 包含多个冲突词
        response_text="## 结论\n...\n## 冲突信号\n- 冲突点：无\n",  # 模型未识别出冲突
        question="综合分析走势"
    )

    print("\n✅ 测试打点完毕！现在读取生成的 JSONL 日志文件：\n")
    print("=" * 60)
    
    if os.path.exists(ERROR_LOG_FILE):
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                print(f"[{data['error_type'].upper()}]")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("-" * 60)
    else:
        print("❌ 日志文件未生成，请检查 utils/error_logger.py 中的路径配置。")

if __name__ == "__main__":
    run_test()