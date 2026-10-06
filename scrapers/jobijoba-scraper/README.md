# jobijoba-scraper

Petit script Python qui récupère les offres d'emploi affichées sur les pages de résultats publiques de [Jobijoba](https://www.jobijoba.com) et les enregistre dans un fichier CSV.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

```bash
# Une ville, 2 pages (60 offres au plus)
python scraper.py "developpeur web" --ville Clermont-ferrand --pages 2

# Plusieurs villes, 5 pages chacune, sans les offres sponsorisées, avec le détail de chaque offre
python scraper.py "developpeur web" --ville Paris --ville Lyon --pages 5 --sans-sponsorises --details
```

Options :

- `mot_cle` : le métier ou mot-clé recherché (obligatoire)
- `--ville` : la ville (facultatif). Option répétable pour chercher dans plusieurs villes en une fois.
- `--pages` : nombre de pages de 30 offres par ville, 10 au maximum (1 par défaut). Les pages suivantes sont chargées comme le fait le bouton « Voir les offres suivantes » du site.
- `--sans-sponsorises` : ignore les offres sponsorisées, souvent sans rapport avec la recherche
- `--details` : ouvre la page de chaque offre pour récupérer la description complète, la date de publication et d'expiration, le code postal, la région et le salaire chiffré (plus lent : 2 secondes par offre)
- `--sortie` : chemin du fichier CSV (`data/offres.csv` par défaut)

Le CSV (séparateur `;`, ouvrable dans Excel) contient pour chaque offre : titre, métier, catégorie, lieu, contrat, entreprise, salaire, télétravail, date, résumé, offre sponsorisée ou non, recherche d'origine et lien vers l'annonce. Avec `--details` s'ajoutent : date de publication, date d'expiration, code postal, région, salaire min, salaire max, période du salaire, temps de travail et description complète. Certaines offres reprises d'autres sites n'ont que la description.

## Bonnes pratiques

- Le script lit le `robots.txt` (jokers `*` et `$` compris) et ne visite que les adresses autorisées. La recherche avec un rayon autour de la ville passe par `/fr/query/`, que le `robots.txt` interdit : elle n'est donc pas proposée. Pour couvrir une zone, ajoutez plusieurs `--ville`.
- Il attend 3 secondes entre deux pages de résultats, 2 secondes entre deux pages d'offre, et limite le nombre de pages.
- Les données récupérées restent en local : le dossier `data/` et les fichiers `.csv` sont exclus du dépôt via `.gitignore`.
- Ce projet n'est pas affilié à Jobijoba. Pour un usage régulier ou commercial, utilisez leur programme d'affiliation officiel (API).
- Si Jobijoba change la structure de ses pages, l'extraction devra être adaptée.
