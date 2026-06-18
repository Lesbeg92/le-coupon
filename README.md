# Le Coupon, ton interface + le moteur en direct

Ton interface n'a pas bougé. Ce dossier ajoute juste un moteur Flask derrière, qui va
chercher en direct la forme, les blessures et le contexte de chaque match, et ton interface
affiche ces données toute seule au chargement.

## Deux façons de l'utiliser

1. Sans moteur: ouvre simplement `frontend/index.html` dans ton navigateur. Tout marche
   comme maintenant, avec l'analyse intégrée. Aucune connexion requise.
2. Avec le moteur en direct: lance Flask (voir ci-dessous). Ton interface se branche
   automatiquement dessus et met à jour le conseil IA et les facteurs avec les vraies infos
   du jour. Si le moteur ne répond pas, ton interface reste sur l'analyse intégrée, rien ne casse.

## Lancer le moteur

Prérequis: Python 3.10+ et une clé API Anthropic (console.anthropic.com).

```bash
cd lecoupon-live
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="ta_cle_ici"
export CLAUDE_MODEL="claude-sonnet-4-6"   # un modele auquel ta cle a acces
python app.py
```

Ouvre ensuite http://127.0.0.1:5000

## Ce qui se passe

- Au chargement, ton interface affiche tout de suite l'analyse intégrée (instantané).
- En arrière-plan, elle interroge le moteur pour les matchs des trois prochains jours, et
  remplace le conseil IA, la confiance, le risque et les facteurs par les vraies données du
  moment. Un petit message "Analyse IA mise à jour en direct" confirme la mise à jour.
- Le moteur met ses recherches en cache 6 heures, donc les ouvertures suivantes sont rapides.

## Important

- Le moteur ne touche jamais à ton tableau: tes pronos, tes résultats, tes points, tes stats
  et tes bonus restent gérés par ton interface (stockage local de ton navigateur). Le moteur
  ne remplit que le conseil IA et les facteurs.
- Le nom du modèle est le réglage le plus probable à ajuster selon ton compte Anthropic.

Jeu gratuit, aucun argent en jeu. Les pronostics restent des paris.
