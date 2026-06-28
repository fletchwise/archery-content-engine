import sqlite3
import json
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def create_tables():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT    NOT NULL,
                platform       TEXT    NOT NULL DEFAULT 'youtube',
                event_name     TEXT    NOT NULL DEFAULT '',
                athlete        TEXT    NOT NULL DEFAULT '',
                match_data     TEXT    NOT NULL,
                stage_a        TEXT,
                stage_b        TEXT,
                stage_c        TEXT,
                stage_d        TEXT,
                final_title    TEXT,
                hook_score     INTEGER DEFAULT 0,
                content_score  INTEGER DEFAULT 0,
                status         TEXT    DEFAULT 'running'
            )
        """)
        conn.commit()
        logger.info("[DB] Tables ready.")
    except Exception as e:
        logger.error(f"[DB] create_tables error: {e}")
        raise
    finally:
        conn.close()

def create_run(match_data):
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO pipeline_runs
                (created_at, platform, event_name, athlete, match_data, status)
            VALUES (?, ?, ?, ?, ?, 'running')
        """, (
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            match_data.get("content", {}).get("platform", "youtube"),
            match_data.get("event",   {}).get("name",    ""),
            match_data.get("athletes",{}).get("home",    {}).get("name", ""),
            json.dumps(match_data, ensure_ascii=False)
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_stage_result(run_id, stage, data):
    if stage not in ("stage_a","stage_b","stage_c","stage_d"):
        raise ValueError(f"Invalid stage: {stage}")
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE pipeline_runs SET {stage} = ? WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), run_id)
        )
        if stage == "stage_a":
            conn.execute(
                "UPDATE pipeline_runs SET hook_score = ? WHERE id = ?",
                (int(data.get("hook_score", 0)), run_id)
            )
        if stage == "stage_d":
            conn.execute("""
                UPDATE pipeline_runs
                SET final_title=?, content_score=?, status='done'
                WHERE id=?
            """, (data.get("title",""), int(data.get("content_score",0)), run_id))
        conn.commit()
    finally:
        conn.close()

def mark_error(run_id, error_msg):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE pipeline_runs SET status='error', stage_d=? WHERE id=?",
            (json.dumps({"error": error_msg}), run_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_history(limit=20):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, created_at, platform, event_name, athlete,
                   final_title, hook_score, content_score, status
            FROM pipeline_runs ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_run_by_id(run_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id=?", (run_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        for col in ("match_data","stage_a","stage_b","stage_c","stage_d"):
            if result.get(col):
                try:
                    result[col] = json.loads(result[col])
                except:
                    pass
        return result
    finally:
        conn.close()
