import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_google_news(query, num_results=5):
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        raise ValueError("⚠️ SERPAPI_KEY not set in .env")

    params = {
        "engine": "google_news",
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": serpapi_key,
        "num": num_results,
        "no_cache": "true"
    }

    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()
    data = response.json()

    articles = []
    for item in data.get("news_results", [])[:num_results]:
        articles.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "source": item.get("source", {}).get("name"),
            "date": item.get("date"),
            "thumbnail": item.get("thumbnail")
        })

    return {
        "query": query,
        "count": len(articles),
        "news": articles
    }

if __name__ == "__main__":
    print(get_google_news("Nvidia stock"))
