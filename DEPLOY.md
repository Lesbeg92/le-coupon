# Utiliser Le Coupon sur ton téléphone, avec les infos en direct

Pour avoir les blessures, la forme et les compos à jour sur ton téléphone, le moteur
(Flask + ta clé API Anthropic) doit tourner quelque part que ton téléphone peut joindre.
Voici les deux façons, de la plus simple à la plus complète.

Dans tous les cas, il te faut une clé API Anthropic (console.anthropic.com). C'est elle qui
fait la recherche et le raisonnement. Son usage est payant, mais à petits montants.

---

## Méthode 1, à la maison (rapide, gratuit, sans hébergement)

Ton téléphone se connecte au moteur qui tourne sur ton ordinateur, sur le même WiFi.

1. Sur ton ordinateur, dans le dossier `lecoupon-live`:
   ```
   pip install -r requirements.txt
   export ANTHROPIC_API_KEY="ta_cle"
   export CLAUDE_MODEL="claude-sonnet-4-5"
   python app.py
   ```
2. Trouve l'adresse IP locale de ton ordinateur:
   - Windows: tape `ipconfig` dans le terminal, cherche "Adresse IPv4", par exemple 192.168.1.42
   - Mac: `ipconfig getifaddr en0`
3. Sur ton téléphone (connecté au même WiFi), ouvre le navigateur et va sur:
   ```
   http://192.168.1.42:5000
   ```
   (remplace par ton IP)
4. Dans le menu du navigateur, choisis "Ajouter à l'écran d'accueil". Tu auras une icône
   comme une vraie app.

Limite: ça marche seulement à la maison et quand ton ordinateur est allumé.

---

## Méthode 2, partout (recommandée pour un usage quotidien)

On met le moteur en ligne sur un hébergeur gratuit. Ton téléphone y accède de n'importe où.

Exemple avec Render (gratuit):
1. Crée un compte sur github.com et mets le dossier `lecoupon-live` dans un dépôt (repo).
2. Crée un compte sur render.com, puis "New" puis "Web Service", et connecte ton repo.
3. Réglages du service:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Dans "Environment", ajoute deux variables:
   - `ANTHROPIC_API_KEY` = ta clé
   - `CLAUDE_MODEL` = un modèle auquel ta clé a accès
5. Render te donne une URL publique, du genre `https://lecoupon.onrender.com`.
6. Ouvre cette URL sur ton téléphone, puis "Ajouter à l'écran d'accueil". Tu as une app
   live, accessible partout.

Bon à savoir:
- Le tier gratuit de Render s'endort après une période sans visite, donc le tout premier
  chargement après une pause peut prendre une minute. Ensuite c'est rapide.
- L'usage de la clé API est payant à la consommation, mais le cache (6 heures) limite les
  appels, donc ça reste modeste.

---

## Alternative sans clé API (pas de live, mais ça marche partout tout de suite)

Si tu ne veux pas gérer de clé pour l'instant, tu peux mettre la version autonome
(`le-coupon-ia/index.html`, avec mon analyse intégrée) en ligne en deux minutes:
1. Va sur app.netlify.com/drop
2. Glisse le fichier `index.html` dans la zone.
3. Netlify te donne une URL. Ouvre-la sur ton téléphone, "Ajouter à l'écran d'accueil".

Tu as l'app complète avec mon analyse, les drapeaux et le suivi des points, mais sans la
mise à jour automatique des blessures. Pour le live, il faut la Méthode 2.

---

Jeu gratuit, aucun argent en jeu côté pronostics. Les pronostics restent des paris.
