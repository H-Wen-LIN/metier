r"""Récupère les nouvelles offres Adzuna (France) des métiers suivis et les enregistre dans data/adzuna/.

Usage :
    .venv\Scripts\python.exe scripts\extraire_adzuna.py                 # tous les métiers de REQUETES
    .venv\Scripts\python.exe scripts\extraire_adzuna.py --verifier      # teste seulement les clés
    .venv\Scripts\python.exe scripts\extraire_adzuna.py --rome M1718    # un seul code, pour essayer

Ce que ça écrit :
    data/adzuna/<AAAA-MM>/<ROME>.jsonl   une ligne par offre (JSON tel que l'API le renvoie),
                                         écrite la première fois qu'on la voit
    data/adzuna/serie.csv                une ligne par métier et par jour : total annoncé,
                                         récupérées, nouvelles

Adzuna n'a pas de code ROME : chaque métier est une requête par mots-clés (REQUETES), à affiner
en lisant les titres renvoyés. Une seule page par métier, triée par date, sur les offres des deux
derniers jours : 23 appels par jour, ~700 par mois, sous le quota gratuit (2 500 par mois).

Conditions d'utilisation (voir guide-adzuna.md) : afficher ces offres est permis avec la mention
« Jobs by Adzuna » ; en tirer des statistiques publiées (comptages, salaires) demande l'accord écrit
d'Adzuna. C'est pourquoi ces données restent hors de data/brut et de data/resume.json.

Clés lues dans .env ou dans l'environnement (secrets GitHub Actions) : ADZUNA_APP_ID, ADZUNA_APP_KEY.
Sans clés, le script le dit et s'arrête sans erreur : la veille France Travail n'en dépend pas.
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraire import METIERS  # noqa: E402  (les libellés des métiers suivis)

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")

API = "https://api.adzuna.com/v1/api"
PAR_PAGE = 50
DOSSIER = RACINE / "data" / "adzuna"

# Code ROME -> paramètres de recherche Adzuna. title_only : mots cherchés dans le titre seulement ;
# what_exclude : mots qui écartent l'offre. Point de départ, à ajuster sur les titres récupérés.
REQUETES = {
    # Cœur marketing
    "M1718": {"title_only": "marketing digital", "what_exclude": "directeur directrice responsable"},
    "M1716": {"title_only": "directeur marketing digital"},
    "M1705": {"title_only": "responsable marketing", "what_exclude": "digital"},
    "M1703": {"title_only": "chef produit", "what_exclude": "digital"},
    "M1620": {"title_only": "assistant marketing"},
    "M1706": {"title_only": "promotion ventes"},
    "M1430": {"title_only": "études marketing"},
    "M1711": {"title_only": "directeur marketing", "what_exclude": "digital"},
    # Digital, contenu, e-commerce
    "E1113": {"title_only": "e-commerce", "what_exclude": "assistant assistante"},
    "D1438": {"title_only": "assistant e-commerce"},
    "E1101": {"title_only": "community manager"},
    "E1124": {"title_only": "social media"},
    "E1405": {"title_only": "SEO"},
    "M1886": {"title_only": "chef projet web"},
    "M1426": {"title_only": "chief digital officer"},
    "M1719": {"title_only": "influence"},
    "E1406": {"title_only": "influenceur"},
    # Communication et commerce, à la frontière
    "E1112": {"title_only": "chargé communication"},
    "E1103": {"title_only": "relations presse"},
    "E1107": {"title_only": "événementiel"},
    "E1404": {"title_only": "publicité"},
    "D1506": {"title_only": "merchandising"},
    "D1415": {"title_only": "CRM"},
}


def cles():
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key or app_key.startswith("xxxx"):
        return None
    return {"app_id": app_id, "app_key": app_key}


def appeler(chemin, params):
    r = requests.get(f"{API}/{chemin}", params=params, headers={"Accept": "application/json"}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} : {r.text[:200]}")
    return r.json()


def ids_connus():
    """Tous les identifiants Adzuna déjà enregistrés, pour ne rien écrire deux fois."""
    vus = set()
    for f in DOSSIER.glob("*/*.jsonl"):
        with f.open(encoding="utf-8") as fh:
            for ligne in fh:
                if ligne.strip():
                    vus.add(json.loads(ligne)["id"])
    return vus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifier", action="store_true", help="teste seulement les clés")
    ap.add_argument("--rome", default="", help="un seul code ROME de REQUETES, pour essayer")
    args = ap.parse_args()

    c = cles()
    if c is None:
        print("Adzuna : clés absentes (ADZUNA_APP_ID, ADZUNA_APP_KEY), rien à faire.")
        return
    try:
        version = appeler("version", c)
    except RuntimeError as e:
        sys.exit(f"Adzuna : clés refusées ou API indisponible ({e}).")
    print(f"Connexion à l'API Adzuna : OK (version {version.get('api_version')})")
    if args.verifier:
        return
    if args.rome and args.rome not in REQUETES:
        sys.exit(f"{args.rome} n'est pas dans REQUETES (scripts/extraire_adzuna.py).")
    codes = [args.rome] if args.rome else list(REQUETES)

    aujourdhui = f"{date.today():%Y-%m-%d}"
    (DOSSIER / aujourdhui[:7]).mkdir(parents=True, exist_ok=True)
    vus = ids_connus()

    lignes_serie = []
    for code in codes:
        params = dict(c, **REQUETES[code], results_per_page=PAR_PAGE,
                      sort_by="date", max_days_old=2)
        try:
            reponse = appeler("jobs/fr/search/1", params)
        except RuntimeError as e:                     # quota atteint, panne : on garde ce qu'on a
            print(f"{code}  arrêt : {e}")
            break
        offres = reponse.get("results", [])
        nouvelles = 0
        with (DOSSIER / aujourdhui[:7] / f"{code}.jsonl").open("a", encoding="utf-8") as brut:
            for o in offres:
                if o["id"] not in vus:
                    vus.add(o["id"])
                    nouvelles += 1
                    brut.write(json.dumps({"id": o["id"], "vu_le": aujourdhui, "rome": code,
                                           "requete": REQUETES[code], "offre": o},
                                          ensure_ascii=False) + "\n")
        lignes_serie.append([aujourdhui, code, reponse.get("count", ""), len(offres), nouvelles])
        print(f"{code}  {METIERS[code][0]:<48} {len(offres):3d} récupérées, {nouvelles:3d} nouvelles")
        time.sleep(2.5)                               # 25 appels par minute au plus

    serie = DOSSIER / "serie.csv"
    lignes = []
    if serie.exists():
        with serie.open(encoding="utf-8") as f:
            lignes = [r for r in csv.reader(f)][1:]
    # Si on relance le même jour, la ligne du jour est remplacée, pas doublée.
    faits = {r[1] for r in lignes_serie}
    lignes = [r for r in lignes if not (r[0] == aujourdhui and r[1] in faits)] + lignes_serie
    with serie.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "rome", "total_annonce", "recuperees", "nouvelles"])
        w.writerows(sorted(lignes))

    print(f"\n{aujourdhui} : Adzuna, {sum(r[4] for r in lignes_serie)} nouvelles offres "
          f"sur {len(lignes_serie)} métiers.")


if __name__ == "__main__":
    main()
