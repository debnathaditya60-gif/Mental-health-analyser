# ai_engine.py
import textwrap, json, re, requests
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
GEMINI_MODEL = "gemini-3.6-flash"  # hardcoded — do not change

_REST_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def _generate(prompt, api_key, temperature=0.7):
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("No Gemini API key set. Go to Settings and enter your key.")
    # ALL key formats (AIzaSy... AND AQ....) use ?key= query param
    url = _REST_URL.format(model=GEMINI_MODEL)
    resp = requests.post(
        url,
        params={"key": key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024
            }
        },
        timeout=30
    )
    if not resp.ok:
        raise ValueError(f"Gemini API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def is_api_key_valid(api_key):
    try:
        _generate("Say hello in one word.", api_key, 0.1)
        return True, ""
    except Exception as e:
        return False, str(e)[:300]

def analyse_entry(mood, stress, energy, sleep_hours, notes, emotion_tags, activities, api_key):
    mood_lbl   = {1:"very low",2:"low",3:"neutral",4:"good",5:"excellent"}
    stress_lbl = {1:"very low",2:"low",3:"moderate",4:"high",5:"very high"}
    sleep_text = f"{sleep_hours} hours" if sleep_hours else "not recorded"
    tags_text  = ", ".join(emotion_tags) if emotion_tags else "none"
    act_text   = ", ".join(activities)   if activities   else "none"
    prompt = f"""You are a compassionate mental wellness AI assistant.

Today journal entry:
- Mood: {mood}/5 ({mood_lbl.get(mood,"")})
- Stress: {stress}/5 ({stress_lbl.get(stress,"")})
- Energy: {energy}/5
- Sleep: {sleep_text}
- Emotions: {tags_text}
- Activities: {act_text}
- Notes: "{notes}"

Reply ONLY in this exact JSON format (no markdown, no extra text):
{{
  "summary": "<2-3 sentence empathetic reflection>",
  "sentiment": "<positive|neutral|negative>",
  "flags": [],
  "suggestions": ["<tip 1>","<tip 2>","<tip 3>"]
}}

Add to flags[] ONLY if mood<=2 AND stress>=4, or notes mention hopelessness or self-harm."""

    raw = _generate(prompt, api_key, 0.4)
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        result = json.loads(raw)
    except:
        result = {
            "summary": "Thank you for logging today. Keep reflecting.",
            "sentiment": "neutral",
            "flags": [],
            "suggestions": [
                "Take a 5-minute mindful breathing break.",
                "Drink water and stretch for 2 minutes.",
                "Write one thing you are grateful for today."
            ]
        }
    result.setdefault("flags", [])
    result.setdefault("suggestions", [])
    result.setdefault("sentiment", "neutral")
    result.setdefault("summary", "")
    return result

def analyse_trends(entries_summary, api_key):
    prompt = f"""You are a mental wellness AI analyst. Review this journal history and write a concise empathetic trend report (max 250 words) covering:
1. Emotional patterns (improving, declining, or cyclical)
2. Recurring stressors or positive triggers
3. 2-3 evidence-based recommendations for next week
4. Whether therapist review is recommended

Journal history:
{entries_summary}

Write in second-person. Be warm, non-judgmental, and specific."""
    return _generate(prompt, api_key, 0.5)

def generate_therapist_report(entries_summary, flags_summary, api_key):
    prompt = f"""You are a clinical support AI. Generate a structured summary for a licensed therapist.

Patient journal data:
{entries_summary}

Flagged concerns:
{flags_summary or "None"}

Include these sections:
1. Overview - mood and stress trajectory
2. Flagged Patterns - concerning periods with dates
3. Positive Indicators - protective factors
4. Recommended Focus Areas - 3 therapy topics
5. Risk Assessment - Low/Moderate/High with rationale

Be factual, clinical, concise. Use bullet points."""
    return _generate(prompt, api_key, 0.3)

def chat_response(user_message, conversation_history, context_summary, api_key):
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in conversation_history[-6:])
    prompt = f"""You are MindJournal AI, a compassionate mental wellness companion. You are NOT a therapist.

User recent wellness context:
{context_summary}

Recent conversation:
{history_text}

User says: "{user_message}"

Respond warmly in 2-4 sentences. If distress is expressed, gently recommend a mental health professional. Never diagnose or prescribe."""
    return _generate(prompt, api_key, 0.7)

def get_daily_affirmation(mood, emotion_tags, api_key):
    tags_text = ", ".join(emotion_tags) if emotion_tags else "reflective"
    prompt = f"""Generate one short genuine non-cliched affirmation (1-2 sentences) for someone feeling {tags_text} with mood {mood}/5 today. Make it personal, warm, grounding. No hashtags or emojis."""
    return _generate(prompt, api_key, 0.9)
