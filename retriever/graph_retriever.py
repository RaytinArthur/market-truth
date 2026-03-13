from datetime import datetime

class GraphRetriever:
    def __init__(self, driver):
        self.driver = driver
    
    def retrieve(self, ticker:str, target_date:str, window: int = 7):
        query = """
        MATCH (target:Company {ticker: $ticker})

        CALL {
            WITH target
            MATCH (related:Company)-[r:SUPPLIES]->(target)
            RETURN related, type(r) AS relation

            UNION

            WITH target
            MATCH (related:Company)-[r:COMPETES_WITH]-(target)
            RETURN related, type(r) AS relation
        }

        MATCH (news:News)-[:MENTIONS]->(related)

        WHERE date(news.date) >= date($target_date) - duration({days:$window})
        AND date(news.date) <= date($target_date) + duration({days:$window})

        RETURN
        related.ticker AS company_ticker,
        relation AS relation_type,
        news.title AS news_title,
        news.date AS date,
        news.publisher AS publisher
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                ticker=ticker,
                target_date=target_date,
                window=window
            )
            records = []
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()

            for r in result:
                news_dt = datetime.strptime(r["date"],"%Y-%m-%d").date()
                date_distance = (news_dt - target_dt).days
                
                company_ticker = r["company_ticker"]
                relation_type = r["relation_type"]
                news_title = r["news_title"]

                path_explanation  = (
                    f"{company_ticker} -[:{relation_type}] -> {ticker}; "
                    f"News '{news_title}' -[:MENTIONS] -> {company_ticker}"
                )
                records.append({
                    "company_ticker": company_ticker,
                    "relation_type": relation_type,
                    "news_title": news_title,
                    "news_date": r["date"],
                    "publisher": r["publisher"] or "Unknown",
                    "path_explanation": path_explanation,
                    "date_distance": date_distance,
                })
        records.sort(key=lambda x:(x["date_distance"], x["company_ticker"]))
            
        return records