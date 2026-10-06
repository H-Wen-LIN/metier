# Guide — l'API Adzuna

Adzuna est un agrégateur : il rassemble les offres de nombreux sites emploi et
les expose dans une API gratuite. Ce guide dit comment obtenir une clé,
interroger les offres françaises, et ce que les conditions d'utilisation
permettent d'en faire sur notre site. Vérifié le 06/10/2026 sur
[developer.adzuna.com](https://developer.adzuna.com/) et sur la spécification
OpenAPI officielle
([`/swagger/spec/test2.json`](https://developer.adzuna.com/swagger/spec/test2.json)).

## 0. À lire avant tout : ce que les CGU autorisent

Les [conditions d'utilisation de l'API](https://developer.adzuna.com/docs/terms_of_service)
distinguent trois usages :

| Usage | Autorisé ? | Condition |
|---|---|---|
| **Afficher les annonces** sur un site | ✅ | Chaque annonce affichée porte la mention « Jobs by Adzuna » (au moins 116 × 23 px), « Jobs » en lien vers adzuna.fr et « Adzuna » sous forme de logo, lié lui aussi |
| **Recherche personnelle** | ✅ | Citer « The Adzuna API » avec un lien vers adzuna.fr partout où les chiffres sont publiés |
| **Tout autre usage par une organisation** (entreprise, administration, **établissement d'enseignement**) | ⚠️ 14 jours d'essai | Pendant l'essai, on teste la couverture et la qualité. Les données ne peuvent pas servir telles quelles **ni agrégées (nombre d'offres, salaires moyens…)** à un travail suivi sans accord écrit. Ensuite, une licence peut être exigée |

**Pour notre site, ça change tout.** Les pages calculent justement des
comptages et des salaires médians. Avec Adzuna, on peut donc sans souci
**afficher les dernières offres** avec la mention « Jobs by Adzuna ». Mais
pour les **mêler aux statistiques** de `data/resume.json`, il faut d'abord
l'accord écrit d'Adzuna. Le projet est porté dans un cadre IAE : le plus sûr
est de leur écrire via le [formulaire de contact](https://www.adzuna.co.uk/jobs/contact-us.html)
(lien donné par les CGU) en présentant le projet pédagogique.

Autres règles des CGU :
- **un seul compte** par personne ou par entité (plusieurs comptes = résiliation) ;
- ne pas contacter les sites d'où viennent les annonces : tout passe par Adzuna ;
- en cas de résiliation, supprimer toutes les données Adzuna du site.

## 1. Obtenir les clés

1. Créer le compte : [developer.adzuna.com/signup](https://developer.adzuna.com/signup).
2. Confirmer l'adresse e-mail, puis se connecter
   ([developer.adzuna.com/login](https://developer.adzuna.com/login)).
3. Le tableau de bord affiche deux valeurs : **`app_id`** (court) et
   **`app_key`** (32 caractères).
4. Les ranger comme les identifiants France Travail, jamais dans un fichier
   versionné :
   - en local, dans `.env` :
     ```
     ADZUNA_APP_ID=xxxxxxxx
     ADZUNA_APP_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     ```
   - sur GitHub, dans Settings → Secrets and variables → Actions :
     `ADZUNA_APP_ID` et `ADZUNA_APP_KEY`.
5. Vérifier que les clés marchent avec l'endpoint `version`, qui ne prend
   aucun autre paramètre et ne compte que pour un appel :
   ```bash
   curl -s "https://api.adzuna.com/v1/api/version?app_id=$ADZUNA_APP_ID&app_key=$ADZUNA_APP_KEY&content-type=application/json"
   ```
   Réponse attendue :
   ```json
   { "__CLASS__": "Adzuna::API::Response::Version", "api_version": 1, "software_version": "2013111200" }
   ```
   Si les clés sont fausses, l'API répond `401` avec `"exception": "AUTH_FAIL"`.

   ⚠️ La page « API Version » de la documentation donne l'URL
   `…/v1/api/jobs/gb/version`. Elle est périmée : testée le 06/10/2026, elle
   répond `404 UNKNOWN_METHOD`. La bonne URL, conforme à la spécification
   OpenAPI, est `…/v1/api/version`, sans `jobs/<pays>`.

## 2. Les quotas gratuits

| Par minute | Par jour | Par semaine | Par mois |
|---|---|---|---|
| 25 appels | 250 | 1 000 | 2 500 |

Le plafond mensuel est le vrai frein : **2 500 appels par mois, soit environ 80
par jour**. Pour nos 23 codes ROME, avec 50 offres par page, une veille
quotidienne complète ne tient pas (voir § 6). Adzuna relève les quotas sur
demande pour les sites qui *publient* ses annonces.

## 3. Premier appel

Toutes les URL partent de `https://api.adzuna.com/v1/api/jobs/fr/`. Le pays
`fr` est dans la liste officielle, à côté de `gb`, `de`, `es`, `it`, `be`, `ch`…

```bash
curl -s "https://api.adzuna.com/v1/api/jobs/fr/search/1?app_id=$ADZUNA_APP_ID&app_key=$ADZUNA_APP_KEY&results_per_page=20&what_phrase=marketing%20digital&content-type=application/json"
```

Ce qu'on reçoit (champs utiles ; les valeurs sont un **exemple fictif**,
construit d'après la documentation) :

```json
{
  "count": 1234,
  "mean": 38500.0,
  "results": [
    {
      "id": "4567890123",
      "title": "Chargé de marketing digital H/F",
      "description": "… extrait de l'annonce …",
      "created": "2026-10-05T08:12:44Z",
      "redirect_url": "https://www.adzuna.fr/jobs/land/ad/4567890123?…",
      "company":  { "display_name": "Exemple SAS" },
      "location": { "display_name": "Clermont-Ferrand, Puy-de-Dôme",
                    "area": ["France", "Auvergne-Rhône-Alpes", "Puy-de-Dôme", "Clermont-Ferrand"] },
      "latitude": 45.77, "longitude": 3.08,
      "category": { "tag": "…", "label": "…" },
      "contract_type": "permanent",
      "contract_time": "full_time",
      "salary_min": 32000, "salary_max": 38000,
      "salary_is_predicted": 0
    }
  ]
}
```

Trois différences avec France Travail :
- la **description est tronquée** : on n'a qu'un extrait, pas l'annonce
  entière. La recherche d'outils de `resumer.py` sera donc moins complète ;
- l'**URL** (`redirect_url`) renvoie vers Adzuna, qui redirige vers le site
  d'origine ;
- `salary_is_predicted = 1` veut dire que le salaire est **estimé par
  Adzuna**, pas écrit dans l'annonce. Il faut l'écarter des statistiques de
  salaires affichés.

## 4. Les paramètres de recherche

Endpoint : `GET /jobs/fr/search/{page}` (la page commence à 1).

| Famille | Paramètre | Ce qu'il fait |
|---|---|---|
| Clés | `app_id`, `app_key` | obligatoires à chaque appel |
| Pagination | `results_per_page` | nombre d'offres par page (50 en pratique, à vérifier avec sa clé) |
| Mots-clés | `what` | mots cherchés, séparés par des espaces |
| | `what_and` | tous les mots doivent y être |
| | `what_or` | au moins un des mots |
| | `what_phrase` | l'expression exacte, dans le titre ou la description |
| | `title_only` | mots cherchés **dans le titre seulement** : le plus précis |
| | `what_exclude` | mots à exclure |
| Lieu | `where` + `distance` | une ville ou un code postal, et un rayon en km (5 km par défaut) |
| | `location0` … `location7` | la hiérarchie renvoyée dans `location.area`, du pays à la ville (exemple de la doc pour le Royaume-Uni : `location0=UK&location1=South East England&location2=Surrey`) |
| Secteur | `category` | une catégorie Adzuna (liste : `GET /jobs/fr/categories`) |
| Contrat | `permanent=1` / `contract=1` | CDI / contrat à durée limitée |
| | `full_time=1` / `part_time=1` | temps plein / partiel |
| Salaire | `salary_min`, `salary_max` | bornes annuelles brutes |
| | `salary_include_unknown=1` | garder aussi les offres sans salaire |
| Fraîcheur | `max_days_old` | âge maximal de l'annonce, en jours |
| Entreprise | `company` | nom canonique de l'employeur |
| Tri | `sort_by` (`date`, `salary`, `relevance`, `hybrid`, `default`) + `sort_dir` (`up`, `down`) | ordre des résultats |

Ce qui **n'existe pas** : pas de code ROME, pas de code INSEE de commune, pas
d'expérience demandée, pas de niveau de diplôme, pas d'alternance distincte.
Les noms exacts des niveaux `location1` / `location2` pour la France et la
liste des catégories ne sont visibles qu'avec une clé : les relever au premier
appel (`location.area` d'une réponse, et `GET /jobs/fr/categories`).

## 5. Passer de nos codes ROME à des mots-clés

Sans code ROME, la précision vient de `title_only` et de `what_exclude`.
Point de départ, à affiner en comparant avec les intitulés réels de France
Travail dans `data/brut/` :

| ROME | Requête Adzuna |
|---|---|
| M1718 Chargé(e) de marketing digital | `title_only=marketing digital` · `what_exclude=directeur responsable` |
| M1716 Directeur(trice) marketing digital | `title_only=directeur marketing digital` |
| M1705 Responsable marketing | `title_only=responsable marketing` · `what_exclude=digital` |
| E1101 Community manager | `title_only=community manager` |
| E1405 Référenceur(se) web (SEO) | `what_or=SEO référenceur` · `title_only=SEO` |
| E1113 Responsable e-commerce | `title_only=e-commerce` |

Le README l'a déjà montré avec France Travail : une requête par mots-clés
ramène du bruit (424 offres pour « marketing digital » contre 113 en M1718).
On teste chaque requête sur 50 offres, on lit les titres, puis on ajuste
`what_exclude`.

## 6. Tenir dans le quota

| Stratégie | Appels | Tient dans 2 500/mois ? |
|---|---|---|
| 23 métiers × toutes les pages, chaque jour | plusieurs centaines par jour | ❌ |
| 23 métiers × 1 page, `sort_by=date`, `max_days_old=1`, chaque jour | 23 × 30 ≈ 690 | ✅ |
| Le cœur marketing (8 métiers) × 2 pages, chaque jour | 8 × 2 × 30 = 480 | ✅ |

La deuxième ligne suffit pour **afficher les nouvelles offres du jour**, ce qui
est justement l'usage que les CGU autorisent. Pour compter le marché, le champ
`count` d'une réponse donne le total sans tout paginer, mais publier ce
total sur le site, c'est de l'agrégation (§ 0).

## 7. Exemple en Python, sur le modèle de `scripts/extraire.py`

> **C'est branché :** `scripts/extraire_adzuna.py` fait tout ça pour les 23
> métiers (une page par métier, triée par date, sur les offres des deux
> derniers jours) et enregistre les offres dans `data/adzuna/`. La veille
> (`.github/workflows/veille.yml`) le lance chaque matin après France Travail,
> dès que les secrets `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont ajoutés. Les
> mots-clés de chaque métier sont dans `REQUETES`, en tête du script.
> L'exemple ci-dessous montre seulement le principe.

```python
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
URL = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"


def chercher_adzuna(params, pages=1, par_page=50):
    """Renvoie les offres Adzuna (France) pour une requête, page après page."""
    offres = []
    for page in range(1, pages + 1):
        r = requests.get(
            URL.format(page=page),
            params=dict(
                params,
                app_id=os.environ["ADZUNA_APP_ID"],
                app_key=os.environ["ADZUNA_APP_KEY"],
                results_per_page=par_page,
            ),
            headers={"Accept": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        lot = r.json().get("results", [])
        offres.extend(lot)
        if len(lot) < par_page:
            break
        time.sleep(2.5)                   # 25 appels par minute au plus
    return offres


nouvelles = chercher_adzuna(
    {"title_only": "marketing digital", "what_exclude": "stage",
     "sort_by": "date", "max_days_old": 1}
)
```

Pour l'intégrer à la veille, il faut ajouter `ADZUNA_APP_ID` et `ADZUNA_APP_KEY`
au bloc `env:` de `.github/workflows/veille.yml`, et écrire dans un dossier à
part (`data/adzuna/`) pour que les chiffres France Travail restent séparés.

## 8. Doublons avec France Travail

Adzuna reprend aussi des offres déjà diffusées par France Travail. Les
identifiants ne correspondent pas : on compare une empreinte
`titre normalisé + entreprise + ville`. Une offre présente des deux côtés
garde la version France Travail, qui est complète et porte un code ROME.

## 9. Les autres endpoints

| Endpoint | Donne | Remarque |
|---|---|---|
| `GET /jobs/fr/categories` | les catégories Adzuna | à appeler une fois pour remplir `category` |
| `GET /jobs/fr/histogram` | la répartition des salaires pour une requête | statistique : accord écrit pour la publier |
| `GET /jobs/fr/top_companies` | les employeurs qui publient le plus | idem |
| `GET /jobs/fr/geodata` | le nombre d'offres par zone | idem |
| `GET /jobs/fr/history` | le salaire moyen mois par mois | idem |
| `GET /version` (à la racine `…/v1/api/version`, pas sous `jobs/fr/`) | la version de l'API | sert à tester les clés (§ 1) |

Ces endpoints répondent directement aux questions du README (« où ? »,
« combien ça paie ? », « qui recrute ? »). C'est un bon argument à mettre en
avant si l'on demande une licence à Adzuna.

## Liens

- Inscription : [developer.adzuna.com/signup](https://developer.adzuna.com/signup)
- Documentation : [developer.adzuna.com/overview](https://developer.adzuna.com/overview) ·
  [recherche](https://developer.adzuna.com/docs/search) ·
  [référence interactive](https://developer.adzuna.com/activedocs)
- Conditions d'utilisation : [developer.adzuna.com/docs/terms_of_service](https://developer.adzuna.com/docs/terms_of_service)
