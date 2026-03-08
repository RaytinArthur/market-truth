import argparse
import sys

from config import DEFAULT_TICKER, DEFAULT_DATE
from retriever.context_builder import build_context
from llm.analyst import analyze

def main() -> int:
    # 使用argparse 支持命令行传参
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default=DEFAULT_TICKER, help = "股票代码")
    parser.add_argument("--date", default=DEFAULT_DATE, help="目标日期 YYYY-MM-DD")
    args = parser.parse_args()
    
    # 1. 拼接上下文：股价 + 相关新闻
    try:
        context = build_context(args.ticker, args.date)
    except Exception as e:
        print(f"错误：build_context 失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 10003
    if not context or not str(context).strip():
        print(f"错误：未构造出任何上下文（ticker={args.ticker}, date={args.date}）。", file=sys.stderr)
        return 10004


    # 2. 构造LLM的问题
    question = f"为什么{args.ticker} 在 {args.date}出现股价异动？"

    # 3. 调用LLM 输出分析报告
    context = context[:8000]
    try:
        report = analyze(context, question)
    except Exception as e:
        print(f"错误：analyze 失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 10005

    # 4. 在终端打印结果
    print("=" * 30)
    print(f"Market Truth 分析报告: {args.ticker} @ {args.date}")
    print("=" * 30)
    print(report)
    print("=" * 30)

if __name__ == "__main__":
    raise SystemExit(main())