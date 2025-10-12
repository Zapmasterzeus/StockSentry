import operator
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, Annotated, List
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import add_messages
import re
from helperfunctions import find_ticker, get_financial_json
from serpapi import get_google_news
from arima import arima_predict
from newsextractor import enrich_news_with_articles
import json
from sentimentest import get_sentiment_api
import textwrap

# from testingguardrail import querying

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
serpapi_key = os.getenv("SERPAPI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=api_key,
    temperature=0.7,
    # model_kwargs={"streaming": False}
)


def replace_reducer(x, y):
    """Takes the latest value"""
    return y if y is not None else x


class ChatState(BaseModel):
    input: str
    output: Annotated[Optional[str], replace_reducer] = ""
    tracker: Annotated[Optional[str], replace_reducer] = None
    finance_data: Annotated[Optional[dict], replace_reducer] = None
    news_data: Annotated[Optional[dict], replace_reducer] = None
    arima_data: Annotated[Optional[dict], replace_reducer] = None
    sentiment_data: Annotated[Optional[dict], replace_reducer] = None
    company_overview: Annotated[Optional[str], replace_reducer] = ""
    final_report: Annotated[Optional[str], replace_reducer] = ""

    counter: Annotated[int, operator.add] = 0


def queryHandlerAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"""
    The user typed '{state.input}' referring to a company or stock.
    Normalize this to the most likely real company name or ticker symbol.
    If you are confident it is already a ticker (like AAPL, TSLA, NVDA), just return that.
    Otherwise, return the company name only — no punctuation, no extra text.
    Examples:
    "ngidea" -> "Nvidia"
    "teslaa" -> "Tesla"
    "microsoft corp" -> "Microsoft"
    "Alphabet Inc Class A" -> "Alphabet"
    Only output the cleaned name or ticker.
    """
    )
    normalized = response.content.strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(
        r"\b(inc|corporation|corp|ltd|limited|plc|sa|nv|class [a-z])\b",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip()
    tracker, name = find_ticker(normalized)

    print(response.content)
    return {
        "tracker": tracker,
        "counter": 1,  # This will be added to existing counter
    }


def financeCallAgent(state: ChatState) -> ChatState:
    ticker_symbol = state.tracker.upper()
    data = get_financial_json(ticker_symbol)

    return {
        "output": f"{data}",
        "finance_data": data,
        "counter": 1,
    }


def newsAgent(state: ChatState) -> ChatState:
    newsdata = get_google_news(state.tracker)

    return {
        "news_data": newsdata,
        "counter": 1,
    }


def arimaAgent(state: ChatState) -> ChatState:
    arimadata = arima_predict(state.tracker)

    return {"arima_data": arimadata, "counter": 1}


def sentimentAgent(state: ChatState) -> ChatState:
    sentiment = enrich_news_with_articles(state.news_data)
    for article in sentiment.get("articles", []):
        if article["article"] == "⚠️ No link available.":
            continue  # skip articles without a link

        sentiment_info = get_sentiment_api(article["article"])
        article["sentiment"] = sentiment_info.get("sentiment", 0.0)
        article["sentiment_label"] = sentiment_info.get("label", "NEUTRAL")
        article["confidence"] = sentiment_info.get("confidence", 0.0)
    articles = sentiment["articles"]
    avg_sentiment = round(sum(a["sentiment"] for a in articles) / len(articles), 2)
    pos_count = len([a for a in articles if a["sentiment"] > 0])
    neg_count = len([a for a in articles if a["sentiment"] < 0])

    sentiment["summary"] = {
        "average_sentiment": avg_sentiment,
        "positive_articles": pos_count,
        "negative_articles": neg_count,
        "overall_tone": (
            "Bullish"
            if avg_sentiment > 0.25
            else "Bearish" if avg_sentiment < -0.2 else "Neutral"
        ),
    }

    return {"sentiment_data": sentiment, "counter": 1}


def finalOutputAgent(state: ChatState) -> ChatState:
    print(state.sentiment_data)
    company_overview_prompt = f"""
You are a professional financial summarization model.

Generate a concise **company overview** for the organization with ticker **{state.tracker}**, based on its public identity and market role.  
If available, include industry, sector, and primary operations.

**Output format (Markdown bullets only):**
- Company Name:
- Ticker:
- Industry & Sector:
- Core Business Areas:
- Headquarters (if known):
- Market Overview: (1–2 sentences summarizing the company’s market presence)
"""
    final_report_prompt = f"""
You are an experienced financial market analyst. Generate a professional, structured **Market Intelligence Report** (Markdown format only).
You will analyze **financial**, **sentiment**, and **forecast (ARIMA + LSTM)** data to produce a clear, directional investment view.  
Do NOT make up data — interpret what's provided. If some data is missing, acknowledge it briefly.

---

### INPUT DATA
**Ticker:** {state.tracker}

**Financial Data:**
{json.dumps(state.finance_data or {}, indent=2)}

**Forecast Data (Includes ARIMA + LSTM):**
{json.dumps(state.arima_data or {}, indent=2)}

**Sentiment Data:**
{json.dumps(state.sentiment_data or {}, indent=2)}

---

### RULES & LOGIC

#### 1️⃣ Financial Analysis
- Extract **EPS**, **P/E Ratio**, **Debt-to-Equity**.
- Identify whether **Revenue**, **Profit**, and **Profit Margin** are trending Up, Down, or Flat by comparing the two most recent entries.
- If the earlier period is zero or missing, skip percentage change.
- Assess valuation based on P/E:
  - P/E < 20 → Undervalued
  - 20–35 → Fairly Valued
  - >35 → Overvalued
- Add a short professional comment on leverage using the Debt-to-Equity ratio.

---

#### 2️⃣ Dual Forecast Analysis (ARIMA + LSTM)
Use both `summary_arima` and `summary_lstm` data.  
Compute and describe:

- **Latest Price** from ARIMA.
- **ARIMA Model:** Mention growth % and predicted trend.  
- **LSTM Model:** Mention growth % and predicted trend.  
- Compare both:
  - If both predict **up**, call it “reinforced bullish momentum”.
  - If both predict **down**, call it “reinforced bearish signal”.
  - If directions differ, call it “forecast divergence”, explaining the likely volatility.
- Mention **difference between ARIMA and LSTM growth rates** (e.g., “LSTM projects stronger momentum at +2.4% vs ARIMA’s modest +0.2%”).  
- Interpret what this means for **short-term sentiment and price action**:
  - If both are positive → near-term upside.
  - If both are negative → risk of correction.
  - If conflicting → choppy or uncertain short-term movement.

Example phrasing:
> “Both forecasting models align on a mild upward trajectory, with LSTM showing stronger bullish confidence (+2.4%) than ARIMA (+0.2%), suggesting potential near-term gains.”

---

#### 3️⃣ Market Sentiment Analysis
- Use `sentiment_data.summary.average_sentiment` for overall score.
- If articles include errors or “⚠️ No link available”, infer tone from title keywords:
  - **Positive:** rise, growth, approval, boost, record, deal, strong, rebound.
  - **Negative:** fall, crash, lawsuit, cut, investigation, concern, miss.
- Output up to **5 articles** formatted as:
  `[Title](link) — Positive/Negative/Mixed. One-sentence insight.`
- Base **Overall Tone** on article mix and average sentiment.

---

#### 4️⃣ Investment Interpretation
- Integrate **financial**, **sentiment**, and **forecast** data.
- Use scoring logic:
  - +1 if sentiment ≥ 0.15  
  - -1 if sentiment ≤ -0.15  
  - +1 if combined forecast growth (avg of ARIMA + LSTM) ≥ 0.3%  
  - -1 if combined forecast growth ≤ -0.3%  
  - +0.5 if Revenue is trending up, -0.5 if down  
  - -1 if P/E > 40 and sentiment ≤ 0
- If total > 0 → 🟢 Bullish  
  Otherwise → 🔴 Bearish

---

### OUTPUT FORMAT

## {state.tracker} Market Intelligence Report

### 1️⃣ Company Snapshot
1–2 lines describing the company’s business, core focus areas, and market relevance.

### 2️⃣ Financial Highlights
- **EPS:** <value>  
- **P/E Ratio:** <value>  
- **Debt-to-Equity:** <value>  
- **Revenue Trend:** Up/Down/Flat (+/-%)  
- **Profit Trend:** Up/Down/Flat (+/-%)  
- **Profit Margin Trend:** Up/Down/Flat  
_Add one professional comment summarizing valuation and leverage._

### 3️⃣ Market Sentiment Overview
- **Average Sentiment:** <score to 2 decimals>  
- **Overall Tone:** Positive / Negative / Mixed  
- **Article Highlights (up to 5):**
  1. [Title](link) — Positive/Negative/Mixed. One-sentence insight.
  2. [Title](link) — Positive/Negative/Mixed. One-sentence insight.
  3. [Title](link) — Positive/Negative/Mixed. One-sentence insight.
  4. [Title](link) — Positive/Negative/Mixed. One-sentence insight.
  5. [Title](link) — Positive/Negative/Mixed. One-sentence insight.

### 4️⃣ Forecast Outlook (Next { (state.arima_data or {}).get('forecast_days', 'N/A') } Days)
- **Latest Price:** <value>  
- **ARIMA Forecast:** <trend> | <growth>%  
- **LSTM Forecast:** <trend> | <growth>%  
- **Comparison:** Mention which model shows stronger momentum and whether they agree.  
- **Interpretation:** Concise 1–2 sentence summary of expected short-term direction.

### 5️⃣ Investment Interpretation
Combine financial, sentiment, and forecast insights.  
Mention key catalysts (new product lines, demand trends) or risks (valuation, competition).  
State if short-term technicals align with fundamentals.

### 6️⃣ Final Verdict
🟢 **Bullish** — or — 🔴 **Bearish**  
(Must choose exactly one.)
"""

    company_overview_prompt = textwrap.dedent(company_overview_prompt)
    final_report_prompt = textwrap.dedent(final_report_prompt)

    company_overview = llm.invoke(company_overview_prompt)
    final_report = llm.invoke(final_report_prompt)

    return {
        "company_overview": company_overview.content,
        "final_report": final_report.content,
        "counter": 1,
    }


graph_builder = StateGraph(ChatState)
graph_builder.add_node("queryHandler", queryHandlerAgent)
graph_builder.add_node("financeAgent", financeCallAgent)
graph_builder.add_node("newsAgent", newsAgent)
graph_builder.add_node("forecastAgent", arimaAgent)
graph_builder.add_node("sentimentAgent", sentimentAgent)
graph_builder.add_node("finalOutputAgent", finalOutputAgent)
graph_builder.add_edge("queryHandler", "financeAgent")
graph_builder.add_edge("queryHandler", "newsAgent")
graph_builder.add_edge("financeAgent", "forecastAgent")
graph_builder.add_edge("forecastAgent", "finalOutputAgent")
graph_builder.add_edge("newsAgent", "sentimentAgent")
graph_builder.add_edge("sentimentAgent", "finalOutputAgent")


graph_builder.set_entry_point("queryHandler")
graph_builder.set_finish_point("finalOutputAgent")

graph = graph_builder.compile()

try:
    with open("workflow.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    import webbrowser

    webbrowser.open("file://" + os.path.abspath("workflow.png"))
except Exception as e:
    print("Error:", e)