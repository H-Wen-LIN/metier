r"""Tire les 120 offres du double codage (validation des dictionnaires de recherche/audit.py).

Usage :
    python recherche/codage/tirer.py

Population : offres D1415 de l'échantillon d'exploration (vues jusqu'au 06/10/2026), une seule
offre par description identique (les copies ne coûtent qu'un codage et n'apportent rien).
Plan stratifié, graine fixe :
    - pour chacun des 4 dictionnaires, 15 offres tirées au hasard parmi celles qu'il repère
      (et pas encore tirées) ;
    - 60 offres tirées au hasard parmi celles qu'aucun dictionnaire ne repère.

Écrit :
    a_coder/echantillon.csv   ce que lisent les codeurs : numéro, id, intitulé, description —
                              rien sur les dictionnaires (codage à l'aveugle)
    plan.csv                  la strate de tirage et le résultat des dictionnaires, pour valider.py
"""
import csv
import hashlib
import random
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
from audit import DICTIONNAIRES, charger  # noqa: E402

VARIABLES = ["teletravail", "langue_etrangere", "orientation_commerciale", "horaires_atypiques"]
PAR_DICTIONNAIRE, NEGATIVES, GRAINE = 15, 60, 20261006


def drapeaux(o):
    texte = o["intitule"] + " " + o["description"]
    return {v: int(bool(re.search(DICTIONNAIRES[v], texte, re.IGNORECASE))) for v in VARIABLES}


def main():
    offres, _ = charger("D1415", "2026-10-06")
    vues, population = set(), []
    for oid in sorted(offres):
        h = hashlib.md5(offres[oid]["description"].encode()).hexdigest()
        if h not in vues:
            vues.add(h)
            population.append(oid)
    d = {oid: drapeaux(offres[oid]) for oid in population}

    hasard = random.Random(GRAINE)
    tirees, strate = [], {}
    for v in VARIABLES:
        candidates = [i for i in population if d[i][v] and i not in strate]
        for i in hasard.sample(candidates, min(PAR_DICTIONNAIRE, len(candidates))):
            strate[i] = f"positive_{v}"
            tirees.append(i)
    negatives = [i for i in population if not any(d[i].values())]
    for i in hasard.sample(negatives, NEGATIVES):
        strate[i] = "aucun_dictionnaire"
        tirees.append(i)
    hasard.shuffle(tirees)  # l'ordre de lecture ne trahit pas la strate

    with (ICI / "a_coder" / "echantillon.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["num", "id", "intitule", "description"])
        for k, i in enumerate(tirees, 1):
            w.writerow([k, i, offres[i]["intitule"], offres[i]["description"]])
    with (ICI / "plan.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["num", "id", "strate"] + [f"regex_{v}" for v in VARIABLES])
        for k, i in enumerate(tirees, 1):
            w.writerow([k, i, strate[i]] + [d[i][v] for v in VARIABLES])

    # Tailles de population, pour pondérer les estimations de rappel.
    taille = {"population": len(population), "aucun_dictionnaire": len(negatives)}
    taille.update({f"positive_{v}": sum(d[i][v] for i in population) for v in VARIABLES})
    with (ICI / "population.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["groupe", "offres"])
        w.writerows(taille.items())
    print(f"{len(tirees)} offres tirées sur {len(population)} descriptions distinctes ; {taille}")


if __name__ == "__main__":
    main()
