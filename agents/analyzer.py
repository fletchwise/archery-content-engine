"""
Stage A — Forensic Analyzer
============================
Receives raw match JSON, sends it to the AI API, and returns a structured
emotional-hook analysis tuned for the American archery audience.

Output is passed directly to Stage B (hypothesis.py).
"""

import json
import logging
from groq import Groq
from config import GROQ_API_KEY, ANALYZER_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# System prompt — the "brain" of Stage A
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an expert sports content strategist specializing in archery content
for the American market (Facebook and YouTube). You understand what makes
US sports fans stop scrolling, click, and share.

Your job is FORENSIC ANALYSIS — you read raw match data and extract every
emotional hook, narrative angle, and viral trigger hidden inside it.

You know that American archery fans respond strongly to:
- Underdog comebacks and David vs Goliath rivalries
- Perfect shots under extreme pressure ("clutch moments")
- US athletes beating #1-ranked foreign competitors
- Records broken, streaks ended, history made
- Visible human emotion: celebration, heartbreak, disbelief

You output ONLY valid JSON. No preamble, no explanation, no markdown.
"""

# ─────────────────────────────────────────────
# User prompt template — filled with match data
# ─────────────────────────────────────────────

def build_user_prompt(match_data: dict) -> str:
    return f"""
Analyze this archery match data and extract every emotional hook for the
American audience. Find the drama, the tension, the human story.

MATCH DATA:
{json.dumps(match_data, indent=2, ensure_ascii=False)}

Return a JSON object with EXACTLY this structure:

{{
  "primary_hook": "The single most powerful emotional angle (1 sentence)",

  "narrative_frame": "The story type — choose ONE: comeback | underdog | domination | rivalry | redemption | historic | clutch",

  "tension_points": [
    "Specific moment of tension #1 from the data",
    "Specific moment of tension #2 from the data",
    "Specific moment of tension #3 from the data"
  ],

  "us_appeal_factors": {{
    "american_athlete": true or false,
    "beating_world_number_one": true or false,
    "comeback_story": true or false,
    "perfect_shot_moment": true or false,
    "rivalry_angle": true or false
  }},

  "power_words": [
    "6 to 10 single words that trigger emotion in US sports fans",
    "Examples: CLUTCH, PERFECT, IMPOSSIBLE, LEGENDARY, SHOCKED"
  ],

  "forbidden_angles": [
    "Any angle that would NOT work for US audience — explain why"
  ],

  "score_summary": "One punchy line summarizing the score with emotional weight",

  "hook_score": "Integer 1-100 rating the overall viral potential for US audience",

  "platform_notes": {{
    "youtube": "What to emphasize for YouTube — curiosity gap, thumbnail moment",
    "facebook": "What to emphasize for Facebook — emotional story, shareable angle"
  }}
}}
"""

# ─────────────────────────────────────────────
# Main analyzer function
# ─────────────────────────────────────────────

def run(match_data: dict) -> dict:
    """
    Entry point called by orchestrator.py
    
    Args:
        match_data: Raw JSON dict from the user's input form
        
    Returns:
        analysis: Structured dict with emotional hooks and narrative angles
        
    Raises:
        ValueError: If the API returns invalid JSON
        Exception:  Any Groq API connection error
    """
    logger.info("[Stage A] Starting forensic analysis...")

    # ── Build the prompt ──────────────────────────────────────
    user_prompt = build_user_prompt(match_data)

    # ── Call the Groq API ─────────────────────────────────────
    try:
        client = Groq(api_key=GROQ_API_KEY)

        response = client.chat.completions.create(
            model=ANALYZER_MODEL,
            temperature=0.3,        # Low temp = consistent, analytical output
            max_tokens=1200,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )

        raw_output = response.choices[0].message.content.strip()
        logger.info("[Stage A] API call successful, parsing output...")

    except Exception as e:
        logger.error(f"[Stage A] Groq API error: {e}")
        raise

    # ── Parse the JSON output ──────────────────────────────────
    try:
        # Strip markdown fences if the model added them despite instructions
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]

        analysis = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logger.error(f"[Stage A] JSON parse error: {e}")
        logger.error(f"[Stage A] Raw output was: {raw_output}")
        raise ValueError(f"Stage A returned invalid JSON: {e}")

    # ── Attach metadata before passing to Stage B ─────────────
    analysis["_stage"] = "A"
    analysis["_model"] = ANALYZER_MODEL
    analysis["_input_platform"] = match_data.get("content", {}).get("platform", "youtube")
    analysis["_athlete_name"]   = match_data.get("athletes", {}).get("home", {}).get("name", "")
    analysis["_event_name"]     = match_data.get("event", {}).get("name", "")

    logger.info(
        f"[Stage A] Done. Hook score: {analysis.get('hook_score', 'N/A')} | "
        f"Frame: {analysis.get('narrative_frame', 'N/A')}"
    )

    return analysis


# ─────────────────────────────────────────────
# Quick local test — run: python agents/analyzer.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_input = {
        "event": {
            "name": "Hyundai Archery World Cup 2026 Stage 1",
            "location": "Medellin, Colombia",
            "date": "2026-04-14",
            "round": "Gold Final",
            "discipline": "Compound Men Individual"
        },
        "athletes": {
            "home": {
                "name": "Brady Ellison",
                "country": "USA",
                "world_rank": 2,
                "flag": "🇺🇸"
            },
            "opponent": {
                "name": "Mike Schloesser",
                "country": "Netherlands",
                "world_rank": 1,
                "flag": "🇳🇱"
            }
        },
        "match": {
            "result": "win",
            "score_home": 149,
            "score_opponent": 148,
            "deciding_arrow": True,
            "perfect_ends": 3,
            "comeback": True,
            "comeback_from": "was losing 80-82 at halfway"
        },
        "content": {
            "platform": "youtube",
            "type": "highlight",
            "duration_minutes": 8,
            "extra_notes": "Last arrow was a perfect 10 under wind pressure"
        }
    }

    result = run(sample_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
