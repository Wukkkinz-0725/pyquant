pyquant — minimal tweet → signal demo

What it does
- Fetches tweets by handle list (stubs if no X token)
- Extracts sentiment with OpenAI (mocked if no key)
- Pulls 7‑day price windows from Yahoo Finance
- Stores results in MySQL if `MYSQL_URI` is set, otherwise uses in‑memory SQLite

Quick start
1) Install deps
   pip install -r requirements.txt

2) Optional: copy and edit env
   cp .env.example .env

3) Launch Jupyter and open the quickstart notebook
   jupyter lab   # open notebooks/00_quickstart.ipynb

Fallback behavior
- If no keys are provided, the notebook runs fully in mock mode, writing to SQLite `:memory:`.
- If `MYSQL_URI` is reachable, tables are created and inserts succeed there instead.

Notes
- Code is intentionally small and uses SQL strings (no ORM models) to keep cells short and readable.
- External API calls are minimal; the Twitter client is stubbed when no token is present.
