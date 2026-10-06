# Scrapers d'offres d'emploi

Deux scrapers indépendants, chacun avec son propre README :

- [`jobijoba-scraper/`](jobijoba-scraper/) : pages de résultats de Jobijoba
- [`wttj-scraper/`](wttj-scraper/) : pages « emploi » de Welcome to the Jungle

Les offres récupérées restent **sur votre ordinateur** : les fichiers CSV, les dossiers `data/` et le journal sont exclus du dépôt par les `.gitignore`.

## Mettre les offres à jour automatiquement

Avec l'option `--mise-a-jour`, un scraper ne remplace plus son CSV : il le complète.

- **Nouvelles offres :** elles sont ajoutées.
- **Offres déjà connues :** elles sont actualisées, en gardant leur date de publication et les informations déjà récupérées. Avec `--details`, Jobijoba ne rouvre pas les offres déjà détaillées.
- **Offres absentes ce jour-là :** elles restent dans le CSV avec le statut `non retrouvée`. L'offre a peut-être expiré, ou elle n'apparaît simplement plus dans les premières pages de résultats.
- **Offres trop anciennes :** celles publiées il y a plus de 6 mois sont retirées. Réglable avec `--max-mois`.
- **Nouvelles colonnes de suivi :** `premiere_vue` (premier jour où l'offre a été vue), `derniere_vue` (dernier jour) et `statut` (`en ligne` ou `non retrouvée`).

Un même CSV peut regrouper plusieurs recherches. Une offre n'est marquée `non retrouvée` que si sa propre recherche (Jobijoba) ou sa propre page (WTTJ) a été relue.

Les fichiers `mise-a-jour.bat` (Windows) et `mise-a-jour.sh` (Mac / Linux) lancent les deux scrapers en mode mise à jour. Chaque exécution ajoute son compte rendu dans `journal-mise-a-jour.log`.

### 1. Installer une fois

Dans ce dossier `scrapers/` :

```bash
python -m venv .venv
# Windows :
.venv\Scripts\pip install -r jobijoba-scraper/requirements.txt
# Mac / Linux :
.venv/bin/pip install -r jobijoba-scraper/requirements.txt
```

Les deux scrapers ont les mêmes dépendances, un seul environnement suffit.

### 2. Choisir ses recherches

Ouvrez `mise-a-jour.bat` (Windows) ou `mise-a-jour.sh` (Mac / Linux) dans un éditeur de texte et adaptez les deux commandes : mot-clé, villes, nombre de pages, pages WTTJ. Gardez toujours `--mise-a-jour`. Pour suivre plusieurs mots-clés, ajoutez une ligne par mot-clé : toutes les lignes d'un même scraper complètent le même CSV.

Lancez le fichier une fois à la main pour vérifier : double-clic sur `mise-a-jour.bat`, ou `./mise-a-jour.sh` dans un terminal. Les résultats sont dans `jobijoba-scraper/data/offres.csv` et `wttj-scraper/data/offres_wttj.csv`.

### 3. Programmer le lancement chaque jour

**Windows (Planificateur de tâches)**

1. Touche Windows + R, tapez `taskschd.msc`, puis Entrée.
2. Dans le panneau de droite : **Créer une tâche de base…**
3. Nom : `Mise à jour des offres`, puis **Suivant**.
4. Déclencheur : **Tous les jours**, choisissez une heure (par exemple 9:00), puis **Suivant**.
5. Action : **Démarrer un programme**.
   - Programme/script : le chemin complet de `mise-a-jour.bat` (bouton **Parcourir…**)
   - Commencer dans : le chemin du dossier `scrapers` (sans guillemets)
6. **Terminer**. Ouvrez ensuite la tâche (double-clic), onglet **Paramètres**, et cochez **Exécuter la tâche dès que possible si un démarrage planifié est manqué**. Ainsi, si l'ordinateur était éteint à l'heure prévue, la mise à jour se fait au prochain démarrage.

**Mac / Linux (cron)**

1. Dans un terminal : `crontab -e`
2. Ajoutez une ligne, en remplaçant le chemin par celui de votre dossier `scrapers` :

   ```
   0 9 * * * /chemin/vers/metier/scrapers/mise-a-jour.sh
   ```

3. Enregistrez et quittez.

Sur Mac, si le dossier est dans Documents, Bureau ou Téléchargements, donnez l'accès complet au disque à `cron` : Réglages Système, puis Confidentialité et sécurité, puis Accès complet au disque, bouton +, et `/usr/sbin/cron` (Cmd + Maj + G pour taper le chemin). Attention : `cron` ne rattrape pas un lancement manqué si le Mac était éteint ou en veille à cette heure-là.

### Bon à savoir

- **Fermez le CSV dans Excel avant l'heure prévue.** Sous Windows, un fichier ouvert ne peut pas être remplacé : le script le signale dans le journal et laisse l'ancien CSV intact.
- **Si un site bloque les requêtes** (réponse 403 ou 429), le script s'arrête sans rien casser, et la mise à jour suivante reprendra normalement.
- **Une mise à jour par jour suffit.** Les sites ne changent pas plus vite, et c'est plus respectueux pour eux.
