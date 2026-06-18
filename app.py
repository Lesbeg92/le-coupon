"""
app.py
Le moteur. Il sert ton interface telle quelle (aucune modification de ton tableau)
et fournit les pronostics en direct via predictor.predict_day (Claude + recherche web).
Ton interface va chercher ces donnees toute seule au chargement.
"""

import os
import re
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
    now = dt.datetime.now().timestamp()
    today = dt.date.today().isoformat()

    blob = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception:
            blob = None

    # Duree de cache adaptative.
    # Jours a venir: 6h, ils bougent peu.
    # Aujourd'hui: 20 min, pour suivre les nouvelles du jour.
    # Match imminent ou en cours: 5 min, pour capter la compo officielle.
    ttl = CACHE_TTL_SECONDS
    if date_iso == today:
        ttl = 20 * 60
        if blob:
            for mm in blob.get("matches", []):
                ko = mm.get("kickoffUTC")
                if not ko:
                    continue
                try:
                    kt = dt.datetime.fromisoformat(str(ko).replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue
                # de 90 min avant le coup d'envoi a 150 min apres
                if -150 * 60 < (kt - now) < 90 * 60:
                    ttl = 5 * 60
                    break

    if not force and blob and (now - blob.get("ts", 0) < ttl):
        return blob["matches"]

    matches = predictor.predict_day(readable(date_iso), date_iso)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ts": now, "matches": matches}, f, ensure_ascii=False, indent=2)
    except Exception:
        # Un cache non ecrit n'empeche pas de renvoyer les pronostics.
        pass
    return matches


@app.route("/")
def index():
    # Servi en brut, sans moteur de template, pour ne rien modifier dans ton interface.
    return send_file(FRONTEND)


@app.route("/api/predictions")
def api_predictions():
    date_iso = request.args.get("date") or dt.date.today().isoformat()
    # Securite: on n'accepte qu'une date AAAA-MM-JJ, sinon on retombe sur aujourd'hui.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_iso)):
        date_iso = dt.date.today().isoformat()
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
