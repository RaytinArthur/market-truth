# retriever/formatter.py

def format_hybrid_context(
    ticker: str,
    date: str,
    stock_info: str,
    direct_news: list[dict],
    related_news: list[dict],
    theme_news: list[dict],
    ablation_mode: str | None = None,
) -> str:
    """
    负责将结构化的检索结果格式化为 Markdown 字符串，供大模型阅读。
    """
    status_text = "[Status: HYBRID_MODE]"
    ablation_note = ""

    if ablation_mode == "DROP_DIRECT_NEWS":
        status_text = "[Status: ABLATION_DROP_DIRECT_NEWS]"
        ablation_note = (
            "Note: Direct company-specific news has been intentionally removed "
            "for ablation testing. Use only indirect supply-chain / related-company "
            "signals and theme evidence. Lower confidence if evidence is weak.\n"
        )

    context_lines = []
    context_lines.append(f"{status_text}\n")
    context_lines.append(f"## STOCK_MOVEMENT\nticker: {ticker}\ndate: {date}\n{stock_info}\n")
    context_lines.append(f"## Experiment Note\n{ablation_note if ablation_note else 'None'}\n")

    # 1. Direct News
    context_lines.append("## Direct News\n")
    if not direct_news:
        context_lines.append("No direct news found.\n")
    else:
        for i, news in enumerate(direct_news, 1):
            context_lines.append(
                f"[{i}]\n"
                f"title: {news.get('title', '')}\n"
                f"date: {news.get('date', '')}\n"
                f"publisher: {news.get('publisher', '')}\n"
                f"link: {news.get('link', '')}\n"
                f"fused_score: {news.get('fused_score', 0):.4f}\n"
                f"time_bonus: {news.get('time_bonus', 0):.2f}\n"
                f"vector_rank: {news.get('vector_rank')}\n"
                f"graph_rank: {news.get('graph_rank')}\n"
            )

    # 2. Related News (Graph)
    context_lines.append("## Supply Chain / Related Company News\n")
    if not related_news:
        context_lines.append("No related company news found.\n")
    else:
        for i, news in enumerate(related_news, 1):
            context_lines.append(
                f"[{i}]\n"
                f"title: {news.get('title', '')}\n"
                f"date: {news.get('date', '')}\n"
                f"publisher: {news.get('publisher', '')}\n"
                f"company_ticker: {news.get('company_ticker', '')}\n"
                f"relation: {news.get('relation', '')}\n"
                f"path_explanation: {news.get('path_explanation', '')}\n"
                f"fused_score: {news.get('fused_score', 0):.4f}\n"
                f"time_bonus: {news.get('time_bonus', 0):.2f}\n"
                f"vector_rank: {news.get('vector_rank')}\n"
                f"graph_rank: {news.get('graph_rank')}\n"
            )

    # 3. Theme News
    context_lines.append("## Themes / Risk Signals\n")
    if not theme_news:
        context_lines.append("No additional theme/risk news found.\n")
    else:
        for i, news in enumerate(theme_news, 1):
            context_lines.append(
                f"[{i}]\n"
                f"title: {news.get('title', '')}\n"
                f"date: {news.get('date', '')}\n"
                f"publisher: {news.get('publisher', '')}\n"
                f"link: {news.get('link', '')}\n"
                f"fused_score: {news.get('fused_score', 0):.4f}\n"
                f"time_bonus: {news.get('time_bonus', 0):.2f}\n"
                f"vector_rank: {news.get('vector_rank')}\n"
                f"graph_rank: {news.get('graph_rank')}\n"
            )

    return "\n".join(context_lines)