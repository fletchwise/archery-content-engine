"""
Stage B — Hypothesis Generator
================================
Receives Stage A's emotional analysis and generates 5 title variations,
each with a DIFFERENT psychological style for the US archery audience.

Temperature: 0.8 (high creativity — we want variety, not repetition)
Output: passed directly to Stage C (verifier.py)
"""

import json
import logging
from groq import Groq
from config import GROQ_API_KEY, HYPOTHESIS_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an elite YouTube and Facebook title copywriter for American sports content.
You specialize in archery — a sport that is exploding in the US ahead of the 2028 Olympics.

You know exactly how American sports fans think:
- SUSPENSE: They click on tension they haven't resolved yet
- STATS: Specific numbers make drama feel real and credible
- DRAMA: A great human story beats pure information every time
- ATHLETE: Named heroes build loyalty and parasocial connection
- RIVALRY: USA vs the world is the oldest American sports narrative

Each of your 5 titles must feel COMPLETELY DIFFERENT in style and angle.
Never write two titles that feel similar — they must serve different psychological needs.

Platform rules you never break:
- YouTube: max 100 characters. Curiosity gap beats full story.
- Facebook: max 80 characters. Emotional punch beats cleverness.

You output ONLY valid JSON. No preamble, no explanation, no markdown fences.
"""

# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────

def build_user_prompt(analysis: dict, platform: str) -> str:
    limit = 100 if platform == "youtube" else 80
    power_words = ", ".join(analysis.get("power_words", []))

    return f"""
Generate 5 {platform.upper()} titles. Max {limit} characters each.
Each title must use a COMPLETELY DIFFERENT psychological style.

─── STAGE A INTELLIGENCE ─────────────────────────
Primary hook   : {analysis.get("primary_hook", "")}
Narrative frame: {analysis.get("narrative_frame", "")}
Tension points : {json.dumps(analysis.get("tension_points", []), ensure_ascii=False)}
Power words    : {power_words}
Score summary  : {analysis.get("score_summary", "")}
Platform note  : {analysis.get("platform_notes", {}).get(platform, "")}
Athlete        : {analysis.get("_athlete_name", "")}
Event          : {analysis.get("_event_name", "")}
──────────────────────────────────────────────────

REQUIRED STYLES (one title each, in this order):

1. SUSPENSE  — Open loop / cliffhanger. Reader MUST click to resolve the tension.
               Example pattern: "He was [bad situation]... what happened next [reaction]"

2. STATS     — Score-driven. Specific numbers make the drama feel undeniably real.
               Example pattern: "[exact score]: The [superlative] [event] in [year]"

3. DRAMA     — Cinematic emotional storytelling. Full human story compressed into one line.
               Example pattern: "[Athlete]'s [adjective] [comeback/moment] at [event]"

4. ATHLETE   — Hero-focused. Athlete name is front and center. Personal achievement framed big.
               Example pattern: "[Athlete Name] [VERB] the [opponent/obstacle] with [moment]"

5. RIVALRY   — Country vs country. National pride. US vs the world.
               Example pattern: "USA vs [Country]: [dramatic summary] [year]"

Return ONLY this JSON (no extra text):
{{
  "titles": [
    {{
      "style": "suspense",
      "title": "Your suspense title here",
      "char_count": 0,
      "why_it_works": "One sentence: what psychological trigger this pulls"
    }},
    {{
      "style": "stats",
      "title": "Your stats title here",
      "char_count": 0,
      "why_it_works": "One sentence: what psychological trigger this pulls"
    }},
    {{
      "style": "drama",
      "title": "Your drama title here",
      "char_count": 0,
      "why_it_works": "One sentence: what psychological trigger this pulls"
    }},
    {{
      "style": "athlete",
      "title": "Your athlete title here",
      "char_count": 0,
      "why_it_works": "One sentence: what psychological trigger this pulls"
    }},
    {{
      "style": "rivalry",
      "title": "Your rivalry title here",
      "char_count": 0,
      "why_it_works": "One sentence: what psychological trigger this pulls"
    }}
  ]
}}

Fill char_count with the ACTUAL character count of each generated title.
"""

# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def run(analysis: dict) -> dict:
    """
    Entry point called by orchestrator.py

    Args:
        analysis: Stage A output dict (emotional hooks + metadata)

    Returns:
        dict with 5 title variations ready for Stage C scoring

    Raises:
        ValueError: If API returns invalid JSON
        Exception:  Any Groq API connection error
    """
    logger.info("[Stage B] Generating 5 title hypotheses...")

    platform    = analysis.get("_input_platform", "youtube")
    user_prompt = build_user_prompt(analysis, platform)

    # ── API call ──────────────────────────────────────────────
    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=HYPOTHESIS_MODEL,
            temperature=0.8,       # High creativity for title variety
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )
        raw_output = response.choices[0].message.content.strip()
        logger.info("[Stage B] API call successful")

    except Exception as e:
        logger.error(f"[Stage B] Groq API error: {e}")
        raise

    # ── Parse JSON ────────────────────────────────────────────
    try:
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        result = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logger.error(f"[Stage B] JSON parse error: {e}")
        raise ValueError(f"Stage B returned invalid JSON: {e}")

    # ── Fix char_count if model left it at 0 ──────────────────
    for t in result.get("titles", []):
        if t.get("char_count", 0) == 0:
            t["char_count"] = len(t.get("title", ""))

    # ── Attach metadata ───────────────────────────────────────
    result["_stage"]      = "B"
    result["_model"]      = HYPOTHESIS_MODEL
    result["_platform"]   = platform
    result["_hook_score"] = analysis.get("hook_score", 0)

    styles = [t.get("style") for t in result.get("titles", [])]
    logger.info(f"[Stage B] Done. Styles generated: {styles}")
    return result


# ─────────────────────────────────────────────
# Local test — run: python agents/hypothesis.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_analysis = {
        "_stage": "A", "_model": "llama-3.3-70b-versatile",
        "_input_platform": "youtube",
        "_athlete_name": "Brady Ellison",
        "_event_name": "Hyundai Archery World Cup 2026 Stage 1",
        "primary_hook": "Brady Ellison defied the world #1 with one perfect arrow under wind",
        "narrative_frame": "comeback",
        "tension_points": [
            "Trailing 80-82 at halfway with no margin for error",
            "Final arrow under wind pressure — win or lose",
            "Beating the world #1 ranked Mike Schloesser"
        ],
        "power_words": ["CLUTCH", "PERFECT", "COMEBACK", "ONE ARROW", "SHOCKED"],
        "score_summary": "149-148: The most dramatic final in 2026",
        "hook_score": 94,
        "platform_notes": {
            "youtube": "Thumbnail moment = last arrow release. Curiosity gap title.",
            "facebook": "Lead with comeback story. Emotional narrative drives shares."
        }
    }

    result = run(sample_analysis)
    print(json.dumps(result, indent=2, ensure_ascii=False))
