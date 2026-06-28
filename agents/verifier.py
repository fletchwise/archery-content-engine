"""
Stage C — Virtual Court Verifier
==================================
Acts as a panel of 3 American sports content consumers who rigorously score
each of the 5 titles from Stage B on CTR potential, US cultural resonance,
and emotional trigger strength.

Temperature: 0.2 (very low — we want consistent, objective scoring, not creativity)
Output: scored titles + clear winner, passed to Stage D (synthesizer.py)
"""

import json
import logging
from groq import Groq
from config import GROQ_API_KEY, VERIFIER_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a panel of 3 American sports content consumers evaluating archery video titles.
Your job is ruthlessly honest scoring — no politeness, no participation trophies.

THE PANEL:
- Judge 1 (Jake, 31, Ohio): Casual fan, watches NFL and bass fishing content. Clicks on drama.
- Judge 2 (Mia, 26, Texas): Competitive recurve archer. Follows World Cup closely. Values authenticity.
- Judge 3 (Derek, 44, California): YouTube power user, 8h/day. Expert at predicting click-through rates.

You score each title on 3 dimensions (0-100 each):
- ctr_score: Would Jake, Mia, and Derek actually CLICK this? (0=never, 100=instant click)
- us_appeal: Does this feel native to US sports culture? (0=foreign/alien, 100=quintessentially American)
- emotion_score: How strong is the emotional response triggered? (0=neutral, 100=goosebumps)

Final score formula: (ctr × 0.5) + (us_appeal × 0.3) + (emotion × 0.2)

WINNER = highest final_score AND within character limit. If tie, prefer higher ctr_score.

You output ONLY valid JSON. No preamble, no explanation, no markdown fences.
"""

# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────

def build_user_prompt(titles_data: dict, platform: str) -> str:
    titles = titles_data.get("titles", [])
    char_limit = 100 if platform == "youtube" else 80

    numbered = "\n".join([
        f"{i+1}. [{t['style'].upper():8s}] \"{t['title']}\"  ({t['char_count']} chars)"
        for i, t in enumerate(titles)
    ])

    return f"""
Score these 5 archery {platform.upper()} titles. Character limit: {char_limit}.

TITLES:
{numbered}

Return ONLY this exact JSON structure:
{{
  "scored_titles": [
    {{
      "style": "suspense",
      "title": "exact title text copied here",
      "ctr_score": 0,
      "us_appeal": 0,
      "emotion_score": 0,
      "final_score": 0,
      "within_limit": true,
      "panel_note": "What Jake, Mia, and Derek each said (1 line per judge)"
    }},
    {{
      "style": "stats",
      "title": "exact title text copied here",
      "ctr_score": 0,
      "us_appeal": 0,
      "emotion_score": 0,
      "final_score": 0,
      "within_limit": true,
      "panel_note": "What Jake, Mia, and Derek each said (1 line per judge)"
    }},
    {{
      "style": "drama",
      "title": "exact title text copied here",
      "ctr_score": 0,
      "us_appeal": 0,
      "emotion_score": 0,
      "final_score": 0,
      "within_limit": true,
      "panel_note": "What Jake, Mia, and Derek each said (1 line per judge)"
    }},
    {{
      "style": "athlete",
      "title": "exact title text copied here",
      "ctr_score": 0,
      "us_appeal": 0,
      "emotion_score": 0,
      "final_score": 0,
      "within_limit": true,
      "panel_note": "What Jake, Mia, and Derek each said (1 line per judge)"
    }},
    {{
      "style": "rivalry",
      "title": "exact title text copied here",
      "ctr_score": 0,
      "us_appeal": 0,
      "emotion_score": 0,
      "final_score": 0,
      "within_limit": true,
      "panel_note": "What Jake, Mia, and Derek each said (1 line per judge)"
    }}
  ],
  "winner": {{
    "style": "the winning style name",
    "title": "the exact winning title text",
    "final_score": 0,
    "winning_reason": "Why this title beat the other 4 (2 sentences)"
  }}
}}

Rules:
- final_score = round((ctr_score × 0.5) + (us_appeal × 0.3) + (emotion_score × 0.2))
- within_limit = true if char_count ≤ {char_limit}, else false
- winner MUST have within_limit = true
- Copy titles EXACTLY from the input — do not rewrite them
"""

# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def run(titles_data: dict) -> dict:
    """
    Entry point called by orchestrator.py

    Args:
        titles_data: Stage B output dict with 5 title variations

    Returns:
        dict with all scored titles + clear winner for Stage D

    Raises:
        ValueError: If API returns invalid JSON
        Exception:  Any Groq API connection error
    """
    logger.info("[Stage C] Scoring 5 titles — calling virtual court...")

    platform    = titles_data.get("_platform", "youtube")
    user_prompt = build_user_prompt(titles_data, platform)

    # ── API call (fast model — scoring is analytical, not creative) ──
    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=VERIFIER_MODEL,
            temperature=0.2,       # Very low — consistent, objective scoring
            max_tokens=1400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )
        raw_output = response.choices[0].message.content.strip()
        logger.info("[Stage C] API call successful")

    except Exception as e:
        logger.error(f"[Stage C] Groq API error: {e}")
        raise

    # ── Parse JSON ────────────────────────────────────────────
    try:
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        result = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logger.error(f"[Stage C] JSON parse error: {e}")
        raise ValueError(f"Stage C returned invalid JSON: {e}")

    # ── Safety: recalculate final_score to ensure formula is correct ──
    for t in result.get("scored_titles", []):
        ctr = t.get("ctr_score", 0)
        usa = t.get("us_appeal", 0)
        emo = t.get("emotion_score", 0)
        t["final_score"] = round((ctr * 0.5) + (usa * 0.3) + (emo * 0.2))

    # ── Safety: verify winner actually has within_limit = true ────────
    winner = result.get("winner", {})
    scored = result.get("scored_titles", [])
    winner_title = winner.get("title", "")
    winner_data  = next((t for t in scored if t.get("title") == winner_title), None)

    if winner_data and not winner_data.get("within_limit", True):
        # Find the best title that IS within limit
        valid = [t for t in scored if t.get("within_limit", True)]
        if valid:
            best = max(valid, key=lambda x: x.get("final_score", 0))
            logger.warning(f"[Stage C] Winner was over limit. Replacing with: {best['style']}")
            result["winner"] = {
                "style":         best["style"],
                "title":         best["title"],
                "final_score":   best["final_score"],
                "winning_reason": "Selected as best within character limit."
            }

    # ── Attach metadata ───────────────────────────────────────
    result["_stage"]    = "C"
    result["_model"]    = VERIFIER_MODEL
    result["_platform"] = platform

    winner = result.get("winner", {})
    logger.info(
        f"[Stage C] Done. Winner: [{winner.get('style','?').upper()}] "
        f"Score: {winner.get('final_score','?')}/100"
    )
    return result


# ─────────────────────────────────────────────
# Local test — run: python agents/verifier.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_titles = {
        "_stage": "B", "_platform": "youtube", "_hook_score": 94,
        "titles": [
            {"style": "suspense", "char_count": 51,
             "title": "He Was LOSING By 2 Points With ONE Arrow Left...",
             "why_it_works": "Cliffhanger — reader must click to resolve tension"},
            {"style": "stats",    "char_count": 61,
             "title": "149 vs 148: The Perfect Final Arrow That Shocked the World #1",
             "why_it_works": "Exact score makes the drama undeniably real"},
            {"style": "drama",    "char_count": 57,
             "title": "Brady Ellison's IMPOSSIBLE Comeback at the 2026 World Cup",
             "why_it_works": "Named hero + impossible framing + event context"},
            {"style": "athlete",  "char_count": 63,
             "title": "Brady Ellison STUNS World #1 With a Perfect 10 Under Wind",
             "why_it_works": "Hero + achievement + physical adversity (wind)"},
            {"style": "rivalry",  "char_count": 63,
             "title": "USA vs Netherlands: One Arrow Decides the 2026 World Cup Gold",
             "why_it_works": "National pride + high stakes + clear framing"}
        ]
    }

    result = run(sample_titles)
    print(json.dumps(result, indent=2, ensure_ascii=False))
