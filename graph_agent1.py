import operator
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional,Annotated,List
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import add_messages
import re
from helperfunctions import find_ticker,get_financial_json
from serpapi import get_google_news
from arima import arima_predict
from newsextractor import enrich_news_with_articles
import json
from sentimentest import get_sentiment_api
import textwrap
#from testingguardrail import querying

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
serpapi_key = os.getenv("SERPAPI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=api_key,
    temperature=0.7,
    #model_kwargs={"streaming": False}
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
    arima_data:Annotated[Optional[dict], replace_reducer] = None
    sentiment_data:Annotated[Optional[dict], replace_reducer] = None
    company_overview: Annotated[Optional[str], replace_reducer] = ""
    final_report: Annotated[Optional[str], replace_reducer] = ""
    
    counter: Annotated[int, operator.add] = 0

def  queryHandlerAgent(state: ChatState) -> ChatState:
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
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(
        r'\b(inc|corporation|corp|ltd|limited|plc|sa|nv|class [a-z])\b',
        '', normalized, flags=re.IGNORECASE
    ).strip()
    tracker,name=find_ticker(normalized)
    
    print(response.content)
    return {
        "tracker": tracker,
        "counter": 1,  # This will be added to existing counter
    }
def  financeCallAgent(state: ChatState) -> ChatState:
    ticker_symbol=state.tracker.upper()
    data=get_financial_json(ticker_symbol)
   
    
    return {
        "output": f"{data}",
        "finance_data": data,
        "counter": 1,
    }

def newsAgent(state: ChatState) -> ChatState:
    newsdata=get_google_news(state.tracker)

    return {
        "news_data": newsdata,
        "counter": 1,
    }



def arimaAgent(state: ChatState) -> ChatState:
    arimadata=arima_predict(state.tracker)

    return {
        "arima_data":arimadata,
        "counter":1
    }




def sentimentAgent(state: ChatState) -> ChatState:
    sentiment=enrich_news_with_articles(state.news_data)
    for article in sentiment.get("articles", []):
        if article["article"] == "⚠️ No link available.":
            continue  # skip articles without a link

        sentiment_info = get_sentiment_api(article["article"])
        article["sentiment"] = sentiment_info.get("sentiment", 0.0)
        article["sentiment_label"] = sentiment_info.get("label", "NEUTRAL")
        article["confidence"] = sentiment_info.get("confidence", 0.0)
    articles = sentiment["articles"]
    avg_sentiment =round(sum(a["sentiment"] for a in articles) / len(articles),2)
    pos_count = len([a for a in articles if a["sentiment"] > 0])
    neg_count = len([a for a in articles if a["sentiment"] < 0])

    sentiment["summary"] = {
    "average_sentiment": avg_sentiment,
    "positive_articles": pos_count,
    "negative_articles": neg_count,
    "overall_tone": "Bullish" if avg_sentiment > 0.25 else "Bearish" if avg_sentiment < -0.2 else "Neutral"
}
    

    return {
        "sentiment_data":sentiment,
        "counter":1
    }


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
You are an experienced financial market analyst. Generate a professional Markdown **Market Intelligence Report** using the structured company data below. 
Do NOT invent facts, but you may interpret titles logically to infer tone if text is unavailable.

---
### INPUT DATA
**Ticker:** {state.tracker}

**Financial Data:**
{json.dumps(state.finance_data or {}, indent=2)}

**Forecast Data:**
{json.dumps(state.arima_data or {}, indent=2)}

**Sentiment Data:**
{json.dumps(state.sentiment_data or {}, indent=2)}
---

### RULES & LOGIC

1. **Financial Analysis**
   - Extract EPS, P/E Ratio, and Debt-to-Equity.
   - Identify whether Revenue, Profit, and Profit Margin are trending up, down, or flat using the last two periods (most recent vs previous).
   - If the older value = 0 or missing, skip percentage calculation.
   - Note whether the company appears **undervalued**, **fairly valued**, or **overvalued** based on P/E (PE < 20 → undervalued; 20–35 → fair; >35 → overvalued).

2. **Sentiment Analysis**
   - Use average sentiment (`sentiment_data.summary.average_sentiment`) if available.
   - For each article (up to 5):
       - If article text contains “Error fetching” or “⚠️ No link available”, **analyze the title itself** to infer tone.
       - Positive indicators: words like *rises, growth, approval, boost, deal, expansion, record*.
       - Negative indicators: words like *fall, drop, crash, investigation, lawsuit, concern, cut, warning*.
       - Label each as **Positive**, **Negative**, or **Mixed** based on title or text sentiment score.
       - Write a **one-sentence insight** summarizing what the article suggests.
   - Example output:
     - [Title](link) — Positive. The article indicates improved investor optimism following product expansion.

3. **Forecast & Outlook**
   - Summarize the ARIMA forecast: latest price, average predicted growth, direction (“up” or “down”).
   - If average growth ≥ 0.3%, note it as “short-term bullish momentum”.
   - If ≤ -0.3%, note “short-term bearish pressure”.
   - Otherwise, “flat/sideways outlook”.

4. **Investment Interpretation**
   - Combine the financial, sentiment, and forecast data.
   - If revenue/profit are improving AND forecast is up → lean Bullish.
   - If revenue/profit are falling AND forecast is down → lean Bearish.
   - If sentiment is strongly negative (avg < -0.2), this may override forecast positivity.

5. **Final Verdict (NO Neutral)**
   - Compute a sentiment-growth score:
       +1 if sentiment ≥ 0.15  
       -1 if sentiment ≤ -0.15  
       +1 if avg_predicted_growth ≥ 0.3  
       -1 if avg_predicted_growth ≤ -0.3  
       +0.5 if last Revenue_Trend increased  
       -0.5 if it decreased  
       -1 if PE_Ratio > 40 and sentiment ≤ 0  
   - Sum results.  
     If total > 0 → 🟢 **Bullish**  
     Else → 🔴 **Bearish**

6. **Output Formatting**
   Use clean Markdown headings and structure:

---

## {state.tracker} Market Intelligence Report

### 1️⃣ Company Snapshot
One or two sentences describing what the company does and its relevance in its sector.

### 2️⃣ Financial Highlights
- **EPS:** <value or N/A>  
- **P/E Ratio:** <value or N/A>  
- **Debt-to-Equity:** <value or N/A>  
- **Revenue Trend:** <Up/Down/Flat>, with percentage if calculable.  
- **Profit Trend:** <Up/Down/Flat>.  
- **Profit Margin Trend:** <Up/Down/Flat>.  
- Add one professional sentence interpreting valuation and leverage.

### 3️⃣ Market Sentiment Overview
- **Average Sentiment:** <score to 2 decimals>  
- **Articles (up to 5):**  
  1. [Title](link) — <Positive/Mixed/Negative>. One-line insight.  
  2. [Title](link) — <Positive/Mixed/Negative>. One-line insight.  
  3. [Title](link) — <Positive/Mixed/Negative>. One-line insight.  
  4. [Title](link) — <Positive/Mixed/Negative>. One-line insight.  
  5. [Title](link) — <Positive/Mixed/Negative>. One-line insight.  
  (If link unavailable, show title only.)

### 4️⃣ Forecast Outlook (Next { (state.arima_data or {}).get('forecast_days', 'N/A') } Days)
- **Latest Price:** <value or N/A>  
- **Predicted Direction:** <Up/Down>  
- **Avg Predicted Growth:** <percentage to 2 decimals>%  
- One sentence summarizing the expected short-term trend.

### 5️⃣ Investment Interpretation
Briefly combine financials, sentiment, and forecast to produce a balanced perspective.  
Mention opportunities and key risks.

### 6️⃣ Final Verdict
🟢 Bullish  — or —  🔴 Bearish  
(Choose **exactly one**. Never use “Neutral”.)
"""



    
    company_overview_prompt = textwrap.dedent(company_overview_prompt)
    final_report_prompt = textwrap.dedent(final_report_prompt)

    company_overview=llm.invoke(company_overview_prompt)
    final_report=llm.invoke(final_report_prompt)


    return {
        "company_overview":company_overview.content,
        "final_report":final_report.content,
        "counter":1
    }
 

graph_builder = StateGraph(ChatState)
graph_builder.add_node("queryHandler",queryHandlerAgent)
graph_builder.add_node("financeAgent",financeCallAgent)
graph_builder.add_node("newsAgent", newsAgent)
graph_builder.add_node("arimaAgent", arimaAgent)
graph_builder.add_node("sentimentAgent", sentimentAgent)
graph_builder.add_node("finalOutputAgent", finalOutputAgent)
graph_builder.add_edge("queryHandler","financeAgent")
graph_builder.add_edge("queryHandler","newsAgent")
graph_builder.add_edge("financeAgent","arimaAgent")
graph_builder.add_edge("arimaAgent","finalOutputAgent")
graph_builder.add_edge("newsAgent","sentimentAgent")
graph_builder.add_edge("sentimentAgent","finalOutputAgent")










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
