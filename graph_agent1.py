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
import json
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


def lstmAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"testing google"
    )

    return None


def arimaAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"testing google"
    )

    return None


def forecastAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"testing google"
    )

    return None


def sentimentAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"testing google"
    )

    return None


def finalOutputAgent(state: ChatState) -> ChatState:
    response = llm.invoke(
        f"testing google"
    )
    return None
 

graph_builder = StateGraph(ChatState)
graph_builder.add_node("queryHandler",queryHandlerAgent)
graph_builder.add_node("financeAgent",financeCallAgent)
graph_builder.add_node("newsAgent", newsAgent)
graph_builder.add_node("lstmAgent", lstmAgent)
graph_builder.add_node("arimaAgent", arimaAgent)
graph_builder.add_node("forecastAgent", forecastAgent)
graph_builder.add_node("sentimentAgent", sentimentAgent)
graph_builder.add_node("finalOutputAgent", finalOutputAgent)
graph_builder.add_edge("queryHandler","financeAgent")
graph_builder.add_edge("financeAgent","lstmAgent")
graph_builder.add_edge("queryHandler","newsAgent")
graph_builder.add_edge("financeAgent","arimaAgent")
graph_builder.add_edge("lstmAgent","forecastAgent")
graph_builder.add_edge("arimaAgent","forecastAgent")
graph_builder.add_edge("forecastAgent","finalOutputAgent")
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
