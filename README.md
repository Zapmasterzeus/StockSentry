## StockSentry

AI‑powered financial research assistant with a FastAPI backend and an Express/EJS + Tailwind frontend. StockSentry analyzes a stock ticker to fetch financials, run sentiment analysis, build an ARIMA forecast, and generate a concise research summary, with charts served from the backend.

### Features
- **Ticker analysis**: POST a ticker and receive financials, sentiment, forecast, charts, and a summary
- **FastAPI backend**: `/health`, `/analyze`, `/analyze-form`, `/search-tickers`
- **Express frontend**: Simple UI with EJS templates, Tailwind styles, and backend warmup/status
- **ARIMA charting**: Matplotlib renders saved images served from `backend/static`
- **Render-ready**: `render.yaml` provisions separate web services for backend and frontend

### Tech Stack
- **Backend**: Python, FastAPI, Uvicorn, NumPy, Pandas, Statsmodels, Matplotlib, LangChain/LangGraph, Requests, yfinance
- **Frontend**: Node.js, Express, EJS, Tailwind CSS, Axios

---

## Quick Start (Local)

> Prereqs: Python 3.11+, Node.js 18+, npm

### 1) Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional: set environment variables (see Env Vars)
# $env:GOOGLE_API_KEY="your_key"
# $env:SERPAPI_KEY="your_key"
# $env:HUGGINGFACE_API_KEY="your_key"

uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2) Frontend
Open a new terminal at the repo root:
```powershell
cd frontend
npm install
# Build CSS once (or use dev to skip minify)
npm run build:css

# Ensure the frontend knows where the backend is
$env:BACKEND_URL="http://localhost:8000"

# Start the server
npm start
# or
npm run dev
```

Visit the frontend at `http://localhost:3000`.

---

## Environment Variables

Backend (set in `backend/.env` or your process env):
- `GOOGLE_API_KEY`: Optional, for Google Generative AI via LangChain integrations
- `SERPAPI_KEY`: Optional, for search (SerpAPI)
- `HUGGINGFACE_API_KEY`: Optional, for model integrations
- Other flags used by LangChain providers (see `backend/requirements.txt` packages)

Frontend:
- `BACKEND_URL`: URL of the FastAPI backend (defaults to `http://localhost:8000` in development)

On Render, secrets should be set in the dashboard (see `render.yaml`).

---

## API Overview (Backend)

Base URL: `http://localhost:8000`

- `GET /` → Basic health info
- `GET /health` → Health check
- `POST /analyze` → Body: `{ "ticker": "TSLA" }`
  - Response includes: `overview`, `financials`, `sentiment`, `forecast`, `charts[]`, `summary`, `company_overview`, `tracker`, `input`, `counter`
- `POST /analyze-form` → Form field `ticker` (used by the frontend form)
- `GET /search-tickers?q=TES` → Lightweight Yahoo Finance search proxy
- Static charts served under `/static` (e.g., `/static/images/<file>.png`)

Run locally with:
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Frontend Overview

- Server: `frontend/server.js` (Express + EJS)
- Views: `frontend/views/index.ejs`, `frontend/views/results.ejs`
- Static: `frontend/public/`
- Tailwind entry: `frontend/src/input.css` → outputs to `frontend/public/css/output.css`

Key behaviors:
- Pings `BACKEND_URL/health` on boot and every 12 minutes to warm the backend
- `POST /analyze` proxies the form to `BACKEND_URL/analyze`
- Provides `/backend-status` for client-side status checks

Scripts:
```json
"build:css": "tailwindcss -i ./src/input.css -o ./public/css/output.css --minify",
"watch:css": "tailwindcss -i ./src/input.css -o ./public/css/output.css --watch",
"start": "npm run build:css && node server.js",
"dev": "node server.js"
```

---

## Project Structure
```text
backend/
  main.py               # FastAPI app and endpoints
  graph_agent1.py       # Graph/agent logic (invoked by /analyze)
  arima.py              # Forecasting utilities (ARIMA)
  newsextractor.py      # News extraction helpers
  sentimentest.py       # Sentiment analysis helpers
  helperfunctions.py    # Shared utilities
  serpapi.py            # SerpAPI integration
  static/               # Served charts/images
frontend/
  server.js             # Express server
  views/                # EJS templates
  public/               # Static assets
  src/input.css         # Tailwind input
render.yaml             # Render.com services (backend + frontend)
```

---

## Deployment (Render.com)

This repo includes `render.yaml` defining two web services:
- `stocksentry-backend` (Python): builds with `pip install -r requirements.txt`, starts `uvicorn main:app`
- `stocksentry-frontend` (Node): builds with `npm install`, starts `npm start`

Notes:
- Set secrets (`GOOGLE_API_KEY`, `SERPAPI_KEY`, `HUGGINGFACE_API_KEY`) in the Render dashboard
- `BACKEND_URL` for the frontend is automatically wired to the backend’s host via `fromService`
- Ensure Python version matches `render.yaml` (currently `3.11.0`)

---

## Troubleshooting

- Backend cold start on free tiers can take 30–60s. The frontend auto‑pings `/health` and shows status.
- If requests time out from the frontend, check `BACKEND_URL` and confirm the backend is reachable.
- For Windows PowerShell, use `$env:VAR="value"` to set env vars in the current session.
- Charts not showing? Confirm images are written under `backend/static/...` and URLs in responses are normalized with forward slashes.

---

## License

This project is licensed under the ISC License (see `frontend/package.json`). You may adapt the license as needed for the whole repo.


