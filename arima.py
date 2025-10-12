import yfinance as yf
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt
import io, base64, warnings
from PIL import Image
import os, warnings, os, uuid
from dotenv import load_dotenv

load_dotenv()
from gradio_client import Client

warnings.filterwarnings("ignore")


def arima_predict(ticker: str, forecast_days: int = 15):

    try:
        # Fetch stock data
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
        client = Client("pzzzzaaa/mltest", hf_token=HF_TOKEN)

        result = client.predict(ticker=ticker, api_name="/predict")
        forecast_values_lstm = [float(v) for v in result["forecast_values"]]
        last_price_lstm = forecast_values_lstm[-1]
        if df.empty:
            return {"error": f"No data found for {ticker}"}

        close = df["Close"].dropna()
        if len(close) < 20:
            return {"error": "Not enough data for ARIMA model"}

        # Fit ARIMA model
        model = ARIMA(close, order=(5, 1, 0))
        model_fit = model.fit()

        # Forecast next N days
        forecast = model_fit.forecast(steps=forecast_days)
        forecast_values = [float(v) for v in forecast]
        last_price = float(close.iloc[-1])
        last_forecast = forecast_values[-1]

        # Create forecast index
        forecast_index = pd.date_range(
            start=close.index[-1] + pd.Timedelta(days=1),
            periods=forecast_days,
            freq="D",
        )

        # Prepare DataFrames
        actual_df = pd.DataFrame(
            {"Date": close.index.tolist(), "Actual": close.values.flatten().tolist()}
        )

        forecast_df = pd.DataFrame(
            {"Date": forecast_index.tolist(), "Forecast": forecast_values}
        )
        forecast_lstm_df = pd.DataFrame(
            {"Date": forecast_index.tolist(), "Forecast": forecast_values_lstm}
        )

        merged_df = pd.concat(
            [actual_df, forecast_df, forecast_lstm_df], ignore_index=True
        )

        # --- Plot the forecast ---
        plt.figure(figsize=(10, 4))
        plt.plot(
            actual_df["Date"],
            actual_df["Actual"],
            label="Historical (1Y)",
            color="blue",
        )
        plt.plot(
            forecast_df["Date"],
            forecast_df["Forecast"],
            "--",
            label=f"Forecast ({forecast_days} Days)",
            color="orange",
        )
        plt.plot(
            forecast_lstm_df["Date"],
            forecast_lstm_df["Forecast"],
            "-",
            label=f"Forecast  LSTM({forecast_days} Days)",
            color="red",
        )
        plt.title(f"{ticker} - ARIMA {forecast_days}-Day Forecast")
        plt.xlabel("Date")
        plt.ylabel("Price ($)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        # --- Save the plot ---
        os.makedirs("static/images", exist_ok=True)
        unique_filename = f"{ticker}_{uuid.uuid4().hex[:8]}.png"
        image_path = os.path.join("static", "images", unique_filename)
        plt.savefig(image_path)
        plt.close()

        # --- Return results ---
        return {
            "ticker": ticker,
            "forecast_model": "ARIMA(5,1,0)",
            "forecast_days": forecast_days,
            "forecast_values_arima": forecast_values,
            "forecast_values_lstm": result["forecast_values"],
            "image_path": image_path,
            "summary_arima": {
                "latest_price": last_price,
                "predicted_trend": "up" if last_forecast > last_price else "down",
                "avg_predicted_growth": round(
                    ((last_forecast - last_price) / last_price) * 100, 2
                ),
            },
            "summary_lstm": result["summary"],  
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def show_plot_from_base64(plot_base64: str, save_path: str = None):
    try:
        image_bytes = base64.b64decode(plot_base64)
        image = Image.open(io.BytesIO(image_bytes))
        plt.figure(figsize=(8, 4))
        plt.imshow(image)
        plt.axis("off")
        plt.title("Decoded ARIMA Forecast Plot")
        plt.show()
        if save_path:
            image.save(save_path)
            print(f"✅ Chart saved successfully as '{save_path}'")
    except Exception as e:
        print(f"❌ Error displaying chart: {str(e)}")


# if __name__ == "__main__":
#     result = arima_predict("AAPL", forecast_days=15)
#     if "error" in result:
#         print("❌", result["error"])
#     else:
#         print("✅ Forecast values:", result["forecast_values"])
#         show_plot_from_base64(result["plot_base64"], save_path="aapl_forecast.png")
