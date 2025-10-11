import streamlit as st
from graph_agent1 import graph, ChatState

# Streamlit Page Setup
st.set_page_config(page_title="InsightInvest", layout="centered")
st.title("💹 InsightInvest – AI Investment Research Analyst")

st.caption("Enter a company name or stock ticker (e.g. TSLA, AAPL) to generate an AI-driven investment outlook report.")

# Input box
user_input = st.text_input("Company or Ticker Symbol", placeholder="e.g. AAPL")

# Submit button
if st.button("Analyze"):
    if not user_input:
        st.warning("⚠️ Please enter a valid company name or ticker.")
    else:
        with st.spinner("🔍 Analyzing company data..."):
            try:
                # Initialize state and run the analysis
                state = ChatState(input=user_input)
                result = graph.invoke(state)

                # Extract output text
                if hasattr(result, "output"):
                    output_text = result.output
                elif hasattr(result, "content"):
                    output_text = result.content
                else:
                    output_text = str(result)

                # Display report
                st.success("✅ Analysis Complete!")
                st.markdown("---")
                st.markdown("### 📈 Investment Report")
                st.write(output_text)

            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
