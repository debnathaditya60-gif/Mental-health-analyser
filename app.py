# app.py - MindJournal AI
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import database as db
import ai_engine as ai
import analytics as ana
from config import (APP_TITLE, APP_VERSION, MOOD_SCALE, STRESS_SCALE,
                    EMOTION_TAGS, GEMINI_API_KEY)

st.set_page_config(page_title="MindJournal AI", page_icon="🧠",
                   layout="wide", initial_sidebar_state="expanded")
db.init_db()

# ── Session state ──────────────────────────────────────────────────────────
for k,v in {"api_key":GEMINI_API_KEY,"chat_history":[],"last_entry_id":None,
            "ai_result":None,"page":"Daily Journal","affirmation":"",
            "affirmation_date":None,"admin_unlocked":False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _key():  return st.session_state.get("api_key","")
def _need_key():
    if not _key():
        st.warning("Please enter your Gemini API Key in Settings to use AI features.")
        st.stop()

PAGES = ["Daily Journal","Analytics Dashboard","AI Insights",
         "AI Companion Chat","Therapist View","Journal History",
         "Admin Dashboard","Settings"]

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 MindJournal AI")
    st.caption(f"v{APP_VERSION}")
    st.divider()
    st.session_state["page"] = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.divider()
    st.metric("Total Entries", db.get_total_entries())
    st.metric("Day Streak",    f"{db.get_streak()} days")
    df7 = db.get_entries_df(days=7)
    if not df7.empty:
        st.metric("7-day Avg Mood",   f"{df7['mood'].mean():.1f} / 5")
        st.metric("7-day Avg Stress", f"{df7['stress'].mean():.1f} / 5")
    st.divider()
    st.caption("Consistency is the key to insight.")

page = st.session_state["page"]

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Daily Journal
# ══════════════════════════════════════════════════════════════════════════════
def page_journal():
    st.title("📓 Daily Journal Entry")
    st.caption(f"Today — {date.today().strftime('%A, %B %d, %Y')}")
    if db.entry_exists_today():
        st.info("You have already logged an entry today. You can add another if you like.")

    with st.form("journal_form", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            st.subheader("Mood")
            mood = st.select_slider("How are you feeling?", options=[1,2,3,4,5], value=3,
                format_func=lambda x: f"{MOOD_SCALE[x][0]} {x}/5")
            st.caption(f"Selected: {MOOD_SCALE[mood][0]}")
        with c2:
            st.subheader("Stress Level")
            stress = st.select_slider("Current stress level?", options=[1,2,3,4,5], value=3,
                format_func=lambda x: f"{STRESS_SCALE[x][0]} {x}/5")
            st.caption(f"Selected: {STRESS_SCALE[stress][0]}")
        with c3:
            st.subheader("Energy & Sleep")
            energy = st.select_slider("Energy today?", options=[1,2,3,4,5], value=3,
                format_func=lambda x: f"{x}/5")
            sleep_hours = st.number_input("Hours slept last night",
                min_value=0.0, max_value=24.0, value=7.0, step=0.5)

        st.subheader("Emotion Tags")
        emotion_tags = st.multiselect("Select all that apply:", EMOTION_TAGS,
            placeholder="Choose emotions...")
        st.subheader("Activities Today")
        activities = st.multiselect("What did you do?",
            ["Exercise","Meditation","Reading","Socialising","Work","Creative hobby",
             "Nature walk","Cooking","Gaming","Music","Journaling","Rest / Self-care"],
            placeholder="Select activities...")
        st.subheader("Personal Notes")
        notes = st.text_area("Write freely — this is your safe space:",
            placeholder="How was your day? Any wins or challenges?", height=140)
        use_ai   = st.toggle("Get AI reflection after saving", value=True)
        submitted = st.form_submit_button("Save Entry", type="primary",
                                          use_container_width=True)

    if submitted:
        eid = db.save_entry(mood=mood, stress=stress, energy=energy,
            sleep_hours=sleep_hours, notes=notes,
            emotion_tags=emotion_tags, activities=activities)
        st.session_state["last_entry_id"] = eid
        st.session_state["ai_result"] = None
        if use_ai and _key():
            with st.spinner("Gemini is reflecting on your entry..."):
                try:
                    res = ai.analyse_entry(mood,stress,energy,sleep_hours,notes,
                                           emotion_tags,activities,_key())
                    db.update_ai_fields(eid, res["summary"], res.get("flags",[]))
                    st.session_state["ai_result"] = res
                except Exception as e:
                    st.warning(f"AI analysis unavailable: {e}")
        st.success("Entry saved successfully!")
        st.balloons()

    if st.session_state.get("ai_result"):
        res = st.session_state["ai_result"]
        st.divider()
        st.subheader("AI Reflection")
        icon = {"positive":"🌟","neutral":"💙","negative":"💛"}.get(res.get("sentiment","neutral"),"💙")
        st.markdown(f"{icon} {res['summary']}")
        if res.get("flags"):
            st.error("**Concern flagged** — consider reaching out to a mental health professional.")
            for fl in res["flags"]:
                st.markdown(f"- {fl}")
        if res.get("suggestions"):
            st.subheader("Micro-Suggestions for Today")
            for i,s in enumerate(res["suggestions"],1):
                st.markdown(f"**{i}.** {s}")
        if _key() and str(date.today()) != str(st.session_state.get("affirmation_date")):
            with st.spinner("Generating your daily affirmation..."):
                try:
                    aff = ai.get_daily_affirmation(mood, emotion_tags, _key())
                    st.session_state["affirmation"] = aff
                    st.session_state["affirmation_date"] = date.today()
                except: pass
        if st.session_state.get("affirmation"):
            st.divider()
            st.subheader("Your Daily Affirmation")
            st.info(f'"{st.session_state["affirmation"]}"')

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Analytics Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def page_analytics():
    st.title("📊 Analytics Dashboard")
    col_f,_ = st.columns([1,3])
    with col_f:
        days_back = st.selectbox("Time range",[7,14,30,60,90,180],index=2,
            format_func=lambda x:f"Last {x} days")
    df = db.get_entries_df(days=days_back)
    if df.empty:
        st.info("No journal entries found. Start logging to see analytics!")
        return

    stats = ana.compute_summary_stats(df)
    flags = ana.detect_concerning_patterns(df)
    if flags:
        crit = [f for f in flags if f["severity"]=="critical"]
        if crit: st.error(f"**{len(crit)} Critical Pattern(s) Detected** — Therapist review recommended.")
        else:    st.warning(f"**{len(flags)} Pattern(s) Flagged** — Review in Therapist View.")

    st.subheader("Key Metrics")
    def _arr(t): return {"improving":"↗ Improving","declining":"↘ Declining","stable":"→ Stable"}.get(t,"")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Avg Mood",   f"{stats['avg_mood']:.1f}/5",   _arr(stats.get("mood_trend","")))
    c2.metric("Avg Stress", f"{stats['avg_stress']:.1f}/5", _arr(stats.get("stress_trend","")))
    c3.metric("Avg Energy", f"{stats['avg_energy']:.1f}/5")
    c4.metric("Avg Sleep",  f"{stats['avg_sleep']} hrs" if stats.get("avg_sleep") else "—")
    c5.metric("Entries",    stats["total_entries"])
    st.divider()

    st.subheader("Mood & Stress Timeline")
    st.plotly_chart(ana.chart_mood_stress_timeline(df), use_container_width=True)
    cl,cr = st.columns(2)
    with cl: st.plotly_chart(ana.chart_mood_distribution(df),  use_container_width=True)
    with cr: st.plotly_chart(ana.chart_weekly_averages(df),    use_container_width=True)
    cl2,cr2 = st.columns(2)
    with cl2: st.plotly_chart(ana.chart_sleep_vs_mood(df),     use_container_width=True)
    with cr2: st.plotly_chart(ana.chart_emotion_heatmap(df),   use_container_width=True)
    st.subheader("Mood Calendar")
    st.plotly_chart(ana.chart_mood_calendar(df), use_container_width=True)

    st.subheader("Most Common Emotions & Activities")
    ce,ca = st.columns(2)
    with ce:
        st.markdown("**Emotions**")
        for tag,cnt in stats.get("top_emotions",[]):
            st.progress(min(cnt/max(1,len(df)),1.0), text=f"{tag} ({cnt}x)")
    with ca:
        st.markdown("**Activities**")
        for act,cnt in stats.get("top_activities",[]):
            st.progress(min(cnt/max(1,len(df)),1.0), text=f"{act} ({cnt}x)")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — AI Insights
# ══════════════════════════════════════════════════════════════════════════════
def page_ai_insights():
    st.title("🤖 AI Insights")
    _need_key()
    days_back = st.selectbox("Analyse entries from the last:",[7,14,30,60],index=1,
        format_func=lambda x:f"{x} days")
    df = db.get_entries_df(days=days_back)
    if df.empty:
        st.info("No entries to analyse yet.")
        return
    if st.button("Generate AI Trend Analysis", type="primary"):
        with st.spinner("Gemini is analysing your wellness patterns..."):
            try:
                report = ai.analyse_trends(ana.format_entries_for_ai(df), _key())
                st.subheader("Your Wellness Trend Report")
                st.markdown(report)
            except Exception as e:
                st.error(f"AI analysis failed: {e}")
    st.divider()
    st.subheader("Detected Patterns")
    flags = ana.detect_concerning_patterns(df)
    if not flags:
        st.success("No concerning patterns detected in this period. Keep it up!")
    else:
        sev_icon = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🔵"}
        for fl in flags:
            icon = sev_icon.get(fl["severity"],"⚪")
            with st.expander(f"{icon} {fl['type'].replace('_',' ').title()} — {fl['severity'].upper()}"):
                st.markdown(fl["message"])
                if fl.get("dates"):
                    st.caption("Dates: " + ", ".join(fl["dates"]))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — AI Companion Chat
# ══════════════════════════════════════════════════════════════════════════════
def page_chat():
    st.title("💬 AI Companion Chat")
    _need_key()
    st.caption("Talk freely with your AI wellness companion. This is NOT therapy.")
    df = db.get_entries_df(days=7)
    context = ana.format_entries_for_ai(df, max_rows=7) if not df.empty else "No recent journal data."
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("How are you feeling? What is on your mind?"):
        st.session_state["chat_history"].append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    resp = ai.chat_response(prompt, st.session_state["chat_history"],
                                            context, _key())
                    st.markdown(resp)
                    st.session_state["chat_history"].append({"role":"assistant","content":resp})
                except Exception as e:
                    err = f"Unable to reach AI: {e}"
                    st.error(err)
                    st.session_state["chat_history"].append({"role":"assistant","content":err})
    if st.session_state["chat_history"]:
        if st.button("Clear Chat"):
            st.session_state["chat_history"] = []
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Therapist View
# ══════════════════════════════════════════════════════════════════════════════
def page_therapist():
    st.title("🩺 Therapist View")
    st.caption("Structured clinical summary for mental health professionals.")
    days_back = st.selectbox("Report period:",[14,30,60,90],index=1,
        format_func=lambda x:f"Last {x} days")
    df = db.get_entries_df(days=days_back)
    if df.empty:
        st.info("No entries available for this period.")
        return
    flags = ana.detect_concerning_patterns(df)
    st.subheader("Flagged Patterns")
    if not flags:
        st.success("No concerning patterns detected in this period.")
    else:
        rows = [{"Severity":f["severity"].upper(),
                 "Type":f["type"].replace("_"," ").title(),
                 "Message":f["message"],
                 "Dates":", ".join(f.get("dates",[])) or "—"} for f in flags]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("Trend Overview")
    st.plotly_chart(ana.chart_mood_stress_timeline(df), use_container_width=True)
    st.divider()
    st.subheader("AI Clinical Report")
    if not _key():
        st.warning("Add your Gemini API key in Settings to generate the AI clinical report.")
    else:
        if st.button("Generate Clinical Summary", type="primary"):
            with st.spinner("Generating clinical summary..."):
                try:
                    report = ai.generate_therapist_report(
                        ana.format_entries_for_ai(df,50),
                        ana.format_flags_for_ai(flags), _key())
                    st.markdown(report)
                    with st.expander("Raw Report Text"):
                        st.code(report, language=None)
                except Exception as e:
                    st.error(f"Report generation failed: {e}")
    st.divider()
    st.subheader("Export Data")
    exp = df.copy(); exp["entry_date"] = exp["entry_date"].astype(str)
    st.download_button("Download CSV", data=exp.to_csv(index=False),
        file_name=f"mindjournal_export_{date.today()}.csv", mime="text/csv",
        use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Journal History
# ══════════════════════════════════════════════════════════════════════════════
def page_history():
    st.title("📚 Journal History")
    entries = db.get_recent_entries(limit=50)
    if not entries:
        st.info("No journal entries yet. Head to Daily Journal to get started!")
        return
    cf1,cf2,cf3 = st.columns(3)
    with cf1: mood_filter   = st.multiselect("Filter by Mood",   [1,2,3,4,5],
        format_func=lambda x:f"{MOOD_SCALE[x][0]} {x}/5")
    with cf2: stress_filter = st.multiselect("Filter by Stress", [1,2,3,4,5],
        format_func=lambda x:f"{STRESS_SCALE[x][0]} {x}/5")
    with cf3: flagged_only  = st.toggle("Show flagged only")

    for entry in entries:
        mi = MOOD_SCALE.get(entry["mood"],   ("?","#888"))
        si = STRESS_SCALE.get(entry["stress"],("?","#888"))
        fl = entry.get("ai_flags",[])
        if mood_filter   and entry["mood"]   not in mood_filter:   continue
        if stress_filter and entry["stress"] not in stress_filter: continue
        if flagged_only  and not fl:                               continue
        flag_badge = " [FLAGGED]" if fl else ""
        title = f"{entry['entry_date']} {entry.get('entry_time','')} | Mood {mi[0]} | Stress {si[0]}{flag_badge}"
        with st.expander(title):
            cc1,cc2,cc3,cc4 = st.columns(4)
            cc1.metric("Mood",   f"{mi[0]} ({entry['mood']}/5)")
            cc2.metric("Stress", f"{si[0]} ({entry['stress']}/5)")
            cc3.metric("Energy", f"{entry.get('energy','—')}/5")
            cc4.metric("Sleep",  f"{entry.get('sleep_hours','—')} hrs")
            if entry.get("emotion_tags"):
                st.markdown("**Emotions:** " + ", ".join(entry["emotion_tags"]))
            if entry.get("activities"):
                st.markdown("**Activities:** " + ", ".join(entry["activities"]))
            if entry.get("notes"):
                st.markdown("**Notes:**")
                st.markdown(f"> {entry['notes']}")
            if entry.get("ai_summary"):
                st.info(f"**AI Reflection:** {entry['ai_summary']}")
            if fl:
                st.error("**AI Flags:** " + " | ".join(fl))
            if st.button("Delete entry", key=f"del_{entry['id']}"):
                db.delete_entry(entry["id"]); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — Admin Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def page_admin():
    st.title("🛡️ Admin Dashboard")
    st.caption("System overview, data health, and full journal management.")

    if not st.session_state.get("admin_unlocked", False):
        st.subheader("Admin Access")
        pin = st.text_input("Enter Admin PIN", type="password", placeholder="Default: 1234")
        if st.button("Unlock", type="primary"):
            if pin == "1234":
                st.session_state["admin_unlocked"] = True
                st.rerun()
            else:
                st.error("Incorrect PIN.")
        st.caption("Default PIN is 1234.")
        return

    if st.button("Lock Admin"):
        st.session_state["admin_unlocked"] = False
        st.rerun()

    st.divider()
    st.subheader("App Health")
    import os, sys
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Python",    sys.version.split()[0])
    c2.metric("Streamlit", st.__version__)
    db_sz = round(os.path.getsize(db._DB_PATH)/1024,1) if os.path.exists(db._DB_PATH) else 0
    c3.metric("Database",  f"{db_sz} KB")
    c4.metric("API Key",   "Set" if _key() else "Missing")

    st.divider()
    st.subheader("Data Overview")
    df_all = db.get_entries_df(days=365)
    total  = db.get_total_entries()
    streak = db.get_streak()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Entries", total)
    c2.metric("Day Streak",    f"{streak} days")
    if not df_all.empty:
        c3.metric("Avg Mood",   str(round(df_all["mood"].mean(),2)) + "/5")
        c4.metric("Avg Stress", str(round(df_all["stress"].mean(),2)) + "/5")
        sl = df_all["sleep_hours"].dropna()
        c5.metric("Avg Sleep",  f"{sl.mean():.1f} hrs" if not sl.empty else "—")
        min_d = df_all["entry_date"].min().strftime("%Y-%m-%d")
        max_d = df_all["entry_date"].max().strftime("%Y-%m-%d")
        st.caption(f"Journal spans {min_d} to {max_d}")
    else:
        c3.metric("Avg Mood","—"); c4.metric("Avg Stress","—"); c5.metric("Avg Sleep","—")

    if not df_all.empty:
        st.divider()
        st.subheader("Full Mood and Stress Timeline")
        st.plotly_chart(ana.chart_mood_stress_timeline(df_all), use_container_width=True)

        st.divider()
        st.subheader("All Entries Table")
        cs,cl2 = st.columns([2,1])
        with cs:  sort_col = st.selectbox("Sort by",["entry_date","mood","stress","energy","sleep_hours"])
        with cl2: limit    = st.selectbox("Show rows",[10,25,50,100],index=1)
        tbl = df_all.sort_values(sort_col, ascending=False).head(limit).copy()
        tbl["entry_date"] = tbl["entry_date"].dt.strftime("%Y-%m-%d")
        tbl["notes"] = tbl["notes"].apply(lambda x:(str(x)[:60]+"...") if x and len(str(x))>60 else x)
        st.dataframe(
            tbl[["entry_date","mood","stress","energy","sleep_hours","notes"]].rename(columns={
                "entry_date":"Date","mood":"Mood","stress":"Stress",
                "energy":"Energy","sleep_hours":"Sleep hrs","notes":"Notes"}),
            use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Active Concern Flags")
    if not df_all.empty:
        flags = ana.detect_concerning_patterns(df_all)
        if not flags:
            st.success("No active concern flags.")
        else:
            sev_icon = {"critical":"[CRITICAL]","high":"[HIGH]","medium":"[MEDIUM]","low":"[LOW]"}
            for fl in flags:
                badge = sev_icon.get(fl["severity"],"[?]")
                ftype = fl["type"].replace("_"," ").title()
                st.warning(f"{badge} {ftype}: {fl['message']}")
    else:
        st.info("No journal data yet.")

    st.divider()
    st.subheader("Export and Backup")
    if not df_all.empty:
        exp = df_all.copy(); exp["entry_date"] = exp["entry_date"].astype(str)
        ce1,ce2 = st.columns(2)
        with ce1:
            st.download_button("Export All as CSV",
                data=exp.to_csv(index=False),
                file_name=f"mindjournal_{date.today()}.csv",
                mime="text/csv", use_container_width=True)
        with ce2:
            st.download_button("Export All as JSON",
                data=exp.to_json(orient="records"),
                file_name=f"mindjournal_{date.today()}.json",
                mime="application/json", use_container_width=True)
    else:
        st.info("No data to export.")

    st.divider()
    st.subheader("Danger Zone")
    with st.expander("Destructive Actions — click to expand"):
        st.error("These actions are permanent and irreversible.")
        confirm = st.text_input("Type CONFIRM DELETE to enable", key="admin_confirm")
        if st.button("Delete ALL Entries", type="secondary", disabled=(confirm != "CONFIRM DELETE")):
            conn = sqlite3.connect(db._DB_PATH)
            conn.execute("DELETE FROM journal_entries")
            conn.commit(); conn.close()
            st.session_state["chat_history"] = []
            st.session_state["ai_result"] = None
            st.success("All entries deleted."); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Settings
# ══════════════════════════════════════════════════════════════════════════════
def page_settings():
    st.title("⚙️ Settings")
    st.subheader("Gemini API Configuration")
    api_in = st.text_input("Gemini API Key",
        value=st.session_state.get("api_key",""),
        type="password", placeholder="AIzaSy... or AQ.Ab8...",
        help="Get a free key at https://aistudio.google.com/apikey")
    cs1,cs2 = st.columns(2)
    with cs1:
        if st.button("Save API Key", type="primary"):
            st.session_state["api_key"] = api_in
            st.success("API Key saved for this session.")
    with cs2:
        if st.button("Validate Key"):
            if api_in:
                with st.spinner("Validating..."):
                    ok, err = ai.is_api_key_valid(api_in)
                    if ok:   st.success("API Key is valid!")
                    else:    st.error(f"Invalid: {err}")
            else:
                st.warning("Enter an API key first.")

    st.divider()
    st.subheader("Key Format Guide")
    st.info("""**Permanent key (recommended):** Starts with `AIzaSy...`  
Get it at: https://aistudio.google.com/apikey → Click **Create API key**  
This key never expires.

**OAuth token (short-lived):** Starts with `AQ.Ab8...`  
These expire in ~1 hour and will stop working. Use the permanent key instead.""")

    st.divider()
    st.subheader("About MindJournal AI")
    st.markdown(f"""
**MindJournal AI** v{APP_VERSION} — powered by **Gemini 2.5 Flash**

**Features:** Daily mood/stress/energy/sleep tracking · Emotion tags · AI reflections ·  
6 interactive charts · Pattern detection · Therapist reports · AI chat companion · CSV/JSON export

**Data Privacy:** All data stored locally in SQLite (`mindjournal.db`). Nothing leaves your device.

**Disclaimer:** This app is NOT a replacement for professional mental health care.
""")
    st.divider()
    st.subheader("Data Management")
    cd1,cd2 = st.columns(2)
    with cd1: st.metric("Total Entries", db.get_total_entries())
    with cd2: st.metric("Database",      "mindjournal.db (local)")
    with st.expander("Danger Zone"):
        st.warning("Irreversible.")
        confirm = st.text_input("Type DELETE to confirm")
        if st.button("Delete ALL entries", type="secondary"):
            if confirm == "DELETE":
                conn = sqlite3.connect(db._DB_PATH)
                conn.execute("DELETE FROM journal_entries")
                conn.commit(); conn.close()
                st.session_state["chat_history"] = []
                st.session_state["ai_result"] = None
                st.success("All entries deleted."); st.rerun()
            else:
                st.error("Type DELETE (all caps) to confirm.")

# ══════════════════════════════════════════════════════════════════════════════
# Router
# ══════════════════════════════════════════════════════════════════════════════
if   page == "Daily Journal":       page_journal()
elif page == "Analytics Dashboard": page_analytics()
elif page == "AI Insights":         page_ai_insights()
elif page == "AI Companion Chat":   page_chat()
elif page == "Therapist View":      page_therapist()
elif page == "Journal History":     page_history()
elif page == "Admin Dashboard":     page_admin()
elif page == "Settings":            page_settings()
