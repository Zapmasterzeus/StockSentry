import requests, os
from dotenv import load_dotenv

load_dotenv()
def get_sentiment_api(text: str):
    HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
    API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment"

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text[:512]}  # truncate long texts

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            scores = {d["label"]: d["score"] for d in data[0]}
            sentiment = scores.get("LABEL_2", 0) - scores.get("LABEL_0", 0)  # pos - neg heuristic
            return {
                "label": max(scores, key=scores.get),
                "confidence": round(max(scores.values()), 3),
                "sentiment": round(sentiment, 3)
            }

    except Exception as e:
        return {"label": "ERROR", "sentiment": 0.0, "error": str(e)}

# print(get_sentiment_api("""If you tell me where you’re hosting your backend (local, Render, Vercel, Colab, or cloud VM),
# I’ll tell you exactly which option is best and help wire it directly into your existing sentimentAgent."""))