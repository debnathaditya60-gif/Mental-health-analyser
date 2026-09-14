# analytics.py
from __future__ import annotations
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from config import (CONCERN_LOW_MOOD_THRESHOLD, CONCERN_HIGH_STRESS_THRESHOLD,
    CONCERN_STREAK_DAYS, CONCERN_WINDOW_DAYS, MOOD_COLOR, STRESS_COLOR,
    NEUTRAL_COLOR, MOOD_SCALE, STRESS_SCALE)

_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Segoe UI, sans-serif", size=12),
    margin=dict(l=20,r=20,t=40,b=20),
    legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
)

def detect_concerning_patterns(df):
    flags = []
    if df.empty or len(df) < 2:
        return flags
    df = df.sort_values("entry_date").copy()
    df["low_mood"]   = df["mood"]   <= CONCERN_LOW_MOOD_THRESHOLD
    df["high_stress"]= df["stress"] >= CONCERN_HIGH_STRESS_THRESHOLD

    def trailing_streak(series):
        count = 0
        for val in reversed(series.tolist()):
            if val: count += 1
            else:   break
        return count

    lm = trailing_streak(df["low_mood"])
    if lm >= CONCERN_STREAK_DAYS:
        flags.append({"type":"LOW_MOOD_STREAK","severity":"high",
            "message":f"Mood has been low for {lm} consecutive days.",
            "dates": df[df["low_mood"]].tail(lm)["entry_date"].dt.strftime("%Y-%m-%d").tolist()})

    hs = trailing_streak(df["high_stress"])
    if hs >= CONCERN_STREAK_DAYS:
        flags.append({"type":"HIGH_STRESS_STREAK","severity":"medium",
            "message":f"Stress has been high for {hs} consecutive days.",
            "dates": df[df["high_stress"]].tail(hs)["entry_date"].dt.strftime("%Y-%m-%d").tolist()})

    if len(df) >= CONCERN_WINDOW_DAYS:
        recent  = df["mood"].iloc[-CONCERN_WINDOW_DAYS:].mean()
        earlier = df["mood"].iloc[:-CONCERN_WINDOW_DAYS].mean() if len(df) > CONCERN_WINDOW_DAYS else None
        if earlier is not None and (earlier - recent) >= 1.5:
            flags.append({"type":"MOOD_DECLINE","severity":"medium",
                "message":f"Mood declined {earlier-recent:.1f} pts over last {CONCERN_WINDOW_DAYS} days.",
                "dates":[]})

    crisis = df[(df["mood"] <= 2) & (df["stress"] >= 4)]
    if len(crisis) >= 2:
        flags.append({"type":"CRISIS_INDICATOR","severity":"critical",
            "message":f"{len(crisis)} days with very low mood AND very high stress detected.",
            "dates": crisis["entry_date"].dt.strftime("%Y-%m-%d").tolist()})

    if "sleep_hours" in df.columns:
        sl = df.dropna(subset=["sleep_hours"])
        if len(sl) >= 5 and sl["sleep_hours"].iloc[-5:].mean() < 6.0:
            flags.append({"type":"POOR_SLEEP","severity":"low",
                "message":f"Average sleep last 5 entries below 6 hours.",
                "dates":[]})
    return flags

def compute_summary_stats(df):
    if df.empty: return {}
    from collections import Counter
    def top_tags(col, n=5):
        c = Counter()
        for tags in df[col]:
            if isinstance(tags, list): c.update(tags)
        return c.most_common(n)
    def trend(vals):
        if len(vals) < 3: return "stable"
        slope = np.polyfit(range(len(vals)), vals, 1)[0]
        return "improving" if slope > 0.05 else ("declining" if slope < -0.05 else "stable")
    return {
        "avg_mood":     round(df["mood"].mean(), 2),
        "avg_stress":   round(df["stress"].mean(), 2),
        "avg_energy":   round(df["energy"].mean(), 2),
        "avg_sleep":    round(df["sleep_hours"].dropna().mean(), 2) if "sleep_hours" in df and df["sleep_hours"].notna().any() else None,
        "total_entries":len(df),
        "date_range":   (df["entry_date"].min(), df["entry_date"].max()),
        "mood_trend":   trend(df["mood"].tolist()),
        "stress_trend": trend(df["stress"].tolist()),
        "best_mood_day":  df.loc[df["mood"].idxmax(), "entry_date"],
        "worst_mood_day": df.loc[df["mood"].idxmin(), "entry_date"],
        "top_emotions":  top_tags("emotion_tags"),
        "top_activities":top_tags("activities"),
    }

def chart_mood_stress_timeline(df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df["entry_date"], y=df["mood"],
        name="Mood", mode="lines+markers",
        line=dict(color=MOOD_COLOR, width=2.5), marker=dict(size=6),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.1)"), secondary_y=False)
    fig.add_trace(go.Scatter(x=df["entry_date"], y=df["stress"],
        name="Stress", mode="lines+markers",
        line=dict(color=STRESS_COLOR, width=2.5, dash="dot"), marker=dict(size=6)), secondary_y=True)
    fig.update_layout(title="Mood & Stress Over Time", **_LAYOUT)
    fig.update_yaxes(title_text="Mood (1-5)",   range=[0.5,5.5], dtick=1, secondary_y=False)
    fig.update_yaxes(title_text="Stress (1-5)", range=[0.5,5.5], dtick=1, secondary_y=True)
    return fig

def chart_mood_distribution(df):
    counts = df["mood"].value_counts().sort_index()
    labels = [f"{MOOD_SCALE[i][0]} {i}" for i in counts.index if i in MOOD_SCALE]
    colors = [MOOD_SCALE[i][1] for i in counts.index if i in MOOD_SCALE]
    fig = go.Figure(go.Bar(x=labels, y=counts.values, marker_color=colors,
        text=counts.values, textposition="outside"))
    fig.update_layout(title="Mood Distribution", xaxis_title="Mood Level",
        yaxis_title="Days", **_LAYOUT)
    return fig

def chart_weekly_averages(df):
    df2 = df.copy()
    df2["week"] = df2["entry_date"].dt.to_period("W").dt.start_time
    weekly = df2.groupby("week")[["mood","stress","energy"]].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=weekly["week"], y=weekly["mood"],   name="Avg Mood",   marker_color=MOOD_COLOR,   opacity=0.85))
    fig.add_trace(go.Bar(x=weekly["week"], y=weekly["stress"], name="Avg Stress", marker_color=STRESS_COLOR, opacity=0.85))
    fig.add_trace(go.Bar(x=weekly["week"], y=weekly["energy"], name="Avg Energy", marker_color="#06b6d4",    opacity=0.85))
    fig.update_layout(title="Weekly Averages", barmode="group",
        xaxis_title="Week", yaxis=dict(range=[0,6],dtick=1), **_LAYOUT)
    return fig

def chart_sleep_vs_mood(df):
    sleep_df = df.dropna(subset=["sleep_hours"]).copy()
    if sleep_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No sleep data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**_LAYOUT)
        return fig
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sleep_df["sleep_hours"], y=sleep_df["mood"], mode="markers",
        marker=dict(size=12, color=sleep_df["stress"], colorscale="RdYlGn_r",
            showscale=True, colorbar=dict(title="Stress"), line=dict(width=1, color="white")),
        text=[f"Stress: {s}" for s in sleep_df["stress"]],
        hovertemplate="Sleep: %{x}h<br>Mood: %{y}<br>%{text}<extra></extra>", name="Entries"))
    if len(sleep_df) >= 2:
        xv = sleep_df["sleep_hours"].values.astype(float)
        yv = sleep_df["mood"].values.astype(float)
        coef = np.polyfit(xv, yv, 1)
        xl = np.linspace(xv.min(), xv.max(), 50)
        fig.add_trace(go.Scatter(x=xl, y=np.polyval(coef, xl), mode="lines",
            line=dict(color="#6366f1", width=2, dash="dash"),
            name=f"Trend (slope: {coef[0]:+.2f})"))
    fig.update_layout(title="Sleep vs Mood (coloured by Stress)",
        xaxis_title="Sleep Hours", yaxis_title="Mood (1-5)",
        yaxis=dict(range=[0.5,5.5], dtick=1), **_LAYOUT)
    return fig

def chart_emotion_heatmap(df):
    from collections import Counter
    all_tags = [t for tags in df["emotion_tags"] for t in (tags if isinstance(tags,list) else [])]
    if not all_tags:
        fig = go.Figure()
        fig.add_annotation(text="No emotion tags recorded yet", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(**_LAYOUT)
        return fig
    counter = Counter(all_tags)
    items = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:15]
    tags, counts = zip(*items)
    fig = go.Figure(go.Bar(x=list(counts), y=list(tags), orientation="h",
        marker_color=MOOD_COLOR, text=list(counts), textposition="outside"))
    fig.update_layout(title="Top Emotions Logged", xaxis_title="Frequency", **_LAYOUT)
    fig.update_yaxes(autorange="reversed")
    return fig

def chart_mood_calendar(df):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data yet", x=0.5, y=0.5, showarrow=False)
        return fig
    cal = df.groupby("entry_date")["mood"].mean().reset_index()
    cal["dow"]  = cal["entry_date"].dt.dayofweek
    cal["week"] = cal["entry_date"].dt.isocalendar().week.astype(int)
    fig = px.density_heatmap(cal, x="week", y="dow", z="mood",
        color_continuous_scale="RdYlGn", range_color=[1,5],
        labels={"week":"Week","dow":"Day","mood":"Avg Mood"},
        title="Mood Calendar Heatmap")
    fig.update_yaxes(tickvals=list(range(7)),
        ticktext=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    fig.update_layout(**_LAYOUT)
    return fig

def format_entries_for_ai(df, max_rows=30):
    rows = []
    for _, row in df.tail(max_rows).iterrows():
        d = row["entry_date"].strftime("%Y-%m-%d") if hasattr(row["entry_date"],"strftime") else str(row["entry_date"])
        tags = ", ".join(row["emotion_tags"]) if isinstance(row["emotion_tags"],list) and row["emotion_tags"] else "none"
        note = (row["notes"] or "")[:100].replace("\n"," ")
        rows.append(f"{d} | Mood:{row['mood']} Stress:{row['stress']} Energy:{row['energy']} Sleep:{row.get('sleep_hours','?')}h | [{tags}] | {note}")
    return "\n".join(rows)

def format_flags_for_ai(flags):
    if not flags: return "No flags detected."
    return "\n".join(f"[{f['severity'].upper()}] {f['type']}: {f['message']}" for f in flags)
