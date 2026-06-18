"""
predictor.py
Le cerveau de l'assistant. Pour une date donnee, il demande a Claude de
rechercher en direct sur le web les vrais matchs du jour, les blessures,
suspensions, compos probables, la forme recente, l'historique et les
conditions, puis de produire un score conseille optimise pour le bareme RTS.
"""

import os
import json
import math
import anthropic

try:
    import odds as _odds
except Exception:
    _odds = None

# Modele a utiliser. Mets ici un modele auquel ta cle a acces (voir console.anthropic.com).
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY manquant. Exporte ta cle avant de lancer l'app.")
        _client = anthropic.Anthropic(api_key=key)
    return _client


SYSTEM = """Tu es un expert en pronostics football, le cerveau de l'assistant personnel "Le Coupon" pour le jeu gratuit Pronostics RTS Coupe du Monde 2026.

BAREME RTS (phase de groupes), a viser:
- +5 si le bon vainqueur (ou le bon nul)
- +1 si le nombre de buts de l'equipe a domicile est exact
- +1 si le nombre de buts de l'equipe visiteuse est exact
- +3 si la difference de buts est exacte avec le bon vainqueur
Un score exact vaut donc 10 points, un nul juste 8.

STRATEGIE de score:
- Le bon vainqueur prime sur tout.
- Pour un favori, privilegie un ecart d'1 ou 2 buts (2-1, 1-0, 2-0) pour maximiser le bonus de difference. Evite les ecarts de 3 buts ou plus sauf demonstration evidente (et dans ce cas mets type="reduit").
- Pour un nul, mets toujours 1-1.

RECHERCHE EN DIRECT (obligatoire, c'est le coeur du travail):
Utilise l'outil de recherche web pour chaque match afin de trouver:
- les vrais matchs de la Coupe du Monde 2026 a la date demandee (calendrier officiel),
- les BLESSURES et forfaits, y compris les pepins a l'entrainement et les joueurs incertains,
- les SUSPENSIONS,
- les COMPOSITIONS probables et le retour ou l'absence de cadres,
- la FORME recente et les resultats de la 1ere et 2e journee,
- l'historique des confrontations (qui domine d'habitude, scores typiques),
- le rythme recent: buts marques et encaisses sur les derniers matchs, attaque prolifique ou defense fragile,
- le repos et le deplacement: jours de recuperation, decalage horaire, distance parcourue,
- l'ENJEU et le risque de rotation: une equipe deja qualifiee ou deja eliminee peut faire tourner et lever le pied,
- le STYLE de jeu: deux equipes prudentes ou defensives donnent souvent un match ferme, propice au nul ou au petit score,
- les conditions (altitude des stades, chaleur, fuseau et deplacement),
- les COTES des bookmakers et le favori du marche, comme signal supplementaire.
Pondere reellement ces elements: un cadre offensif blesse baisse la note d'une equipe, un retour de titulaire la remonte, etc.
Croise ensuite ton analyse des faits avec les cotes du marche. Si elles vont dans le meme sens, ta confiance peut monter. Si elles divergent nettement de ta lecture, reste prudent et explique pourquoi tu suis l'une plutot que l'autre. Les cotes sont un signal fort, mais ne remplacent pas la lecture des faits.

EVALUE LE RISQUE DE NUL: avant de trancher, estime la probabilite d'un match nul. Deux equipes de niveau proche, deux equipes prudentes, un enjeu qui pousse a ne pas perdre, ou une cote du nul basse, sont autant de signaux. Si le nul est credible, baisse la confiance et n'hesite pas a proposer 1-1.

SCORES REALISTES: privilegie les scores les plus frequents du football (1-0, 2-1, 1-1, 2-0, 0-0, 2-2). Evite les scores rares ou fantaisistes sauf raison tres forte appuyee par les faits ET les cotes.

PRUDENCE QUAND C'EST INCERTAIN: si tu n'es pas sur, securise le bon vainqueur avec un ecart d'un seul but, plutot que de tenter un score large peu probable. Le bon vainqueur rapporte deja 5 points, c'est la base a ne pas gacher. Calibre "confiance" honnetement: haute seulement quand faits et cotes concordent, basse quand le match est ouvert.

SORTIE:
Reponds UNIQUEMENT avec un tableau JSON valide, sans aucun texte avant ou apres, sans balises Markdown.
Donne l'heure de coup d'envoi en UTC au format ISO 8601 avec Z (champ kickoffUTC).
Liste TOUS les matchs dont le coup d'envoi tombe le jour demande en HEURE SUISSE (Europe/Zurich), tries par heure croissante. Inclus aussi les matchs deja joues ce jour-la, avec leur score reel dans resultatA/resultatB (sinon null).
Chaque element:
{"kickoffUTC":"2026-06-18T19:00:00Z","lieu":"ville","journee":"2e journee, groupe A","equipeA":"...","drapeauA":"emoji","equipeB":"...","drapeauB":"emoji","scoreA":0,"scoreB":0,"resultatA":null,"resultatB":null,"type":"victoire|nul|reduit","confiance":"haute|moyenne|basse","xgA":1.4,"xgB":1.0,"analyse":"2 phrases max","facteurs":["blessure ou info cle 1","info cle 2"],"distribution":[{"score":"2-1","p":0.15},{"score":"1-1","p":0.13},{"score":"1-0","p":0.12},{"score":"2-0","p":0.10},{"score":"0-0","p":0.08},{"score":"3-1","p":0.07}]}.
Le champ "facteurs" liste en clair les infos live retenues (blessures, suspensions, retours, forme), pour que l'utilisateur voie ce que tu as pris en compte. Inclus aussi une ligne sur le marche quand l'information existe, par exemple "Marche: France favorite (cote ~1.5)".
Le champ "distribution" donne les 6 a 10 scores finaux les plus plausibles avec leur probabilite estimee (p entre 0 et 1), reflet honnete de ton analyse. Le score conseille sera recalcule a partir de cette distribution pour maximiser l'esperance de points RTS, donc soigne surtout cette distribution. Donne surtout "xgA" et "xgB", les buts attendus de chaque equipe, un nombre decimal realiste (souvent entre 0.4 et 3.0), qui resume la force offensive face a la defense adverse en tenant compte de la forme, des absents, du contexte et des cotes. Ces deux nombres nourrissent un modele de Poisson qui calcule la distribution complete des scores, les probabilites victoire/nul/defaite et le pari optimal. Soigne-les particulierement. La distribution reste un filet de secours. Dans "analyse", reste qualitatif sur le raisonnement et ne fige pas un score chiffre.
N'utilise jamais le tiret cadratin. Ne commence aucune phrase par "Je". Si aucun match ce jour-la, renvoie []."""


def _extract_json(blocks):
    text = "".join(getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text")
    text = text.replace("```json", "").replace("```", "").strip()
    s, e = text.find("["), text.rfind("]")
    if s == -1 or e == -1:
        raise ValueError("Reponse sans JSON exploitable")
    return json.loads(text[s:e + 1])


def rts_points(pa, pb, ra, rb):
    """Points RTS (phase de groupes) d'un pronostic pa-pb face a un resultat ra-rb."""
    pts = 0
    pw = 1 if pa > pb else (-1 if pa < pb else 0)
    rw = 1 if ra > rb else (-1 if ra < rb else 0)
    if pw == rw:
        pts += 5
    if pa == ra:
        pts += 1
    if pb == rb:
        pts += 1
    if pw == rw and (pa - pb) == (ra - rb):
        pts += 3
    return pts


def _parse_score(value):
    try:
        a, b = str(value).replace(":", "-").split("-")
        return int(a), int(b)
    except Exception:
        return None


def ev_optimal(distribution):
    """Choisit le score qui maximise l'esperance de points RTS sur la distribution donnee."""
    outcomes = []
    total = 0.0
    for d in distribution or []:
        sc = _parse_score(d.get("score"))
        p = d.get("p")
        if sc is None or not isinstance(p, (int, float)) or p <= 0:
            continue
        outcomes.append((sc[0], sc[1], float(p)))
        total += float(p)
    if not outcomes or total <= 0:
        return None
    outcomes = [(a, b, p / total) for (a, b, p) in outcomes]
    best, best_ev = None, -1.0
    for pa in range(0, 6):
        for pb in range(0, 6):
            ev = sum(p * rts_points(pa, pb, ra, rb) for (ra, rb, p) in outcomes)
            if ev > best_ev + 1e-9:
                best_ev, best = ev, (pa, pb)
    return best


def _poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def poisson_matrix(xg_a, xg_b, maxg=8):
    """Distribution complete des scores via deux lois de Poisson independantes."""
    pa = [_poisson_pmf(i, xg_a) for i in range(maxg + 1)]
    pb = [_poisson_pmf(j, xg_b) for j in range(maxg + 1)]
    sa, sb = sum(pa) or 1.0, sum(pb) or 1.0
    pa = [x / sa for x in pa]
    pb = [x / sb for x in pb]
    return [(i, j, pa[i] * pb[j]) for i in range(maxg + 1) for j in range(maxg + 1)]


def ev_optimal_matrix(matrix):
    best, best_ev = None, -1.0
    for pa in range(0, 6):
        for pb in range(0, 6):
            ev = sum(p * rts_points(pa, pb, ra, rb) for (ra, rb, p) in matrix)
            if ev > best_ev + 1e-9:
                best_ev, best = ev, (pa, pb)
    return best


def outcome_probs(matrix):
    home = sum(p for (a, b, p) in matrix if a > b)
    draw = sum(p for (a, b, p) in matrix if a == b)
    away = sum(p for (a, b, p) in matrix if a < b)
    return home, draw, away


def fit_xg_to_market(ph, pd, pa):
    """Trouve (xgA, xgB) dont le Poisson reproduit au mieux les probas du marche."""
    best, err = None, 1e9
    grid = [x / 10.0 for x in range(2, 36)]  # 0.2 .. 3.5
    for xa in grid:
        for xb in grid:
            h, d, a = outcome_probs(poisson_matrix(xa, xb))
            e = (h - ph) ** 2 + (d - pd) ** 2 + (a - pa) ** 2
            if e < err:
                err, best = e, (xa, xb)
    return best


def predict_day(date_readable, date_iso):
    client = _get_client()
    user = (
        f"Donne les pronostics pour tous les matchs de la Coupe du Monde 2026 dont le coup d'envoi "
        f"tombe le {date_readable} en heure suisse (jour {date_iso}, fuseau Europe/Zurich). "
        f"Recherche d'abord le calendrier officiel, puis pour chaque match: blessures, suspensions, "
        f"compos probables, forme et rythme recents, historique, enjeu et rotation possible, style de jeu, "
        f"et les cotes des bookmakers. Estime le risque de nul, puis pondere tout et propose un score realiste."
    )
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 14}],
        messages=[{"role": "user", "content": user}],
    )
    matches = _extract_json(msg.content)
    for m in matches:
        if m.get("resultatA") is not None:
            continue  # match deja joue, on ne touche pas au conseil historique
        xg_a, xg_b = m.get("xgA"), m.get("xgB")
        opt = None
        has_xg = isinstance(xg_a, (int, float)) and isinstance(xg_b, (int, float)) and xg_a > 0 and xg_b > 0
        if has_xg:
            xa = min(float(xg_a), 6.0)
            xb = min(float(xg_b), 6.0)
            # Cotes reelles du marche (si dispo), melangees aux buts attendus du modele.
            mk = None
            if _odds is not None:
                try:
                    mk = _odds.match_probs(m.get("equipeA", ""), m.get("equipeB", ""))
                except Exception:
                    mk = None
            if mk:
                ph, pdr, pa_ = mk
                xa_m, xb_m = fit_xg_to_market(ph, pdr, pa_)
                w = 0.55  # poids du marche dans le melange
                xa = w * xa_m + (1 - w) * xa
                xb = w * xb_m + (1 - w) * xb
                eqa, eqb = m.get("equipeA", "Dom"), m.get("equipeB", "Ext")
                cote = "Cotes marche: %s %d%%, nul %d%%, %s %d%%" % (eqa, round(ph * 100), round(pdr * 100), eqb, round(pa_ * 100))
                fac0 = m.get("facteurs") or []
                if isinstance(fac0, list):
                    fac0.insert(0, cote)
                    m["facteurs"] = fac0
            matrix = poisson_matrix(xa, xb)
            opt = ev_optimal_matrix(matrix)
            h, d, a = outcome_probs(matrix)
            top = max(h, d, a)
            m["confiance"] = "haute" if top >= 0.55 else ("moyenne" if top >= 0.42 else "basse")
            eqa, eqb = m.get("equipeA", "Dom"), m.get("equipeB", "Ext")
            ligne = "Modele: %s %d%%, nul %d%%, %s %d%%" % (eqa, round(h * 100), round(d * 100), eqb, round(a * 100))
            fac = m.get("facteurs") or []
            if isinstance(fac, list):
                fac.insert(0, ligne)
                m["facteurs"] = fac
        if opt is None:
            opt = ev_optimal(m.get("distribution"))
        if opt:
            m["scoreA"], m["scoreB"] = opt[0], opt[1]
            diff = abs(opt[0] - opt[1])
            m["type"] = "nul" if opt[0] == opt[1] else ("reduit" if diff >= 3 else "victoire")
    return matches
