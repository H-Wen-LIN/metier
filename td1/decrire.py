r"""TD 1 — étape 2 : décrire et montrer la base du métier étudié.

Lit td1/base.csv et td1/trace.json (écrits par td1/preparer.py) et produit :

    td1/graphiques/*.png   un graphique par variable, chacun avec sa phrase de lecture
    td1/TD1.md             le dossier du jour : nature des variables, trace, tableaux,
                           graphiques, lectures, désordre de la base

Usage :
    python td1/preparer.py
    python td1/decrire.py

Périmètre de chaque chiffre :
  - variables qualitatives et dates : offres actives sans les doublons ;
  - salaire : emplois salariés, sans les doublons, avec un salaire exploitable ;
  - désordre de la base : toutes les offres actives, doublons compris.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
GRAPHIQUES = ICI / "graphiques"

BLEU, BLEU_CLAIR, GRIS, ORANGE = "#2c5d8f", "#9dbbd9", "#9a9a9a", "#d9822b"
EXPERIENCE = ["Débutant accepté", "Moins d'un an", "1 an", "2 ans", "3 ans", "4 ans",
              "5 ans", "6 ans et plus"]
EXP_MANQUANTE = "Exigée, sans durée"
FORMATIONS = ["< Bac", "Bac", "Bac+2", "Bac+3/4", "Bac+5"]
FORM_MANQUANTE = "Non renseignée"


def n(x, dec=0):
    """1234.5 -> '1 234' (espace fine insécable, à la française)."""
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def pct(a, b, dec=0):
    return f"{n(100 * a / b, dec)} %"


def sauver(fig, nom, lecture, source):
    """Pose la phrase de lecture et la source sous le graphique, puis enregistre."""
    fig.text(0.01, 0.01, f"Lecture : {lecture}\n{source}", fontsize=8.5, color="#333",
             ha="left", va="bottom", wrap=True)
    fig.savefig(GRAPHIQUES / nom, dpi=150)
    plt.close(fig)
    return f"graphiques/{nom}"


def barres(ax, etiquettes, valeurs, total, couleurs=BLEU):
    """Barres horizontales, de haut en bas dans l'ordre donné, axe à zéro, effectif et part."""
    y = np.arange(len(etiquettes))[::-1]
    ax.barh(y, valeurs, color=couleurs)
    ax.set_yticks(y, etiquettes)
    ax.set_xlim(0, max(valeurs) * 1.25)
    for yi, v in zip(y, valeurs):
        ax.text(v + max(valeurs) * 0.01, yi, f"{n(v)} ({pct(v, total)})", va="center", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("nombre d'offres")


def tableau_md(df):
    """DataFrame -> tableau Markdown (sans dépendre de tabulate)."""
    cols = [str(c) for c in df.columns]
    lignes = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lignes.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(lignes)


def main():
    GRAPHIQUES.mkdir(exist_ok=True)
    base = pd.read_csv(ICI / "base.csv", dtype={"departement": str})
    trace = json.loads((ICI / "trace.json").read_text(encoding="utf-8"))
    jour = trace["date"]
    date_fr = pd.Timestamp(jour).strftime("%d/%m/%Y")
    codes = ", ".join(trace["metiers"])
    metiers_txt = ", ".join(f"{c} {l}" for c, l in trace["metiers"].items())
    source = (f"Données : France Travail, API Offres d'emploi v2, dépôt metier, "
              f"code ROME {codes}, offres actives au {date_fr}.")
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold"})

    tout = base
    offres = base[~base["doublon"]]
    sal = offres[offres["salarie"] & offres["salaire_min_annuel"].notna()]["salaire_min_annuel"]
    N_tout, N, N_sal = len(tout), len(offres), len(sal)
    md = []  # le dossier, section par section
    figures = {}

    # 1. La trace du nettoyage
    etapes = trace["etapes"]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    fig.subplots_adjust(left=0.3, bottom=0.25, top=0.88)
    lib = [e["etape"] for e in etapes]
    val = [e["n"] for e in etapes]
    y = np.arange(len(lib))[::-1]
    ax.barh(y, val, color=[BLEU_CLAIR] * 3 + [BLEU])
    ax.set_yticks(y, lib)
    ax.set_xlim(0, max(val) * 1.35)
    for yi, e in zip(y, etapes):
        ax.text(e["n"] + max(val) * 0.01, yi, n(e["n"]) + (f"   − {n(e['retire'])}" if e["retire"] else ""),
                va="center", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("De la base brute à l'analyse de salaire")
    figures["trace"] = sauver(
        fig, "01_trace.png",
        f"l'analyse de salaire porte sur {n(etapes[-1]['n'])} offres, pas sur {n(etapes[0]['n'])}.",
        source)

    # 2. Formation demandée (qualitative ordinale, très souvent absente)
    form = offres["formation"].fillna(FORM_MANQUANTE)
    eff_f = form.value_counts().reindex(FORMATIONS + [FORM_MANQUANTE], fill_value=0)
    valides_f = eff_f[FORMATIONS].sum()
    t_form = pd.DataFrame({
        "Formation": eff_f.index,
        "Effectif": [n(v) for v in eff_f.values],
        "Pourcentage": [pct(v, N, 1) for v in eff_f.values],
        "% valide": [pct(eff_f[c], valides_f, 1) if c in FORMATIONS and valides_f else "manquant"
                     for c in eff_f.index],
    })
    t_form.loc[len(t_form)] = ["**Total**", n(N), "100 %", "100 %"]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    fig.subplots_adjust(left=0.22, bottom=0.22, top=0.9)
    barres(ax, list(eff_f.index), list(eff_f.values), N,
           couleurs=[BLEU] * len(FORMATIONS) + [GRIS])
    ax.set_title(f"Niveau de formation demandé, dans l'ordre, sur {n(N)} offres")
    top_f = eff_f[FORMATIONS].idxmax()
    lect_form = (f"{n(eff_f[FORM_MANQUANTE])} offres sur {n(N)} ({pct(eff_f[FORM_MANQUANTE], N)}) "
                 f"ne disent rien du diplôme ; parmi les {n(valides_f)} qui le font, "
                 f"{n(eff_f[top_f])} demandent « {top_f} ».")
    figures["formation"] = sauver(fig, "02_formation.png", lect_form, source)

    # 3. Contrat (qualitative nominale)
    par_contrat = offres["contrat"].value_counts()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    fig.subplots_adjust(left=0.25, bottom=0.22, top=0.9)
    barres(ax, par_contrat.index, par_contrat.values, N)
    ax.set_title(f"Type de contrat, sur {n(N)} offres")
    cdi = par_contrat.get("CDI", 0)
    lect_contrat = f"{n(cdi)} offres sur {n(N)} sont en CDI ({pct(cdi, N)})."
    figures["contrat"] = sauver(fig, "03_contrat.png", lect_contrat, source)

    # 4. Expérience (qualitative ordinale) : tableau de fréquences et barres dans l'ordre
    exp = offres["experience"].fillna(EXP_MANQUANTE)
    eff = exp.value_counts().reindex(EXPERIENCE + [EXP_MANQUANTE], fill_value=0)
    valides = eff[EXPERIENCE].sum()
    cumul = (eff[EXPERIENCE].cumsum() / valides * 100)
    t_exp = pd.DataFrame({
        "Expérience": eff.index,
        "Effectif": [n(v) for v in eff.values],
        "Pourcentage": [pct(v, N, 1) for v in eff.values],
        "% valide": [pct(eff[c], valides, 1) if c in EXPERIENCE else "manquant" for c in eff.index],
        "% cumulé": [f"{n(cumul[c], 1)} %" if c in EXPERIENCE else "" for c in eff.index],
    })
    t_exp.loc[len(t_exp)] = ["**Total**", n(N), "100 %", "100 %", ""]
    moins_2 = cumul["1 an"]
    rang_median = valides / 2
    classe_mediane = next(c for c in EXPERIENCE if eff[EXPERIENCE].cumsum()[c] >= rang_median)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    fig.subplots_adjust(left=0.25, bottom=0.2, top=0.9)
    barres(ax, list(eff.index), list(eff.values), N,
           couleurs=[BLEU] * len(EXPERIENCE) + [GRIS])
    ax.set_title(f"Expérience demandée, dans l'ordre, sur {n(N)} offres")
    lect_exp = (f"{n(moins_2, 1)} % des {n(valides)} offres qui donnent une durée demandent moins "
                f"de deux ans d'expérience ; {n(eff['Débutant accepté'])} acceptent un débutant.")
    figures["experience"] = sauver(fig, "04_experience.png", lect_exp, source)

    # 5. Salaire (quantitative) : résumé, histogramme, loi normale, boîte à moustaches
    q1, med, q3 = sal.quantile([0.25, 0.5, 0.75])
    moy, et = sal.mean(), sal.std()
    asym, aplat = stats.skew(sal, bias=False), stats.kurtosis(sal, fisher=True, bias=False)
    tranches = np.arange(0, sal.max() + 5000, 5000)
    classe_modale = pd.cut(sal, tranches, right=False).value_counts().idxmax()
    mode_txt = f"{n(classe_modale.left)} à {n(classe_modale.right)}"
    t_sal = pd.DataFrame({
        "Indicateur": ["Effectif", "Moyenne", "Médiane", "Classe modale (tranches de 5 000)",
                       "Écart-type", "Variance", "Minimum", "1er quartile", "3e quartile",
                       "Maximum", "Étendue", "Écart interquartile", "Asymétrie (skewness)",
                       "Aplatissement (kurtosis, en excès)"],
        "Valeur": [n(N_sal), f"{n(moy)} €", f"{n(med)} €", f"{mode_txt} €", f"{n(et)} €",
                   f"{n(et ** 2 / 1e6)} millions d'« euros au carré »", f"{n(sal.min())} €",
                   f"{n(q1)} €", f"{n(q3)} €", f"{n(sal.max())} €",
                   f"{n(sal.max() - sal.min())} €", f"{n(q3 - q1)} €",
                   n(asym, 2), n(aplat, 2)],
    })
    fig, (ax, axb) = plt.subplots(2, 1, figsize=(9, 5.6), height_ratios=[4, 1], sharex=True)
    fig.subplots_adjust(bottom=0.2, top=0.9, hspace=0.08)
    ax.hist(sal, bins=tranches, color=BLEU_CLAIR, edgecolor="white", density=True,
            label="salaires affichés")
    xs = np.linspace(0, sal.max(), 400)
    ax.plot(xs, stats.norm.pdf(xs, moy, et), color=GRIS, lw=1.5,
            label="loi normale de même moyenne et écart-type")
    ax.axvline(med, color=BLEU, ls="--", lw=1.5, label=f"médiane {n(med)} €")
    ax.axvline(moy, color=ORANGE, ls="-", lw=1.5, label=f"moyenne {n(moy)} €")
    ax.set_yticks([])
    ax.set_ylabel("densité")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.text(0.99, 0.45, f"asymétrie {n(asym, 2)}\naplatissement {n(aplat, 2)}\n(loi normale : 0 et 0)",
            transform=ax.transAxes, ha="right", fontsize=8.5, color="#333")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title(f"Salaire annuel brut minimum affiché, sur {n(N_sal)} offres")
    axb.boxplot(sal, orientation="horizontal", widths=0.6, patch_artist=True,
                boxprops={"facecolor": BLEU_CLAIR}, medianprops={"color": BLEU})
    axb.set_yticks([])
    axb.spines[["top", "right", "left"]].set_visible(False)
    axb.set_xlabel("euros bruts par an")
    axb.xaxis.set_major_formatter(lambda v, _: n(v))
    tire = "vers le haut" if moy > med else "vers le bas"
    lect_sal = (f"la moitié des {n(N_sal)} offres propose moins de {n(med)} € par an ; "
                f"la moyenne, {n(moy)} €, est tirée {tire} par les valeurs extrêmes "
                f"(asymétrie {n(asym, 2)}).")
    figures["salaire"] = sauver(fig, "05_salaire.png", lect_sal, source)

    # 6. Salaire en classes, de deux façons
    bornes_10k = [0, 20000, 30000, 40000, 50000, np.inf]
    lib_10k = ["Moins de 20 000", "20 000 à 30 000", "30 000 à 40 000", "40 000 à 50 000",
               "50 000 et plus"]
    c10 = pd.cut(sal, bornes_10k, right=False, labels=lib_10k).value_counts().reindex(lib_10k)
    bornes_q = [-np.inf, q1, med, q3, np.inf]
    lib_q = [f"Moins de {n(q1)}", f"{n(q1)} à {n(med)}", f"{n(med)} à {n(q3)}", f"{n(q3)} et plus"]
    cq = pd.cut(sal, bornes_q, right=False, labels=lib_q).value_counts().reindex(lib_q)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    fig.subplots_adjust(left=0.16, wspace=0.75, bottom=0.25, top=0.85)
    barres(a1, lib_10k, c10.values, N_sal)
    a1.set_title("Tranches de 10 000 €", fontsize=10.5)
    barres(a2, lib_q, cq.values, N_sal)
    a2.set_title("Quartiles : quatre groupes égaux", fontsize=10.5)
    fig.suptitle(f"Le même salaire découpé de deux façons, {n(N_sal)} offres",
                 fontweight="bold")
    classe_max = c10.idxmax()
    if cq.max() - cq.min() <= 0.04 * N_sal:
        suite_q = "en quartiles, chaque classe en compte environ un quart."
    else:
        suite_q = (f"en quartiles, les classes vont de {n(cq.min())} à {n(cq.max())} offres : "
                   "les salaires égaux à une borne les déséquilibrent.")
    lect_classes = (f"en tranches de même largeur, {pct(c10.max(), N_sal)} des offres tombent "
                    f"dans « {classe_max} » ; " + suite_q)
    figures["classes"] = sauver(fig, "06_salaire_classes.png", lect_classes, source)

    # 7. Département (qualitative nominale, écrite en chiffres)
    dep = offres["departement"].fillna("").replace("", "Non renseigné")
    par_dep = dep.value_counts()
    top = par_dep.drop("Non renseigné", errors="ignore").head(10)
    autres = N - top.sum()
    etiq = list(top.index) + ["Autres départements et non renseigné"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    fig.subplots_adjust(left=0.4, bottom=0.18, top=0.9)
    barres(ax, etiq, list(top.values) + [autres], N, couleurs=[BLEU] * len(top) + [GRIS])
    ax.set_title(f"Les 10 départements qui publient le plus, sur {n(N)} offres")
    lect_dep = (f"le département {top.index[0]} compte {n(top.iloc[0])} offres sur {n(N)} "
                f"({pct(top.iloc[0], N)}) ; les 10 premiers en regroupent {pct(top.sum(), N)}, "
                f"le Puy-de-Dôme (63) en compte {n(par_dep.get('63', 0))}.")
    figures["departement"] = sauver(fig, "07_departement.png", lect_dep, source)
    nb_deps = int((par_dep.index != "Non renseigné").sum())

    # 8. Date de publication (date) : effectifs par semaine
    pub = pd.to_datetime(offres["date_publication"])
    semaines = pub.dt.to_period("W-SUN").value_counts().sort_index()
    # la semaine en cours n'est pas finie : on ne garde que les semaines complètes
    completes = semaines[semaines.index.end_time < pd.Timestamp(jour)]
    recentes = completes[completes.index.start_time >= pd.Timestamp(jour) - pd.Timedelta(days=91)]
    avant_juillet = int((pub < "2026-07-01").sum())
    fig, ax = plt.subplots(figsize=(9, 3.8))
    fig.subplots_adjust(bottom=0.28, top=0.88)
    ax.plot(recentes.index.start_time, recentes.values, marker="o", color=BLEU)
    ax.set_ylim(0, recentes.max() * 1.15)
    ax.set_ylabel("offres publiées")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.set_xlabel("semaine de publication (lundi)")
    ax.set_title("Offres encore actives, par semaine de publication (semaines complètes)")
    derniere = recentes.index[-1]
    lect_pub = (f"{n(recentes.iloc[-1])} des {n(N)} offres actives ont été publiées la semaine du "
                f"{derniere.start_time:%d/%m} ; {n(avant_juillet)} datent d'avant juillet.")
    figures["publication"] = sauver(fig, "08_publication.png", lect_pub, source)

    # 9. Offres actives jour par jour (série du dépôt)
    serie = pd.read_csv(RACINE / "data" / "serie.csv")
    serie = serie[serie["rome"].isin(trace["metiers"]) & (serie["date"] <= trace["date"])]
    serie = serie.groupby("date")["total"].sum()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    fig.subplots_adjust(bottom=0.28, top=0.88)
    x = pd.to_datetime(serie.index)
    ax.plot(x, serie.values, marker="o", color=BLEU)
    for xi, v in [(x[0], serie.iloc[0]), (x[-1], serie.iloc[-1])]:
        ax.annotate(n(v), (xi, v), textcoords="offset points", xytext=(0, 8), ha="center")
    ax.set_ylabel("offres actives")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.set_title(f"Offres actives {codes}, jour par jour (doublons compris)")
    ecart = serie.iloc[-1] - serie.iloc[0]
    d0, d1 = pd.Timestamp(serie.index[0]), pd.Timestamp(serie.index[-1])
    lect_serie = (f"{n(serie.iloc[0])} offres actives le {d0:%d/%m}, {n(serie.iloc[-1])} le "
                  f"{d1:%d/%m}, soit {n(abs(ecart))} de {'plus' if ecart >= 0 else 'moins'} en "
                  f"{(d1 - d0).days} jours. L'axe ne part pas de zéro : permis sur une courbe.")
    figures["serie"] = sauver(fig, "09_serie.png", lect_serie, source)

    # 10. Le désordre de la base (toutes les offres actives)
    manques = pd.Series({
        "Aucun salaire exploitable": int(tout["salaire_min_annuel"].isna().sum()),
        "Entreprise non nommée": int((tout["entreprise"].fillna("") == "").sum()),
        "Pas un emploi salarié": int((~tout["salarie"]).sum()),
        "Doublon probable": trace["doublons"]["offres_dans_un_groupe"],
        "Publiée avant juillet": int((pd.to_datetime(tout["date_publication"]) < "2026-07-01").sum()),
        "Expérience exigée, sans durée": int((tout["experience"] == EXP_MANQUANTE).sum()),
        "Aucune position sur la carte": int((tout["position"] == "aucune").sum()),
    }).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    fig.subplots_adjust(left=0.3, bottom=0.22, top=0.9)
    barres(ax, manques.index, manques.values, N_tout, couleurs=ORANGE)
    ax.set_title(f"Ce qui manque ou trompe, sur {n(N_tout)} offres actives")
    sans_sal = manques["Aucun salaire exploitable"]
    lect_manques = (f"{n(sans_sal)} offres sur {n(N_tout)} ({pct(sans_sal, N_tout)}) n'ont aucun "
                    f"salaire exploitable : une moyenne décrit les offres qui l'affichent, pas le marché.")
    figures["desordre"] = sauver(fig, "10_desordre.png", lect_manques, source)
    unites = tout["salaire_unite"].value_counts()

    # Le dossier du jour
    variables = pd.DataFrame([
        ["metier / rome", "qualitative nominale", "effectifs, fréquences", "barres", "un code ROME ne se moyenne pas"],
        ["contrat", "qualitative nominale", "effectifs, fréquences", "barres", ""],
        ["salarie, teletravail, doublon", "qualitative nominale (binaire)", "effectifs, fréquences", "barres", ""],
        ["departement", "qualitative nominale", "effectifs, fréquences", "barres", "écrit en chiffres, mais pas quantitatif"],
        ["experience", "qualitative ordinale", "fréquences, % cumulé, médiane", "barres dans l'ordre", "recodée en classes d'années"],
        ["formation", "qualitative ordinale", "fréquences, médiane", "barres dans l'ordre", "Bac < Bac+2 < Bac+3/4 < Bac+5"],
        ["salaire_min_annuel", "quantitative continue", "moyenne, médiane, écart-type, quartiles", "histogramme, boîte à moustaches", "ramené à l'année"],
        ["date_publication", "date", "effectifs par semaine", "courbe", ""],
        ["id, url, intitule, entreprise", "identifiants / texte", "—", "—", "ne se résument pas tels quels"],
    ], columns=["Variable", "Nature", "Résumé", "Graphique", "Remarque"])
    t_trace = pd.DataFrame([{"Étape": e["etape"], "Offres": n(e["n"]),
                             "Retirées": f"− {n(e['retire'])}" if e["retire"] else "",
                             "Pourquoi": e["pourquoi"]} for e in etapes])
    t_contrat = pd.DataFrame({"Contrat": par_contrat.index, "Effectif": [n(v) for v in par_contrat],
                              "Fréquence": [pct(v, N, 1) for v in par_contrat]})
    t_contrat.loc[len(t_contrat)] = ["**Total**", n(N), "100 %"]
    t_classes = pd.DataFrame({"Tranches de 10 000 €": lib_10k, "Offres": [n(v) for v in c10]})
    t_quart = pd.DataFrame({"Quartiles": lib_q, "Offres": [n(v) for v in cq]})
    ecartes = "; ".join(f"« {t} » × {k}" for t, k in trace["salaires_ecartes"].items())

    def fig_md(cle, titre, lecture):
        return f"![{titre}]({figures[cle]})\n\n*Lecture : {lecture}*\n"

    md += [
        f"# TD 1 — Décrire et montrer : le marché du métier {metiers_txt}",
        "",
        f"**Données** : {trace['source']} ; {trace['requete']} ; offres actives au **{date_fr}**.  ",
        f"**Périmètre** : {metiers_txt}, France entière.  ",
        "**Refaire tous les chiffres** : `python td1/preparer.py` puis `python td1/decrire.py`.",
        "",
        "> La base change chaque matin : chaque chiffre ci-dessous vaut pour le "
        f"{date_fr}, et il est donné avec son effectif.",
        "",
        "## 1. Les variables et leur nature",
        "",
        "La nature de la variable décide du résumé et du graphique autorisés.",
        "",
        tableau_md(variables),
        "",
        "## 2. La trace du nettoyage",
        "",
        "Avant le premier graphique : combien de lignes au départ, ce qui est retiré, et pourquoi. "
        "Rien n'est effacé de `base.csv` : les lignes retirées sont marquées "
        "(colonnes `doublon`, `salarie`).",
        "",
        tableau_md(t_trace),
        "",
        f"Doublons : {trace['doublons']['groupes']} groupes d'annonces au même intitulé, même "
        f"entreprise, même lieu, soit {trace['doublons']['offres_dans_un_groupe']} offres "
        f"(tailles de groupe : {', '.join(f'{k} exemplaires × {v}' for k, v in trace['doublons']['tailles'].items())}). "
        "On compte des offres, pas des postes : dans chaque groupe, on garde la plus récente.",
        "",
        "Recodages :",
        "",
        f"- **salaire** : le libellé texte arrive en trois unités ({n(unites.get('Annuel', 0))} en "
        f"annuel, {n(unites.get('Mensuel', 0))} en mensuel, {n(unites.get('Horaire', 0))} en horaire) ; "
        "ramené en brut annuel (mensuel × 12, horaire × 1 820 heures payées), on garde le minimum de la "
        "fourchette ; hors de 4 000 à 250 000 € par an, la saisie est jugée fausse et écartée "
        f"(les plus fréquentes : {ecartes}) ;",
        "- **expérience** : « 1 An(s) », « 6 Mois », « 24 Mois »… recodés en "
        "classes d'années dans l'ordre ; « Expérience exigée » sans durée mise à part, en manquant.",
        "",
        fig_md("trace", "Trace du nettoyage",
               f"l'analyse de salaire porte sur {n(etapes[-1]['n'])} offres, pas sur {n(etapes[0]['n'])}."),
        "## 3. Variables qualitatives : effectifs et fréquences",
        "",
        f"Périmètre : les {n(N)} offres actives sans les doublons.",
        "",
        "### Niveau de formation demandé (ordinale)",
        "",
        tableau_md(t_form),
        "",
        fig_md("formation", "Formation demandée", lect_form),
        "### Département",
        "",
        f"Les offres viennent de {nb_deps} départements. Un numéro de département s'écrit en "
        "chiffres mais ne se moyenne pas : c'est une variable nominale.",
        "",
        fig_md("departement", "Départements", lect_dep),
        "### Type de contrat",
        "",
        tableau_md(t_contrat),
        "",
        fig_md("contrat", "Type de contrat", lect_contrat),
        "### Expérience demandée (ordinale)",
        "",
        "Le pourcentage se calcule sur toutes les offres ; le pourcentage valide, sur les seules "
        f"{n(valides)} offres qui donnent une durée ; le cumulé additionne les classes dans l'ordre.",
        "",
        tableau_md(t_exp),
        "",
        f"Classe médiane : **{classe_mediane}** (l'offre du milieu, parmi celles qui donnent une durée).",
        "",
        fig_md("experience", "Expérience demandée", lect_exp),
        "## 4. Variable quantitative : le salaire",
        "",
        f"Périmètre : les {n(N_sal)} emplois salariés, sans doublon, avec un salaire exploitable. "
        f"Ce salaire décrit les offres qui l'affichent, pas le marché : {pct(sans_sal, N_tout)} "
        "des offres n'en affichent aucun.",
        "",
        tableau_md(t_sal),
        "",
        fig_md("salaire", "Salaire affiché", lect_sal),
        f"Asymétrie {n(asym, 2)} : " + ("la distribution s'étire vers les hauts salaires"
        if asym > 0 else "la distribution s'étire vers les bas salaires") +
        f" ; aplatissement {n(aplat, 2)}, donné « en excès » (0 pour une loi normale). "
        "Quand la distribution n'est pas symétrique, on lit la **médiane** plutôt que la moyenne.",
        "",
        "### Mettre le salaire en classes",
        "",
        "Aucun découpage n'est neutre : des tranches de même largeur ou des classes de même effectif "
        "(quartiles). On garde toujours la variable d'origine.",
        "",
        tableau_md(t_classes),
        "",
        tableau_md(t_quart),
        "",
        fig_md("classes", "Salaire en classes", lect_classes),
        "## 5. Les dates",
        "",
        fig_md("publication", "Semaine de publication", lect_pub),
        fig_md("serie", "Offres actives jour par jour", lect_serie),
        "## 6. Le désordre de la base",
        "",
        f"Compté sur les {n(N_tout)} offres actives, doublons compris.",
        "",
        tableau_md(pd.DataFrame({"Problème": manques.index, "Offres": [n(v) for v in manques],
                                 "Part": [pct(v, N_tout) for v in manques]})),
        "",
        fig_md("desordre", "Désordre de la base", lect_manques),
        "Et la base ne voit que France Travail : les offres publiées seulement ailleurs "
        "(APEC, LinkedIn, sites des entreprises) n'y sont pas.",
        "",
    ]
    (ICI / "TD1.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Écrit : td1/TD1.md et {len(figures)} graphiques dans td1/graphiques/")
    print(f"  {N_tout} offres actives, {N} sans doublon, {N_sal} salaires exploitables")
    print(f"  salaire : médiane {n(med)}, moyenne {n(moy)}, écart-type {n(et)}, "
          f"asymétrie {n(asym, 2)}, aplatissement {n(aplat, 2)}")


if __name__ == "__main__":
    main()
