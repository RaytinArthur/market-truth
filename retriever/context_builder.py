from config import TOP_K_NEWS
from retriever.stock_retriever import get_stock_anomaly
from retriever.vector_search import search_news

def build_context(ticker:str, date:str) -> str:
    stock_info = get_stock_anomaly(ticker,date)
    
    query = f"{ticker} news {date}"
    news_list = search_news(query, top_k= 3)

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
{news}
"""
    return context