import logging
from flask import Flask, request, jsonify, render_template
from config import SECRET_KEY, DEBUG
import database as db
from pipeline.orchestrator import run_pipeline

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

db.create_tables()
logger.info("Archery Content Engine ready.")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    match_data = request.get_json(silent=True)
    if not match_data:
        return jsonify({"success": False, "error": "Request body must be JSON."}), 400
    for field in ("event", "athletes", "match", "content"):
        if field not in match_data:
            return jsonify({"success": False, "error": f"Missing field: '{field}'"}), 400
    run_id = db.create_run(match_data)
    try:
        result = run_pipeline(match_data, run_id)
        return jsonify(result), 200
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Request #{run_id} failed: {error_msg}")
        db.mark_error(run_id, error_msg)
        return jsonify({"success": False, "request_id": run_id, "error": error_msg}), 500

@app.route("/history")
def history():
    limit = request.args.get("limit", 20, type=int)
    runs  = db.get_history(limit)
    return jsonify({"runs": runs, "count": len(runs)}), 200

@app.route("/run/")
def get_run(run_id):
    run = db.get_run_by_id(run_id)
    if not run:
        return jsonify({"error": f"Run #{run_id} not found"}), 404
    return jsonify(run), 200

if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
