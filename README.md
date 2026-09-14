# MindJournal AI 🧠

An AI-powered mental wellness journaling app built with **Streamlit** and **Gemini 2.5 Flash**.

## Features
- **Daily Journal** — Log mood (1-5), stress, energy, sleep, emotion tags, activities, and free-text notes
- **Analytics Dashboard** — 6 interactive Plotly charts: timeline, distribution, weekly averages, sleep vs mood, emotion heatmap, calendar
- **AI Insights** — Gemini-powered trend reports and pattern detection
- **AI Companion Chat** — Conversational wellness companion powered by Gemini
- **Therapist View** — Structured clinical summaries + CSV export for professional review
- **Journal History** — Browse, filter, and delete past entries
- **Pattern Detection** — Automatic flagging of low-mood streaks, high-stress streaks, mood declines, crisis indicators, and poor sleep

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Gemini API Key
Either:
- Enter it in the app via **Settings → Gemini API Key** (recommended, stored in session only)
- Or create a `.env` file:
  ```
  GEMINI_API_KEY=your_api_key_here
  ```
  Get a free key at https://aistudio.google.com

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Deploy to Streamlit Cloud
1. Push this repo to GitHub
2. Go to https://share.streamlit.io
3. Connect your repo and set `GEMINI_API_KEY` as a secret

## Project Structure
```
Mental Health/
├── app.py            # Main Streamlit application (7 pages)
├── database.py       # SQLite persistence layer
├── ai_engine.py      # Gemini 2.5 Flash integration
├── analytics.py      # Trend analysis & chart builders
├── config.py         # Constants & configuration
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── .streamlit/
    └── config.toml   # Dark theme configuration
```

## Tech Stack
- **Frontend**: Streamlit (pure Python, no HTML/CSS/JS)
- **AI**: Google Gemini 2.5 Flash via `google-generativeai`
- **Database**: SQLite (local, via Python `sqlite3`)
- **Charts**: Plotly (interactive, zero-JS from user perspective)
- **Data**: Pandas + NumPy

## Disclaimer
This application is NOT a replacement for professional mental health care.
If you are in crisis, please contact a mental health professional or your local crisis line.
