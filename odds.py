"""
odds.py
Recupere les cotes reelles du marche via The Odds API (the-odds-api.com),
les convertit en probabilites sans marge (de-vig) et les expose par match.

Tout est tolerant aux pannes. Sans cle ODDS_API_KEY, ou en cas d'erreur reseau,
les fonctions renvoient None ou une liste vide, et le moteur retombe sur son
estimation interne. Aucune exception ne remonte vers l'application.

Reglages par variables d'environnement:
- ODDS_API_KEY    : ta cle The Odds API (obligatoire pour activer la fonction)
- ODDS_SPORT_KEY  : cle du tournoi (defaut: decouverte automatique du Mondial)
- ODDS_REGIONS    : regions de bookmakers (defaut: "eu,uk")
"""

import os
import ssl
import json
import time
import unicodedata
import urllib.request

_TTL = 15 * 60  # cache des cotes: 15 minutes
_events_cache = {"ts": 0.0, "events": []}
_sport_cache = {"ts": 0.0, "key": None}
_ctx = ssl.create_default_context()


def _key():
    return os.environ.get("ODDS_API_KEY")


def _regions():
    return os.environ.get("ODDS_REGIONS", "eu,uk")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "le-coupon/1.0"})
    with urllib.request.urlopen(req, timeout=20, context=_ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return "".join(c for c in s if c.isalnum())


# Noms francais de l'app -> nom anglais probable chez The Odds API.
FR_TO_EN = {
    "Mexique": "Mexico", "Afrique du Sud": "South Africa", "Coree du Sud": "South Korea",
    "Tchequie": "Czechia", "Canada": "Canada", "Bosnie-Herzegovine": "Bosnia and Herzegovina",
    "Etats-Unis": "USA", "Paraguay": "Paraguay", "Qatar": "Qatar", "Suisse": "Switzerland",
    "Bresil": "Brazil", "Maroc": "Morocco", "Haiti": "Haiti", "Ecosse": "Scotland",
    "Australie": "Australia", "Turquie": "Turkey", "Allemagne": "Germany", "Curacao": "Curacao",
    "Pays-Bas": "Netherlands", "Japon": "Japan", "Cote d'Ivoire": "Ivory Coast",
    "Equateur": "Ecuador", "Suede": "Sweden", "Tunisie": "Tunisia", "Espagne": "Spain",
    "Cap-Vert": "Cape Verde", "Belgique": "Belgium", "Egypte": "Egypt",
    "Arabie saoudite": "Saudi Arabia", "Uruguay": "Uruguay", "Iran": "Iran",
    "Nouvelle-Zelande": "New Zealand", "France": "France", "Senegal": "Senegal",
    "Irak": "Iraq", "Norvege": "Norway", "Argentine": "Argentina", "Algerie": "Algeria",
    "Autriche": "Austria", "Jordanie": "Jordan", "Portugal": "Portugal", "RD Congo": "DR Congo",
    "Angleterre": "England", "Croatie": "Croatia", "Ghana": "Ghana", "Panama": "Panama",
    "Ouzbekistan": "Uzbekistan", "Colombie": "Colombia",
}

# Alias normalises pour absorber les variantes d'ecriture cote API.
_ALIASES = {
    "usa": {"usa", "unitedstates", "unitedstatesofamerica"},
    "czechia": {"czechia", "czechrepublic"},
    "southkorea": {"southkorea", "korearepublic", "republicofkorea", "korea"},
    "ivorycoast": {"ivorycoast", "cotedivoire"},
    "drcongo": {"drcongo", "congodr", "democraticrepublicofthecongo", "congodemocraticrepublic"},
    "turkey": {"turkey", "turkiye"},
    "capeverde": {"capeverde", "caboverde"},
    "bosniaandherzegovina": {"bosniaandherzegovina", "bosniaherzegovina", "bosnia"},
    "newzealand": {"newzealand"},
}


def _team_keys(fr):
    """Ensemble de noms normalises acceptables pour une equipe francaise."""
    en = FR_TO_EN.get(_strip_accents_key(fr))
    base = _norm(en) if en else _norm(fr)
    return _ALIASES.get(base, {base})


def _strip_accents_key(fr):
    """Retrouve la cle FR_TO_EN meme si l'accent ou l'apostrophe differe."""
    target = _norm(fr)
    for k in FR_TO_EN:
        if _norm(k) == target:
            return k
    return fr


def _resolve_sport_key():
    forced = os.environ.get("ODDS_SPORT_KEY")
    if forced:
        return forced
    if _sport_cache["key"] and (time.time() - _sport_cache["ts"] < 6 * 3600):
        return _sport_cache["key"]
    try:
        sports = _get("https://api.the-odds-api.com/v4/sports/?apiKey=%s" % _key())
        best = None
        for s in sports:
            title = (s.get("title") or "").lower()
            group = (s.get("group") or "").lower()
            if "soccer" in group and "world cup" in title and s.get("active"):
                best = s.get("key")
                break
        if not best:
            best = "soccer_fifa_world_cup"
        _sport_cache.update({"ts": time.time(), "key": best})
        return best
    except Exception:
        return "soccer_fifa_world_cup"


def _devig(implied):
    total = sum(implied.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in implied.items()}


def get_events():
    """Liste de dicts {home, away, ph, pd, pa} (probas de-viggees). [] si indisponible."""
    if not _key():
        return []
    if _events_cache["events"] and (time.time() - _events_cache["ts"] < _TTL):
        return _events_cache["events"]
    try:
        sport = _resolve_sport_key()
        url = (
            "https://api.the-odds-api.com/v4/sports/%s/odds/?apiKey=%s&regions=%s&markets=h2h&oddsFormat=decimal"
            % (sport, _key(), _regions())
        )
        raw = _get(url)
        events = []
        for ev in raw:
            home = ev.get("home_team")
            away = ev.get("away_team")
            if not home or not away:
                continue
            sums = {"home": 0.0, "draw": 0.0, "away": 0.0}
            counts = {"home": 0, "draw": 0, "away": 0}
            for bk in ev.get("bookmakers", []):
                for mk in bk.get("markets", []):
                    if mk.get("key") != "h2h":
                        continue
                    for oc in mk.get("outcomes", []):
                        name = oc.get("name")
                        price = oc.get("price")
                        if not price or price <= 1.0:
                            continue
                        if name == home:
                            slot = "home"
                        elif name == away:
                            slot = "away"
                        elif str(name).lower() == "draw":
                            slot = "draw"
                        else:
                            continue
                        sums[slot] += 1.0 / price
                        counts[slot] += 1
            if min(counts.values()) == 0:
                continue
            implied = {k: sums[k] / counts[k] for k in sums}
            probs = _devig(implied)
            if not probs:
                continue
            events.append({
                "home": _norm(home), "away": _norm(away),
                "ph": probs["home"], "pd": probs["draw"], "pa": probs["away"],
            })
        _events_cache.update({"ts": time.time(), "events": events})
        return events
    except Exception:
        return []


def match_probs(equipe_a, equipe_b):
    """Probas (pA_gagne, pNul, pB_gagne) orientees A=domicile, ou None si introuvable."""
    try:
        events = get_events()
        if not events:
            return None
        ka = _team_keys(equipe_a)
        kb = _team_keys(equipe_b)
        for ev in events:
            h, a = ev["home"], ev["away"]
            if h in ka and a in kb:
                return (ev["ph"], ev["pd"], ev["pa"])
            if h in kb and a in ka:
                return (ev["pa"], ev["pd"], ev["ph"])
        return None
    except Exception:
        return None
