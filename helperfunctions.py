import requests
import yfinance as yf
import pandas as pd
import json


def find_ticker(user_query: str):
    try:
        # Hit Yahoo Finance public search endpoint directly
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={user_query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)

        data = response.json()
        if "quotes" in data and len(data["quotes"]) > 0:
            first = data["quotes"][0]
            ticker = first.get("symbol")
            name = first.get("shortname") or first.get("longname") or "Unknown"
            return ticker, name
        else:
            print("No matches found.")
    except Exception as e:
        print("Error:", e)
    return None, None


def get_financial_json(ticker_symbol: str):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        eps = info.get("trailingEps", None)
        pe_ratio = info.get("trailingPE", None)
        debt_to_equity = info.get("debtToEquity", None)

        financials = ticker.quarterly_financials

        if financials.empty:
            return {"error": "No financial data available"}

        df = financials.T.fillna(0)

        # Convert timestamps to string for JSON
        def to_serializable_dict(series):
            return {
                str(date.date()): float(value)
                for date, value in series.dropna().items()
            }

        revenue_trend = to_serializable_dict(df["Total Revenue"].tail(4))
        profit_trend = to_serializable_dict(df["Net Income"].tail(4))
        profit_margin_trend = {
            date: round(profit_trend[date] / revenue_trend[date] * 100, 2)
            for date in profit_trend.keys()
            if date in revenue_trend and revenue_trend[date] != 0
        }

        return {
            "ticker": ticker_symbol,
            "EPS": eps,
            "PE_Ratio": pe_ratio,
            "Debt_to_Equity": debt_to_equity,
            "Revenue_Trend": revenue_trend,
            "Profit_Trend": profit_trend,
            "Profit_Margin_Trend": profit_margin_trend,
        }

    except Exception as e:
        return {"error": str(e)}


# print(get_financial_json("NVDA"))

# print(find_ticker("nvidia"))
