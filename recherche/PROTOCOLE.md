# Des offres aux hypothèses — protocole de recherche quantitative

**Métier** : D1415 Chargé(e) de relation client (CRM). **Source** : API France Travail Offres d'emploi v2, une requête `codeROME` par jour (`scripts/extraire.py`).
**Échantillon d'exploration** : les 561 offres distinctes vues du 22/09 au 06/10/2026 (dernière version de chaque offre, `data/brut/`).
**Refaire les chiffres de l'audit** : `python recherche/audit.py --jusquau 2026-10-06`.

> **Règle de méthode.** L'échantillon d'exploration a servi à une seule chose : savoir ce qui est observable, combien de fois, et avec quels trous. Aucun croisement entre une variable explicative et une variable à expliquer n'a été calculé, à une exception près, signalée en §3 (contrat × affichage du salaire), dont l'hypothèse est donc retirée de la liste confirmatoire.
> Les hypothèses retenues seront testées sur un **échantillon de confirmation** : les offres créées **après le 06/10/2026**, collectées pendant 13 semaines (jusqu'au 05/01/2027). Le protocole est gelé par son commit : les règles de codage, les tests, le seuil et la correction ne changent plus quand les données arrivent.

---

## Étape 1 — Audit des données disponibles

### 1.1 Trois constats qui commandent toute la suite

**1. Deux canaux, deux bases.** 226 offres (40 %) sont saisies directement chez France Travail (`origineOffre.origine = 1`) ; 335 (60 %) viennent de sites partenaires (Meteojob, Directemploi, Distrijob…). Les champs structurés n'existent que dans le premier canal :

| Champ | FT (1), n = 226 | Partenaire (2), n = 335 |
|---|---|---|
| qualification | 100 % | 0,3 % |
| taille de l'établissement | 97,8 % | 16,1 % |
| compétences | 95,1 % | 0 % |
| temps plein / partiel | 100 % | 1,2 % |
| « offre manquant de candidats » | 99,6 % | 0 % |
| avantages (`listeComplements`) | 127 offres hors alternance | 0 |
| salaire (champ présent) | 100 % | 32,2 % |
| employeur nommé | 90,3 % | 49,6 % |

Conséquence : ces données ne manquent pas au hasard. L'absence dépend du canal de diffusion. Toute hypothèse qui mobilise la qualification, la taille, les avantages ou le temps de travail ne vaut **que pour les offres saisies chez France Travail** et ne s'étend pas au marché. Le canal sera, partout, une variable de contrôle ou de stratification. Imputer ces valeurs manquantes serait une faute : elles n'ont pas été cachées, elles n'ont jamais existé.

**2. Le salaire bute sur un plancher.** Le plus petit taux horaire affiché est 12,31 € ; ramené à 35 h (× 151,67), il donne 1 867 € par mois, soit 22 405 € par an. C'est le SMIC en vigueur (montant à vérifier sur le décret de revalorisation). 29 % des salaires mensuels et 70 % des salaires horaires affichés (hors alternance) sont à moins de 2 % de ce plancher. La distribution est tronquée à gauche par la loi et présente un pic au SMIC. Cela exclut les tests qui supposent la normalité, donne un rôle central à la médiane et aux quantiles, et suggère un modèle censuré (Tobit) en contrôle de robustesse.

**3. La conversion du site crée un faux écart.** `scripts/resumer.py` multiplie un salaire horaire par 1 607 h (heures travaillées) mais un salaire mensuel par 12 (soit 151,67 h × 12 = 1 820 h payées, congés compris). Au même SMIC, l'horaire donne 19 782 € et le mensuel 22 405 €, soit **−11,7 %**. L'horaire est surreprésenté dans l'intérim (15 offres sur 38 intérims qui affichent un salaire, contre 16 sur 142 en CDI). Sans correction, on « trouverait » un salaire plus bas en intérim qui n'est qu'un artefact de conversion. **Règle de ce protocole : horaire × 1 820.**

### 1.2 Variables, une par une

Taux de remplissage sur les 561 offres d'exploration. « Recodage » renvoie à la règle de construction donnée en §1.3.

| Variable (champ API) | Type | Exploitable ? | Qualité | Biais possibles |
|---|---|---|---|---|
| Intitulé (`intitule`) | texte | recodage (niveau de poste par mots-clés, déjà dans `resumer.py`) | 100 % ; libellés hétérogènes (« conseiller », « téléconseiller », « chargé de clientèle ») | le code ROME est attribué par l'employeur ou l'agence : des postes de vente ou d'accueil sont classés D1415 |
| Description (`description`) | texte | recodage par dictionnaires validés | 100 % ; 135 offres partagent une description identique avec au moins une autre (48 groupes) | modèles de texte copiés-collés ; tronquée à 5 000 caractères ; un mot présent ne dit pas que la chose existe (« télétravail après 6 mois ») |
| Code ROME (`romeCode`) | qualitative nominale | direct (constant ici) | — | erreurs de classement |
| Type de contrat (`typeContrat`) | qualitative nominale (CDI, CDD, MIS = intérim, SAI) | direct | 100 % ; CDI 259, CDD 179, intérim 122, saisonnier 1 | l'alternance est rangée en CDD ou CDI : à isoler par `alternance` |
| Durée du contrat (`typeContratLibelle`) | quantitative discrète (mois) | recodage (« CDD - 12 Mois » → 12 ; jours / 30) | 100 % des CDD / intérims | intérim : durée de mission initiale, souvent renouvelée ; 1 mois très fréquent (54) |
| Nature / alternance (`natureContrat`, `alternance`) | qualitative nominale (binaire) | direct | 88 alternances (80 apprentissages, 8 professionnalisations) | salaire fixé en % du SMIC selon l'âge : **à exclure de toute analyse de salaire** ; des écoles publient des « offres » pour recruter des élèves (22 offres d'un même institut de formation) |
| Expérience exigée (`experienceExige`) | qualitative nominale binaire (E exigée / D débutant accepté) | direct | 100 % ; E 254, D 307 | déclaratif ; « exigée » ne veut pas dire éliminatoire |
| Durée d'expérience (`experienceLibelle`) | qualitative ordinale, ou quantitative discrète en années | recodage (`exp_ans`) | durée connue pour 521 offres ; 40 « Expérience exigée » sans durée | valeurs arrondies (1, 2, 3, 5 ans) ; 58 % de débutants : ex-aequo massifs |
| Formation (`formations`) | qualitative ordinale (< Bac … Bac+5) | recodage | **13,2 %** (74 offres ; 31 % en canal FT) | ceux qui la renseignent ne sont pas un échantillon aléatoire : **inutilisable comme variable explicative principale** |
| Qualification (`qualificationLibelle`) | qualitative ordinale (manœuvre … cadre, codes 1 à 9) | direct, regroupé | canal FT seulement ; employé qualifié 127, non qualifié 57, agent de maîtrise 23, technicien 10, autres 10 | déclaration de l'employeur, pas la grille de la convention collective ; ouvriers et employés ne sont pas sur la même échelle |
| Compétences (`competences`) | liste | **non** | 75 % des offres qui en listent ont exactement le même jeu de 5 compétences : le formulaire les pré-remplit | le nombre de compétences mesure l'usage du formulaire, pas l'exigence du poste |
| Qualités professionnelles | liste (3 au plus) | faible | 26,6 % | choisies dans une liste fermée, peu de variance |
| Langues (`langues`) | binaire | champ trop rare (5,7 %) ; dictionnaire sur la description : 10,3 % | — | une langue citée n'est pas forcément exigée |
| Permis (`permis`) | binaire | faible | 9,4 % | — |
| Déplacements (`deplacementLibelle`) | ordinale (jamais, ponctuels, fréquents) | faible | 18,2 % (canal FT seulement) | — |
| Temps de travail (`dureeTravailLibelleConverti`, heures dans `dureeTravailLibelle`) | binaire, et quantitative (h/semaine) | direct en canal FT | 19 temps partiels seulement | sert à ramener le salaire en équivalent temps plein, pas à tester |
| Salaire (`salaire.libelle`) | quantitative continue | recodage (§1.3) | exploitable pour 226 / 473 offres hors alternance (47,8 %) ; 46 % en fourchette | plancher légal ; erreurs d'unité (« Annuel de 480 à 1 801 € » = mensuel saisi en annuel) ; salaire **affiché**, pas payé ; hors indemnité de précarité de 10 % (CDD, intérim) et congés payés de l'intérim |
| Avantages (`salaire.listeComplements`) | liste → binaires et comptage | recodage | canal FT seulement (127 offres) | certains suivent un seuil légal : CSE dès 11 salariés, participation dès 50, complémentaire santé obligatoire. Les compter mesure en partie la taille |
| Rémunération variable | binaire | recodage (« Primes », « Commissions » dans `listeComplements`, ou « variable », « commission » dans `salaire.commentaire`) | canal FT | « Primes » mélange prime d'objectif et 13e mois : bruit de mesure |
| Employeur (`entreprise.nom`) | nominale (215 noms) / binaire « anonyme » | recodage binaire | nommé : 90 % canal FT, 50 % partenaires | un employeur à plusieurs offres (202 offres : Bricomarché 27, un réseau d'intérim 13) : observations non indépendantes |
| Secteur NAF (`secteurActivite`) | nominale (≈ 90 modalités) | recodage en grands secteurs | 71,7 % | **c'est le secteur de celui qui publie** : 144 offres (25,7 %) sont publiées par une agence d'emploi ou d'intérim (NAF 78). Le secteur de l'entreprise utilisatrice est inconnu pour elles |
| Intermédiation | binaire | recodage : NAF 78 ou contrat MIS | — | variable propre, plus fiable que le secteur |
| Taille de l'établissement (`trancheEffectifEtab`) | qualitative ordinale (11 tranches) | regroupée en 5 classes | 49 % (canal FT) | taille de l'**établissement**, pas de l'entreprise ; pour une agence, taille de l'agence ; « 0 salarié » ambigu (33 offres) |
| Localisation (`lieuTravail`) | nominale (département) | recodage : Île-de-France oui/non ; région | 97 % ; 140 offres en Île-de-France (25 %) | lieu de l'offre, parfois le siège ; 15 offres « France » |
| Télétravail | binaire | dictionnaire sur la description (le site lit seulement le mot « télétravail ») | 8,4 % (47) | mention ≠ droit : « possible après la période d'essai », « 1 jour par mois » ; aucune négation détectée, à vérifier à la main |
| Orientation commerciale | binaire | dictionnaire (objectifs de vente, prospection, télévente, appels sortants…) | 18,4 % (103) | à valider ; même texte que d'autres variables tirées de la description |
| Horaires atypiques | binaire | dictionnaire (samedi, week-end, dimanche) + `contexteTravail.horaires` | 10,7 % | — |
| Offre manquant de candidats (`offresManqueCandidats`) | binaire | direct, canal FT | 32 vraies sur 225 | **définition non documentée** : calculée pour l'offre ou pour le métier × territoire ? À établir avant tout usage |
| Nombre de postes (`nombrePostes`) | quantitative discrète | **non** | 552 offres sur 561 valent 1 | pas de variance |
| Date de création (`dateCreation`) | date | direct | 100 % | `dateActualisation` change sans que l'offre change |
| Durée en ligne | quantitative continue, censurée | recodage : présence quotidienne dans `data/actives/` | 232 offres disparues en 15 jours ; 5 réapparues après une absence | disparaître ≠ être pourvue (annulée, expirée) ; offres créées avant le 22/09 : troncature à gauche |
| Versions d'une offre | quantitative discrète | `data/brut/` garde chaque version | 98 offres modifiées | rare ; à décrire, pas à tester |

### 1.3 Construction des variables recodées (règles gelées)

- **Population salariale** : `natureContrat = "Contrat travail"`, `alternance = false`, contrat ∈ {CDI, CDD, MIS}.
- **Salaire minimum annuel brut** `S` : on lit seulement l'en-tête du libellé (`resumer.salaire_min_max`), puis annuel × 1, mensuel × 12, **horaire × 1 820** ; on garde le bas de la fourchette. Si les heures hebdomadaires *h* sont connues et *h* < 35 : S × 35 / *h* (équivalent temps plein). Valide si S ∈ [0,95 × SMIC annuel ; 150 000 €]. En dessous, la saisie est une erreur ou un temps partiel non déclaré. Robustesse : point milieu de la fourchette, et récupération des « annuel » entre 1 000 et 5 000 € comme mensuels.
- **Au plancher** : S ≤ 1,02 × SMIC annuel (binaire).
- **Salaire affiché** : le libellé commence par « Annuel », « Mensuel » ou « Horaire » (binaire), que le montant soit plausible ou non : afficher est un comportement, la plausibilité est une question de saisie.
- **Expérience** : `experienceExige` (E / D) en principal ; années (`exp_ans`) en secondaire, classes 0 / < 2 ans / 2 ans et plus.
- **Qualification** : employé non qualifié < employé qualifié < technicien ou agent de maîtrise ; ouvriers, manœuvres et cadres exclus (moins de 5 % des offres).
- **Taille** : 0-9 / 10-49 / 50-199 / 200-499 / 500 et plus ; « 0 salarié » et NAF 78 exclus.
- **Dictionnaires** : expressions régulières de `recherche/audit.py`. Avant l'échantillon de confirmation, on tire 120 offres d'exploration (60 positives, 60 négatives selon le dictionnaire). Deux codeurs les lisent sans voir le résultat du dictionnaire, puis on calcule le κ de Cohen entre codeurs et la précision / le rappel du dictionnaire. Seuil : κ ≥ 0,70 et précision ≥ 0,85. Sinon, on corrige le dictionnaire sur l'exploration, jamais sur la confirmation.
  *Exemple de ce que la validation attrape : une première version du dictionnaire « outil CRM nommé » cherchait `sage` ; elle comptait 21 % des offres, à cause de « repassage », « passage en caisse », « apprentissage ». Corrigée, elle en compte 1,2 %.*
- **Unité d'analyse** : l'offre. Les doublons stricts (même intitulé, même employeur, même lieu) sont retirés comme au TD 1. Les offres d'un même employeur restent, avec des erreurs-types groupées par employeur (*cluster* = nom de l'employeur ; employeur anonyme = groupe par empreinte de la description).

---

## Étape 2 — Relations potentielles, et où elles sont testables

| Relation | Toutes offres | Canal FT seul | Base élargie (23 ROME) seulement |
|---|---|---|---|
| contrat ↔ salaire | ✔ | | |
| expérience ↔ salaire | ✔ | | |
| localisation ↔ salaire | ✔ | | |
| qualification ↔ salaire | | ✔ | |
| taille ↔ salaire | | ✔ | |
| contrat ↔ expérience exigée | ✔ (complet) | | |
| anonymat ↔ affichage du salaire | ✔ (complet) | | |
| orientation commerciale ↔ rémunération variable | | ✔ | |
| affichage du salaire ↔ durée en ligne | ✔ (après suivi) | | |
| télétravail ↔ salaire | trop peu (≈ 50 offres avec salaire en 13 semaines) | | ✔ (609 mentions sur 5 276 offres) |
| langue ↔ salaire | trop peu | | ✔ |
| diplôme ↔ salaire | ✘ (13 % renseigné) | ✘ | ✘ |
| nombre de compétences ↔ salaire | ✘ (formulaire pré-rempli) | ✘ | ✘ |
| secteur ↔ salaire | ✘ comme hypothèse (secteur de l'agence) ; ✔ comme contrôle regroupé | | |

Variables de contexte, à contrôler partout : **canal** (FT / partenaire), **intermédiation** (agence, intérim), **Île-de-France**, **semaine de création**, **employeur** (*cluster*).

---

## Étape 3 — Hypothèses candidates

Chaque hypothèse part d'un mécanisme qui la rend plausible. Une hypothèse est d'autant plus intéressante que deux théories y prédisent des signes opposés : le test tranche alors entre elles.

| # | Hypothèse (H1) | Mécanisme / théorie | Verdict |
|---|---|---|---|
| H1 | Le salaire affiché diffère entre CDI, CDD et intérim | différences compensatrices (le temporaire paie plus) **contre** segmentation (le temporaire est le segment secondaire, moins payé) | **Très forte** |
| H2 | Plus l'expérience demandée est longue, plus le salaire affiché est élevé | capital humain **contre** compression par le SMIC | **Forte** : sens attendu, mais la *taille* du gradient près du plancher est la vraie question |
| H3 | Les offres dont l'employeur n'est pas nommé affichent moins souvent un salaire | opacité stratégique / asymétrie d'information ; intermédiaires | **Très forte** |
| H4 | L'affichage du salaire dépend du type de contrat | coût de la transparence selon le segment | **Écartée du confirmatoire** : ce croisement a été vu pendant l'audit (CDI 54 %, CDD 51 %, intérim 31 %). Il devient un contrôle dans le modèle de H3 |
| H5 | Les offres « débutant accepté » sont plus souvent au plancher (SMIC) | le SMIC est contraignant pour les postes d'entrée | Moyenne : redondant avec H2, garder en robustesse |
| H6 | Les offres orientées vente (objectifs, prospection) proposent plus souvent une rémunération variable | théorie de l'agence : on paie au résultat quand le résultat se mesure | **Forte** |
| H7 | À orientation commerciale égale, le fixe est plus bas quand il y a du variable | substitution fixe / variable | Moyenne : puissance faible, variable « Primes » bruitée |
| H8 | Le salaire croît avec la taille de l'établissement | prime de taille (*employer-size wage premium*) | **Forte**, canal FT seulement, puissance limite |
| H9 | Le nombre d'avantages croît avec la taille | politique sociale des grandes entreprises | Faible : en partie tautologique (CSE, participation, mutuelle suivent des seuils légaux) |
| H10 | Le salaire affiché est plus élevé en Île-de-France | prime urbaine, coût de la vie, concurrence entre employeurs | **Forte** |
| H11 | Le salaire diffère selon que l'offre mentionne le télétravail | différence compensatrice (le télétravail se paie par un salaire plus bas) **contre** sélection (le télétravail va aux postes plus qualifiés) | Moyenne pour D1415 (puissance) ; **forte sur la base élargie** |
| H12 | Une langue étrangère demandée est associée à un salaire plus élevé | prime de compétence rare | Moyenne (n) ; base élargie |
| H13 | Les CDI exigent plus souvent de l'expérience que les CDD et l'intérim | filtrage plus sévère quand l'embauche engage dans la durée (coûts de séparation) **contre** productivité immédiate exigée en mission courte | **Très forte** : variables complètes, deux prédictions opposées |
| H14 | Les offres signalées « manquant de candidats » affichent un salaire plus bas | monopsone : un salaire bas attire moins de candidats | Moyenne : définition de l'indicateur inconnue ; si elle est calculée au niveau métier × territoire, l'hypothèse ne porte plus sur l'offre |
| H15 | Les offres qui affichent un salaire disparaissent plus vite | recherche dirigée : un salaire affiché attire plus de candidatures et accélère le recrutement | **Forte** (originale, plus difficile) |
| H16 | Les horaires atypiques (week-end) sont associés à un salaire plus élevé | différence compensatrice | Moyenne : mesure par dictionnaire, souvent « magasin ouvert le samedi » |
| H17 | La qualification déclarée (employé qualifié vs non qualifié) se traduit par un salaire plus élevé | grilles conventionnelles **contre** tassement des premiers niveaux au SMIC | **Forte** ; le résultat nul est ici informatif : test d'équivalence |
| H18 | Plus de compétences demandées → salaire plus élevé | — | **Éliminée** : 75 % des listes sont le même jeu pré-rempli de 5 compétences |
| H19 | Le diplôme demandé est associé au salaire | capital humain, signal | **Éliminée** : 13 % renseigné, sélection forte |
| H20 | Le salaire diffère selon le secteur | — | **Éliminée** comme hypothèse : le secteur observé est celui de l'agence pour un quart des offres ; reste un contrôle |
| H21 | Le temps partiel est moins payé | — | **Éliminée** : 19 cas, et tautologique tant que le salaire n'est pas ramené au temps plein |
| H22 | Le nombre de postes… | — | **Éliminée** : aucune variance |

---

## Étape 4 — Associer le bon test

Principes de choix, valables pour toutes les hypothèses :

- **Salaire** : asymétrique, avec un pic au plancher et beaucoup d'ex-aequo. On utilise des tests de rang (Mann-Whitney, Kruskal-Wallis, Spearman) et une régression sur le logarithme avec erreurs-types robustes. La médiane et les quantiles sont le résumé de référence. Pas de *t* de Student comme test principal.
- **Deux binaires** : Khi² 2 × 2 si tous les effectifs attendus sont ≥ 5, sinon test exact de Fisher. Avec une variable de stratification (le canal) : **Cochran-Mantel-Haenszel**, plus un test de Breslow-Day pour vérifier que l'effet est le même dans chaque strate.
- **Nominale × ordinale** (contrat × expérience) : Khi² en principal, et un modèle logistique ordinal pour le sens et les contrôles.
- **Durée en ligne** : analyse de survie, parce que les offres encore en ligne à la fin de l'étude sont censurées. Un Mann-Whitney sur des durées censurées serait faux.
- **Non-indépendance** : jusqu'à 27 offres d'un même employeur. Tous les modèles prennent des erreurs-types groupées par employeur. Les tests bivariés sont refaits en robustesse avec une seule offre par employeur, tirée au hasard.

Les fiches détaillées sont en §8.2.

---

## Étape 5 — Interpréter, pas seulement « p < 0,05 »

Pour chaque test, le rapport contient :

| Élément | Pourquoi |
|---|---|
| n réellement utilisé (après exclusions), et la trace des exclusions | un test sur 120 offres ne dit pas la même chose qu'un test sur 1 200 |
| statistique de test et p-value exacte (pas « p < 0,05 ») | |
| seuil α = 5 % pour la famille d'hypothèses, corrigé par Holm (§7) | |
| **taille d'effet** avec intervalle de confiance à 95 % (bootstrap groupé par employeur pour les mesures de rang) | c'est la réponse à la question ; la p-value dit seulement si l'on peut écarter le hasard |
| sens de la relation | |
| comparaison à la **plus petite différence qui compte** (SESOI) fixée à l'avance | sépare « significatif » de « important » |
| vérification des conditions | |

**Statistiquement significatif ≠ important en pratique.** Avec 1 000 offres, un écart de salaire médian de 300 € par an (≈ 20 € nets par mois) peut être « significatif » sans rien changer pour un candidat. À l'inverse, avec 60 offres, un écart de 3 000 € peut être « non significatif » sans pour autant être nul. La p-value mêle la taille de l'effet et la taille de l'échantillon. L'intervalle de confiance les sépare.

Seuils d'importance pratique fixés ici, avant de voir les données :

| Grandeur | Plus petite différence qui compte |
|---|---|
| écart de salaire | 5 % du salaire médian (≈ 1 150 € bruts par an, ≈ 75 € nets par mois) |
| écart de proportion (affichage, expérience exigée, variable) | 10 points |
| odds ratio | < 0,67 ou > 1,5 |
| corrélation de rang | \|ρ\| ≥ 0,10 |
| rapport de risques instantanés (survie) | < 0,80 ou > 1,25 |

Quatre lectures possibles :

1. l'IC exclut 0 et dépasse le seuil : effet établi et important ;
2. l'IC exclut 0 mais reste sous le seuil : effet réel, négligeable en pratique ;
3. l'IC contient 0 et reste sous le seuil : absence d'effet important, établie par un **test d'équivalence (TOST)** ;
4. l'IC contient 0 et dépasse le seuil : on ne peut pas conclure, l'échantillon est trop petit.

Ne pas rejeter H0 n'est pas prouver H0. Seul le cas 3 permet d'affirmer « pas de différence qui compte ».

---

## Étape 6 — Régression et contrôles

### 6.1 Pourquoi une régression

Les hypothèses H1, H2, H10, H17 et H8 portent toutes sur le salaire, et leurs X sont liés entre eux : l'intérim est concentré dans les agences, qui publient sans nom d'employeur et affichent à l'heure ; l'Île-de-France a plus de CDI ; les postes « débutant » sont plus souvent en intérim. Un écart brut CDI / intérim peut venir de l'expérience demandée, du lieu ou du canal. Seule une estimation conjointe sépare ces effets. Ce n'est pas un ornement : les tests bivariés et la régression peuvent donner des conclusions opposées, et l'écart entre les deux est un résultat en soi.

### 6.2 Deux modèles, parce que deux bases

**Modèle A — toutes offres salariées avec un salaire valide** (≈ 560 attendues en confirmation) :

ln(S<sub>i</sub>) = β<sub>0</sub> + β<sub>1</sub> CDD<sub>i</sub> + β<sub>2</sub> Intérim<sub>i</sub> + β<sub>3</sub> Exp<sub>i</sub> + β<sub>4</sub> IDF<sub>i</sub> + β<sub>5</sub> Canal<sub>i</sub> + β<sub>6</sub> Agence<sub>i</sub> + β<sub>7</sub> Fourchette<sub>i</sub> + γ<sub>semaine</sub> + ε<sub>i</sub>

**Modèle B — canal FT seulement** (≈ 435 attendues), où l'on ajoute ce qui n'existe que là :

… + β<sub>8</sub> Qualification<sub>i</sub> + β<sub>9</sub> Taille<sub>i</sub> + β<sub>10</sub> Variable<sub>i</sub>

- **Variable dépendante** : ln S. Le logarithme rend les coefficients lisibles en pourcentages et réduit l'asymétrie.
- **Explicatives d'intérêt** : contrat (H1), expérience (H2, en classes pour ne pas imposer une forme linéaire), Île-de-France (H10), qualification (H17), taille (H8).
- **Facteurs de confusion** : canal (il conditionne à la fois l'affichage et le type d'employeur), agence (elle conditionne le contrat et le niveau affiché), fourchette affichée (on prend le bas de fourchette : une offre en fourchette a mécaniquement un minimum plus bas).
- **Lecture d'un coefficient** : 100 × (e<sup>β</sup> − 1) % d'écart de salaire minimum affiché, *toutes choses observées égales par ailleurs*, entre offres, pas entre personnes. β<sub>2</sub> = −0,05 se lit : « à expérience, lieu, canal et intermédiation égaux, une offre d'intérim affiche un salaire minimum inférieur d'environ 4,9 % à celui d'un CDI ». Ce n'est pas « passer en CDI augmente le salaire de 5 % ».
- **Colinéarité attendue** : intérim et agence se recouvrent largement. On contrôle le facteur d'inflation de la variance (VIF > 5 = alerte). Si le recouvrement est quasi total, on garde le contrat et on présente le modèle sans agence, en le disant.

### 6.3 Diagnostics

Résidus en fonction des valeurs prédites (forme, hétéroscédasticité) ; Q-Q plot des résidus ; erreurs-types HC3 groupées par employeur, de toute façon ; VIF ; distances de Cook (refaire sans les 1 % d'offres les plus influentes) ; test RESET de Ramsey ; linéarité de l'expérience (classes contre années).

### 6.4 Robustesse, parce que le plancher déforme la moyenne

1. **Régression quantile** à la médiane et au 3e quartile : l'effet peut n'exister qu'au-dessus du plancher.
2. **Tobit** censuré à gauche au SMIC : le salaire « voulu » de certaines offres est caché par la loi.
3. Hors offres au plancher.
4. Point milieu de la fourchette au lieu du minimum.
5. Une offre par employeur.

Si le signe d'un coefficient change d'une spécification à l'autre, on ne conclut pas.

### 6.5 Ce que la régression ne règle pas

La **sélection** : on observe le salaire de 48 % des offres seulement, et afficher n'est pas aléatoire (c'est l'objet de H3). Un modèle de Heckman exigerait une variable qui joue sur l'affichage sans jouer sur le niveau du salaire. Le canal est candidat, mais rien ne garantit qu'il soit sans effet sur le salaire. On ne le fera donc qu'en analyse de sensibilité, en le disant. Tous les résultats de salaire portent sur **les offres qui affichent un salaire**.

### 6.6 Les modèles logistiques

- **H3** : logit P(salaire affiché) = α + δ<sub>1</sub> Anonyme + δ<sub>2</sub> Contrat + δ<sub>3</sub> Canal + δ<sub>4</sub> Agence + δ<sub>5</sub> Exp + δ<sub>6</sub> IDF.
- **H13** : logit P(expérience exigée).
- **H6** : logit P(rémunération variable).

On rapporte les odds ratios **et** les effets marginaux moyens en points de pourcentage (plus lisibles). Règle : au moins 10 événements par paramètre. Si un groupe est entièrement à 0 ou à 1 (séparation), on passe à une régression logistique de Firth. On vérifie la calibration et l'aire sous la courbe ROC, comme description seulement.

---

## Étape 7 — Stratégie de recherche

```
NIVEAU 0  Audit (fait)             — remplissage, canaux, plancher, conversion, doublons, flux
          Validation des codages   — double codage de 120 offres, κ, précision/rappel des dictionnaires
          GEL DU PROTOCOLE         — commit du 06/10/2026 ; confirmation = offres créées à partir du 07/10/2026

NIVEAU 1  Exploration (échantillon d'exploration, et description de l'échantillon de confirmation)
          fréquences, médianes et quartiles, histogrammes, boîtes par groupe, tableaux croisés
          → sur l'exploration : PAS de test ; on décrit et on prépare le codage

NIVEAU 2  Tests bivariés confirmatoires (échantillon de confirmation)
          9 hypothèses, 1 test principal chacune, correction de Holm sur la famille

NIVEAU 3  Multivarié
          modèles A et B (salaire), logistiques (H3, H6, H13), Cox (H15)
          + robustesse §6.4 ; diagnostics §6.3
```

**Tests multiples.** Neuf tests à 5 % chacun donnent, si toutes les H0 sont vraies, une probabilité d'au moins un faux positif de 1 − 0,95<sup>9</sup> ≈ **37 %**.

- **Famille confirmatoire** (les 9 tests principaux de §8.2) : correction de **Holm-Bonferroni**, avec un risque global d'erreur fixé à 5 %. Holm garantit la même chose que Bonferroni en étant moins sévère. Le test le plus petit est comparé à 0,05 / 9 = 0,0056, le suivant à 0,05 / 8, etc.
- **Analyses secondaires** (comparaisons deux à deux après un Kruskal-Wallis, sous-groupes, versions par dictionnaire, base élargie) : contrôle du taux de fausses découvertes par **Benjamini-Hochberg** (q = 10 %), étiquetées « exploratoires » dans le rapport.
- **Robustesse** : pas de correction. Ce ne sont pas de nouvelles hypothèses mais la même estimée autrement. On rapporte toutes les spécifications, pas la meilleure.
- **Interdit** : ajouter une hypothèse, changer une règle de codage ou un seuil après avoir vu l'échantillon de confirmation. Tout ajout est déclaré « post hoc ».

**Taille de l'échantillon de confirmation** (puissance 80 %, calculée avec `statsmodels`) :

| Test | Effet visé | n nécessaire à α = 5 % | n nécessaire à α = 0,0056 (Holm, 1er rang) |
|---|---|---|---|
| Mann-Whitney, groupes égaux | d = 0,3 | 184 par groupe | 306 par groupe |
| Mann-Whitney, groupes 1:4 | d = 0,3 | 109 + 438 | 182 + 729 |
| Mann-Whitney, groupes égaux | d = 0,5 | 67 par groupe | 111 par groupe |
| Khi², 1 ddl | w = 0,2 | 196 | 327 |
| Khi², 4 ddl | w = 0,1 | 1 194 | 1 842 |
| Spearman | ρ = 0,2 | 206 | 340 |
| Cox, 2 groupes équilibrés | HR = 1,3 | 456 événements | — |
| Cox, 2 groupes équilibrés | HR = 1,5 | 191 événements | — |

Flux observé : 15,2 nouvelles offres D1415 par jour, soit **≈ 1 380 en 13 semaines** (≈ 1 160 hors alternance, ≈ 560 avec un salaire valide, ≈ 535 en canal FT). Ce flux suffit pour des effets moyens (d ≈ 0,3, w ≈ 0,15). Il ne suffit pas pour les petits effets ni pour le télétravail (H11). Pour celui-ci, la base des 23 ROME (≈ 135 nouvelles offres par jour), avec le métier en effet fixe, est la seule option.

---

## Étape 8 — Sortie

### 8.1 Tableau d'ensemble

| # | Hypothèse | Variables | Type de données | Test | H0 | H1 | Intérêt | Difficulté | Priorité |
|---|---|---|---|---|---|---|---|---|---|
| H13 | Contrat ↔ expérience exigée | contrat ; experienceExige | nominale (3) × binaire | Khi² 3 × 2 ; logit | indépendance | association | très fort | faible | **1** |
| H3 | Anonymat ↔ affichage du salaire | employeur nommé ; salaire affiché | binaire × binaire, strate canal | CMH ; logit | OR commun = 1 | OR ≠ 1 | très fort | faible | **1** |
| H1 | Contrat ↔ salaire | contrat ; S | nominale (3) × continue | Kruskal-Wallis ; modèle A | même distribution | au moins un groupe diffère | très fort | moyenne (conversion, précarité) | **1** |
| H10 | Île-de-France ↔ salaire | IDF ; S | binaire × continue | Mann-Whitney ; modèle A | même distribution | décalage | fort | faible | **2** |
| H2 | Expérience ↔ salaire | années ; S | ordinale × continue | Spearman ; modèle A, quantiles | ρ = 0 | ρ ≠ 0 | fort | faible | **2** |
| H17 | Qualification ↔ salaire | employé qualifié / non qualifié ; S | binaire × continue | Mann-Whitney + TOST | même distribution / écart ≥ 5 % | décalage / écart < 5 % | fort | moyenne (canal FT) | **2** |
| H6 | Orientation commerciale ↔ variable | dictionnaire ; listeComplements | binaire × binaire | Khi² ou Fisher ; logit | OR = 1 | OR ≠ 1 | fort | moyenne (validation) | **2** |
| H15 | Affichage du salaire ↔ durée en ligne | salaire affiché ; jours en ligne | binaire × durée censurée | log-rank ; Cox | HR = 1 | HR ≠ 1 | fort | élevée | **2** |
| H8 | Taille ↔ salaire | tranche ; S | ordinale × continue | Jonckheere-Terpstra ; modèle B | pas de tendance | tendance monotone | fort | moyenne (canal FT, n limite) | **3** |
| H11 | Télétravail ↔ salaire | dictionnaire ; S | binaire × continue | Mann-Whitney ; régression, ROME en effet fixe | même distribution | décalage | fort | élevée (mesure) | 3, base élargie |
| H12 | Langue étrangère ↔ salaire | dictionnaire ; S | binaire × continue | Mann-Whitney | idem | idem | moyen | moyenne | 4, base élargie |
| H14 | Manque de candidats ↔ salaire | offresManqueCandidats ; S | binaire × continue | Mann-Whitney | idem | idem | moyen | élevée (définition) | 4 |
| H16 | Horaires atypiques ↔ salaire | dictionnaire ; S | binaire × continue | Mann-Whitney | idem | idem | moyen | moyenne | 4 |
| H7 | Variable ↔ niveau du fixe | variable ; S | binaire × continue | Mann-Whitney | idem | fixe plus bas | moyen | élevée | 4 |
| H5 | Débutant ↔ au plancher | experienceExige ; au plancher | binaire × binaire | Khi² | indépendance | association | moyen | faible | robustesse de H2 |
| H4 | Contrat ↔ affichage | contrat ; salaire affiché | nominale × binaire | Khi² | — | — | — | — | écartée (vue à l'audit) → contrôle |
| H9 | Taille ↔ nombre d'avantages | tranche ; comptage | ordinale × discrète | Spearman | — | — | faible | — | écartée (seuils légaux) |
| H18–H22 | Compétences, diplôme, secteur, temps partiel, nombre de postes | — | — | — | — | — | — | — | **éliminées** (§3) |

### 8.2 Les neuf hypothèses retenues

---

#### H13 — Le type de contrat et l'expérience exigée

1. **Question** : les employeurs filtrent-ils plus sévèrement à l'entrée quand l'embauche est durable ?
2. **H0** : la part d'offres exigeant de l'expérience est la même en CDI, CDD et intérim.
3. **H1** (bilatérale) : elle diffère. Prédiction « filtrage » : CDI > CDD, intérim. Prédiction « productivité immédiate » : intérim > CDI. Le test tranche entre les deux.
4. **Variables** : `typeContrat`, `experienceExige` ; contrôles `origineOffre`, NAF 78, IDF, qualification (modèle B).
5. **Codage** : contrat ∈ {CDI, CDD, intérim} (saisonnier exclu) ; Y = 1 si `experienceExige = "E"` ; population salariale hors alternance. Secondaire : expérience en 3 classes ordonnées (0 / < 2 ans / ≥ 2 ans), « exigée sans durée » exclue.
6. **Test** : Khi² d'indépendance 3 × 2. Puis régression logistique avec contrôles et erreurs groupées par employeur. Secondaire : logistique ordinale (proportional odds) sur les 3 classes.
7. **Conditions** : effectifs attendus ≥ 5 par case (largement remplie) ; indépendance (refaire avec une offre par employeur) ; pour le modèle ordinal, test de Brant de proportionnalité des odds.
8. **n souhaitable** : 241 pour w = 0,2 (385 avec la correction de Holm au 1er rang) ; ≈ 1 160 attendues, ce qui permet de voir w ≈ 0,1.
9. **Effet** : V de Cramér ; différences de proportions CDI − CDD, CDI − intérim avec IC ; OR ajustés ; seuil pratique 10 points.
10. **Contrôles** : canal (le formulaire FT et les sites partenaires ne posent pas la question de la même façon), agence, Île-de-France.
11. **Biais** : « exigée » est déclaratif ; les agences publient des modèles d'offre standard ; un poste en CDD peut déboucher sur un CDI.
12. **Limites** : on mesure l'exigence affichée, pas la sélection réelle. Une association n'établit pas que le contrat *cause* le niveau d'exigence : le type de poste peut déterminer les deux.

---

#### H3 — L'anonymat de l'employeur et l'affichage du salaire

1. **Question** : la transparence est-elle une stratégie d'ensemble, au sens où ceux qui cachent leur nom cachent aussi le salaire ?
2. **H0** : l'odds ratio commun (à canal égal) entre « employeur anonyme » et « salaire affiché » vaut 1.
3. **H1** (bilatérale) : il diffère de 1. Prédiction « opacité » : OR < 1. Prédiction contraire possible : les agences anonymes affichent souvent un taux horaire, d'où OR > 1.
4. **Variables** : `entreprise.nom`, `salaire.libelle`, `origineOffre`, `typeContrat`, NAF 78.
5. **Codage** : X = 1 si aucun nom d'employeur ; Y = 1 si le libellé commence par Annuel / Mensuel / Horaire ; population salariale hors alternance.
6. **Test** : Cochran-Mantel-Haenszel stratifié par canal, plus Breslow-Day (homogénéité de l'OR entre canaux). Puis logit avec contrat, agence, expérience et IDF.
7. **Conditions** : effectifs attendus suffisants dans chaque strate ; si Breslow-Day rejette, on rapporte un OR par canal et non un OR commun.
8. **n souhaitable** : ≈ 345 pour un écart de 15 points (40 % contre 55 %), ≈ 575 avec correction ; ≈ 1 160 attendues.
9. **Effet** : OR de Mantel-Haenszel avec IC ; effet marginal moyen en points de pourcentage ; seuil OR < 0,67 ou > 1,5.
10. **Contrôles** : canal (**confusion majeure** : les offres partenaires sont à la fois plus souvent anonymes, 50 % contre 10 %, et moins souvent dotées d'un champ salaire) ; contrat et agence (H4, vue à l'audit, devient un contrôle).
11. **Biais** : un employeur « anonyme » peut être nommé dans la description, ce qu'on peut vérifier sur un échantillon ; dans le canal partenaire, l'absence de nom ou de salaire peut venir de la conversion du flux plutôt que d'un choix du recruteur.
12. **Limites** : association entre deux comportements de publication. Aucune conclusion sur les intentions du recruteur.

---

#### H1 — Le type de contrat et le salaire affiché

1. **Question** : les emplois temporaires affichent-ils un salaire différent des CDI, et dans quel sens ?
2. **H0** : la distribution de S est la même en CDI, CDD et intérim.
3. **H1** (bilatérale) : au moins un groupe diffère. Différences compensatrices : temporaire > CDI. Segmentation : temporaire < CDI.
4. **Variables** : `typeContrat`, `salaire.libelle`, heures hebdomadaires, contrôles du modèle A.
5. **Codage** : S selon §1.3, **horaire × 1 820** obligatoire.
6. **Test** : Kruskal-Wallis. Si significatif, Dunn deux à deux avec correction de Holm (secondaire). Puis modèle A.
7. **Conditions** : formes de distribution comparables entre groupes pour lire le résultat comme un écart de médianes (à vérifier sur les boîtes ; sinon, lire comme une dominance stochastique) ; ex-aequo au plancher : correction des ex-aequo, et en complément un Khi² sur « au plancher ».
8. **n souhaitable** : ≈ 180 par groupe pour d = 0,3 ; l'intérim affichant peu de salaires, il sera le groupe limitant (≈ 95 attendus).
9. **Effet** : ε² de Kruskal-Wallis ; écarts de Hodges-Lehmann deux à deux en € avec IC ; δ de Cliff ; seuil 5 %.
10. **Contrôles** : expérience, IDF, canal, agence, fourchette.
11. **Biais** : le salaire affiché d'un CDD ou d'un intérim **n'inclut pas l'indemnité de fin de contrat (10 %)**, ni, pour l'intérim, l'indemnité de congés payés (10 %). Un écart de −10 % sur le salaire affiché peut donc correspondre à une rémunération totale *égale*. On rapporte les deux lectures (affiché ; affiché × 1,10 ou × 1,21).
12. **Limites** : salaire affiché, pas salaire payé ; offres qui affichent, pas toutes les offres (§6.5).

---

#### H10 — L'Île-de-France et le salaire

1. **Question** : y a-t-il une prime francilienne sur un métier proche du SMIC ?
2. **H0** : même distribution de S en Île-de-France et ailleurs.
3. **H1** (bilatérale) : décalage de la distribution.
4. **Variables** : département du lieu de travail, S.
5. **Codage** : IDF = départements 75, 77, 78, 91, 92, 93, 94, 95 ; offres « France » exclues.
6. **Test** : Mann-Whitney, puis modèle A (β<sub>4</sub>).
7. **Conditions** : indépendance (*cluster* employeur : les grandes enseignes multi-sites) ; formes de distribution comparables.
8. **n souhaitable** : groupes 1:3, ≈ 140 en IDF et 420 ailleurs pour d = 0,3 ; c'est l'ordre de grandeur attendu.
9. **Effet** : écart de Hodges-Lehmann en € et en %, avec IC ; corrélation rang-bisériale.
10. **Contrôles** : contrat, expérience, canal, agence, taille (modèle B).
11. **Biais** : lieu de l'offre parfois au siège ; plancher national, qui comprime l'écart vers le bas.
12. **Limites** : écart nominal, non corrigé du coût de la vie ; ne dit rien du salaire réel des personnes.

---

#### H2 — L'expérience demandée et le salaire

1. **Question** : quelle est la valeur d'une année d'expérience dans un métier dont le plancher est le SMIC ?
2. **H0** : ρ de Spearman entre années demandées et S égal à 0.
3. **H1** : ρ ≠ 0. On attend ρ > 0 ; la question de recherche porte sur la **pente**.
4. **Variables** : `experienceLibelle` (années), S.
5. **Codage** : débutant = 0, mois / 12 ; « exigée sans durée » exclue (sensibilité : codée 1 an).
6. **Test** : Spearman, avec IC par bootstrap groupé par employeur. Puis régression quantile à la médiane et au 3e quartile, et modèle A.
7. **Conditions** : relation monotone (vérifier sur les médianes par classe) ; nombreux ex-aequo à 0 an (58 %), auxquels le ρ est sensible : on rapporte aussi le τ-b de Kendall.
8. **n souhaitable** : 206 pour ρ = 0,2 (340 après correction) ; ≈ 530 attendues.
9. **Effet** : ρ ; **% de salaire par année demandée** (régression), comparé au seuil de 5 % sur l'écart débutant → 2 ans.
10. **Contrôles** : contrat, IDF, qualification (modèle B).
11. **Biais** : durées arrondies ; « débutant accepté » ne veut pas dire « débutant préféré ».
12. **Limites** : prime à l'exigence affichée, pas rendement de l'expérience réelle des personnes recrutées.

---

#### H17 — La qualification déclarée a-t-elle un prix ?

1. **Question** : « employé qualifié » et « employé non qualifié » sont-ils payés différemment, ou les premiers niveaux sont-ils tassés au SMIC ?
2. **H0** (test de différence) : même distribution. **H0 du test d'équivalence (TOST)** : l'écart de médiane est d'au moins 5 %.
3. **H1** : décalage (Mann-Whitney) / écart compris entre −5 % et +5 % (TOST). C'est l'hypothèse où le résultat « nul » est le plus intéressant, d'où le TOST : sans lui, on ne pourrait rien affirmer.
4. **Variables** : `qualificationLibelle`, S ; canal FT seulement.
5. **Codage** : 127 employés qualifiés et 57 non qualifiés dans l'exploration ; technicien et agent de maîtrise en secondaire (Spearman sur les 3 niveaux ordonnés).
6. **Test** : Mann-Whitney, et TOST sur ln S (deux tests unilatéraux de Welch, ou par bootstrap sur l'écart de Hodges-Lehmann).
7. **Conditions** : comme H1 ; le TOST suppose que la marge de 5 % soit fixée avant (c'est le cas).
8. **n souhaitable** : on attend ≈ 250 employés qualifiés et ≈ 110 non qualifiés avec un salaire valide, de quoi détecter d ≈ 0,35. Pour le TOST à ± 5 %, la précision dépendra de la dispersion : à vérifier sur l'IC obtenu.
9. **Effet** : écart de Hodges-Lehmann en % avec IC à 90 % (lecture TOST) et à 95 %.
10. **Contrôles** : expérience, contrat, IDF, taille.
11. **Biais** : la qualification est choisie par la personne qui saisit l'offre, sans référence obligatoire à la convention collective.
12. **Limites** : canal FT seulement ; ne dit rien des grilles conventionnelles elles-mêmes.

---

#### H6 — L'orientation commerciale et la rémunération variable

1. **Question** : paie-t-on au résultat quand le résultat se mesure (vente, objectifs) ?
2. **H0** : OR = 1 entre orientation commerciale et rémunération variable.
3. **H1** : OR ≠ 1 (attendu : > 1).
4. **Variables** : description (X), `salaire.listeComplements` et `salaire.commentaire` (Y) ; canal FT.
5. **Codage** : X selon le dictionnaire `orientation_commerciale`, **validé** (§1.3). Y tiré **seulement des champs structurés du salaire**, jamais de la description, pour que X et Y ne soient pas lus dans le même paragraphe (biais de méthode commune).
6. **Test** : Khi² 2 × 2 (Fisher si un effectif attendu est < 5) ; puis logit avec contrat, taille, agence.
7. **Conditions** : effectifs attendus ; au moins 10 événements par paramètre dans le logit.
8. **n souhaitable** : avec ≈ 18 % d'offres commerciales et ≈ 535 offres FT, ≈ 95 exposées : on détecte un OR de l'ordre de 2. En dessous, la réponse sera « non concluant ».
9. **Effet** : OR et différence de proportions avec IC.
10. **Contrôles** : contrat, taille, agence.
11. **Biais** : « Primes » mêle prime d'objectif et 13e mois, ce qui ajoute du bruit et pousse vers une absence d'effet ; erreurs du dictionnaire (d'où la validation).
12. **Limites** : association de deux mentions dans une annonce ; on ne sait pas si la part variable est réellement versée.

---

#### H15 — Afficher le salaire et la durée de mise en ligne

1. **Question** : les offres qui affichent un salaire sont-elles retirées plus vite ?
2. **H0** : même fonction de survie en ligne (HR = 1).
3. **H1** : HR ≠ 1 (recherche dirigée : HR > 1, retrait plus rapide).
4. **Variables** : présence quotidienne (`data/actives/`), `dateCreation`, salaire affiché ; contrôles.
5. **Codage** : cohorte des offres **créées** à partir du 07/10 (pas de troncature à gauche). Durée = dernier jour vu − date de création. Événement = absence lors de **deux extractions consécutives** (5 offres sont réapparues après une absence d'un jour). Censure = encore en ligne le 05/01/2027. Les jours sans extraction réussie sont exclus du calcul.
6. **Test** : Kaplan-Meier et log-rank ; Cox avec canal, contrat, agence, IDF ; *cluster* employeur.
7. **Conditions** : proportionnalité des risques (résidus de Schoenfeld ; sinon, Cox stratifié par canal ou effet variable dans le temps) ; censure non informative.
8. **n souhaitable** : 191 événements pour HR = 1,5 ; 456 pour HR = 1,3. Avec ≈ 1 380 offres et 41 % de disparitions en 15 jours, c'est atteignable.
9. **Effet** : HR avec IC ; écart de durée médiane en ligne en jours.
10. **Contrôles** : **canal surtout** (une offre partenaire peut expirer mécaniquement au bout d'un délai fixe), contrat (une mission d'intérim d'un mois se pourvoit vite par nature).
11. **Biais** : disparaître ≠ être pourvue (annulation, expiration, republication sous un autre identifiant) ; la limite de 1 150 offres par requête n'est pas atteinte pour D1415 (≈ 350 actives) mais l'est peut-être pour d'autres métiers.
12. **Limites** : la meilleure interprétation est « durée de vie de l'annonce », pas « délai de recrutement ». C'est l'hypothèse la plus originale du lot, et celle qui demande le plus de prudence.

---

#### H8 — La taille de l'établissement et le salaire

1. **Question** : retrouve-t-on la prime de taille sur ce métier ?
2. **H0** : pas de tendance de S selon la tranche d'effectif.
3. **H1** : tendance monotone (attendue croissante).
4. **Variables** : `trancheEffectifEtab`, S ; canal FT, hors agences (NAF 78).
5. **Codage** : 5 classes (§1.3) ; « 0 salarié » exclu.
6. **Test** : Jonckheere-Terpstra (alternative ordonnée, plus puissant qu'un Kruskal-Wallis ici) ; Spearman en complément ; modèle B.
7. **Conditions** : classes assez remplies (fusionner 200-499 et 500 et plus si moins de 20 offres).
8. **n souhaitable** : 340 pour ρ = 0,2 avec correction ; ≈ 315 attendues. C'est **à la limite**, d'où sa priorité 3 et une collecte prolongée si besoin.
9. **Effet** : ρ, ou τ de Kendall ; écart de médiane entre les classes extrêmes en %.
10. **Contrôles** : qualification, contrat, IDF.
11. **Biais** : taille de l'établissement, pas de l'entreprise (un magasin de 30 salariés d'une enseigne nationale).
12. **Limites** : canal FT seulement ; prime de taille confondue avec le secteur.

---

### 8.3 Ce qu'il reste à faire, dans l'ordre

1. **Corriger la conversion horaire** (× 1 820) ou, au minimum, la recalculer dans le script d'analyse. Sinon, H1 est biaisée d'avance.
2. **Établir la définition de `offresManqueCandidats`** dans la documentation de l'API avant d'envisager H14.
3. **Double codage** de 120 offres d'exploration pour les dictionnaires (télétravail, orientation commerciale, horaires atypiques, langues), puis gel des dictionnaires.
4. **Collecter** jusqu'au 05/01/2027 sans regarder les croisements. On peut contrôler la seule chose qui ne biaise pas les tests : que la collecte tourne et que les effectifs montent (`recherche/audit.py`).
5. **Écrire le script d'analyse confirmatoire avant le 05/01/2027**, puis l'exécuter une fois.
6. **Rapporter tout** : les 9 tests, les effets, les IC, y compris les résultats non significatifs et les cas « non concluants ».

### 8.4 Ce que ces données ne permettront jamais de dire

- **Le marché** : seulement France Travail, sans l'APEC ni LinkedIn. Les postes qualifiés et les cadres sont sous-représentés.
- **Les postes** : on observe des **offres**. Une offre peut couvrir plusieurs postes, ou un même poste plusieurs offres.
- **Les salaires payés** : on observe le salaire **affiché**, par 48 % des offres.
- **Les causes** : aucune variable n'est manipulée ni tirée au hasard. Toutes les conclusions sont des **associations conditionnelles** (« à contrat, lieu et canal égaux, les offres X affichent… »), jamais « X fait augmenter le salaire ».
