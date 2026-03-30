from concurrent.futures import ThreadPoolExecutor
import contextvars
from datetime import datetime

from config import TOP_K_NEWS
from retriever.graph_retriever import GraphRetriever
from retriever.stock_retriever import get_stock_anomaly_by_date
from retriever.vector_retriever import VectorRetriever
from utils.latency_tracker import LatencyTracker

# 返回新闻的 标题+日期 tuple
def _normalize_news_key(news: dict) -> tuple[str, str]:
    title = (
        news.get("title")
        or news.get("news_title")
        or ""
    ).strip().lower()
    date = (
        news.get("date")
        or news.get("news_date")
        or ""
    ).strip().lower()
    return title, date

# 计算时间bonus，相差日期越小， bonus越大
def _compute_time_bonus(news_date: str, target_date:str) -> float:
    """
    Time bonus should stay much smaller than the RRF main body
    """
    if not news_date or not target_date:
        return 0.0
    
    try:
        d1 = datetime.strptime(news_date, "%Y-%m-%d")
        d2 = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        return 0.0
    
    day_diff = abs((d1-d2).days)

    if day_diff == 0:
        return 0.01
    if day_diff <= 1:
        return 0.005
    if day_diff <= 3:
        return 0.002
    return 0.0

# 返回 vector 和 graph分别的结果
# 每个结果，都是{[新闻]:排名, [新闻]:排名...}
def _build_rank_maps(
    deduped_vector: list[dict],
    deduped_graph: list[dict],
) -> tuple[dict[tuple[str,str], int], dict[tuple[str, str], int]]:

    vector_rank_map = {
        _normalize_news_key(news): rank
        for rank, news in enumerate(deduped_vector, start = 1)
    }

    graph_rank_map = {
        _normalize_news_key(news): rank
        for rank, news in enumerate(deduped_graph, start=1)
    }

    return vector_rank_map, graph_rank_map

def _fuse_hybrid_results (
    vector_results: list[dict],
    graph_results: list[dict],
    target_date: str,
    k:int = 20,
) -> list[dict]:
    """
    Fuse vector + graph candidts with 
    score = RRF(vector+graph) + time_bonus
    """
    deduped_vector = _dedup_news(vector_results, title_key="title", date_key="date")
    deduped_graph = _dedup_news(graph_results, title_key="news_title", date_key="news_date")

    vector_rank_map, graph_rank_map = _build_rank_maps(deduped_vector, deduped_graph)

    merged_by_key: dict[tuple[str, str], dict] = {}

    for news in deduped_vector:
        key = _normalize_news_key(news)
        merged_by_key[key] = {
            "title": news.get("title", ""),
            "date": news.get("date", ""),
            "publisher": news.get("publisher", ""),
            "link": news.get("link", ""),
            "company_ticker": "",
            "relation": "",
            "path_explanation": "",
            "from_vector": True,
            "from_graph": False,
            "raw_vector": news,
            "raw_graph": None,
        }

    for news in deduped_graph:
        key = _normalize_news_key(news)

        if key not in merged_by_key:
            merged_by_key[key] = {
                "title": news.get("news_title", news.get("title", "")),
                "date": news.get("news_date", news.get("date", "")),
                "publisher": news.get("publisher", ""),
                "link": news.get("link", ""),
                "company_ticker": news.get("company_ticker", ""),
                "relation": news.get("relation_type", ""),
                "path_explanation": news.get("path_explanation", ""),
                "from_vector": False,
                "from_graph": True,
                "raw_vector": None,
                "raw_graph": news,
            }
        else:
            # 将graph的信息带入
            merged_by_key[key]["from_graph"] = True
            merged_by_key[key]["raw_graph"] = news

            if not merged_by_key[key].get("company_ticker"):
                merged_by_key[key]["company_ticker"] = news.get("company_ticker", "")
            if not merged_by_key[key].get("relation"):
                merged_by_key[key]["relation"] = news.get("relation_type", "")
            if not merged_by_key[key].get("path_explanation"):
                merged_by_key[key]["path_explanation"] = news.get("path_explanation", "")
    
    fused_results = []

    for key, item in merged_by_key.items():
        score = 0.0

        if key in vector_rank_map:
            score += 1.0 / (k + vector_rank_map[key])
        if key in graph_rank_map:
            score += 1.0 / (k+ graph_rank_map[key])
        
        time_bonus = _compute_time_bonus(item["date"], target_date)
        score += time_bonus

        item["fused_score"] = score
        item["time_bonus"] = time_bonus
        item["vector_rank"] = vector_rank_map.get(key)
        item["graph_rank"] = graph_rank_map.get(key)

        fused_results.append(item)

    fused_results.sort(key=lambda x: x.get("fused_score", 0.0), reverse=True)
    return fused_results

def _dedup_news(
        news_list: list[dict],
        title_key: str,
        date_key: str
) -> list[dict]:
    """
    dedup news by normalized(title, date)
    keep the first occurence

    因为两种检索结果字段名不一样，所以需要title_key date_key
    """
    seen = set()
    deduped = []
    for news in news_list:
        title = (news.get(title_key, "") or "").strip().lower()
        date = (news.get(date_key, "") or "").strip().lower()
        dedup_key = (title, date)

        if dedup_key in seen:
            continue 
        
        seen.add(dedup_key)
        deduped.append(news)
    return deduped

def _split_hybrid_sections(
        vector_results: list[dict],
        graph_results: list[dict],
        target_date: str,
        direct_top_n: int=3,
        k: int = 20, 
) -> tuple[list[dict], list[dict], list[dict]]:
    """    
    Split hybrid retrieval results into:
    1. direct_news
    2. related_news
    3. theme_news

    More natural strategy:
    - direct_news: top fused results that are from_vector=True
    - related_news: remaining graph-involved results
    - theme_news: remaining vector-only results
    """
    fused_results = _fuse_hybrid_results(
        vector_results=vector_results,
        graph_results=graph_results,
        target_date=target_date,
        k = k,
    )
    direct_news = []
    related_news = []
    theme_news = []

    # 1. Direct News: 优先挑from_vector=True的高分新闻
    for news in fused_results:
        if news.get("from_vector") and len(direct_news) < direct_top_n:
            direct_news.append(news)

    direct_keys = {
        _normalize_news_key(news)
        for news in direct_news
    }

    # 2. 其余新闻按语义区分
    for news in fused_results:
        key = _normalize_news_key(news)
        if key in direct_keys:
            continue
        if news.get("from_graph"):
            related_news.append(news)
        elif news.get("from_vector"):
            theme_news.append(news)
    
    return direct_news, related_news, theme_news

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
    direct_news, related_news, theme_news = _split_hybrid_sections(
        vector_results=vector_results, graph_results=graph_results,
        target_date=date,  direct_top_n=3,  k=20
    )
    tracker.stop("fusion")

    model_label = "HYBRID"
    if ablation_mode == "DROP_DIRECT_NEWS":
        direct_news = []
        model_label = "ABLATION_DROP_DIRECT_NEWS"
    
    print(
        f"[CONTEXT_BUILDER] mode={model_label} "
        f"vector_hits={len(vector_results)} "
        f"graph_hits={len(graph_results)} "
        f"direct={len(direct_news)} "
        f"related={len(related_news)} "
        f"themes={len(theme_news)}"
    )

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