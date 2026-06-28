import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "your-groq-key-here")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ANALYZER_MODEL    = "llama-3.3-70b-versatile"
HYPOTHESIS_MODEL  = "llama-3.3-70b-versatile"
VERIFIER_MODEL    = "llama-3.1-8b-instant"
SYNTHESIZER_MODEL = "llama-3.3-70b-versatile"

DATABASE_PATH = "archery_engine.db"

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
