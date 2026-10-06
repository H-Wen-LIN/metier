# wttj-scraper

Petit script Python qui récupère les offres d'emploi affichées sur les pages « emploi » publiques de [Welcome to the Jungle](https://www.welcometothejungle.com) et les enregistre dans un fichier CSV.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

1. Sur Welcome to the Jungle, trouvez une ou plusieurs pages emploi qui correspondent à votre recherche, par exemple
   `https://www.welcometothejungle.com/fr/pages/emploi-developpeur-web-paris-75000`
   (astuce : cherchez sur Google « welcome to the jungle emploi [métier] [ville] »).
2. Lancez le script avec le nom des pages ou leurs URL complètes :

```bash
# Une page
python scraper.py emploi-developpeur-web-paris-75000

# Plusieurs pages, plus 5 pages « emploi » liées (métiers ou villes proches)
python scraper.py emploi-developpeur-web-paris-75000 emploi-developpeur-paris-75000 --suivre 5
```

Options :

- `pages` : un ou plusieurs noms de page ou URL complètes (obligatoire)
- `--suivre` : visite aussi jusqu'à N pages « emploi » liées depuis les pages données, 20 au maximum (0 par défaut)
- `--sortie` : chemin du fichier CSV (`data/offres_wttj.csv` par défaut)

Chaque page fournit ses 20 offres les plus récentes. Le site affiche d'autres pages de résultats (`?page=2`…), mais son `robots.txt` interdit les URL avec paramètres (`Disallow: /*?`) : le script ne les visite pas. Pour obtenir plus d'offres, donnez plusieurs pages (autres métiers proches, autres villes) ou utilisez `--suivre`. Si une page renvoie 0 offre, vérifiez son nom sur le site.

Le CSV (séparateur `;`, ouvrable dans Excel) contient : titre, entreprise, description de l'entreprise, contrat, durée du contrat (mois), lieu, département, région, latitude, longitude, télétravail, salaire (texte, minimum, maximum, période), expérience minimum (années), niveau d'études, secteur, taille de l'entreprise, année de création, date de publication (AAAA-MM-JJ), « recrute activement », résumé du poste, missions principales, avantages, page d'origine et lien vers l'offre.

Ces informations viennent des données que le site intègre dans la page. Si elles disparaissent, le script se rabat sur la lecture des cartes d'offres, avec moins de colonnes remplies.

## Bonnes pratiques

- Le script lit le `robots.txt` (jokers `*` et `$` compris) et ne visite que les adresses autorisées.
- Il attend 5 secondes entre deux pages et s'arrête dès que le site répond 403 ou 429 (requêtes limitées). Dans ce cas, réessayez plus tard.
- Les données récupérées restent en local : le dossier `data/` et les fichiers `.csv` sont exclus du dépôt via `.gitignore`.
- Ce projet n'est pas affilié à Welcome to the Jungle. Consultez leurs CGU avant tout usage régulier.
- Si le site change la structure de ses pages, l'extraction devra être adaptée.
