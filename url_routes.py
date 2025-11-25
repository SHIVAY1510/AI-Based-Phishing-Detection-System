from flask import Blueprint, request, jsonify
from db import db
from models import URLRecord
from flask_login import login_required, current_user

urls = Blueprint("urls", __name__)


# -------- SAVE URL --------
@urls.post("/save_url")
@login_required
def save_url():
    data = request.get_json() or {}

    url = data.get("url")
    result = data.get("result")

    if not url or result is None:
        return jsonify({"error": "url and result are required"}), 400

    user_id = getattr(current_user, 'id', None)
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    record = URLRecord(user_id=user_id, url=url, result=result)

    try:
        db.session.add(record)
        db.session.commit()
        return jsonify({"message": "URL saved"}), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Database error", "detail": str(exc)}), 500


# -------- DASHBOARD (protected) --------
@urls.get("/dashboard")
@login_required
def dashboard():
    user_id = getattr(current_user, 'id', None)
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    records = URLRecord.query.filter_by(user_id=user_id).order_by(URLRecord.timestamp.desc()).all()

    total = len(records)

    def classify_result(text: str):
        if not text:
            return 'other'
        t = text.lower()
        if 'phish' in t:
            return 'phishing'
        if 'safe' in t or 'legit' in t or 'legitimate' in t:
            return 'safe'
        return 'other'

    safe = sum(classify_result(r.result) == 'safe' for r in records)
    phishing = sum(classify_result(r.result) == 'phishing' for r in records)
    other = total - safe - phishing

    recent = [ {"url": r.url, "result": r.result, "timestamp": r.timestamp.isoformat()} for r in records[:10] ]

    return jsonify({
        "total": total,
        "safe": round((safe / total * 100), 1) if total else 0,
        "phishing": round((phishing / total * 100), 1) if total else 0,
        "other": round((other / total * 100), 1) if total else 0,
        "recent": recent
    })