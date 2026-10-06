r"""Audit des données avant de formuler des hypothèses : ce qui est observable, combien, avec quels trous.

Usage :
    python recherche/audit.py                 # D1415, toutes les offres vues jusqu'à aujourd'hui
    python recherche/audit.py --rome M1718    # un autre code ROME
    python recherche/audit.py --jusquau 2026-10-06

Règle : ce script ne calcule QUE des distributions marginales, des taux de remplissage et des
problèmes de mesure. Il ne croise jamais une variable explicative avec une variable à expliquer :
les hypothèses de recherche/PROTOCOLE.md doivent être testées sur des offres que personne n'a
regardées en les formulant (échantillon de confirmation, offres créées après le gel du protocole).

Lit data/brut/*/*.jsonl (dernière version de chaque offre) et data/actives/*.csv (présence jour par jour).
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
from resumer import exp_ans, salaire_min_max  # noqa: E402  (mêmes règles que le site)

IDF = {"75", "77", "78", "91", "92", "93", "94", "95"}

# Dictionnaires sur l'intitulé + la description. Chaque entrée : (motif repéré, motif qui annule).
# Validés par le double codage de 120 offres (recherche/codage/resultats.md) :
#   teletravail (v2), langue_etrangere, horaires_atypiques : utilisables ;
#   orientation_commerciale : NON utilisable (rappel 26 %, et 70 % de précision au mieux) :
#     cette variable se code par lecture, avec la grille recherche/codage/a_coder/CODEBOOK.md ;
#   outil_crm_nomme, centre_appels : non validés, prévalence descriptive seulement.
DICTIONNAIRES = {
    # v2 : « hybride » seul repérait les véhicules hybrides ; « pas de télétravail possible » était
    # compté ; « Smart Working » et « travail à domicile » étaient manqués.
    "teletravail": (r"t[ée]l[ée][- ]?travail|remote|smart[- ]?working|travail (à|a) (domicile|distance)"
                    r"|(travail|poste|mode|organisation|rythme|format) hybride|en hybride",
                    r"(pas de|sans|aucun|non) t[ée]l[ée][- ]?travail|t[ée]l[ée][- ]?travail (non|impossible|exclu)"),
    "langue_etrangere": (r"\banglais\b|english|bilingue|espagnol|allemand|italien|n[ée]erlandais|portugais", None),
    "horaires_atypiques": (r"samedi|week-end|weekend|dimanche", None),
    "outil_crm_nomme": (r"salesforce|zendesk|hubspot|dynamics|freshdesk|zoho|genesys|odigo", None),
    "centre_appels": (r"centre d'appels?|call[- ]cent|centre de contact|plateau t[ée]l[ée]phonique", None),
}


def repere(nom, texte):
    """1 si le dictionnaire repère le texte (motif trouvé, et pas de motif qui l'annule)."""
    motif, annule = DICTIONNAIRES[nom]
    return re.search(motif, texte, re.IGNORECASE) is not None and not (
        annule and re.search(annule, texte, re.IGNORECASE))



def charger(rome, jusquau):
    """Dernière version de chaque offre du code ROME, et le jour où on l'a vue pour la première fois."""
    offres, premiere = {}, {}
    for f in sorted((RACINE / "data" / "brut").glob(f"*/{rome}.jsonl")):
        for ligne in f.open(encoding="utf-8"):
            if ligne.strip():
                v = json.loads(ligne)
                if jusquau and v["vu_le"] > jusquau:
                    continue
                offres[v["id"]] = v["offre"]
                premiere.setdefault(v["id"], v["vu_le"])
    return offres, premiere


def rempli(o, champ):
    val = o.get(champ)
    if champ == "entreprise":
        return bool((val or {}).get("nom"))
    return val not in (None, "", [], {})


def unite(o):
    mot = ((o.get("salaire") or {}).get("libelle") or "").split(" ", 1)[0]
    return mot if mot in ("Annuel", "Mensuel", "Horaire") else "aucune"


def montant(o):
    m = re.match(r"\w+ de (\d+(?:\.\d+)?)", (o.get("salaire") or {}).get("libelle") or "")
    return float(m.group(1)) if m else None


def pct(a, b):
    return f"{a:>5d} / {b:<5d} {100 * a / b:5.1f} %" if b else f"{a} / 0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rome", default="D1415")
    ap.add_argument("--jusquau", default="", help="AAAA-MM-JJ : ignore les versions vues après")
    args = ap.parse_args()

    offres, premiere = charger(args.rome, args.jusquau)
    d = list(offres.values())
    n = len(d)
    print(f"# Audit {args.rome} — {n} offres distinctes vues entre {min(premiere.values())} "
          f"et {max(premiere.values())}\n")

    # 1. Remplissage, selon le canal : origine 1 = saisie à France Travail, 2 = site partenaire.
    canaux = {c: [o for o in d if o["origineOffre"]["origine"] == c] for c in ("1", "2")}
    print("## Taux de remplissage par canal\n")
    print(f"{'champ':30s} {'tous':>8s} {'FT (1)':>8s} {'partenaire (2)':>15s}")
    champs = ["entreprise", "salaire", "secteurActivite", "qualificationCode", "trancheEffectifEtab",
              "competences", "qualitesProfessionnelles", "formations", "langues", "permis",
              "deplacementCode", "offresManqueCandidats", "dureeTravailLibelleConverti"]
    for c in champs:
        cells = [100 * sum(rempli(o, c) for o in g) / max(len(g), 1) for g in (d, canaux["1"], canaux["2"])]
        print(f"{c:30s} {cells[0]:7.1f}% {cells[1]:7.1f}% {cells[2]:14.1f}%")
    print(f"{'(effectif)':30s} {n:8d} {len(canaux['1']):8d} {len(canaux['2']):15d}")

    # 2. Le salaire : unité, plancher, conversion.
    hors_alt = [o for o in d if not o["alternance"]]
    exploitables = [o for o in hors_alt if salaire_min_max((o.get("salaire") or {}).get("libelle"))[0]]
    print("\n## Salaire (hors alternance)\n")
    print("salaire exploitable           ", pct(len(exploitables), len(hors_alt)))
    print("unités                        ", dict(Counter(unite(o) for o in hors_alt)))
    print("unités par contrat            ", {t: dict(Counter(unite(o) for o in hors_alt if o["typeContrat"] == t))
                                             for t in ("CDI", "CDD", "MIS")})
    horaires = [montant(o) for o in hors_alt if unite(o) == "Horaire"]
    plancher_h = min(horaires) if horaires else None
    if plancher_h:
        plancher_m = plancher_h * 151.67
        mensuels = [montant(o) for o in hors_alt if unite(o) == "Mensuel"]
        print(f"plancher horaire observé       {plancher_h:.2f} €  -> mensuel 35 h = {plancher_m:.0f} €, "
              f"annuel = {12 * plancher_m:.0f} €")
        print("mensuels ≤ plancher + 2 %     ", pct(sum(m <= 1.02 * plancher_m for m in mensuels), len(mensuels)))
        print("horaires ≤ plancher + 2 %     ", pct(sum(h <= 1.02 * plancher_h for h in horaires), len(horaires)))
        print(f"biais de conversion : horaire × 1 607 h = {plancher_h * 1607:.0f} € contre "
              f"mensuel × 12 = {12 * plancher_m:.0f} € pour le même plancher "
              f"({100 * (plancher_h * 1607 / (12 * plancher_m) - 1):+.1f} %)")
    fourchettes = [salaire_min_max(o["salaire"]["libelle"]) for o in exploitables]
    print("fourchette (max > min)        ", pct(sum(b > a for a, b in fourchettes), len(fourchettes)))
    print("temps partiel déclaré         ", sum(o.get("dureeTravailLibelleConverti") == "Temps partiel" for o in d))

    # 3. Variables complètes et presque sans variance.
    print("\n## Distributions marginales\n")
    print("contrat        ", dict(Counter(o["typeContrat"] for o in d)))
    print("nature         ", dict(Counter(o["natureContrat"] for o in d)))
    print("expérience     ", dict(Counter(o["experienceExige"] for o in d)),
          "| durée connue :", sum(exp_ans(o["experienceLibelle"]) is not None for o in d))
    print("qualification  ", dict(Counter(o.get("qualificationLibelle") for o in d)))
    print("taille étab.   ", dict(Counter(o.get("trancheEffectifEtab") for o in d).most_common(6)))
    print("Île-de-France  ", pct(sum((o["lieuTravail"].get("libelle") or "")[:2] in IDF for o in d), n))
    print("NAF 78 (agences d'emploi, intérim) :", pct(sum(o.get("secteurActivite") == "78" for o in d), n))
    print("nombrePostes   ", dict(Counter(o["nombrePostes"] for o in d)))
    jeux = Counter(tuple(sorted(c.get("code", "") for c in o["competences"])) for o in d if o.get("competences"))
    if jeux:
        print("compétences : jeu le plus fréquent =", pct(jeux.most_common(1)[0][1], sum(jeux.values())),
              "des offres qui en listent (modèle pré-rempli du formulaire)")

    # 4. Variables tirées du texte : prévalence seulement.
    print("\n## Dictionnaires sur l'intitulé + la description (prévalence)\n")
    for nom in DICTIONNAIRES:
        print(f"{nom:25s}", pct(sum(repere(nom, o["intitule"] + " " + o["description"]) for o in d), n))

    # 5. Indépendance des observations.
    employeurs = Counter((o.get("entreprise") or {}).get("nom") for o in d if rempli(o, "entreprise"))
    textes = Counter(hashlib.md5(o["description"].encode()).hexdigest() for o in d)
    print("\n## Indépendance des observations\n")
    print("employeurs nommés distincts   ", len(employeurs), "| offres d'un employeur à ≥ 2 offres :",
          sum(c for c in employeurs.values() if c >= 2), "| les plus présents :", employeurs.most_common(3))
    print("descriptions identiques       ", sum(c for c in textes.values() if c > 1), "offres dans",
          sum(c > 1 for c in textes.values()), "groupes")

    # 5 bis. offresManqueCandidats : un drapeau posé sur l'offre, qui dépend de son âge.
    ages, change = Counter(), 0
    versions = defaultdict(list)
    for f in sorted((RACINE / "data" / "brut").glob(f"*/{args.rome}.jsonl")):
        for ligne in f.open(encoding="utf-8"):
            if ligne.strip():
                v = json.loads(ligne)
                if (not args.jusquau or v["vu_le"] <= args.jusquau) and v["offre"]["origineOffre"]["origine"] == "1":
                    versions[v["id"]].append((v["vu_le"], v["offre"]["dateCreation"][:10],
                                              v["offre"].get("offresManqueCandidats")))
    for vs in versions.values():
        vraies = [date.fromisoformat(vu) - date.fromisoformat(cree) for vu, cree, x in vs if x is True]
        if vraies:
            ages[min(vraies).days] += 1
        change += len({x for _, _, x in vs}) > 1
    print("\n## offresManqueCandidats (canal FT)\n")
    print("âge (jours) à la première version « vraie » :", dict(sorted(ages.items())))
    print("offres dont la valeur change d'une version à l'autre :", change, "sur", len(versions))

    # 6. Flux : combien d'offres nouvelles par jour, pour dimensionner l'échantillon de confirmation.
    jours = sorted(premiere.values())
    flux = Counter(jours)
    suivants = [c for j, c in sorted(flux.items())[1:]]
    if suivants:
        par_jour = sum(suivants) / len(suivants)
        print(f"\n## Flux\n\nnouvelles offres par jour (hors 1er jour) : {par_jour:.1f} "
              f"-> ~{91 * par_jour:.0f} en 13 semaines")

    presence = defaultdict(list)
    fichiers = sorted((RACINE / "data" / "actives").glob("*.csv"))
    for f in fichiers:
        if args.jusquau and f.stem > args.jusquau:
            continue
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if r["rome"] == args.rome:
                presence[r["id"]].append(f.stem)
    if presence:
        dernier = max(j for v in presence.values() for j in v)
        print("offres disparues de la liste des actives :", pct(sum(v[-1] != dernier for v in presence.values()),
                                                                len(presence)))


if __name__ == "__main__":
    main()
