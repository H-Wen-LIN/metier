r"""TD 1 — étape 1 : préparer la base du métier étudié.

Lit data/resume.json (les offres actives du jour, déjà retravaillées par scripts/resumer.py),
garde les codes ROME de ROMES (le périmètre), recode les variables et écrit :

    td1/base.csv             une ligne par offre active, avec les colonnes recodées et deux
                             drapeaux : doublon (True = copie d'une autre offre) et salarie
    td1/trace.json           la trace du nettoyage : combien de lignes, ce qui est retiré, pourquoi

Usage :
    python td1/preparer.py

Rien n'est supprimé du CSV : les lignes retirées d'une analyse sont marquées, pas effacées,
pour que chaque chiffre puisse être refait et vérifié.
"""
import csv
import json
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = Path(__file__).resolve().parent

# Le périmètre : le ou les codes ROME étudiés (la liste complète vit dans scripts/extraire.py).
ROMES = ["D1415"]  # Chargé(e) de relation client (CRM)

# Contrats qui ne sont pas des emplois salariés (franchise, libéral, commercial, reprise).
NON_SALARIES = {"FRA", "LIB", "CCE", "REP"}

# Expérience demandée : variable ordinale, recodée en classes d'années, dans cet ordre.
EXPERIENCE = ["Débutant accepté", "Moins d'un an", "1 an", "2 ans", "3 ans", "4 ans",
              "5 ans", "6 ans et plus"]
EXP_MANQUANTE = "Exigée, sans durée"


def classe_experience(ans, libelle):
    """exp_ans (0, 0.5, 3…) -> classe ordonnée ; None avec un libellé -> exigée sans durée."""
    if ans is None:
        return EXP_MANQUANTE if libelle else None
    if ans == 0:
        return "Débutant accepté"
    if ans < 1:
        return "Moins d'un an"
    if ans >= 6:
        return "6 ans et plus"
    return f"{int(ans)} an" if int(ans) == 1 else f"{int(ans)} ans"


def unite_salaire(libelle):
    """'Mensuel de 2000.0 Euros…' -> 'Mensuel' ; texte libre ou vide -> None."""
    mot = (libelle or "").split(" ", 1)[0].capitalize()
    return mot if mot in ("Annuel", "Mensuel", "Horaire") else None


def cle_doublon(o):
    """Même intitulé, même entreprise, même lieu : la définition du doublon probable du TD 1."""
    return (" ".join((o["intitule"] or "").lower().split()),
            (o["entreprise"] or "").strip().lower(),
            o["lieu"] or "")


def main():
    resume = json.loads((RACINE / "data" / "resume.json").read_text(encoding="utf-8"))
    jour = resume["date"]
    metiers = {m["code"]: m["libelle"] for m in resume["metiers"] if m["code"] in ROMES}
    contrats = resume["contrats"]
    offres = [o for o in resume["offres"] if o["rome"] in metiers]

    # Doublons : dans chaque groupe, on garde l'offre publiée le plus récemment.
    offres.sort(key=lambda o: o["date"] or "", reverse=True)
    vues = set()
    lignes = []
    for o in offres:
        cle = cle_doublon(o)
        doublon = cle in vues
        vues.add(cle)
        unite = unite_salaire(o["salaire"])
        lignes.append({
            "id": o["id"],
            "rome": o["rome"],
            "metier": metiers[o["rome"]],
            "intitule": o["intitule"],
            "entreprise": o["entreprise"] or "",
            "departement": o["dep"] or "",
            "lieu": o["lieu"] or "",
            "position": o["prec"] or "aucune",
            "contrat": contrats.get(o["contrat"], o["contrat"] or ""),
            "contrat_code": o["contrat"] or "",
            "salarie": o["contrat"] not in NON_SALARIES,
            "experience_brute": o["experience"] or "",
            "experience": classe_experience(o["exp_ans"], o["experience"]) or "",
            "formation": o["formation"] or "",
            "teletravail": o["teletravail"],
            "salaire_brut_texte": o["salaire"] or "",
            "salaire_unite": unite or "",
            "salaire_min_annuel": o["smin"] if o["smin"] is not None else "",
            "salaire_max_annuel": o["smax"] if o["smax"] is not None else "",
            "date_publication": o["date"],
            "doublon": doublon,
            "url": o["url"] or "",
        })
    lignes.sort(key=lambda l: (l["rome"], l["id"]))

    with (SORTIE / "base.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)

    # La trace : chaque étape part de la précédente.
    depart = len(lignes)
    sans_doublon = [l for l in lignes if not l["doublon"]]
    salaries = [l for l in sans_doublon if l["salarie"]]
    avec_salaire = [l for l in salaries if l["salaire_min_annuel"] != ""]
    affiche_invraisemblable = sum(1 for l in salaries
                                  if l["salaire_brut_texte"] and l["salaire_min_annuel"] == "")
    ecartes = Counter(l["salaire_brut_texte"] for l in salaries
                      if l["salaire_brut_texte"] and l["salaire_min_annuel"] == "")
    groupes = Counter(cle_doublon({"intitule": l["intitule"], "entreprise": l["entreprise"],
                                   "lieu": l["lieu"]}) for l in lignes)
    trace = {
        "date": jour,
        "source": resume["source"],
        "requete": resume["requete"],
        "metiers": metiers,
        "etapes": [
            {"etape": "Offres actives du périmètre", "n": depart, "retire": 0,
             "pourquoi": f"{', '.join(metiers)}, offres actives au {jour}"},
            {"etape": "Sans les doublons", "n": len(sans_doublon),
             "retire": depart - len(sans_doublon),
             "pourquoi": "même intitulé, même entreprise, même lieu : on garde la plus récente"},
            {"etape": "Emplois salariés", "n": len(salaries),
             "retire": len(sans_doublon) - len(salaries),
             "pourquoi": "franchises, professions libérales et commerciales retirées"},
            {"etape": "Avec un salaire exploitable", "n": len(avec_salaire),
             "retire": len(salaries) - len(avec_salaire),
             "pourquoi": f"aucun salaire affiché, ou montant hors de 4 000 à 250 000 € bruts "
                         f"par an ({affiche_invraisemblable} saisies invraisemblables)"},
        ],
        "salaires_ecartes": dict(ecartes.most_common(5)),
        "doublons": {
            "offres_dans_un_groupe": sum(n for n in groupes.values() if n > 1),
            "groupes": sum(1 for n in groupes.values() if n > 1),
            "tailles": dict(sorted(Counter(n for n in groupes.values() if n > 1).items())),
        },
    }
    (SORTIE / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2),
                                       encoding="utf-8")

    print(f"Base : {depart} offres actives {', '.join(metiers)} au {jour} -> td1/base.csv")
    for e in trace["etapes"]:
        print(f"  {e['n']:>5}  {e['etape']}" + (f"  (− {e['retire']} : {e['pourquoi']})"
                                                 if e["retire"] else ""))


if __name__ == "__main__":
    main()
