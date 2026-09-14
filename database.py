# database.py
import sqlite3, json, os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import pandas as pd
from config import DB_PATH

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH)

_DDL = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date     TEXT NOT NULL,
    entry_time     TEXT NOT NULL,
    mood           INTEGER NOT NULL,
    stress         INTEGER NOT NULL,
    energy         INTEGER NOT NULL DEFAULT 3,
    sleep_hours    REAL,
    notes          TEXT DEFAULT '',
    emotion_tags   TEXT DEFAULT '[]',
    activities     TEXT DEFAULT '[]',
    ai_summary     TEXT DEFAULT '',
    ai_flags       TEXT DEFAULT '[]',
    therapist_note TEXT DEFAULT '',
    created_at     TEXT NOT NULL
);
"""

def _get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.executescript(_DDL)

def save_entry(mood, stress, energy, sleep_hours, notes,
               emotion_tags, activities, ai_summary="", ai_flags=None, entry_date=None):
    now = datetime.now()
    ai_flags = ai_flags or []
    entry_date = entry_date or now.strftime("%Y-%m-%d")
    sql = """INSERT INTO journal_entries
        (entry_date,entry_time,mood,stress,energy,sleep_hours,notes,
         emotion_tags,activities,ai_summary,ai_flags,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"""
    with _get_conn() as conn:
        cur = conn.execute(sql, (
            entry_date, now.strftime("%H:%M:%S"),
            mood, stress, energy, sleep_hours, notes,
            json.dumps(emotion_tags), json.dumps(activities),
            ai_summary, json.dumps(ai_flags), now.isoformat()
        ))
        return cur.lastrowid

def update_ai_fields(entry_id, ai_summary, ai_flags):
    with _get_conn() as conn:
        conn.execute("UPDATE journal_entries SET ai_summary=?,ai_flags=? WHERE id=?",
                     (ai_summary, json.dumps(ai_flags), entry_id))

def get_entry(entry_id):
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM journal_entries WHERE id=?", (entry_id,)).fetchone()
    return _row_to_dict(row) if row else None

def get_entries_df(days=90):
    with _get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM journal_entries ORDER BY entry_date DESC, entry_time DESC LIMIT 500", conn)
    if df.empty:
        return df
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    for col in ("emotion_tags","activities","ai_flags"):
        df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x,str) else [])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df[df["entry_date"] >= cutoff].sort_values("entry_date").reset_index(drop=True)

def get_recent_entries(limit=10):
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM journal_entries ORDER BY entry_date DESC, entry_time DESC LIMIT ?",
            (limit,)).fetchall()
    return [_row_to_dict(r) for r in rows]

def get_all_entries():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM journal_entries ORDER BY entry_date DESC, entry_time DESC").fetchall()
    return [_row_to_dict(r) for r in rows]

def delete_entry(entry_id):
    with _get_conn() as conn:
        conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))

def entry_exists_today():
    today = date.today().isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM journal_entries WHERE entry_date=? LIMIT 1", (today,)).fetchone()
    return row is not None

def get_streak():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT entry_date FROM journal_entries ORDER BY entry_date DESC").fetchall()
    if not rows:
        return 0
    import datetime as dt
    dates = [dt.date.fromisoformat(r["entry_date"]) for r in rows]
    streak, expected = 0, dt.date.today()
    for d in dates:
        if d == expected:
            streak += 1
            expected -= dt.timedelta(days=1)
        else:
            break
    return streak

def get_total_entries():
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]

def _row_to_dict(row):
    d = dict(row)
    for key in ("emotion_tags","activities","ai_flags"):
        if isinstance(d.get(key), str):
            try:    d[key] = json.loads(d[key])
            except: d[key] = []
    return d
