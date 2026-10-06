r"""Double codage des 120 offres : accord entre codeurs, puis qualité des dictionnaires.

Usage :
    python recherche/codage/valider.py

Lit :
    codeur_A.csv, codeur_B.csv   les deux codages à l'aveugle (grille a_coder/CODEBOOK.md)
    arbitrage.csv                la décision sur chaque désaccord (num, variable, valeur, raison)
    plan.csv, population.csv     la strate de tirage, le résultat des dictionnaires, les effectifs

Écrit resultats.md :
    1. accord entre codeurs : % d'accord et kappa de Cohen, variable par variable ;
    2. dictionnaire contre référence (accords + arbitrages) : précision, rappel, kappa.

Le rappel est pondéré par le plan de sondage : les offres « aucun dictionnaire » (60 tirées sur
302) et les offres repérées par un autre dictionnaire n'ont pas la même probabilité d'être tirées.
"""
import csv
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
from audit import repere  # noqa: E402  (les dictionnaires corrigés)
VARIABLES = ["teletravail", "langue_etrangere", "orientation_commerciale", "horaires_atypiques"]
SEUIL_KAPPA, SEUIL_PRECISION = 0.70, 0.85


def lire(nom):
    with (ICI / nom).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    marge = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - marge, centre + marge


def pc(x):
    return "—" if x != x else f"{100 * x:.0f} %"


def main():
    plan = {int(r["num"]): r for r in lire("plan.csv")}
    a = {int(r["num"]): r for r in lire("codeur_A.csv")}
    b = {int(r["num"]): r for r in lire("codeur_B.csv")}
    assert set(a) == set(b) == set(plan), "les deux codages doivent couvrir les 120 offres"
    arbitrage = {(int(r["num"]), r["variable"]): int(r["valeur"]) for r in lire("arbitrage.csv")}
    population = {r["groupe"]: int(r["offres"]) for r in lire("population.csv")}
    nums = sorted(plan)

    lignes = ["# Double codage de 120 offres D1415 — résultats", "",
              "Produit par `python recherche/codage/valider.py`. Plan de tirage : `tirer.py` ; "
              "grille : `a_coder/CODEBOOK.md`.", "",
              "## 1. Accord entre les deux codeurs", "",
              "| Variable | Codées 1 (A / B) | Accord | κ de Cohen | Désaccords | Verdict |",
              "|---|---|---|---|---|---|"]
    reference = {}
    for v in VARIABLES:
        xa = [int(a[k][v]) for k in nums]
        xb = [int(b[k][v]) for k in nums]
        po, k = kappa(xa, xb)
        desaccords = [n for n, p, q in zip(nums, xa, xb) if p != q]
        manquants = [n for n in desaccords if (n, v) not in arbitrage]
        assert not manquants, f"{v} : désaccords sans arbitrage {manquants}"
        reference[v] = {n: (p if p == q else arbitrage[(n, v)]) for n, p, q in zip(nums, xa, xb)}
        verdict = "suffisant" if k >= SEUIL_KAPPA else "**insuffisant : grille à préciser**"
        lignes.append(f"| `{v}` | {sum(xa)} / {sum(xb)} | {pc(po)} | {k:.2f} | {len(desaccords)} | {verdict} |")
    doutes = sum(int(a[k]["doute"]) for k in nums), sum(int(b[k]["doute"]) for k in nums)
    lignes += ["", f"Offres marquées « doute » : {doutes[0]} (A), {doutes[1]} (B). "
               f"Seuil retenu au protocole : κ ≥ {SEUIL_KAPPA:.2f}.", "",
               "## 2. Les dictionnaires contre la référence", "",
               "Référence = le code des deux codeurs quand ils s'accordent, l'arbitrage sinon "
               "(`arbitrage.csv`, une raison par décision).", "",
               "| Variable | Repérées par le dictionnaire (échantillon) | Précision [IC 95 %] | "
               "Rappel estimé (pondéré) | κ dictionnaire / référence | Verdict |",
               "|---|---|---|---|---|---|"]
    n_aucun = population["aucun_dictionnaire"]
    n_au_moins_un = population["population"] - n_aucun
    for v in VARIABLES:
        ref, rx = reference[v], {n: int(plan[n][f"regex_{v}"]) for n in nums}
        positifs = [n for n in nums if rx[n]]
        vp = sum(ref[n] for n in positifs)
        precision = vp / len(positifs) if positifs else float("nan")
        bas, haut = wilson(vp, len(positifs))
        # Faux négatifs : deux strates parmi les offres que le dictionnaire ne repère pas.
        neg_aucun = [n for n in nums if not rx[n] and plan[n]["strate"] == "aucun_dictionnaire"]
        neg_autres = [n for n in nums if not rx[n] and plan[n]["strate"] != "aucun_dictionnaire"]
        taux_aucun = sum(ref[n] for n in neg_aucun) / len(neg_aucun) if neg_aucun else 0
        taux_autres = sum(ref[n] for n in neg_autres) / len(neg_autres) if neg_autres else 0
        n_pos = population[f"positive_{v}"]
        vp_pop = precision * n_pos
        fn_pop = taux_aucun * n_aucun + taux_autres * (n_au_moins_un - n_pos)
        rappel = vp_pop / (vp_pop + fn_pop) if vp_pop + fn_pop else float("nan")
        _, k = kappa([rx[n] for n in nums], [ref[n] for n in nums])
        ok = precision >= SEUIL_PRECISION and rappel >= 0.70
        verdict = "utilisable" if ok else "**à corriger avant la confirmation**"
        lignes.append(f"| `{v}` | {len(positifs)} | {pc(precision)} [{pc(bas)} ; {pc(haut)}] | "
                      f"{pc(rappel)} | {k:.2f} | {verdict} |")
        erreurs = [(n, rx[n], ref[n]) for n in nums if rx[n] != ref[n]]
        if erreurs:
            lignes.append("| | erreurs : " + ", ".join(
                f"n°{n} ({'faux positif' if r else 'faux négatif'})" for n, r, _ in erreurs) + " | | | | |")
    lignes += ["", f"Seuils du protocole : précision ≥ {pc(SEUIL_PRECISION)}, rappel ≥ 70 %. "
               "Le rappel combine le taux de faux négatifs des 60 offres qu'aucun dictionnaire ne "
               f"repère (pondérées par {n_aucun}) et celui des offres repérées par un autre "
               "dictionnaire ; avec si peu de faux négatifs attendus, son incertitude est grande."]

    # 3. Les dictionnaires corrigés, sur le même échantillon : estimation optimiste, puisqu'ils
    # ont été corrigés en lisant ces erreurs (le contrôle hors échantillon est dans PROTOCOLE.md).
    textes = {int(r["num"]): r["intitule"] + " " + r["description"] for r in lire("a_coder/echantillon.csv")}
    lignes += ["", "## 3. Après correction (même échantillon : estimation optimiste)", "",
               "| Variable | Vrais positifs | Faux positifs | Faux négatifs | Précision | Rappel (non pondéré) |",
               "|---|---|---|---|---|---|"]
    for v in ("teletravail",):
        p = {n: int(repere(v, textes[n])) for n in nums}
        vp = sum(p[n] and reference[v][n] for n in nums)
        fp = sum(p[n] and not reference[v][n] for n in nums)
        fn = sum(not p[n] and reference[v][n] for n in nums)
        lignes.append(f"| `{v}` v2 | {vp} | {fp} | {fn} | {pc(vp / max(vp + fp, 1))} | {pc(vp / max(vp + fn, 1))} |")
    lignes += ["", "`orientation_commerciale` n'a pas de version corrigée : un dictionnaire large "
               "(vente, vendre, négocier, prospect, développement commercial…) atteint 96 % de rappel "
               "mais 70 % de précision sur cet échantillon. Le concept ne se lit pas dans les mots : "
               "il se code par lecture."]
    (ICI / "resultats.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
