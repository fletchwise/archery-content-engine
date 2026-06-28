"""
orchestrator.py — The Maestro
================================
Chains the 4 agents in sequence and manages data flow between them:

  INPUT → [A: Analyze] → [B: Hypothesize] → [C: Verify] → [D: Synthesize] → OUTPUT

Each stage's output becomes the next stage's input.
Progress is saved to SQLite after EVERY stage — so if Stage D fails,
you still have Stages A, B, C saved and can debug from there.
"""

import logging
import time

import database as db
from agents.analyzer    import run as run_analyzer
from agents.hypothesis  import run as run_hypothesis
from agents.verifier    import run as run_verifier
from agents.synthesizer import run as run_synthesizer

logger = logging.getLogger(__name__)


def run_pipeline(match_data: dict, request_id: int) -> dict:
    """
    Executes the full 4-stage pipeline.

    Args:
        match_data:  Raw JSON dict from the user's input form
        request_id:  SQLite row ID — used to log progress at each stage

    Returns:
        dict with keys:
          success, request_id, elapsed_sec, result (Stage D output),
          all_titles (scored list), hook_score, narrative, content_score

    Raises:
        Exception with stage label if any agent fails
    """
    pipeline_start = time.time()
    logger.info(f"[Pipeline] ── Starting request #{request_id} ──")

    # ──────────────────────────────────────────────────────────
    # Stage A: Forensic Analyzer
    # Extracts emotional hooks and narrative angle from match data
    # ──────────────────────────────────────────────────────────
    try:
        logger.info("[Pipeline] Stage A starting...")
        stage_a = run_analyzer(match_data)
        db.update_stage_result(request_id, "stage_a", stage_a)
        logger.info(f"[Pipeline] Stage A done. Hook score: {stage_a.get('hook_score')}")

    except Exception as e:
        logger.error(f"[Pipeline] Stage A failed: {e}")
        raise Exception(f"Stage A (Analyzer) failed: {str(e)}")

    # ──────────────────────────────────────────────────────────
    # Stage B: Hypothesis Generator
    # Uses Stage A's hooks to generate 5 title variations
    # ──────────────────────────────────────────────────────────
    try:
        logger.info("[Pipeline] Stage B starting...")
        stage_b = run_hypothesis(stage_a)            # <-- receives Stage A output
        db.update_stage_result(request_id, "stage_b", stage_b)
        logger.info(f"[Pipeline] Stage B done. Titles: {len(stage_b.get('titles', []))}")

    except Exception as e:
        logger.error(f"[Pipeline] Stage B failed: {e}")
        raise Exception(f"Stage B (Hypothesis) failed: {str(e)}")

    # ──────────────────────────────────────────────────────────
    # Stage C: Virtual Court Verifier
    # Scores all 5 titles and selects the winner
    # ──────────────────────────────────────────────────────────
    try:
        logger.info("[Pipeline] Stage C starting...")
        stage_c = run_verifier(stage_b)              # <-- receives Stage B output
        db.update_stage_result(request_id, "stage_c", stage_c)
        winner  = stage_c.get("winner", {})
        logger.info(
            f"[Pipeline] Stage C done. Winner: [{winner.get('style','?').upper()}] "
            f"Score: {winner.get('final_score','?')}/100"
        )

    except Exception as e:
        logger.error(f"[Pipeline] Stage C failed: {e}")
        raise Exception(f"Stage C (Verifier) failed: {str(e)}")

    # ──────────────────────────────────────────────────────────
    # Stage D: Final Synthesizer
    # Builds the complete content package from the winning title
    # Needs: Stage C output + Stage A analysis + original match data
    # ──────────────────────────────────────────────────────────
    try:
        logger.info("[Pipeline] Stage D starting...")
        stage_d = run_synthesizer(stage_c, stage_a, match_data)   # <-- receives all 3
        db.update_stage_result(request_id, "stage_d", stage_d)
        logger.info(
            f"[Pipeline] Stage D done. Content score: {stage_d.get('content_score')}"
        )

    except Exception as e:
        logger.error(f"[Pipeline] Stage D failed: {e}")
        raise Exception(f"Stage D (Synthesizer) failed: {str(e)}")

    # ──────────────────────────────────────────────────────────
    # Build and return the final response
    # ──────────────────────────────────────────────────────────
    elapsed = round(time.time() - pipeline_start, 1)
    logger.info(f"[Pipeline] ── Complete in {elapsed}s for request #{request_id} ──")

    return {
        "success":       True,
        "request_id":    request_id,
        "elapsed_sec":   elapsed,
        "result":        stage_d,                          # The full content package
        "all_titles":    stage_d.get("_all_titles", []),   # All 5 scored titles
        "hook_score":    int(stage_a.get("hook_score", 0)),
        "narrative":     stage_a.get("narrative_frame", ""),
        "content_score": stage_d.get("content_score", 0)
    }
