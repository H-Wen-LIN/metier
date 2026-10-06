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

Adzuna n'a pas de code ROME : chaque métier est une ou plusieurs recherches de mots dans le
titre (REQUETES), à affiner en lisant les titres renvoyés. Les offres des deux derniers jours,
triées par date, 50 par page, jusqu'à `pages` pages : la pagination s'arrête dès qu'une page
n'est pas pleine. Environ 40 appels par jour, ~1 200 par mois, sous le quota gratuit (2 500).

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


def R(*titres, exclure=(), pages=1):
    """Une entrée de REQUETES : les recherches à faire pour un métier.

    titres  : chaque chaîne est une recherche Adzuna `title_only` ; tous ses mots doivent figurer
              dans le titre (« directeur marketing » = directeur ET marketing). Plusieurs chaînes
              = plusieurs recherches, réunies.
    exclure : mots qui écartent une offre s'ils sont dans son TITRE. Filtré ici, pas par l'API :
              le `what_exclude` d'Adzuna regarde aussi la description et écarte trop d'offres
              (« directeur marketing » : 42 offres sur 30 jours, 9 avec what_exclude=digital).
    pages   : pages de 50 offres au plus, par recherche ; à relever si un métier dépasse 50 offres
              en deux jours (voir total_annonce dans data/adzuna/serie.csv).
    """
    return {"titres": list(titres), "exclure": list(exclure), "pages": pages}


# Code ROME -> recherches Adzuna. Volumes du 06/10/2026, offres des deux derniers jours, en commentaire.
REQUETES = {
    # Cœur marketing
    "M1718": R("marketing digital", exclure=("directeur", "directrice", "responsable", "head")),   # 36
    "M1716": R("directeur marketing digital", "responsable marketing digital"),                   # 1 + 3
    "M1705": R("responsable marketing", exclure=("digital",)),                                     # 13
    "M1703": R("chef produit", exclure=("digital",), pages=2),                                     # 66
    "M1620": R("assistant marketing", pages=2),                                                    # 50
    "M1706": R("promotion ventes"),
    "M1430": R("études marketing"),
    "M1711": R("directeur marketing", "head marketing", exclure=("digital",)),                     # 2 + 2
    # Digital, contenu, e-commerce
    "E1113": R("e-commerce", exclure=("assistant", "assistante"), pages=2),                        # 91
    "D1438": R("assistant e-commerce"),
    "E1101": R("community manager", pages=5),                                                      # 211
    "E1124": R("social media"),
    "E1405": R("SEO"),
    "M1886": R("chef projet web"),
    "M1426": R("chief digital"),                                    # rare : 1 offre sur 30 jours
    "M1719": R("influence"),                                                                       # 19
    "E1406": R("influenceur", "créateur contenu", "UGC"),                                          # 0 + 2 + 0
    # Communication et commerce, à la frontière
    "E1112": R("chargé communication", pages=2),                                                   # 97
    "E1103": R("relations presse", "relations publiques", "attaché presse"),                       # 38 sur 30 j
    "E1107": R("événementiel", pages=2),                                                           # 61
    "E1404": R("publicité"),
    "D1506": R("merchandising"),
    "D1415": R("CRM"),
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
    arret = None
    for code in codes:
        req = REQUETES[code]
        total, offres = 0, {}
        for titre in req["titres"]:
            for page in range(1, req["pages"] + 1):
                params = dict(c, title_only=titre, results_per_page=PAR_PAGE,
                              sort_by="date", max_days_old=2)
                try:
                    reponse = appeler(f"jobs/fr/search/{page}", params)
                except RuntimeError as e:             # quota atteint, panne : on garde ce qu'on a
                    arret = f"{code}  arrêt : {e}"
                    break
                if page == 1:
                    total += reponse.get("count") or 0
                lot = reponse.get("results", [])
                for o in lot:
                    if not any(m in o.get("title", "").lower() for m in req["exclure"]):
                        offres.setdefault(o["id"], o)
                time.sleep(2.5)                       # 25 appels par minute au plus
                if len(lot) < PAR_PAGE:
                    break
            if arret:
                break
        if arret:
            print(arret)
            break
        nouvelles = 0
        with (DOSSIER / aujourdhui[:7] / f"{code}.jsonl").open("a", encoding="utf-8") as brut:
            for o in offres.values():
                if o["id"] not in vus:
                    vus.add(o["id"])
                    nouvelles += 1
                    brut.write(json.dumps({"id": o["id"], "vu_le": aujourdhui, "rome": code,
                                           "requete": req, "offre": o},
                                          ensure_ascii=False) + "\n")
        lignes_serie.append([aujourdhui, code, total, len(offres), nouvelles])
        print(f"{code}  {METIERS[code][0]:<48} {total:4d} annoncées, {len(offres):3d} gardées, "
              f"{nouvelles:3d} nouvelles")

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
