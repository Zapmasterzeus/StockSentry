from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid tkinter issues
from dotenv import load_dotenv
from graph_agent1 import graph, ChatState
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="InsightInvest AI Financial Research API", 
    version="1.0.0",
    description="AI-powered financial analysis with multi-agent system"
)

# Mount static files for serving charts
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AnalysisRequest(BaseModel):
    ticker: str

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

# Health check endpoint
@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        status="running",
        message="InsightInvest AI Financial Research API",
        version="1.0.0"
    )

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="All systems operational",
        version="1.0.0"
    )

# Main analysis endpoint
@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    try:
        logger.info(f"Starting analysis for: {request.ticker}")
        user_input = request.ticker.strip()
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Ticker symbol is required")
        
        # Create initial state with user input
        initial_state = ChatState(input=user_input)
        
        # Run the analysis in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, graph.invoke, initial_state)
        print(final_state)
        
        # logger.info(f"Analysis completed. Final state type: {type(final_state)}")
        
        # Handle both dict and ChatState object responses
        if isinstance(final_state, dict):
            # If it's a dict, extract values directly
            tracker = final_state.get('tracker', user_input)
            finance_data = final_state.get('finance_data', {})
            sentiment_data = final_state.get('sentiment_data', {})
            arima_data = final_state.get('arima_data', {})
            final_report = final_state.get('final_report', '')
            company_overview = final_state.get('company_overview', '')
            counter = final_state.get('counter', 0)
        else:
            # If it's a ChatState object, use attributes
            tracker = getattr(final_state, 'tracker', user_input)
            finance_data = getattr(final_state, 'finance_data', {})
            sentiment_data = getattr(final_state, 'sentiment_data', {})
            arima_data = getattr(final_state, 'arima_data', {})
            final_report = getattr(final_state, 'final_report', '')
            company_overview = getattr(final_state, 'company_overview', '')
            counter = getattr(final_state, 'counter', 0)
        
        logger.info(f"Analysis completed for: {tracker}")
        
        # Build response matching the exact structure from your example
        response = {
            "overview": f"Analysis for {tracker}",
            "financials": finance_data,
            "sentiment": sentiment_data,
            "forecast": arima_data,
            "charts": [],
            "summary": final_report,
            "company_overview": company_overview,
            "tracker": tracker,
            "input": user_input,
            "counter": counter
        }
        
        # Add chart path if available
        if arima_data and "image_path" in arima_data:
            chart_path = arima_data["image_path"]
            # Convert Windows path to URL path
            if chart_path:
                chart_url = chart_path.replace("\\", "/")
                response["charts"] = [f"/{chart_url}"]
        
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed for {request.ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Alternative form endpoint
@app.post("/analyze-form")
async def analyze_form(ticker: str = Form(...)):
    try:
        logger.info(f"Starting form analysis for: {ticker}")
        user_input = ticker.strip()
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Ticker symbol is required")
        
        # Create initial state with user input
        initial_state = ChatState(input=user_input)
        
        # Run the analysis
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, graph.invoke, initial_state)
        
        # Handle both dict and ChatState object responses
        if isinstance(final_state, dict):
            # If it's a dict, extract values directly
            tracker = final_state.get('tracker', user_input)
            finance_data = final_state.get('finance_data', {})
            sentiment_data = final_state.get('sentiment_data', {})
            arima_data = final_state.get('arima_data', {})
            final_report = final_state.get('final_report', '')
            company_overview = final_state.get('company_overview', '')
            counter = final_state.get('counter', 0)
        else:
            # If it's a ChatState object, use attributes
            tracker = getattr(final_state, 'tracker', user_input)
            finance_data = getattr(final_state, 'finance_data', {})
            sentiment_data = getattr(final_state, 'sentiment_data', {})
            arima_data = getattr(final_state, 'arima_data', {})
            final_report = getattr(final_state, 'final_report', '')
            company_overview = getattr(final_state, 'company_overview', '')
            counter = getattr(final_state, 'counter', 0)
        
        logger.info(f"Form analysis completed for: {tracker}")
        
        # Build response
        response = {
            "overview": f"Analysis for {tracker}",
            "financials": finance_data,
            "sentiment": sentiment_data,
            "forecast": arima_data,
            "charts": [],
            "summary": final_report,
            "company_overview": company_overview,
            "tracker": tracker,
            "input": user_input,
            "counter": counter
        }
        
        # Add chart path if available
        if arima_data and "image_path" in arima_data:
            chart_path = arima_data["image_path"]
            if chart_path:
                chart_url = chart_path.replace("\\", "/")
                response["charts"] = [f"/{chart_url}"]
        
        return response
        
    except Exception as e:
        logger.error(f"Form analysis failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Get analysis status (if you want to track long-running analyses)
@app.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    # This could be implemented with a task queue in the future
    return {"status": "completed", "analysis_id": analysis_id}

# Ticker search endpoint
@app.get("/search-tickers")
async def search_tickers(q: str):
    """Search for ticker symbols using Yahoo Finance"""
    try:
        import requests
        
        if not q or len(q.strip()) < 1:
            return {"tickers": []}
        
        # Use Yahoo Finance search API
        search_url = f"https://query1.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=8&newsCount=0"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        quotes = data.get('quotes', [])
        
        tickers = []
        for quote in quotes[:8]:  # Limit to 8 results
            ticker_info = {
                "symbol": quote.get('symbol', ''),
                "name": quote.get('longname') or quote.get('shortname', ''),
                "exchange": quote.get('exchange', ''),
                "price": None,
                "change": None
            }
            
            # Try to get current price if available
            if quote.get('regularMarketPrice'):
                ticker_info["price"] = f"{quote['regularMarketPrice']:.2f}"
            if quote.get('regularMarketChange'):
                ticker_info["change"] = f"{quote['regularMarketChange']:.2f}"
            
            tickers.append(ticker_info)
        
        return {"tickers": tickers}
        
    except Exception as e:
        logger.error(f"Ticker search failed for '{q}': {str(e)}")
        return {"tickers": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)