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
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

BASE = "https://www.jobijoba.com"
USER_AGENT = "jobijoba-scraper-perso/1.0 (projet personnel, usage modere)"
DELAI_SECONDES = 3          # entre deux pages de résultats
DELAI_DETAILS_SECONDES = 2  # entre deux pages d'offre (option --details)
PAGES_MAX = 10              # 30 offres par page
MAX_MOIS_DEFAUT = 6         # ancienneté maximale des offres conservées
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

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
            "teletravail", "date", "anciennete_jours", "date_affichee", "resume", "sponsorise",
            "recherche", "url"]
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
        "date_affichee": texte(carte.select_one(".publication_date")),
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

    publication = date_depuis_texte(offre["date_affichee"])
    offre["date"] = publication.isoformat() if publication else ""

    lien = carte.find("a", href=re.compile(r"/annonce/"))
    if lien:
        offre["url"] = urljoin(BASE, lien["href"])
    else:
        encode = carte.select_one("[data-atc]")
        if encode:
            offre["url"] = decoder_lien(encode["data-atc"])
    return offre


def date_depuis_texte(valeur, maintenant=None):
    """Convertit « Il y a 13 h », « Hier », « 11 juin »… en date.

    Jobijoba n'affiche pas l'année : « 11 juin » est compris comme le 11 juin
    passé le plus récent. Seule l'option --details donne la date exacte.
    """
    maintenant = maintenant or datetime.now()
    valeur = valeur.strip().lower()
    if not valeur:
        return None
    if valeur.startswith("aujourd"):
        return maintenant.date()
    if valeur.startswith("hier"):
        return maintenant.date() - timedelta(days=1)
    m = re.match(r"il y a (\d+)\s*(min|h|j|jour|sem|mois)", valeur)
    if m:
        n, unite = int(m.group(1)), m.group(2)
        ecart = {"min": timedelta(minutes=n), "h": timedelta(hours=n), "j": timedelta(days=n),
                 "jour": timedelta(days=n), "sem": timedelta(weeks=n), "mois": timedelta(days=30 * n)}
        return (maintenant - ecart[unite]).date()
    m = re.match(r"(\d{1,2})\s+([a-zéû]+)(?:\s+(\d{4}))?", valeur)
    if m and m.group(2) in MOIS:
        jour, mois = int(m.group(1)), MOIS.index(m.group(2)) + 1
        annee = int(m.group(3)) if m.group(3) else maintenant.year
        try:
            resultat = date(annee, mois, jour)
            if not m.group(3) and resultat > maintenant.date():
                resultat = date(annee - 1, mois, jour)
        except ValueError:
            return None
        return resultat
    return None


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
        print(f"  {nouvelles} offres récupérées")

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


def ajouter_details(session, regles, offres, deja_lues=()):
    a_lire = [o for o in offres if "/annonce/" in o["url"] and o["url"] not in deja_lues
              and robots_autorise(regles, o["url"])]
    for o in offres:
        o.update(dict.fromkeys(COLONNES_DETAILS, ""))
    if not a_lire:
        return
    print(f"Lecture du détail de {len(a_lire)} offres (environ {len(a_lire) * DELAI_DETAILS_SECONDES // 60 + 1} min)…")
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
            if offre.get("date_publication"):  # date exacte, plus fiable que la liste
                offre["date"] = offre["date_publication"]
        if i % 10 == 0:
            print(f"  {i}/{len(a_lire)}")


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

def scraper(mot_cle, villes=None, pages=1, details=False, sponsorises=True,
            max_mois=MAX_MOIS_DEFAUT, deja_lues=()):
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

    # Filtre une première fois avant --details pour ne pas ouvrir d'offres trop anciennes
    offres = filtrer_par_anciennete(offres, max_mois)
    if details and offres:
        ajouter_details(session, regles, offres, deja_lues)
        offres = filtrer_par_anciennete(offres, max_mois)
    return offres


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
    p.add_argument("--max-mois", type=int, default=MAX_MOIS_DEFAUT,
                   help=f"Écarte les offres publiées il y a plus de N mois ({MAX_MOIS_DEFAUT} par défaut, 0 = toutes)")
    p.add_argument("--mise-a-jour", action="store_true",
                   help="Met à jour le CSV de sortie existant au lieu de le remplacer")
    p.add_argument("--sortie", default="data/offres.csv", help="Fichier CSV de sortie")
    args = p.parse_args()

    pages = min(max(args.pages, 1), PAGES_MAX)
    max_mois = max(args.max_mois, 0)
    anciennes = lire_csv(args.sortie) if args.mise_a_jour else []
    # En mise à jour, les offres déjà détaillées ne sont pas rouvertes
    deja_lues = {o["url"] for o in anciennes if o.get("description")}
    offres = scraper(args.mot_cle, args.ville, pages, args.details, not args.sans_sponsorises,
                     max_mois, deja_lues)
    if args.mise_a_jour:
        offres = filtrer_par_anciennete(fusionner(anciennes, offres, "recherche"), max_mois)
    enregistrer_csv(offres, args.sortie)


if __name__ == "__main__":
    sys.exit(main())
