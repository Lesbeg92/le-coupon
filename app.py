"""
app.py
Le moteur. Il sert ton interface telle quelle (aucune modification de ton tableau)
et fournit les pronostics en direct via predictor.predict_day (Claude + recherche web).
Ton interface va chercher ces donnees toute seule au chargement.
"""

import os
import json
import datetime as dt
from flask import Flask, request, jsonify, send_file

import predictor

BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE, "frontend", "index.html")
CACHE_DIR = os.path.join(BASE, "cache")
CACHE_TTL_SECONDS = 6 * 3600

os.makedirs(CACHE_DIR, exist_ok=True)
app = Flask(__name__)

FR_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
FR_MONTHS = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
             "aout", "septembre", "octobre", "novembre", "decembre"]


def readable(date_iso):
    d = dt.date.fromisoformat(date_iso)
    return f"{FR_DAYS[d.weekday()]} {d.day} {FR_MONTHS[d.month]} {d.year}"


def cache_path(date_iso):
    return os.path.join(CACHE_DIR, f"{date_iso}.json")


def get_predictions(date_iso, force=False):
    path = cache_path(date_iso)
    if not force and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
            if dt.datetime.now().timestamp() - blob.get("ts", 0) < CACHE_TTL_SECONDS:
                return blob["matches"]
        except Exception:
            pass
    matches = predictor.predict_day(readable(date_iso), date_iso)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ts": dt.datetime.now().timestamp(), "matches": matches}, f, ensure_ascii=False, indent=2)
    return matches


@app.route("/")
def index():
    # Servi en brut, sans moteur de template, pour ne rien modifier dans ton interface.
    return send_file(FRONTEND)


@app.route("/api/predictions")
def api_predictions():
    date_iso = request.args.get("date") or dt.date.today().isoformat()
    force = request.args.get("refresh") == "1"
    try:
        matches = get_predictions(date_iso, force=force)
        return jsonify({"ok": True, "date": date_iso, "matches": matches})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # host 0.0.0.0 pour que ton telephone puisse joindre le serveur sur le meme WiFi
    app.run(host="0.0.0.0", port=port)
