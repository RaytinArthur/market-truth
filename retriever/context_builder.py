from concurrent.futures import ThreadPoolExecutor
import contextvars
from datetime import datetime

from config import TOP_K_NEWS
from retriever.fusion import split_hybrid_sections
from retriever.formatter import format_hybrid_context
from retriever.graph_retriever import GraphRetriever
from retriever.stock_retriever import get_stock_anomaly_by_date
from retriever.vector_retriever import VectorRetriever
from utils.latency_tracker import LatencyTracker

def build_context(ticker:str, date:str) -> str:
    """
    Legacy context builder (vector-only).
    Used by existing pipeline.
    """
    stock_info = get_stock_anomaly_by_date(ticker,date)
    query = f"{ticker} news {date}"

    retriever = VectorRetriever()
    news_list = retriever.search_news_by_ticker_and_date(
        query, ticker=ticker,target_date=date, top_k=int(TOP_K_NEWS)
    )

    context = f"""
## STOCK_MOVEMENT
ticker: {ticker}
date: {date}
{stock_info}

## RELATED_NEWS
    """
    if not news_list:
        context += "No relevant news found.\n"
        print("!!!![CONTEXT_BUILDER] 未获取到新闻！！！！")

    for i , news in enumerate(news_list, 1):
        context += f"""
[{i}]
title: {news.get("title", "")}
date: {news.get("date", "")}
publisher: {news.get("publisher", "")}
link: {news.get("link", "")}
"""
    return context


def build_hybrid_context(
    ticker: str,
    date: str,
    vector_results: list[dict] | None = None,
    graph_results: list[dict] | None = None,
    ablation_mode:str | None = None,
) -> str:
    
    tracker = LatencyTracker()
    stock_info = get_stock_anomaly_by_date(ticker, date)

    # 并发获取 Vector 和 Graph 数据
    def fetch_vector():
        if vector_results is not None:
            return vector_results
        tracker.start("vector")
        query = f"{ticker} news {date}"
        res = VectorRetriever().search_news_by_ticker_and_date(
            query, ticker=ticker, target_date=date, top_k=int(TOP_K_NEWS)
        )
        tracker.stop("vector")
        return res
    
    def fetch_graph():
        if graph_results is not None:
            return graph_results
        tracker.start("graph")
        res  = GraphRetriever().retrieve(ticker=ticker,target_date=date)
        tracker.stop("graph")
        return res
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 拷贝当前主线程的上下文
        # 用 ctx.run 包裹你的方法，把上下文“强行注入”给子线程
        f_vector = executor.submit(contextvars.copy_context().run, fetch_vector)
        f_graph = executor.submit(contextvars.copy_context().run, fetch_graph)

        vector_results = f_vector.result()
        graph_results = f_graph.result()

    tracker.start("fusion")
    direct_news, related_news, theme_news = split_hybrid_sections(
        vector_results=vector_results, graph_results=graph_results,
        target_date=date,  direct_top_n=3,  k=20
    )
    tracker.stop("fusion")

    if ablation_mode == "DROP_DIRECT_NEWS":
        direct_news = []
        model_label = "ABLATION_DROP_DIRECT_NEWS"
    else:
        model_label = "HYBRID"

    print(
        f"[CONTEXT_BUILDER] mode={model_label} "
        f"vector_hits={len(vector_results)} "
        f"graph_hits={len(graph_results)} "
        f"direct={len(direct_news)} "
        f"related={len(related_news)} "
        f"themes={len(theme_news)}"
    )

    # 把一切组装工作交给排版层
    return format_hybrid_context(
        ticker=ticker,
        date=date,
        stock_info=stock_info,
        direct_news=direct_news,
        related_news=related_news,
        theme_news=theme_news,
        ablation_mode=ablation_mode
    )
