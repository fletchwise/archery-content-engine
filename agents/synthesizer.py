"""
Stage D — Final Synthesizer
=============================
Receives the winning title from Stage C and builds the COMPLETE content package:

  ✓ Polished final title
  ✓ Platform-optimized caption (Facebook 150-200w / YouTube 100-150w)
  ✓ 15 strategic hashtags (broad + niche + event + trending)
  ✓ Optimal posting time with reasoning (US time zones)
  ✓ Thumbnail overlay text (YouTube only)
  ✓ Pinned first comment suggestion (YouTube only)
  ✓ Content quality score (0-100)

This is the FINAL output delivered to the user.
Temperature: 0.6 (balanced — creative caption, but consistent structure)
"""

import json
import logging
from groq import Groq
from config import GROQ_API_KEY, SYNTHESIZER_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior social media strategist for American sports content on YouTube and Facebook.
You specialize in archery — a sport growing fast in the US ahead of the 2028 LA Olympics.

You build COMPLETE content packages: not just titles, but everything a creator needs to
publish immediately without editing anything.

YOUR STANDARDS:
- YouTube descriptions: First 2 lines visible before "Show more" — make them count.
  Hook → Story → Call to action. No filler. No timestamps (they don't have chapters yet).
- Facebook captions: First line MUST stop the scroll. Tell the story emotionally.
  End with a question that invites comments (drives algorithm).
- Hashtags: ALWAYS mix 5 broad (#archery) + 5 niche (#compoundbow) + 5 event/specific.
  Niche hashtags get more targeted reach than mega-tags alone.
- Posting time: Based on when American sports fans are ACTUALLY online.
  Prime: Thu-Sun evenings EST. Absolute peak: Saturday 1-3 PM EST.
- Thumbnail text: 3-5 words max. High contrast. Makes the freeze-frame click-worthy.

You output ONLY valid JSON. No preamble, no explanation, no markdown fences.
"""

# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────

def build_user_prompt(verified_data: dict, analysis: dict, match_data: dict) -> str:
    winner   = verified_data.get("winner", {})
    platform = verified_data.get("_platform", "youtube")

    event    = match_data.get("event", {})
    athletes = match_data.get("athletes", {})
    match    = match_data.get("match", {})
    content  = match_data.get("content", {})

    home     = athletes.get("home", {})
    opp      = athletes.get("opponent", {})

    cap_range = "150-200 words" if platform == "facebook" else "100-150 words"

    return f"""
Build a complete content package for this winning title.

─── WINNING TITLE ────────────────────────────────
Style  : {winner.get("style", "").upper()}
Title  : "{winner.get("title", "")}"
Score  : {winner.get("final_score", 0)}/100
Reason : {winner.get("winning_reason", "")}

─── MATCH CONTEXT ────────────────────────────────
Event      : {event.get("name", "")} — {event.get("location", "")}
Date       : {event.get("date", "")}  |  Round: {event.get("round", "")}
Discipline : {event.get("discipline", "")}
Home       : {home.get("name", "")} ({home.get("country", "")}) — World Rank #{home.get("world_rank", "?")}
Opponent   : {opp.get("name", "")} ({opp.get("country", "")}) — World Rank #{opp.get("world_rank", "?")}
Result     : {home.get("name", "")} {match.get("result", "").upper()} {match.get("score_home", "")}-{match.get("score_opponent", "")}
Comeback   : {match.get("comeback", False)}  |  From: {match.get("comeback_from", "N/A")}
Key moment : {content.get("extra_notes", "")}

─── EMOTIONAL INTELLIGENCE (from Stage A) ────────
Primary hook   : {analysis.get("primary_hook", "")}
Narrative frame: {analysis.get("narrative_frame", "")}
Power words    : {", ".join(analysis.get("power_words", []))}
──────────────────────────────────────────────────

Platform: {platform.upper()}

Return ONLY this JSON:
{{
  "platform": "{platform}",

  "title": "Final polished version (may be slightly refined from winner, must stay same style)",

  "caption": "Full {platform} caption — {cap_range}. Write naturally with emotion. For Facebook: end with an engaging question. For YouTube: first 2 lines must hook before Show More.",

  "hashtags": [
    "#archery",
    "#archerysports",
    "#arrowshooting",
    "#compoundbow",
    "#recurvebow",
    "#bowhunting",
    "#archerylove",
    "#archerynation",
    "#worldarchery",
    "#worldcup2026",
    "#archeryworldcup",
    "#bradyellison",
    "#usaarchery",
    "#olympicarchery",
    "#archery2026"
  ],

  "optimal_post_time": {{
    "day": "Best day name",
    "time_est": "H:MM AM/PM EST",
    "time_gmt": "HH:MM GMT",
    "reason": "Why this time maximizes US audience reach for this type of content"
  }},

  "thumbnail_text": "3-5 WORD OVERLAY for YouTube thumbnail (null for Facebook)",

  "first_comment": "Text to pin as first YouTube comment to boost engagement (null for Facebook)",

  "content_score": 0
}}

Replace the sample hashtags with 15 REAL strategic hashtags for this specific match.
Mix: 5 broad + 5 niche archery + 5 event/athlete specific.
content_score: Your 0-100 rating for the overall quality of this complete package.
"""

# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def run(verified_data: dict, analysis: dict, match_data: dict) -> dict:
    """
    Entry point called by orchestrator.py

    Args:
        verified_data: Stage C output (winning title + all scored titles)
        analysis:      Stage A output (emotional hooks — for context)
        match_data:    Original user input JSON

    Returns:
        Final content package dict — this is what the user copies and publishes

    Raises:
        ValueError: If API returns invalid JSON
        Exception:  Any Groq API connection error
    """
    logger.info("[Stage D] Building final content package...")

    user_prompt = build_user_prompt(verified_data, analysis, match_data)

    # ── API call ──────────────────────────────────────────────
    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=SYNTHESIZER_MODEL,
            temperature=0.6,       # Balanced: creative caption, consistent structure
            max_tokens=1600,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ]
        )
        raw_output = response.choices[0].message.content.strip()
        logger.info("[Stage D] API call successful")

    except Exception as e:
        logger.error(f"[Stage D] Groq API error: {e}")
        raise

    # ── Parse JSON ────────────────────────────────────────────
    try:
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        result = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logger.error(f"[Stage D] JSON parse error: {e}")
        raise ValueError(f"Stage D returned invalid JSON: {e}")

    # ── Ensure exactly 15 hashtags ────────────────────────────
    hashtags = result.get("hashtags", [])
    if len(hashtags) < 15:
        # Pad with generic archery tags if model returned fewer
        extras = ["#sportsshooting", "#archerylife", "#target", "#bowshooting"]
        result["hashtags"] = (hashtags + extras)[:15]
    elif len(hashtags) > 15:
        result["hashtags"] = hashtags[:15]

    # ── Ensure all hashtags start with # ──────────────────────
    result["hashtags"] = [
        h if h.startswith("#") else f"#{h}"
        for h in result["hashtags"]
    ]

    # ── Attach pipeline metadata (carried through to frontend) ─
    result["_stage"]         = "D"
    result["_model"]         = SYNTHESIZER_MODEL
    result["_hook_score"]    = analysis.get("hook_score", 0)
    result["_winning_style"] = verified_data.get("winner", {}).get("style", "")
    result["_all_titles"]    = verified_data.get("scored_titles", [])

    logger.info(
        f"[Stage D] Done. Content score: {result.get('content_score', 'N/A')} | "
        f"Post: {result.get('optimal_post_time', {}).get('day', '?')} "
        f"{result.get('optimal_post_time', {}).get('time_est', '?')}"
    )
    return result
