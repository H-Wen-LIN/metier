# Double codage de 120 offres D1415 — résultats

Produit par `python recherche/codage/valider.py`. Plan de tirage : `tirer.py` ; grille : `a_coder/CODEBOOK.md`.

## 1. Accord entre les deux codeurs

| Variable | Codées 1 (A / B) | Accord | κ de Cohen | Désaccords | Verdict |
|---|---|---|---|---|---|
| `teletravail` | 19 / 19 | 100 % | 1.00 | 0 | suffisant |
| `langue_etrangere` | 23 / 23 | 100 % | 1.00 | 0 | suffisant |
| `orientation_commerciale` | 51 / 60 | 92 % | 0.85 | 9 | suffisant |
| `horaires_atypiques` | 25 / 24 | 99 % | 0.97 | 1 | suffisant |

Offres marquées « doute » : 29 (A), 31 (B). Seuil retenu au protocole : κ ≥ 0.70.

## 2. Les dictionnaires contre la référence

Référence = le code des deux codeurs quand ils s'accordent, l'arbitrage sinon (`arbitrage.csv`, une raison par décision).

| Variable | Repérées par le dictionnaire (échantillon) | Précision [IC 95 %] | Rappel estimé (pondéré) | κ dictionnaire / référence | Verdict |
|---|---|---|---|---|---|
| `teletravail` | 21 | 81 % [60 % ; 92 %] | 81 % | 0.82 | **à corriger avant la confirmation** |
| | erreurs : n°8 (faux négatif), n°85 (faux positif), n°94 (faux positif), n°100 (faux positif), n°107 (faux négatif), n°108 (faux positif) | | | | |
| `langue_etrangere` | 23 | 100 % [86 % ; 100 %] | 100 % | 1.00 | utilisable |
| `orientation_commerciale` | 26 | 69 % [50 % ; 83 %] | 26 % | 0.21 | **à corriger avant la confirmation** |
| | erreurs : n°2 (faux négatif), n°4 (faux positif), n°7 (faux négatif), n°12 (faux négatif), n°14 (faux positif), n°17 (faux négatif), n°18 (faux positif), n°21 (faux négatif), n°25 (faux négatif), n°26 (faux positif), n°27 (faux négatif), n°28 (faux négatif), n°33 (faux négatif), n°34 (faux négatif), n°37 (faux négatif), n°38 (faux négatif), n°39 (faux négatif), n°41 (faux négatif), n°42 (faux négatif), n°44 (faux négatif), n°46 (faux positif), n°49 (faux négatif), n°50 (faux négatif), n°52 (faux positif), n°53 (faux négatif), n°54 (faux négatif), n°57 (faux négatif), n°62 (faux négatif), n°69 (faux négatif), n°70 (faux négatif), n°73 (faux négatif), n°81 (faux négatif), n°86 (faux négatif), n°95 (faux négatif), n°97 (faux positif), n°98 (faux négatif), n°99 (faux négatif), n°101 (faux négatif), n°102 (faux négatif), n°103 (faux négatif), n°104 (faux négatif), n°113 (faux positif), n°117 (faux négatif), n°118 (faux négatif), n°119 (faux négatif) | | | | |
| `horaires_atypiques` | 26 | 92 % [76 % ; 98 %] | 90 % | 0.93 | utilisable |
| | erreurs : n°6 (faux positif), n°98 (faux positif), n°104 (faux négatif) | | | | |

Seuils du protocole : précision ≥ 85 %, rappel ≥ 70 %. Le rappel combine le taux de faux négatifs des 60 offres qu'aucun dictionnaire ne repère (pondérées par 302) et celui des offres repérées par un autre dictionnaire ; avec si peu de faux négatifs attendus, son incertitude est grande.

## 3. Après correction (même échantillon : estimation optimiste)

| Variable | Vrais positifs | Faux positifs | Faux négatifs | Précision | Rappel (non pondéré) |
|---|---|---|---|---|---|
| `teletravail` v2 | 19 | 0 | 0 | 100 % | 100 % |

`orientation_commerciale` n'a pas de version corrigée : un dictionnaire large (vente, vendre, négocier, prospect, développement commercial…) atteint 96 % de rappel mais 70 % de précision sur cet échantillon. Le concept ne se lit pas dans les mots : il se code par lecture.
