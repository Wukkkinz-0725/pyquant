# pyquant

Minimal notebook-friendly crypto signal experiment. Fetch tweets, analyze sentiment via OpenAI, pull price windows from Yahoo Finance, and store everything in a relational database.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: fill keys
jupyter lab            # open notebooks/00_quickstart.ipynb
```

Without API keys the notebook runs in mock mode and uses an in-memory SQLite database.
