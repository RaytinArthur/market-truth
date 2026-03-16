from retriever.context_builder import build_hybrid_context
from retriever.vector_retriever import search_news_by_ticker_and_date


def main():
    ticker = "AAPL"
    date = "2024-08-05"

    query = f"{ticker} news {date}"

    vector_results = search_news_by_ticker_and_date(
        query=query,
        ticker=ticker,
        target_date=date,
        top_k=5,
    )

    graph_results = [
        {
            "company_ticker": "TSM",
            "relation": "SUPPLIES",
            "news_title": "Supply chain report: Apple iPhone 16 production orders revised amid economic uncertainty",
            "news_date": "2024-08-01",
            "publisher": "DigiTimes",
            "path_explanation": "TSM -[:SUPPLIES] -> AAPL",
            "link": ""
        },
        {
            "company_ticker": "TSM",
            "relation": "SUPPLIES",
            "news_title": "TSMC signals cautious outlook for smartphone chip demand in H2 2024",
            "news_date": "2024-08-01",
            "publisher": "Bloomberg",
            "path_explanation": "TSM -[:SUPPLIES] -> AAPL",
            "link": ""
        }
    ]

    context = build_hybrid_context(
        ticker=ticker,
        date=date,
        vector_results=vector_results,
        graph_results=graph_results,
    )

    print("=" * 80)
    print("HYBRID CONTEXT TEST")
    print("=" * 80)
    print(context)


if __name__ == "__main__":
    main()