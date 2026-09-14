# config.py
import os
from dotenv import load_dotenv
load_dotenv()

APP_TITLE   = "MindJournal AI"
APP_ICON    = "Brain"
APP_VERSION = "1.0.0"

GEMINI_MODEL   = "gemini-3.6-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DB_PATH = "mindjournal.db"

MOOD_SCALE = {
    1: ("Very Low",  "#ef4444"),
    2: ("Low",       "#f97316"),
    3: ("Neutral",   "#eab308"),
    4: ("Good",      "#22c55e"),
    5: ("Excellent", "#10b981"),
}
STRESS_SCALE = {
    1: ("Very Low",  "#10b981"),
    2: ("Low",       "#22c55e"),
    3: ("Moderate",  "#eab308"),
    4: ("High",      "#f97316"),
    5: ("Very High", "#ef4444"),
}
EMOTION_TAGS = [
    "Anxious","Calm","Excited","Grateful","Happy",
    "Hopeful","Irritable","Lonely","Motivated","Overwhelmed",
    "Peaceful","Sad","Stressed","Tired","Content",
]
CONCERN_LOW_MOOD_THRESHOLD    = 2
CONCERN_HIGH_STRESS_THRESHOLD = 4
CONCERN_STREAK_DAYS           = 3
CONCERN_WINDOW_DAYS           = 7

MOOD_COLOR    = "#6366f1"
STRESS_COLOR  = "#f43f5e"
NEUTRAL_COLOR = "#94a3b8"
ADMIN_PIN     = os.getenv("ADMIN_PIN", "1234")
