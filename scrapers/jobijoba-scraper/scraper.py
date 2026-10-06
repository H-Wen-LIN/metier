"""
Scraper des offres d'emploi Jobijoba (pages de résultats publiques).

Usage :
    python scraper.py "developpeur web" --ville Clermont-ferrand --pages 2
    python scraper.py "developpeur web" --ville Paris --ville Lyon --pages 5 --details

Le script respecte le robots.txt, attend entre chaque requête et s'identifie
avec un User-Agent explicite. Utilisez-le avec modération.
"""

import argparse
import codecs
import csv
import json
import os
import re
import sys
import time
from urllib.parse import quote_plus, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

BASE = "https://www.jobijoba.com"
USER_AGENT = "jobijoba-scraper-perso/1.0 (projet personnel, usage modere)"
DELAI_SECONDES = 3          # entre deux pages de résultats
DELAI_DETAILS_SECONDES = 2  # entre deux pages d'offre (option --details)
PAGES_MAX = 10              # 30 offres par page

# Icône de chaque caractéristique d'une offre -> colonne du CSV
ICONES = {
    "icon-map-marker": "lieu",
    "icon-register": "contrat",
    "icon-apartment": "entreprise",
    "icon-resume-briefcase": "metier",
    "icon-banknot": "salaire",
    "icon-home": "teletravail",
}

COLONNES = ["titre", "metier", "categorie", "lieu", "contrat", "entreprise", "salaire",
            "teletravail", "date", "resume", "sponsorise", "recherche", "url"]
COLONNES_DETAILS = ["date_publication", "date_expiration", "code_postal", "region",
                    "salaire_min", "salaire_max", "salaire_periode", "temps_travail",
                    "description"]


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


# --- Pages de résultats -------------------------------------------------------

def construire_url(mot_cle, ville=None):
    url = f"{BASE}/fr/emploi/{quote_plus(mot_cle.strip())}"
    if ville:
        url += "/" + quote_plus(ville.strip().capitalize())
    return url


def texte(node):
    return node.get_text(" ", strip=True) if node else ""


def decoder_lien(code):
    """Les liens des offres sont encodés en ROT13 dans l'attribut data-atc ("=pt=" = ".")."""
    url = codecs.decode(code, "rot13").replace("=cg=", ".")
    return url if url.startswith("http") else ""


def extraire_offre(carte):
    offre = dict.fromkeys(COLONNES, "")
    offre.update({
        "titre": texte(carte.select_one(".offer-header-title")),
        "date": texte(carte.select_one(".publication_date")),
        "resume": texte(carte.select_one(".description")).replace("…", "").strip(),
        "sponsorise": carte.select_one(".sponsorised") is not None,
    })
    for feature in carte.select(".offer-features .feature"):
        icone = feature.select_one(".iconwrap span[class]")
        colonne = next((ICONES[c] for c in (icone.get("class") if icone else []) if c in ICONES), None)
        if colonne:
            offre[colonne] = texte(feature)

    # Catégorie (secteur) fournie dans les données de suivi de la carte
    produit = carte.select_one("[data-product]")
    if produit:
        try:
            infos = json.loads(produit["data-product"])["ecommerce"]["click"]["products"][0]
            offre["categorie"] = infos.get("category", "")
        except (ValueError, KeyError, IndexError):
            pass

    lien = carte.find("a", href=re.compile(r"/annonce/"))
    if lien:
        offre["url"] = urljoin(BASE, lien["href"])
    else:
        encode = carte.select_one("[data-atc]")
        if encode:
            offre["url"] = decoder_lien(encode["data-atc"])
    return offre


def etat_recherche(html):
    """Reconstitue les paramètres envoyés par le bouton « Voir les offres suivantes »."""
    def tags(fonction):
        bloc = re.search(rf"function {fonction}\(\)\s*\{{(.*?)\n\s*\}}", html, re.S)
        if not bloc:
            return []
        return [
            {cle: json.loads(f'"{valeur}"') for cle, valeur in
             re.findall(r'(libelle|url|type):\s*"((?:[^"\\]|\\.)*)"', tag)}
            for tag in re.findall(r"tagsinput\(\"add\",\s*\{(.*?)\}", bloc.group(1), re.S)
        ]

    whats = {"company": [], "sector": [], "jobtitle": [], "unknown": []}
    what_urls = {"company": [], "sector": [], "jobtitle": [], "unknown": []}
    for tag in tags("addWhatTagsInput"):
        type_ = tag.get("type") if tag.get("type") in whats else "unknown"
        whats[type_].append(tag.get("libelle", ""))
        what_urls[type_].append(tag.get("url", ""))
    where = (tags("addWhereTagsInput") or [{}])[0]
    return {
        "whats": json.dumps(whats, ensure_ascii=False, separators=(",", ":")),
        "whatUrls": json.dumps(what_urls, ensure_ascii=False, separators=(",", ":")),
        "where": where.get("url", ""), "where_type": where.get("type", ""),
        "perimeter": "0", "period": "", "contract_type": "", "remote_work_type": "",
    }


def page_suivante(soup, etat):
    """Paramètres de la requête AJAX de la page suivante, ou None s'il n'y en a plus."""
    bouton = soup.select_one("#pagination .next[data-next-page]")
    if bouton is None or etat is None:
        return None
    return dict(etat, page=bouton["data-next-page"], editor_id=bouton.get("data-editor-id", ""),
                clean=bouton.get("data-clean-url", ""), category=bouton.get("data-category", ""))


def scraper_recherche(session, regles, mot_cle, ville, pages, offres, vues, sponsorises=True):
    recherche = f"{mot_cle} / {ville}" if ville else mot_cle
    url, params, etat = construire_url(mot_cle, ville), None, None

    for page in range(1, pages + 1):
        if page > 1:
            url = f"{BASE}/fr/ajax_pagination"
            time.sleep(DELAI_SECONDES)
        if not robots_autorise(regles, url):
            print(f"robots.txt n'autorise pas {url}, arrêt.")
            break
        print(f"[{recherche}] page {page}")
        r = session.get(url, params=params, timeout=20)
        if r.status_code != 200:
            print(f"Réponse {r.status_code}, arrêt.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        if page == 1:
            etat = etat_recherche(r.text)
            total = re.search(r"sur (\d+)\)", texte(soup.select_one("#pagination")))
            if total:
                print(f"  {total.group(1)} offres annoncées par le site")

        nouvelles = 0
        for carte in soup.select("div.offer"):
            offre = extraire_offre(carte)
            if not offre["titre"] or (offre["sponsorise"] and not sponsorises):
                continue
            cle = offre["url"] or (offre["titre"], offre["lieu"], offre["entreprise"])
            if cle in vues:
                continue
            vues.add(cle)
            offre["recherche"] = recherche
            offres.append(offre)
            nouvelles += 1
        print(f"  {nouvelles} nouvelles offres")

        params = page_suivante(soup, etat)
        if nouvelles == 0 or params is None:
            break


# --- Pages d'offre (option --details) -----------------------------------------

def nettoyer_html(fragment):
    texte_brut = BeautifulSoup(fragment.replace("<br", "\n<br"), "html.parser").get_text()
    return re.sub(r"\n{3,}", "\n\n", texte_brut).strip()


def extraire_details(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "JobPosting":
            continue
        adresse = (data.get("jobLocation") or {}).get("address") or {}
        salaire = ((data.get("baseSalary") or {}).get("value")) or {}
        type_emploi = data.get("employmentType") or []
        return {
            "date_publication": (data.get("datePosted") or "")[:10],
            "date_expiration": (data.get("validThrough") or "")[:10],
            "code_postal": adresse.get("postalCode", ""),
            "region": adresse.get("addressRegion", ""),
            "salaire_min": salaire.get("minValue", ""),
            "salaire_max": salaire.get("maxValue", ""),
            "salaire_periode": {"YEAR": "an", "MONTH": "mois", "HOUR": "heure"}.get(
                salaire.get("unitText", ""), salaire.get("unitText", "")),
            "temps_travail": ", ".join(type_emploi if isinstance(type_emploi, list) else [type_emploi]),
            "description": nettoyer_html(data.get("description", "")),
        }
    # Certaines offres (reprises d'autres sites) n'ont pas de JSON-LD : description seule
    blocs = soup.select(".offer.current .permalink-description")
    return {"description": "\n\n".join(b.get_text("\n", strip=True) for b in blocs)}


def ajouter_details(session, regles, offres):
    a_lire = [o for o in offres if "/annonce/" in o["url"] and robots_autorise(regles, o["url"])]
    print(f"Lecture du détail de {len(a_lire)} offres (environ {len(a_lire) * DELAI_DETAILS_SECONDES // 60 + 1} min)…")
    for o in offres:
        o.update(dict.fromkeys(COLONNES_DETAILS, ""))
    for i, offre in enumerate(a_lire, 1):
        if i > 1:
            time.sleep(DELAI_DETAILS_SECONDES)
        try:
            r = session.get(offre["url"], timeout=20)
        except requests.RequestException as e:
            print(f"  {offre['url']} : {e}")
            continue
        if r.status_code == 200:
            offre.update(extraire_details(r.text))
        if i % 10 == 0:
            print(f"  {i}/{len(a_lire)}")


# --- Programme principal ------------------------------------------------------

def scraper(mot_cle, villes=None, pages=1, details=False, sponsorises=True):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    offres, vues = [], set()
    try:
        regles = lire_regles_robots(session)
    except Exception as e:
        print(f"Impossible de lire robots.txt ({e}), arrêt par prudence.")
        return offres

    for i, ville in enumerate(villes or [None]):
        if i > 0:
            time.sleep(DELAI_SECONDES)
        scraper_recherche(session, regles, mot_cle, ville, pages, offres, vues, sponsorises)

    if details and offres:
        ajouter_details(session, regles, offres)
    return offres


def enregistrer_csv(offres, chemin):
    if not offres:
        print("Aucune offre à enregistrer.")
        return
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=offres[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(offres)
    print(f"{len(offres)} offres enregistrées dans {chemin}")


def main():
    p = argparse.ArgumentParser(description="Récupère des offres d'emploi sur Jobijoba.")
    p.add_argument("mot_cle", help='Métier ou mot-clé, ex. "developpeur web"')
    p.add_argument("--ville", action="append",
                   help="Ville, ex. Clermont-ferrand (option répétable : --ville Paris --ville Lyon)")
    p.add_argument("--pages", type=int, default=1,
                   help=f"Nombre de pages de 30 offres par ville (max {PAGES_MAX})")
    p.add_argument("--details", action="store_true",
                   help="Ouvre chaque offre pour récupérer la description complète, le code postal, "
                        "le salaire chiffré… (plus lent)")
    p.add_argument("--sans-sponsorises", action="store_true",
                   help="Ignore les offres sponsorisées (souvent sans rapport avec la recherche)")
    p.add_argument("--sortie", default="data/offres.csv", help="Fichier CSV de sortie")
    args = p.parse_args()

    pages = min(max(args.pages, 1), PAGES_MAX)
    offres = scraper(args.mot_cle, args.ville, pages, args.details, not args.sans_sponsorises)
    enregistrer_csv(offres, args.sortie)


if __name__ == "__main__":
    sys.exit(main())
