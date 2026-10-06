"""
Scraper des offres d'emploi Welcome to the Jungle (pages « emploi » publiques).

Usage :
    python scraper.py emploi-developpeur-web-paris-75000
    python scraper.py emploi-developpeur-web-paris-75000 emploi-developpeur-web-lyon --suivre 5
    python scraper.py https://www.welcometothejungle.com/fr/pages/emploi-developpeur-web-paris-75000

Le script respecte le robots.txt, attend entre chaque page et s'identifie
avec un User-Agent explicite. Utilisez-le avec modération.
"""

import argparse
import csv
import json
import os
import re
import time
from datetime import date
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

BASE = "https://www.welcometothejungle.com"
USER_AGENT = "wttj-scraper-perso/1.0 (projet personnel, usage modere)"
DELAI_SECONDES = 5
PAGES_LIEES_MAX = 20
MAX_MOIS_DEFAUT = 6  # ancienneté maximale des offres conservées

CONTRATS = {
    "full_time": "CDI", "temporary": "CDD / Temporaire", "internship": "Stage",
    "apprenticeship": "Alternance", "freelance": "Freelance", "part_time": "Temps partiel",
    "vie": "VIE", "graduate_program": "Graduate program", "volunteer": "Bénévolat",
    "other": "Autres",
}
TELETRAVAIL = {
    "fulltime": "Télétravail total", "partial": "Télétravail fréquent",
    "punctual": "Télétravail occasionnel", "no": "Télétravail non autorisé", "unknown": "",
}
PERIODES = {"yearly": "an", "monthly": "mois", "daily": "jour", "hourly": "heure"}
ETUDES = {"bac": "Bac", "cap_bep": "CAP / BEP", "doctorate": "Doctorat"}

COLONNES = ["titre", "entreprise", "description_entreprise", "contrat", "duree_contrat_mois",
            "lieu", "departement", "region", "latitude", "longitude", "teletravail",
            "salaire", "salaire_min", "salaire_max", "salaire_periode", "experience_min_annees",
            "niveau_etudes", "secteur", "taille", "annee_creation", "date", "anciennete_jours",
            "recrute_activement", "resume", "missions", "avantages", "page", "url"]


# --- robots.txt ---------------------------------------------------------------

def lire_regles_robots(session):
    """Lit les règles « User-agent: * » du robots.txt (le RobotFileParser de Python ignore les jokers *)."""
    r = session.get(f"{BASE}/robots.txt", timeout=20)
    r.raise_for_status()
    regles, groupe_etoile, dans_agents = [], False, False
    for ligne in r.text.splitlines():
        ligne = ligne.split("#")[0].strip()
        if ":" not in ligne:
            continue
        cle, valeur = (x.strip() for x in ligne.split(":", 1))
        cle = cle.lower()
        if cle == "user-agent":
            groupe_etoile = (groupe_etoile and dans_agents) or valeur == "*"
            dans_agents = True
            continue
        dans_agents = False
        if groupe_etoile and cle in ("allow", "disallow") and valeur:
            motif = re.escape(valeur).replace(r"\*", ".*")
            if motif.endswith(r"\$"):
                motif = motif[:-2] + "$"
            regles.append((len(valeur), cle == "allow", re.compile(motif)))
    return regles


def robots_autorise(regles, url):
    parties = urlsplit(url)
    chemin = parties.path + (f"?{parties.query}" if parties.query else "")
    correspondances = [(longueur, autorise) for longueur, autorise, motif in regles if motif.match(chemin)]
    # La règle la plus longue l'emporte ; à égalité, Allow l'emporte
    return max(correspondances)[1] if correspondances else True


# --- Extraction ---------------------------------------------------------------

def construire_url(page_ou_url):
    if page_ou_url.startswith("http"):
        return page_ou_url.split("?")[0]
    return f"{BASE}/fr/pages/{page_ou_url.strip('/')}"


def nom_page(url):
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]


def donnees_initiales(html):
    """Données JSON que le site intègre dans la page (window.__INITIAL_DATA__)."""
    m = re.search(r"window\.__INITIAL_DATA__\s*=\s*", html)
    if not m:
        return None
    try:
        valeur, _ = json.JSONDecoder().raw_decode(html[m.end():])
        return json.loads(valeur) if isinstance(valeur, str) else valeur
    except ValueError:
        return None


def montant(valeur):
    if valeur in (None, ""):
        return ""
    return f"{valeur / 1000:g}K" if valeur >= 1000 else f"{valeur:g}"


def offre_depuis_json(hit):
    org = hit.get("organization") or {}
    bureau = (hit.get("offices") or [{}])[0]
    geo = (hit.get("_geoloc") or [{}])[0]
    smin, smax = hit.get("salary_minimum"), hit.get("salary_maximum")
    periode = PERIODES.get(hit.get("salary_period") or "", hit.get("salary_period") or "")
    salaire = ""
    if smin or smax:
        fourchette = " à ".join(montant(v) for v in (smin, smax) if v)
        salaire = f"{fourchette} {hit.get('salary_currency') or ''}".strip() + (f" / {periode}" if periode else "")
    duree = [hit.get("contract_duration_minimum"), hit.get("contract_duration_maximum")]
    etudes = hit.get("education_level") or ""
    taille = org.get("nb_employees")
    slug_org, slug = org.get("slug", ""), hit.get("slug", "")
    publication = hit.get("published_at") or ""

    return {
        "titre": hit.get("name", ""),
        "entreprise": org.get("name", ""),
        "description_entreprise": org.get("summary") or "",
        "contrat": CONTRATS.get(hit.get("contract_type") or "", hit.get("contract_type") or ""),
        "duree_contrat_mois": " à ".join(str(d) for d in duree if d),
        "lieu": bureau.get("city") or "",
        "departement": bureau.get("district") or "",
        "region": bureau.get("state") or "",
        "latitude": geo.get("lat", ""),
        "longitude": geo.get("lng", ""),
        "teletravail": TELETRAVAIL.get(hit.get("remote") or "", hit.get("remote") or ""),
        "salaire": salaire,
        "salaire_min": smin or "",
        "salaire_max": smax or "",
        "salaire_periode": periode,
        "experience_min_annees": hit.get("experience_level_minimum") if hit.get("experience_level_minimum") is not None else "",
        "niveau_etudes": ETUDES.get(etudes, etudes.replace("bac_", "Bac +")),
        "secteur": ", ".join(s.get("name", "") if isinstance(s, dict) else str(s)
                             for s in hit.get("sectors") or []),
        "taille": f"{taille:,} collaborateurs".replace(",", " ") if taille else "",
        "annee_creation": org.get("creation_year") or "",
        "date": hit.get("published_at_date") or publication[:10],
        "recrute_activement": False,
        "resume": hit.get("summary") or "",
        "missions": " | ".join(hit.get("key_missions") or []),
        "avantages": " | ".join(hit.get("benefits") or []),
        "url": f"{BASE}/fr/companies/{slug_org}/jobs/{slug}" if slug_org and slug else "",
    }


def texte(node):
    return node.get_text(" ", strip=True) if node else ""


ROLES = {
    "Contract": "contrat", "Location": "lieu", "Remote": "teletravail",
    "Salary": "salaire", "Tag": "secteur", "Department": "taille",
}


def offre_depuis_carte(carte):
    """Lecture d'une carte d'offre dans le HTML (complète ou remplace les données JSON)."""
    titre = carte.find(["h2", "h3"])
    lien = carte.find("a", href=re.compile(r"/companies/[^/]+/jobs/"))
    if titre is None or lien is None:
        return None
    logo = carte.select_one('img[data-testid^="job-thumb-logo"]')
    date = carte.find("time")
    offre = dict.fromkeys(COLONNES, "")
    offre.update({
        "titre": texte(titre), "entreprise": logo.get("alt", "") if logo else "",
        "description_entreprise": texte(carte.find("p")),
        "date": date.get("datetime", "")[:10] if date else "",
        "recrute_activement": False, "url": urljoin(BASE, lien["href"]),
    })
    # Chaque caractéristique est précédée d'une icône <svg alt="...">
    for icone in carte.find_all("svg", alt=True):
        if icone["alt"] == "Megaphone":
            offre["recrute_activement"] = True
        elif icone["alt"] in ROLES:
            offre[ROLES[icone["alt"]]] = texte(icone.parent).replace("Salaire :", "").strip()
    return offre


def extraire_page(html):
    """Renvoie (offres, nombre total annoncé, pages « emploi » liées)."""
    soup = BeautifulSoup(html, "html.parser")
    cartes = [o for o in (offre_depuis_carte(c) for c in
              soup.select('li[data-testid="jobs-results-list-list-item-wrapper"]')) if o]
    par_url = {o["url"]: o for o in cartes}

    offres, total = [], None
    data = donnees_initiales(html) or {}
    for requete in data.get("queries", []):
        cle = requete.get("queryKey") or []
        if not cle or cle[0] != "featured-context-results":
            continue
        for resultat in (requete.get("state", {}).get("data") or {}).get("results", []):
            # Un même bloc peut aussi lister des entreprises : on ne garde que les offres
            hits = [h for h in resultat.get("hits", []) if "organization" in h and "contract_type" in h]
            if not hits:
                continue
            total = resultat.get("nbHits", total)
            for hit in hits:
                offre = offre_depuis_json(hit)
                carte = par_url.get(offre["url"])
                if carte:
                    offre["recrute_activement"] = carte["recrute_activement"]
                offres.append(offre)
    if not offres:  # repli si le site cesse d'intégrer les données JSON
        offres = [dict(dict.fromkeys(COLONNES, ""), **o) for o in cartes]

    liees = []
    for a in soup.find_all("a", href=re.compile(r"^/fr/pages/emploi-[^?#]+$")):
        url = urljoin(BASE, a["href"])
        if url not in liees:
            liees.append(url)
    return offres, total, liees


# --- Mise à jour d'un CSV existant (option --mise-a-jour) ---------------------

COLONNES_SUIVI = ["premiere_vue", "derniere_vue", "statut"]


def cle_offre(offre):
    return offre.get("url") or "|".join(offre.get(c, "") for c in ("titre", "entreprise", "lieu"))


def lire_csv(chemin):
    if not os.path.exists(chemin):
        return []
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def fusionner(anciennes, nouvelles, champ_zone):
    """Fusionne les offres du jour avec celles du CSV existant.

    - offre déjà connue : mise à jour, en gardant sa date de première apparition,
      sa date de publication et les informations déjà récupérées ;
    - offre nouvelle : ajoutée ;
    - offre connue absente aujourd'hui alors que sa recherche/page a été relue :
      gardée avec le statut « non retrouvée » (expirée, ou simplement plus dans
      les premières pages de résultats).
    """
    aujourd_hui = date.today().isoformat()
    par_cle = {cle_offre(o): o for o in anciennes}
    zones_relues = {o.get(champ_zone, "") for o in nouvelles}
    resultat, vues, nb_nouvelles = [], set(), 0

    for offre in nouvelles:
        cle = cle_offre(offre)
        if cle in vues:
            continue
        vues.add(cle)
        ancienne = par_cle.get(cle)
        if ancienne:
            for champ, valeur in ancienne.items():
                if valeur and offre.get(champ) in ("", None):
                    offre[champ] = valeur
            if ancienne.get("date"):
                offre["date"] = ancienne["date"]
        else:
            nb_nouvelles += 1
        offre["premiere_vue"] = (ancienne or {}).get("premiere_vue") or aujourd_hui
        offre["derniere_vue"] = aujourd_hui
        offre["statut"] = "en ligne"
        resultat.append(offre)

    nb_non_retrouvees = 0
    for cle, ancienne in par_cle.items():
        if cle in vues:
            continue
        if ancienne.get(champ_zone, "") in zones_relues and ancienne.get("statut") != "non retrouvée":
            ancienne["statut"] = "non retrouvée"
            nb_non_retrouvees += 1
        resultat.append(ancienne)

    print(f"Mise à jour : {nb_nouvelles} nouvelles offres, {len(nouvelles) - nb_nouvelles} déjà connues, "
          f"{nb_non_retrouvees} non retrouvées aujourd'hui")
    resultat.sort(key=lambda o: o.get("date") or "", reverse=True)
    return resultat


# --- Programme principal ------------------------------------------------------

def date_limite(max_mois, aujourd_hui=None):
    """Date d'il y a max_mois mois (le jour est ramené au dernier jour du mois si besoin)."""
    aujourd_hui = aujourd_hui or date.today()
    total = aujourd_hui.year * 12 + aujourd_hui.month - 1 - max_mois
    annee, mois = divmod(total, 12)
    for jour in range(aujourd_hui.day, 27, -1):
        try:
            return date(annee, mois + 1, jour)
        except ValueError:
            continue
    return date(annee, mois + 1, min(aujourd_hui.day, 28))


def filtrer_par_anciennete(offres, max_mois):
    """Garde les offres publiées depuis moins de max_mois mois (0 = pas de filtre)."""
    aujourd_hui = date.today()
    for offre in offres:
        offre["anciennete_jours"] = ""
        try:
            offre["anciennete_jours"] = (aujourd_hui - date.fromisoformat(offre["date"])).days
        except ValueError:
            offre["date"] = ""
    if not max_mois:
        return offres
    limite = date_limite(max_mois, aujourd_hui).isoformat()
    gardees = [o for o in offres if not o["date"] or o["date"] >= limite]
    if len(gardees) < len(offres):
        print(f"{len(offres) - len(gardees)} offres publiées avant le {limite} écartées")
    sans_date = sum(1 for o in gardees if not o["date"])
    if sans_date:
        print(f"{sans_date} offres sans date lisible conservées")
    return gardees


def scraper(pages, suivre=0, max_mois=MAX_MOIS_DEFAUT):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    offres, vues = [], set()
    try:
        regles = lire_regles_robots(session)
    except Exception as e:
        print(f"Impossible de lire robots.txt ({e}), arrêt par prudence.")
        return offres

    a_visiter = [construire_url(p) for p in pages]
    visitees, liees_ajoutees = set(), 0
    while a_visiter:
        url = a_visiter.pop(0)
        if url in visitees:
            continue
        if not robots_autorise(regles, url):
            print(f"robots.txt n'autorise pas {url}, page ignorée.")
            continue
        if visitees:
            time.sleep(DELAI_SECONDES)
        visitees.add(url)
        print(f"Page : {url}")
        r = session.get(url, timeout=20)
        if r.status_code in (403, 429):
            print(f"  réponse {r.status_code} : le site limite les requêtes, arrêt. Réessayez plus tard.")
            break
        if r.status_code != 200:
            print(f"  réponse {r.status_code}, page ignorée.")
            continue

        trouvees, total, liees = extraire_page(r.text)
        nouvelles = 0
        for offre in trouvees:
            cle = offre["url"] or (offre["titre"], offre["entreprise"])
            if cle in vues:
                continue
            vues.add(cle)
            offre["page"] = nom_page(url)
            offres.append(offre)
            nouvelles += 1
        info_total = f" (sur {total} annoncées par le site)" if total else ""
        print(f"  {nouvelles} offres récupérées{info_total}")
        if not trouvees:
            print("  aucune offre sur cette page : vérifiez son nom sur le site (ex. emploi-developpeur-web-paris-75000)")

        for lien in liees:
            if liees_ajoutees >= suivre:
                break
            if lien not in visitees and lien not in a_visiter:
                a_visiter.append(lien)
                liees_ajoutees += 1

    return filtrer_par_anciennete(offres, max_mois)


def enregistrer_csv(offres, chemin):
    if not offres:
        print("Aucune offre à enregistrer.")
        return
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    colonnes = list(COLONNES)
    for offre in offres:  # toutes les colonnes rencontrées, dans l'ordre
        colonnes += [c for c in offre if c not in colonnes]
    # Écrit dans un fichier temporaire puis remplace : l'ancien CSV reste intact en cas d'erreur
    temporaire = chemin + ".tmp"
    with open(temporaire, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colonnes, delimiter=";", restval="")
        writer.writeheader()
        writer.writerows(offres)
    try:
        os.replace(temporaire, chemin)
    except PermissionError:
        os.remove(temporaire)
        print(f"Impossible d'écrire {chemin} : est-il ouvert dans Excel ? Fermez-le et relancez.")
        return
    print(f"{len(offres)} offres enregistrées dans {chemin}")


def main():
    p = argparse.ArgumentParser(description="Récupère des offres sur Welcome to the Jungle.")
    p.add_argument("pages", nargs="+",
                   help="Une ou plusieurs pages (ex. emploi-developpeur-web-paris-75000) ou URL complètes")
    p.add_argument("--suivre", type=int, default=0,
                   help=f"Visite aussi jusqu'à N pages « emploi » liées (métiers ou villes proches, max {PAGES_LIEES_MAX})")
    p.add_argument("--max-mois", type=int, default=MAX_MOIS_DEFAUT,
                   help=f"Écarte les offres publiées il y a plus de N mois ({MAX_MOIS_DEFAUT} par défaut, 0 = toutes)")
    p.add_argument("--mise-a-jour", action="store_true",
                   help="Met à jour le CSV de sortie existant au lieu de le remplacer")
    p.add_argument("--sortie", default="data/offres_wttj.csv", help="Fichier CSV de sortie")
    args = p.parse_args()

    max_mois = max(args.max_mois, 0)
    offres = scraper(args.pages, min(max(args.suivre, 0), PAGES_LIEES_MAX), max_mois)
    if args.mise_a_jour:
        offres = filtrer_par_anciennete(fusionner(lire_csv(args.sortie), offres, "page"), max_mois)
    enregistrer_csv(offres, args.sortie)


if __name__ == "__main__":
    main()
