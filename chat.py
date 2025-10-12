import streamlit as st
import json
import pandas as pd
import ast
from graph_agent1 import graph, ChatState

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="InsightInvest", layout="centered")
st.markdown(
    "<h1 style='text-align:center;'>💹 InsightInvest</h1>", unsafe_allow_html=True
)
st.caption("AI-Powered Investment Research Assistant")

# ---------------- USER INPUT ----------------
user_input = st.text_input("Company or Ticker Symbol", placeholder="e.g. AAPL")

# ---------------- BUTTON ----------------
if st.button("Analyze"):
    if not user_input:
        st.warning("⚠️ Please enter a valid company name or ticker.")
    else:
        with st.spinner("🔍 Analyzing company data..."):
            try:
                # Run analysis
                state = ChatState(input=user_input)
                result = graph.invoke(state)

                # Extract output
                if hasattr(result, "output"):
                    output_text = result.output
                elif hasattr(result, "content"):
                    output_text = result.content
                else:
                    output_text = str(result)

                # ---------------- JSON PARSING ----------------
                try:
                    data = json.loads(output_text)
                except Exception:
                    try:
                        data = ast.literal_eval(output_text)
                    except Exception as e:
                        st.error(
                            f"❌ Could not parse JSON output. Please check format.\n\nError: {e}"
                        )
                        st.stop()

                # ---------------- HEADER ----------------
                company_name = "Unknown Company"
                try:
                    company_name = (
                        data.get("company_overview", "")
                        .splitlines()[0]
                        .replace("* Company Name:", "")
                        .strip()
                    )
                except Exception:
                    pass
                ticker = data.get("tracker", "N/A")

                st.markdown(
                    f"""
                    <div style="text-align:center; margin-bottom:25px;">
                        <h2 style="margin-bottom:0;">{company_name}</h2>
                        <p style="color:gray; font-size:18px;">Investment Report – {ticker}</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                # ---------------- COMPANY OVERVIEW ----------------
                st.markdown("### 🏢 Company Overview")
                overview_text = (
                    data.get("company_overview", "")
                    .replace("*", "•")
                    .replace("\n", "\n\n")
                )
                st.markdown(
                    f"<div style='background-color:#f8f9fa; padding:12px; border-radius:8px;'>{overview_text}</div>",
                    unsafe_allow_html=True,
                )

                # ---------------- FINANCIAL HEALTH ----------------
                st.markdown("### 💰 Financial Health")
                finance = data.get("finance_data", {})

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("P/E Ratio", round(finance.get("PE_Ratio", 0) or 0, 2))
                col2.metric("EPS", finance.get("EPS", "N/A"))
                col3.metric(
                    "Debt-to-Equity", round(finance.get("Debt_to_Equity", 0) or 0, 2)
                )
                col4.metric("Ticker", finance.get("ticker", ""))

                # --- Trend Chart ---
                st.markdown("#### 📊 Revenue & Profit Margin Trends")
                rev_trend = pd.Series(finance.get("Revenue_Trend", {}))
                profit_trend = pd.Series(finance.get("Profit_Margin_Trend", {}))

                if not rev_trend.empty:
                    trend_df = pd.DataFrame(
                        {
                            "Revenue (in B)": rev_trend / 1e9,
                            "Profit Margin (%)": profit_trend,
                        }
                    )
                    st.line_chart(trend_df)
                else:
                    st.info("No trend data available.")

                # ---------------- SENTIMENT & FORECAST ----------------
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 📰 News Sentiment")
                    sentiment_summary = data.get("sentiment_data", {}).get(
                        "summary", {}
                    )
                    avg_sent = sentiment_summary.get("average_sentiment")
                    tone = sentiment_summary.get("overall_tone", "Neutral")

                    try:
                        avg_sent_value = (
                            float(avg_sent) if avg_sent is not None else 0.0
                        )
                        normalized_sent = max(0.0, min((avg_sent_value + 1) / 2, 1.0))
                    except Exception:
                        avg_sent_value, normalized_sent = 0.0, 0.5

                    st.write(f"**Overall Tone:** {tone}")
                    st.progress(normalized_sent)
                    st.write(
                        f"**Positive:** {sentiment_summary.get('positive_articles', 0)} | "
                        f"**Negative:** {sentiment_summary.get('negative_articles', 0)}"
                    )

                with col2:
                    st.markdown("### 📈 Growth Outlook")
                    arima = data.get("arima_data", {})
                    if "image_path" in arima:
                        st.image(
                            arima["image_path"],
                            caption="15-Day Price Forecast",
                            use_container_width=True,
                        )
                    else:
                        st.info("No forecast chart available.")

                # ---------------- FINAL REPORT ----------------
                st.markdown("---")
                st.subheader("🧠 AI Market Intelligence Report")
                report = data.get("final_report", "")
                st.markdown(
                    f"<div style='background-color:#ffffff; padding:20px; border-radius:10px; line-height:1.6;'>{report}</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "<center><p style='color:gray;'>📊 Generated by <b>InsightInvest AI Analyst</b></p></center>",
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")

# ---------------- STYLES ----------------
st.markdown(
    """
<style>
    .stApp { background-color: #f9fafc; }
    h1, h2, h3 { color: #111; font-weight: 600; }
    .stMetric { background-color: white !important; border-radius: 8px; padding: 10px; }
    .css-1d391kg { background-color: white !important; }
</style>
""",
    unsafe_allow_html=True,
)
