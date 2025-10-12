import requests
from bs4 import BeautifulSoup
import random
import re


def extract_article_text(
    url: str, max_paragraphs: int = 10, max_words: int = 200
) -> str:
    """
    Fetch and extract readable article text from a URL (limited to ~200 words).
    Falls back gracefully if content cannot be parsed.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Try <article> tag, else fallback to all <p> tags
        article = soup.find("article")
        paragraphs = article.find_all("p") if article else soup.find_all("p")

        text_blocks = []
        for p in paragraphs:
            content = p.get_text(strip=True)
            if len(content) > 40:  # skip short/junk lines
                text_blocks.append(content)
            if len(text_blocks) >= max_paragraphs:
                break

        full_text = " ".join(text_blocks)
        words = re.findall(r"\b\w+\b", full_text)
        if len(words) > max_words:
            # Truncate to first 200 words
            truncated_text = " ".join(words[:max_words]) + "..."
        else:
            truncated_text = full_text

        return truncated_text if truncated_text else "⚠️ No readable article text found."

    except Exception as e:
        return f"❌ Error fetching article: {e}"


def enrich_news_with_articles(news_json: dict) -> dict:
    """
    Transform news JSON to include extracted article text (~200 words)
    and random sentiment score. Returns structured dict (no file saving).
    """
    enriched = {"query": news_json.get("query", ""), "articles": []}

    for item in news_json.get("news", []):
        title = item.get("title", "Untitled")
        link = item.get("link")

        if not link:
            article_text = "⚠️ No link available."
        else:
            article_text = extract_article_text(link, max_paragraphs=10, max_words=200)

        sentiment = round(random.uniform(-1, 1), 2)  # Fake sentiment for now

        enriched["articles"].append(
            {
                "title": title,
                "link": link or "N/A",
                "article": article_text,
                "sentiment": sentiment,
            }
        )

    return enriched


# if __name__ == "__main__":
#     sample_data = {
#         "query": "Nvidia stock",
#         "count": 5,
#         "news": [
#             {"title": "Nvidia stock price target raised by Cantor Fitzgerald", "link": None},
#             {"title": "Great News for Nvidia Stock Investors!",
#              "link": "https://www.fool.com/investing/2025/10/11/great-news-for-nvidia-stock-investors-as-demand-co/"},
#             {"title": "Prediction: This Unstoppable Stock Will Join Nvidia...",
#              "link": "https://www.nasdaq.com/articles/prediction-unstoppable-stock-will-join-nvidia-microsoft-apple-and-alphabet-3-trillion-0"},
#             {"title": "CoreWeave vs Nvidia Stock: Who Will Dominate the AI Market?",
#              "link": "https://www.techi.com/coreweave-stock-vs-nvidia-stock-ai-market/"}
#         ]
#     }

#     result = enrich_news_with_articles(sample_data)
#     print(result)
